import boto3
from botocore.exceptions import ClientError
import logging
import os
import zipfile
from datetime import datetime
from uuid import uuid4
import time

logging.basicConfig(level=logging.INFO)


class FarOpt(object):
    def __init__(self, framework = 'ortools', stackname = 'faropt'):
        
        # Check if backend stack is launched
        cf = boto3.client('cloudformation')
        try:
            response = cf.describe_stacks(StackName=stackname)
            if response['Stacks'][0]['StackStatus'] in ['CREATE_COMPLETE','UPDATE_COMPLETE']:
                logging.info('FarOpt backend is ready!')
                self.ready = True
                self.stackname = stackname
                self.bucket = response['Stacks'][0]['Outputs'][0]['OutputValue'] # S3 bucket
                self.jobtable = response['Stacks'][0]['Outputs'][2]['OutputValue'] # DynamoDB table for jobs
                self.recipetable = response['Stacks'][0]['Outputs'][1]['OutputValue'] # DynamoDB table for recipes
                self.configured = False
                self.submitted = False
        except Exception as e:
            self.ready = False
            logging.error(e)
        
        self.allowed_frameworks = ['ortools']
        
        if framework not in self.allowed_frameworks:
            logging.warning("Only ortools is supported for now. You entered "+framework)
            #exit(0)
        else:
            self.framework = framework
    
    def configure (self,source_dir):
        logging.info("Listing project files ...")
        file_name = "source.zip"
        zf = zipfile.ZipFile("source.zip", "w")
    
        for dirname, subdirs, files in os.walk(source_dir):
            #zf.write(dirname)
            print(dirname, subdirs, files)
            for filename in files:
                print(filename)
                zf.write(os.path.join(dirname,filename),os.path.relpath(dirname+'/'+filename,source_dir))
        zf.close()
        
        self.path_file_name = os.path.abspath(file_name)
        self.file_name = file_name
            
        self.configured = True
        logging.info("Configured job!")
        
    def submit(self):
        if self.configured :
            logging.info("Submitting job")
            s3_client = boto3.client('s3')
            self.ddb_resource = boto3.resource('dynamodb')
            self.ddb_table = self.ddb_resource.Table(self.jobtable)
            
            try:
                eventid = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')+'-'+str(uuid4())
                response = s3_client.upload_file(self.path_file_name, self.bucket,eventid+'/'+self.file_name)
                
                logging.info("Submitted job! id: " + str(eventid))

                self.jobname = eventid
                
                # Add job to dynamoDB
                job = {
                'jobid': self.jobname,
                'bucket': self.bucket,
                'path': eventid+'/'+self.file_name}
                
                self.ddb_table.put_item(Item=job)
                
                
            except ClientError as e:
                logging.error(e)
                return False
        else:
            logging.error('Please configure the job first!')
            
        self.submitted = True
    
    def list_jobs(self, limit=10):
        ddb_client = boto3.client('dynamodb')
        
        response = ddb_client.scan(
            TableName=self.jobtable,
            Limit=limit)
        
        alljobs = []
        for job in response['Items']:
            alljobs.append({'jobid':job['jobid']['S'], 'bucket':job['bucket']['S'], 'path':job['path']['S']})
            print(f"jobid:{job['jobid']['S']} | bucket:{job['bucket']['S']} | path:{job['path']['S']}")

    
    def stream_logs(self,start_time=0, skip=0):
        #def log_stream(client, log_group, stream_name, start_time=0, skip=0): from SM stream logs

        next_token = None
    
        event_count = 1
        while event_count > 0:
            if next_token is not None:
                token_arg = {"nextToken": next_token}
            else:
                token_arg = {}
            
            taskarn = self.status()['tasks'][0]['taskArn'].split('/')[-1]
            client = boto3.client('logs')
                        
            response = client.get_log_events(
                logGroupName='faroptlogGroup',
                logStreamName='faroptlogs/FarOptImage/' + taskarn,
                startTime=start_time,
                startFromHead=True,
                **token_arg
            )
            
            next_token = response["nextForwardToken"]
            events = response["events"]
            event_count = len(events)
            if event_count > skip:
                events = events[skip:]
                skip = 0
            else:
                skip = skip - event_count
                events = []
            for ev in events:
                yield ev
     
    
    def stop(self):
        # if self.primary_status() in ['STOPPED','DEPROVISIONING','RUNNING']:
        client = boto3.client('ecs')
        taskarn = self.status()['tasks'][0]['taskArn'].split('/')[-1]
        response = client.stop_task(
            cluster='FarOptCluster',
            task=taskarn,
            reason='User stopped task'
            )
        # else:
        #     logging.info('Job status: ' + self.primary_status())
            
    
    def printlogs(self,response):

        for ev in response['events']:
            print(str(ev['timestamp']) + ' | ' + ev['message'])
    
    def logs(self):

        if self.primary_status() in ['STOPPED','DEPROVISIONING','RUNNING']:
            taskarn = self.status()['tasks'][0]['taskArn'].split('/')[-1]
            client = boto3.client('logs')
            response = client.get_log_events(
                        logGroupName='faroptlogGroup',
                        logStreamName='faroptlogs/FarOptImage/' + taskarn)
            
            self.printlogs(response)

        else:
            print('Please wait for the task to start running | ' + self.primary_status())
                
                
    def primary_status(self):
        return self.status()['tasks'][0]['lastStatus']
        
    def status(self):
        if self.submitted:

            client = boto3.client('ecs')
            response1 = client.list_tasks(
                        cluster='FarOptCluster',
                        startedBy=self.jobname)
            
            running_tasks = response1['taskArns']
            
            if running_tasks == []:
                logging.info("No running tasks. Checking completed tasks...")
                #check if stopped tasks exist
                response1 = client.list_tasks(
                        cluster='FarOptCluster',
                        startedBy=self.jobname,
                        desiredStatus='STOPPED')
                        
                stopped_tasks = response1['taskArns']
                        
            response = client.describe_tasks(cluster='FarOptCluster',
            tasks=[response1['taskArns'][0]])
            
            return response
                        
        else:
            logging.error("Please submit a job first!")