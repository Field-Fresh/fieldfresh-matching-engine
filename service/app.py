import os
from typing import Any

import tomodachi
from tomodachi import aws_sns_sqs, aws_sns_sqs_publish
from tomodachi.discovery import AWSSNSRegistration
from tomodachi.envelope import JsonBase

from data import MatchSet, OrderSet, BuyOrder, SellOrder
from optim.engines import OMMEngine

class ExampleAWSSNSSQSService(tomodachi.Service):
    name = "example-aws-sns-sqs-service"
    log_level = "INFO"
    uuid = str(os.environ.get("SERVICE_UUID") or "")

    # Build own "discovery" functions, to be run on start and stop
    # See tomodachi/discovery/aws_sns_registration.py for example
    discovery = [AWSSNSRegistration]

    # The message envelope class defines how a message should be processed when sent and received
    # See tomodachi/envelope/json_base.py for a basic example using JSON and transferring some metadata
    message_envelope = JsonBase

    # Some options can be specified to define credentials, used ports, hostnames, access log, etc.
    options = {
        "aws_sns_sqs": {
            "region_name": "us-east-1",  # specify AWS region (example: 'eu-west-1')
            "aws_access_key_id": "AKIAQ3VBKKEENKC6II6G",  # specify AWS access key (example: 'AKIAXNTIENCJIY2STOCI')
            "aws_secret_access_key": "9E/U0mTTjihzzI4WnRGmu6IXCOmQYgv1QaNVUo49",  # specify AWS secret key (example: 'f7sha92hNotarealsecretkeyn29ShnSYQi3nzgA')
        },
        "aws_endpoint_urls": {
            "sns": "https://sns.us-east-1.amazonaws.com/059394117896/",
            "sqs": "https://sqs.us-east-1.amazonaws.com/059394117896/stage-field-fresh-matching-engine-sqs_1",
        },
    }

    # @aws_sns_sqs("test-pub")
    # async def route1a(self, data: Any) -> None:
    #     self.log('Received data (function: route1a) - "{}"'.format(data))

    @aws_sns_sqs("dev-field-fresh-mate-sns", queue_name="stage-field-fresh-matching-engine-sqs_1")
    async def recvSystemOrders(self, data: dict) -> None:
        '''Receive new orders sent to MATE. Preprocess them (asynchronously?) and store the parameters
        '''
        self.log('Received New Orders (function: recvSystemOrders) - "{}"'.format(data))

    # @tomodachi.http("GET", r"/test-pub")
    # async def test_pub(self, request) -> None:

    #     # await aws_sns_sqs_publish(self, data, topic=topic, wait=False)

    

    # async def _started_service(self) -> None:
    #     async def publish(data: Any, topic: str) -> None:
    #         self.log('Publish data "{}"'.format(data))
    #         await aws_sns_sqs_publish(self, data, topic=topic, wait=False)

    #     await publish("友達", "example-route1")
    #     await publish("other data", "example-route2")