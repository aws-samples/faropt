import boto3
from botocore.exceptions import ClientError
import logging
import os
import zipfile
from datetime import datetime, timedelta
from uuid import uuid4
import time
import base64
import json

logging.basicConfig(level=logging.INFO)


class FarOpt(object):
    """FarOpt class used to initialize, configure and submit jobs to the back end
    :param framework: Currently only ortools, TO DO is to extend to other frameworks. Note that other frameworks like pyomo, DEAP, inspyred and pulp are supported
    :type framework: string, optional
    :param stackname: Points to the backend CDK stack that needs to be launched separately. Default name is faropt, but you many need to pass in another name while testing
    :type stackname: string, optional 
    """
    def __init__(self, framework = 'ortools', stackname = 'faropt'):
        """Constructor method: Gets buckets and tables associated with the already launched stack
        """
        # Check if backend stack is launched
        cf = boto3.client('cloudformation')
        try:
            response = cf.describe_stacks(StackName=stackname)
            if response['Stacks'][0]['StackStatus'] in ['CREATE_COMPLETE','UPDATE_COMPLETE']:
                logging.info('FarOpt backend is ready!')
                self.ready = True
                self.stackname = stackname
                
                outputs = response['Stacks'][0]['Outputs']
                for output in outputs:
                    
                    if output['OutputKey']=='s3asyncoutput':
                        self.asyncbucket = output['OutputValue']
                        logging.info('Async Bucket: ' + self.asyncbucket)
                    
                    if output['OutputKey']=='s3output':
                        self.bucket = output['OutputValue']
                        logging.info('Bucket: ' + self.bucket)
                    
                    if output['OutputKey']=='recipetable':
                        self.recipetable = output['OutputValue']
                        logging.info('Recipe Table: ' + self.recipetable)
                    
                    if output['OutputKey']=='jobtable':
                        self.jobtable = output['OutputValue']
                        logging.info('Job table: ' + self.jobtable)
                    
                    if output['OutputKey']=='lambdaopt':
                        self.lambdaopt = output['OutputValue']
                        logging.info('Lambda Opt function: ' + self.lambdaopt)
                        
                        
                
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
        """Zips up a local folder containing your main.py code, and any other subfolders/files required to run your project. Make note of the output structure printed to see if all files that you need are printed.ArithmeticError
        
        :param source_dir: path to your source, such as './home/src/'
        :type source_dir: string
        """
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
        
    def add_recipe(self,recipe_name,maintainer='Faropt SDK user'):
        """Adds a recipe referencing the job that you submitted (see self object params). 
        
        :param recipe_name: Friendly name for your recipe
        :type recipe_name: string
        :param maintainer: Recipe author/maintainer
        :type source_dir: string, optional. Defaults to 'Faropt SDK User'
        """
        if self.configured:
            self.ddb_resource = boto3.resource('dynamodb')
            self.ddb_table = self.ddb_resource.Table(self.recipetable)
            UID = str(uuid4())
            job = {
                'recipeid': UID,
                'description':recipe_name,
                'bucket': self.bucket,
                'path': self.jobname+'/'+self.file_name,
                'maintainer':maintainer,
                'code':'see path'
            }
                
            self.ddb_table.put_item(Item=job)
            
        else:
            logging.error('Please configure the job first!')
            
    def run_s3_job(self, bucket, key, micro=False):
        """Runs job based on a source file in bucket/key. For example, place a source.zip in s3://bucket/key/source.zip and submit a job
        
        :param bucket: Bucket name
        :type bucket: string
        :param key: path/key on S3 that looks like path/to/s3/key/source.zip inside the bucket
        :type key: string
        :param micro: Submit a micro job. 
        :type micro: bool
        """
        
        logging.info("Downloading source...")
        s3 = boto3.client('s3')
        with open('/tmp/source.zip', 'wb') as f:
            s3.download_fileobj(bucket, key, f)
            
        self.path_file_name = os.path.abspath('/tmp/source.zip')
        self.file_name = 'source.zip'
        logging.info("Configured job!")
        self.configured = True
        if micro:
            self.stage()
            
        self.submit(micro = micro)
        
    def get_recipe_id_from_description(self, description):
        """Returns UUID of a recipe based on friendly description/ recipe name
        
        :param description: friendly description/ recipe name
        :type description: string
        :return: First UUID that matches the description of the recipe
        :rtype: uuid4()
        """
        self.list_recipes(verbose=False)
        for r in self.recipes:
            if r['description'] == description:
                return r['recipeid']
        
        
    def run_recipe(self, recipe_id):
        """Runs already registered recipe
        
        :param recipe_id: UUID of recipe
        :type recipe_id: string
        """
        try:
            self.ddb_resource = boto3.resource('dynamodb')
            self.ddb_table = self.ddb_resource.Table(self.recipetable)

            response = self.ddb_table.get_item(Key={'recipeid': recipe_id})
            path = response['Item']['path']
            bucket = response['Item']['bucket']
            
            logging.info("Downloading recipe...")
            s3 = boto3.client('s3')
            with open('/tmp/source.zip', 'wb') as f:
                s3.download_fileobj(bucket, path, f)
            
            self.path_file_name = os.path.abspath('/tmp/source.zip')
            self.file_name = 'source.zip'
            logging.info("Configured job!")
            self.configured = True
            self.submit()
        
        except ClientError as e:
                logging.error(e)
                return False
        
        
    def wait(self):
        """Polls for the primary status of the container task that runs this job. You should see PROVISIONING > PENDING > RUNNING > STOPPED > JOB COMPLETED

        :return: primary status of the job that was submitted
        :rtype: list
        """
        while self.primary_status()!='STOPPED':
            print(self.primary_status())
            time.sleep(3)
            
        logging.info("JOB COMPLETED!")
        
        
    def stage(self):
        """Uploads the source.zip but does not submit to fargate. Useful when you want to run later
        """
        logging.info("Staging job")
        s3_client = boto3.client('s3')
        try:
            eventid = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')+'-'+str(uuid4())
            response = s3_client.upload_file(self.path_file_name, self.asyncbucket,'staged/'+eventid+'/source.zip')
            
            logging.info("Staged job! id: " + str(eventid))

            self.jobname = eventid
            self.stagedkey = 'staged/'+eventid
    
            logging.info(f"Look for s3://{self.asyncbucket}/staged/{self.jobname}/source.zip")
        except:
            logging.error("Could not stage job")
        
        
    def submit(self, micro=False):
        """Runs job defined in object params. Creates a new job ID to track and sets submitted to True. Check self.jobname to reference the job that was submitted. View self.logs() once the job has completed
        
        :param micro: Submit a micro job. By submitting a micro job, you are restricted to using ortools, pyomo and deap libraries for jobs that last up to 5 minutes
        :type micro: bool
        """
        if self.configured :
            logging.info("Submitting job")
            s3_client = boto3.client('s3')
            self.ddb_resource = boto3.resource('dynamodb')
            self.ddb_table = self.ddb_resource.Table(self.jobtable)
            
            if not micro:
                try:
                    self.micro = False
                    eventid = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')+'-'+str(uuid4())
                    response = s3_client.upload_file(self.path_file_name, self.bucket,eventid+'/source.zip')
                    
                    logging.info("Submitted job! id: " + str(eventid))
                    
                    self.jobname = eventid
                    
                    # Add job to dynamoDB
                    job = {
                    'jobid': self.jobname,
                    'bucket': self.bucket,
                    'path': eventid+'/source.zip'}
                    
                    self.ddb_table.put_item(Item=job)
                except ClientError as e:
                    logging.error(e)
                    return False
            
            else:
                try:
                    self.stage()
                    self.micro = True
                    logging.info("By submitting a micro job, you are restricted to using ortools, pyomo and deap libraries for jobs that last up to 5 minutes")
                    lamclient = boto3.client("lambda")
                    response = lamclient.invoke(
                        FunctionName=self.lambdaopt,
                        InvocationType='RequestResponse',
                        LogType='Tail',
                        Payload=json.dumps({'s3bucket':self.asyncbucket,'s3key':self.stagedkey}).encode())
                        
                    # Add job to dynamoDB
                    job = {
                    'jobid': self.stagedkey,
                    'bucket': self.asyncbucket,
                    'path': self.stagedkey+'/source.zip'}
                    
                    self.ddb_table.put_item(Item=job)
                    
                    base64_message = response['LogResult']
                    print(base64.b64decode(base64_message.encode()).decode())
                    self.micrologs = base64.b64decode(base64_message.encode()).decode()
                    
                except ClientError as e:
                    logging.error(e)
                    return False
            
        else:
            logging.error('Please configure the job first!')
            
        self.submitted = True
    
    def list_recipes(self, limit=10, verbose=True):
        """Returns list of recipes registered
        
        :param limit: Number of recipes to return, Defaults to 10
        :type limit: int, optional
        :param verbose: Verbose print of the recipe table, Defaults to True
        :type verbose: bool, optional
        :return: Recipe table scan (raw) results
        :rtype: boto3 response
        """
        ddb_client = boto3.client('dynamodb')
        
        response = ddb_client.scan(
            TableName=self.recipetable,
            Limit=limit)
        
        allrecipes = []
        for job in response['Items']:
            allrecipes.append({'recipeid':job['recipeid']['S'], 'bucket':job['bucket']['S'], 'path':job['path']['S'], 'description':job['description']['S'], 'maintainer':job['maintainer']['S'], 'code':job['code']['S']})
            if verbose:
                print(f"recipeid:{job['recipeid']['S']} | bucket:{job['bucket']['S']} | path:{job['path']['S']} | description:{job['description']['S']} | maintainer:{job['maintainer']['S']}")
        self.recipes = allrecipes
        
        return response
                  
    def list_jobs(self, limit=10, verbose=True):
        """Returns list of jobs submitted
        
        :param limit: Number of jobs to return, Defaults to 10
        :type limit: int, optional
        :param verbose: Verbose print of the job table, Defaults to True
        :type verbose: bool, optional
        :return: job table scan (raw) results
        :rtype: boto3 response
        """
        ddb_client = boto3.client('dynamodb')
        
        response = ddb_client.scan(
            TableName=self.jobtable,
            Limit=limit)
        
        alljobs = []
        for job in response['Items']:
            alljobs.append({'jobid':job['jobid']['S'], 'bucket':job['bucket']['S'], 'path':job['path']['S']})
            if verbose:
                print(f"jobid:{job['jobid']['S']} | bucket:{job['bucket']['S']} | path:{job['path']['S']}")
        
        self.jobs = alljobs
        
        return response

    
    def stream_logs(self,start_time=0, skip=0):
        """Internal, use self.logs() instead of streaming
        """
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
        """Stops a submitted task
        """
        # if self.primary_status() in ['STOPPED','DEPROVISIONING','RUNNING']:
        if self.submitted and self.micro==False:
            client = boto3.client('ecs')
            taskarn = self.status()['tasks'][0]['taskArn'].split('/')[-1]
            response = client.stop_task(
                cluster='FarOptCluster',
                task=taskarn,
                reason='User stopped task'
                )
        else:
            logging.info("Please ensure you have submitted a non-micro job")
        # else:
        #     logging.info('Job status: ' + self.primary_status())
            
    
    def printlogs(self,response):

        for ev in response['events']:
            print(str(ev['timestamp']) + ' | ' + ev['message'])
    
    def logs(self):
        """Prints logs of a submitted job. 
        """
        if self.primary_status() in ['STOPPED','DEPROVISIONING','RUNNING']:
            if self.micro == False:
                taskarn = self.status()['tasks'][0]['taskArn'].split('/')[-1]
                client = boto3.client('logs')
                response = client.get_log_events(
                            logGroupName='faroptlogGroup',
                            logStreamName='faroptlogs/FarOptImage/' + taskarn)
                
                self.printlogs(response)
            
            else:
                print(self.micrologs)

        else:
            print('Please wait for the task to start running | ' + self.primary_status())
                
                
    def primary_status(self):
        """Returns the last status of the submitted job; Can be PROVISIONING > PENDING > RUNNING > STOPPED > JOB COMPLETED 
        
        :return: primary staus
        :rtype: string
        """
        if self.micro == False:
            return self.status()['tasks'][0]['lastStatus']
        else:
            return 'STOPPED'
        
    def status(self):
        """Returns the full status of the submitted job; used in primary_status, which should be enough for most use cases
        """
        if self.submitted and self.micro==False:

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
            logging.error("Please submit a non-micro job first!")
                      
    def get_metric_data(self,metric_name):
        """Returns raw metric data that was submitted from the backend. To use this, do from utils import * in your main.py, and then use log_metric like this, for e.g: log_metric('total_distance',total_distance)
        
        :return: response from cloudwatch 
        :rtype: json string
        """

        cloudwatch = boto3.resource('cloudwatch')
        metric = cloudwatch.Metric('FarOpt',metric_name)

        response = metric.get_statistics(
        Dimensions=[
            {
                'Name': 'jobid',
                'Value': self.jobname
            },
        ],
        StartTime=datetime.now() - timedelta(minutes=24),
        EndTime=datetime.now(),
        Period=1,Statistics=['Average','Minimum','Maximum'])

        return response