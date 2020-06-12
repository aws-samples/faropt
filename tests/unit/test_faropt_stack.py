import json
import pytest

from aws_cdk import core
from faropt.faropt_stack import FaroptStack


def get_template():
    app = core.App()
    FaroptStack(app, "faropt")
    return json.dumps(app.synth().get_stack("faropt").template)


def test_sqs_queue_created():
    assert("AWS::SQS::Queue" in get_template())


def test_sns_topic_created():
    assert("AWS::SNS::Topic" in get_template())
