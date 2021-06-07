from aws_cdk import (
    aws_iam as iam,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_ec2 as ec2,
    aws_logs as logs,
    aws_servicediscovery as sd,
    aws_sns_subscriptions as subs,
    core,
    aws_ecs as ecs,
    aws_lambda as _lambda,
    aws_s3 as _s3,
    aws_s3_notifications,
    aws_dynamodb as ddb
)

import boto3
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

class FaroptStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Build and push faropt container
        dockercontainer = ecs.ContainerImage.from_asset(directory = 'Dockerstuff', build_args=['-t faropt .'])
        
        # Create vpc
        vpc = ec2.Vpc(self, 'MyVpc', max_azs=3)     # default is all AZs in region
        subnets = vpc.private_subnets

        # Create log groups for workers
        w_logs = logs.LogGroup(self, 'faroptlogGroup', log_group_name='faroptlogGroup')
        
        # #Create role for ECS
        nRole = iam.Role(self,'ECSExecutionRole',
            assumed_by = iam.ServicePrincipal('ecs-tasks'))
        
        nPolicy = iam.Policy(
            self,
            "ECSExecutionPolicy",
            policy_name = "ECSExecutionPolicy",
            statements = [iam.PolicyStatement(actions = 
                ['ecr:BatchCheckLayerAvailability',
                'ecr:GetDownloadUrlForLayer',
                'ecr:BatchGetImage',
                'ecr:GetAuthorizationToken',
                'logs:CreateLogStream',
                'logs:PutLogEvents','sagemaker:*','s3:*','cloudwatch:PutMetricData'], resources=['*',]),]).attach_to_role(nRole)


        # Create ECS cluster
        cluster = ecs.Cluster(self, 'FarOptCluster', 
            vpc=vpc, cluster_name='FarOptCluster')

        nspace = cluster.add_default_cloud_map_namespace(name='local-faropt',type=sd.NamespaceType.DNS_PRIVATE,vpc=vpc)
        
        # create s3 bucket
        
        s3 = _s3.Bucket(self, "s3bucket")
        s3async = _s3.Bucket(self, "s3async")
        
        # 
        pkey1 = ddb.Attribute(name='jobid', type=ddb.AttributeType.STRING)
        jobtable = ddb.Table(self,"FaroptJobTable", table_name='FaroptJobTable',partition_key=pkey1)#,
        
        pkey2 = ddb.Attribute(name='recipeid', type=ddb.AttributeType.STRING)
        recipetable = ddb.Table(self,"FaroptRecipeTable", table_name='FaroptRecipeTable',partition_key=pkey2)#,
        # billing_mode=None, encryption=None, encryption_key=None,
        # point_in_time_recovery=None, read_capacity=None, removal_policy=None,
        # replication_regions=None, server_side_encryption=None,
        # sort_key=None, stream=None, time_to_live_attribute=None, write_capacity=None)
        
        # -------------------- Add worker task ------------------------
        
        faroptTask = ecs.TaskDefinition(self, 'taskDefinitionScheduler',
            cpu='4096', memory_mib='16384',network_mode=ecs.NetworkMode.AWS_VPC,
            placement_constraints=None, execution_role=nRole,
            family='Faropt-Scheduler', task_role=nRole, compatibility = ecs.Compatibility.FARGATE)

        faroptTask.add_container('FarOptImage', image=dockercontainer, cpu=4096,
        memory_limit_mib=16384, memory_reservation_mib=16384,environment={'s3bucket':s3.bucket_name},
        logging=ecs.LogDriver.aws_logs(stream_prefix='faroptlogs',log_group = w_logs))
            
        
        
        # ------------------------------------------------------
        # Try to trigger a fargate task from Lambda on S3 trigger
        
        # create lambda function
        function = _lambda.Function(self, "lambda_function",
                                    runtime=_lambda.Runtime.PYTHON_3_7,
                                    handler="lambda-handler.main",
                                    code=_lambda.Code.asset("./lambda"),
                                    environment= {
                                        'cluster_name': cluster.cluster_name,
                                        'launch_type':'FARGATE',
                                        'task_definition':faroptTask.to_string(),
                                        'task_family':faroptTask.family,
                                        'subnet1':subnets[0].subnet_id,
                                        'subnet2':subnets[-1].subnet_id,
                                        'bucket':s3.bucket_name
                                    },
                                    initial_policy = [iam.PolicyStatement(actions=['ecs:RunTask','ecs:PutAccountSetting','s3:*','iam:PassRole'],resources=['*'])])
        
        

        # create s3 notification for lambda function
        notification = aws_s3_notifications.LambdaDestination(function)

        # assign notification for the s3 event type (ex: OBJECT_CREATED)
        s3.add_event_notification(_s3.EventType.OBJECT_CREATED, notification)
        
        
        # Lambda opt function with layer
        
        # 1- create layer
        
        layercode2 = _lambda.Code.from_asset(path="./layers/orblacknp.zip") # adding np to the layer
        layer2 = _lambda.LayerVersion(self,id="layer2",code=layercode2)
        
        # 2- create function
        function2 = _lambda.Function(self, "lambda_function2",
                                    runtime=_lambda.Runtime.PYTHON_3_7,
                                    handler="lambda-handler.main",
                                    code=_lambda.Code.asset("./lambda2"),
                                    environment= {
                                        'cluster_name': cluster.cluster_name,
                                        'launch_type':'FARGATE',
                                        'task_definition':faroptTask.to_string(),
                                        'task_family':faroptTask.family,
                                        'subnet1':subnets[0].subnet_id,
                                        'subnet2':subnets[-1].subnet_id,
                                        'bucket':s3.bucket_name
                                    },
                                    timeout=core.Duration.seconds(900),
                                    memory_size=10240,
                                    layers = [layer2],
                                    initial_policy = [iam.PolicyStatement(actions=['ecs:RunTask','ecs:PutAccountSetting','s3:*','iam:PassRole','cloudwatch:PutMetricData','cloudformation:DescribeStacks'],resources=['*'])])

        
        
        
        # Lambda API resolver with faropt layer
                # 1- create layer
        
        layercode3 = _lambda.Code.from_asset(path="./layers/faroptlayer.zip") # adding np to the layer
        layer3 = _lambda.LayerVersion(self,id="layer3",code=layercode3)
        
        # layercode4 = _lambda.Code.from_asset(path="./layers/faroptlayerasync.zip") # adding np to the layer
        # layer4 = _lambda.LayerVersion(self,id="layer4",code=layercode4)
        
        # 2- create function
        function3 = _lambda.Function(self, "lambda_function3",
                                    runtime=_lambda.Runtime.PYTHON_3_7,
                                    handler="lambda-handler.lambda_handler",
                                    code=_lambda.Code.asset("./lambda3"),
                                    environment= {
                                        'cluster_name': cluster.cluster_name,
                                        'launch_type':'FARGATE',
                                        'task_definition':faroptTask.to_string(),
                                        'task_family':faroptTask.family,
                                        'subnet1':subnets[0].subnet_id,
                                        'subnet2':subnets[-1].subnet_id,
                                        'bucket':s3.bucket_name
                                    },
                                    timeout=core.Duration.seconds(120),
                                    memory_size=2048,
                                    layers = [layer3],
                                    initial_policy = [iam.PolicyStatement(actions=['ecs:RunTask',
                                    'ecs:PutAccountSetting','s3:*','iam:PassRole','cloudwatch:PutMetricData',
                                    'ecr:*','dynamodb:*',"cloudformation:Describe*","cloudformation:Get*","cloudformation:List*",
                                    "logs:CreateLogStream","logs:PutLogEvents",'cloudformation:DescribeStacks'],resources=['*'])])

        
        
        
        
        
        # OUTPUTS
        core.CfnOutput(self, 's3output', value=s3.bucket_name, export_name='bucket')
        core.CfnOutput(self, 'jobtable', value=jobtable.table_name, export_name='jobtable')
        core.CfnOutput(self, 'recipetable', value=recipetable.table_name, export_name='recipetable')
        core.CfnOutput(self, 's3asyncoutput', value=s3async.bucket_name, export_name='asyncbucket')
        core.CfnOutput(self, 'lambdaopt', value=function2.function_name, export_name='lambdaopt')