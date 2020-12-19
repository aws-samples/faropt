#!/usr/bin/env python3

from aws_cdk import core

from faropt.faropt_stack import FaroptStack
import os

app = core.App()

FaroptStack(app, "faropt", env={'region': os.environ["CDK_DEFAULT_REGION"], 'account':os.environ["CDK_DEFAULT_ACCOUNT"] }, trustedAccount= os.environ["CDK_DEFAULT_ACCOUNT"]) #overriding region for test

app.synth()

