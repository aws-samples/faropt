#!/usr/bin/env python3

from aws_cdk import core

from faropt.faropt_stack import FaroptStack
import os

app = core.App()

FaroptStack(app, "faropt") #overriding region for test

app.synth()

