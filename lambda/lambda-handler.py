import boto3
import os

def main(event, context):
    # save event to logs
    print(event)
    jobname = event['Records'][0]['s3']['object']['key'].split('/')[0]
    print(jobname)
    
    client = boto3.client('ecs')
    
    response = client.put_account_setting(
    name='serviceLongArnFormat',
    value='enabled'
    )
    response = client.put_account_setting(
        name='taskLongArnFormat',
        value='enabled'
    )
    response = client.put_account_setting(
        name='containerInstanceLongArnFormat',
        value='enabled'
    )
    
    
    coverrides = { "containerOverrides": [ { "name": "FarOptImage", "environment": [ { "name": "s3key", "value": jobname } ] } ] }
    
    
    
    response = client.run_task(
    cluster=os.environ['cluster_name'], # # name of the cluster
    launchType = os.environ['launch_type'],
    taskDefinition=os.environ['task_family'], # replace with your task definition name and revision
    count = 1,
    startedBy=jobname,
    overrides = coverrides,
    platformVersion='LATEST',
    enableECSManagedTags=True,
    tags=[
        {
            'key': 'jobname',
            'value': jobname
        },
    ],
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