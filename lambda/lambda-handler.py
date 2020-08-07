import boto3
import os

def main(event, context):
    # save event to logs
    print(event)
    print(event['Records'][0]['s3']['object']['key'])
    
    
    coverrides = { "containerOverrides": [ { "name": "FarOptImage", "environment": [ { "name": "s3key", "value": event['Records'][0]['s3']['object']['key'] } ] } ] }
    
    
    client = boto3.client('ecs')
    response = client.run_task(
    cluster=os.environ['cluster_name'], # # name of the cluster
    launchType = os.environ['launch_type'],
    taskDefinition=os.environ['task_family'], # replace with your task definition name and revision
    count = 1,
    overrides = coverrides,
    platformVersion='LATEST',
    networkConfiguration={
        'awsvpcConfiguration': {
            'subnets': [
                os.environ['subnet1'], # replace with your public subnet or a private with NAT
                os.environ['subnet2'] # Second is optional, but good idea to have two
                ],
                'assignPublicIp': 'DISABLED'
        }
        })

    print(response)
    
    return {
        'statusCode': 200,
        'body': "Running task"
    }