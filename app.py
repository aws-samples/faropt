#!/usr/bin/env python3

from aws_cdk import core

from faropt.faropt_stack import FaroptStack

app = core.App()
FaroptStack(app, "faropt")#, env={'region': 'us-west-2'}) #overriding region for test

app.synth()

