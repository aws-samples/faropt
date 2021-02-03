import boto3
from botocore.exceptions import ClientError
import logging
from io import StringIO
import pkg_resources
import json
import shutil
import os
from faropt import FarOpt

try:
    from skopt import Optimizer
except ImportError:
    logging.error('Reinstall package using pip install faropt[async] to use this functionality. If you have already done that, try uninstalling and reinstalling scipy')

#import pickle

logging.basicConfig(level=logging.INFO)



class RoutingOpt(object):
    """RoutingOpt class for vehicle routing problem. This class computes a feasible and optimal solution for assigning routes to vehicles, given a set of locations to be visited and vehicle starting locations. The goal of the optimization problem is to minimize the overall distance traveled while making sure each location is visited exactly once.
    """

    def __init__(self, region_name, bucket_name, vehicles_file, locations_file, output_file, max_distance, stackname='faropt'):
        """Constructor method: Gets buckets and tables associated with the already launched stack. In addition it also gets the S3 location and names for data abd output files.
        :param region_name: Name of the S3 bucket region
        :type region_name: string
        :param bucket_name: Name of the S3 bucket
        :type bucket_name: string
        :param vehicles_file: Name (and path) of the csv file with vehicles' starting locations (Lat, Long)
        :type vehicles_file: string
        :param locations_file: Name (and path) of the csv file with locations to be visited (Lat, Long)
        :type locations_file: string
        :param output_file: Name (and path) of the output csv file with final routes computed by the optimizer
        :type output_file: string
        """

        
        # Check if backend stack is launched
        cf = boto3.client('cloudformation')
        try:
            response = cf.describe_stacks(StackName=stackname)
            if response['Stacks'][0]['StackStatus'] in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
                logging.info('FarOpt backend is ready!')
                self.ready = True
                self.stackname = stackname

                outputs = response['Stacks'][0]['Outputs']
                for output in outputs:

                    if output['OutputKey'] == 's3asyncoutput':
                        self.asyncbucket = output['OutputValue']
                        logging.info('Async Bucket: ' + self.asyncbucket)

                    if output['OutputKey'] == 's3output':
                        self.bucket = output['OutputValue']
                        logging.info('Bucket: ' + self.bucket)

                    if output['OutputKey'] == 'recipetable':
                        self.recipetable = output['OutputValue']
                        logging.info('Recipe Table: ' + self.recipetable)

                    if output['OutputKey'] == 'jobtable':
                        self.jobtable = output['OutputValue']
                        logging.info('Job table: ' + self.jobtable)
            
            main_file = pkg_resources.resource_filename('faropt', 'data/routing/main.py')
            
            

        except Exception as e:
            self.ready = False
            logging.error(e)
            
    
        #Copy the generic main file of routing
        os.makedirs(os.path.dirname('/tmp/src/'), exist_ok=True)
        shutil.copy(main_file, '/tmp/src/')
        
        #Write inputs into JSON
    
        # Data to be written  
        inputdict ={  
            "region_name" : region_name,  
            "bucket_name" : bucket_name,  
            "vehicles_file" : vehicles_file,  
            "locations_file" : locations_file,
            "output_file": output_file,
            "max_distance": max_distance
        }  
             
        with open("/tmp/src/inputs.json", "w") as outfile:  
            json.dump(inputdict, outfile) 
            
    def submit(self,micro=False):
        fo = FarOpt()
        fo.configure('/tmp/src')
        fo.submit(micro=micro)
        return fo