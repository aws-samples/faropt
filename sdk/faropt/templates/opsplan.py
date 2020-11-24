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


class OpsPlanOpt(object):
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
            
  