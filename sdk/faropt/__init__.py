import boto3
from botocore.exceptions import ClientError
import logging
import os
import zipfile
from datetime import datetime
from uuid import uuid4


class FarOpt(object):
    def __init__(self, framework = 'ortools', stackname = 'faropt'):
        
        # Check if backend stack is launched
        cf = boto3.client('cloudformation')
        try:
            response = cf.describe_stacks(StackName=stackname)
            if response['Stacks'][0]['StackStatus'] in ['CREATE_COMPLETE','UPDATE_COMPLETE']:
                print('FarOpt backend is ready!')
                self.ready = True
                self.stackname = stackname
                self.bucket = response['Stacks'][0]['Outputs'][0]['OutputValue']
                self.configured = False
                self.submitted = False
        except Exception as e:
            self.ready = False
            print(e)
        
        self.allowed_frameworks = ['ortools']
        
        if framework not in self.allowed_frameworks:
            logging.warning("Only ortools is supported for now. You entered "+framework)
            #exit(0)
        else:
            self.framework = framework
    
    def configure (self,source_dir):
        print("Listing project files ...")
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
        print("Configured job!")
        
    def submit(self):
        if self.configured :
            print("Submitting job")
            s3_client = boto3.client('s3')
            try:
                eventid = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')+'-'+str(uuid4())
                response = s3_client.upload_file(self.path_file_name, self.bucket,eventid+'/'+self.file_name)
                print(eventid)
                print("Submitted job!")
                self.jobname = eventid
            except ClientError as e:
                logging.error(e)
                return False
        else:
            logging.error('Please configure the job first!')
            
        self.submitted = True
    
    def primary_status(self):
        
        return self.status()['tasks'][0]['lastStatus']
    
    
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
        
    
    def logs(self, stream=False):
        
        if self.primary_status() in ['STOPPED','DEPROVISIONING','RUNNING']:
            if stream == False:
                taskarn = self.status()['tasks'][0]['taskArn'].split('/')[-1]
                client = boto3.client('logs')
                response = client.get_log_events(
                            logGroupName='faroptlogGroup',
                            logStreamName='faroptlogs/FarOptImage/' + taskarn)
            
                print(response)
            else:
                for ev in self.stream_logs():
                    print(ev)
        else:
            print('Job status: ' + self.primary_status()+ ' | Please wait for job to start running')
    
        
    def status(self):
        if self.submitted:

            client = boto3.client('ecs')
            response1 = client.list_tasks(
                        cluster='FarOptCluster',
                        startedBy=self.jobname)
            
            running_tasks = response1['taskArns']
            
            if running_tasks == []:
                print("No running tasks. Checking completed tasks...")
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