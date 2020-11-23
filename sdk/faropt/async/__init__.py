import boto3
from botocore.exceptions import ClientError
import logging
import os
import zipfile
from datetime import datetime, timedelta
from uuid import uuid4
import time
try:
    from skopt import Optimizer
except ImportError:
    logging.error('Reinstall package using pip install faropt[async] to use this functionality. If you have already done that, try uninstalling and reinstalling scipy')

import pickle

logging.basicConfig(level=logging.INFO)


class AsyncOpt(object):
    def __init__(self, stackname = 'faropt'):
        
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
                

        except Exception as e:
            self.ready = False
            logging.error(e)
            
    
    def update_model(self, modelname, opt):
        with open('/tmp/model.pkl', 'wb') as f:
            pickle.dump(opt, f)
        
        s3_client = boto3.client('s3')
        response = s3_client.upload_file('/tmp/model.pkl', self.asyncbucket, modelname+'/model.pkl')
        logging.info('Updated model!')
        
    
    def create_model(self, bounds, modeltag=''):
        self.modelname = str(uuid4())
        
        if all(isinstance(item, tuple) for item in bounds):
            logging.info('Creating model with bounds: ' + str(bounds))
        
            opt = Optimizer(bounds, "GP", acq_func="EI",acq_optimizer="sampling",initial_point_generator="lhs")
            
            self.update_model(self.modelname, opt)
            
            logging.info('created model with name '+ self.modelname)
            
            if modeltag!='':
                s3_client = boto3.client('s3')
                response = s3_client.put_object_tagging(
                    Bucket=self.asyncbucket,
                    Key=self.modelname+'/model.pkl',
                    Tagging={
                        'TagSet': [
                            {
                                'Key': 'tag',
                                'Value': modeltag
                            },]})
            
            return self.modelname
        else:
            logging.error('Input bounds as a list of tuples, like [(-2.0, 2.0), ...]')
        
        
    def ask_model(self, modelname):
        s3_client = boto3.client('s3')
        response = s3_client.download_file(self.asyncbucket,self.modelname+'/model.pkl','/tmp/model.pkl')
        
        with open('/tmp/model.pkl', 'rb') as f:
            opt_restored = pickle.load(f)
        
        self.model = opt_restored
        # self.update_model(self.modelname, self.model)
            
        return opt_restored.ask()
        
        
        
    def tell_model(self, modelname, xval, fval):
        s3_client = boto3.client('s3')
        response = s3_client.download_file(self.asyncbucket,self.modelname+'/model.pkl','/tmp/model.pkl')
        
        with open('/tmp/model.pkl', 'rb') as f:
            opt_restored = pickle.load(f)
        
        self.model = opt_restored
        res = opt_restored.tell(xval, fval)
        self.update_model(self.modelname, self.model)
        
        return res
        
    def list_models(self):
        bucket = self.asyncbucket

        client = boto3.client('s3')
        result = client.list_objects(Bucket=bucket,Delimiter='/model.pkl')
        for o in result.get('CommonPrefixes'):
            tmpprefix = o.get('Prefix')
            
            response = client.get_object_tagging(Bucket=self.asyncbucket,Key=tmpprefix)
            
            if response['TagSet']==[]:
                print('model ', ' <None> :', tmpprefix)
            else:
                print('model ', response['TagSet'][0]['Value'], ':', tmpprefix)
        
        
        