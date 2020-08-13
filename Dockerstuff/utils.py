import boto3
import os

cw = boto3.client('cloudwatch')
s3 = boto3.client('s3')

def save(filename):
    print('Saving ' + filename + ' to s3://'+ os.environ['s3bucket'] + '/' + os.environ['s3key'])
    
    response = s3.upload_file(filename, os.environ['s3bucket'], os.environ['s3key']+'/output/' + filename.split('/')[-1])
    
    print(response)

def log_metric(key,value):
    response = cw.put_metric_data(
        MetricData = [
            {
                'MetricName': key,
                'Dimensions': [
                    {
                        'Name': 'jobid',
                        'Value': os.environ['s3key']
                    }
                ],
                'Unit': 'None',
                'Value': value
            },
        ],
        Namespace='FarOpt'
    )