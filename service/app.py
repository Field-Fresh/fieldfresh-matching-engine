import os
from typing import Any

import tomodachi
from tomodachi import aws_sns_sqs, aws_sns_sqs_publish
from tomodachi.discovery import AWSSNSRegistration
from ._msgclasses import OrderJson

from ffengine.data import OrderSet, BuyOrder, SellOrder
from ffengine.optim.engines import OMMEngine
import json
from datetime import datetime
import asyncio

import debugpy
import time

aws_credentials = json.load(open('aws_credentials.json'))

# debugpy.listen(8090)
# time.sleep(10)

# TODO: convert `print` to logging

class MatchingEngineService(tomodachi.Service):
    name = "matching-engine-service"
    log_level = "INFO"
    uuid = str(os.environ.get("SERVICE_UUID") or "")

    # Build own "discovery" functions, to be run on start and stop
    # See tomodachi/discovery/aws_sns_registration.py for example
    discovery = [AWSSNSRegistration]

    message_envelope = OrderJson

    # Some options can be specified to define credentials, used ports, hostnames, access log, etc.
    options = {
        "http": {
            "port": 8080,
        },
        "aws_sns_sqs": {
            "region_name": "us-east-1",
            "aws_access_key_id": aws_credentials["aws_access_key_id"],
            "aws_secret_access_key": aws_credentials["aws_secret_access_key"],
        },
        "aws_endpoint_urls": {
            "sns": "https://sns.us-east-1.amazonaws.com/059394117896/",
            "sqs": "https://sqs.us-east-1.amazonaws.com/059394117896/stage-field-fresh-matching-engine-sqs_1",
        },
    }

    MATCHING_PERIOD_SECONDS = 1*1*2*60 # currently for testing, match ever 2m. This number is formatted as days*hours*minutes*seconds
    MATCH_BATCH_SIZE = 3
    MODEL_CONFIG = {"unit_tcost" : 300}
    DEBUG_MODE = False

    global_lock = asyncio.Lock()
    round_number = 0
    ordersets = {}
    datalocks = {}
    _matchsets = {}
    processed_flags = {}

    @aws_sns_sqs("dev-field-fresh-mate-sns", queue_name="stage-field-fresh-matching-engine-sqs_1")
    async def recvSystemOrders(self, order: Any, order_type: str, batch_info: dict ) -> None:
        '''Receive new orders sent to MATE. Preprocess them and store the parameters.
        '''


        total_orders = batch_info["totalMessageCount"]
        orderset_id = batch_info["batchId"]

        async with self.global_lock:
            if not orderset_id in self.ordersets:
                print("adding new orderset")
                self.ordersets[orderset_id] = OrderSet()
                self.datalocks[orderset_id] = asyncio.Lock()
                self.processed_flags[orderset_id] = {'buy' : False, 'sell' : False}

        async with self.datalocks[orderset_id]:
            if order_type == "buyOrder.created":
                try:
                    self.ordersets[orderset_id].add_buy_order(order)
                    print('added buy order')
                except ValueError as e:
                    print(e)
                self.processed_flags[orderset_id]['buy'] = (total_orders == self.ordersets[orderset_id].n_buy_orders)
            elif order_type == "sellOrder.created":
                try:
                    self.ordersets[orderset_id].add_sell_order(order)
                    print('added sell order')
                except ValueError as e:
                    print(e)
                self.processed_flags[orderset_id]['sell'] = (total_orders == self.ordersets[orderset_id].n_sell_orders)

        print(len(self.ordersets[orderset_id]), len(self.ordersets[orderset_id]._all_orders))
        print(self.processed_flags[orderset_id])
        if self.processed_flags[orderset_id]['buy'] and self.processed_flags[orderset_id]['sell']:
            self.processed_flags.pop(orderset_id)
            self.datalocks.pop(orderset_id)
            print(f"Order set len: {len(self.ordersets[orderset_id])}")
            print(f"buy orders: {self.ordersets[orderset_id].n_buy_orders}")
            print(f"sell orders: {self.ordersets[orderset_id].n_sell_orders}")

            assert len(self.ordersets[orderset_id]) == len(self.ordersets[orderset_id]._all_orders), f"Critical failure: {len(self.ordersets[orderset_id]) - len(self.ordersets[orderset_id]._all_orders)} duplicated orders"

            # start matching
            matcher = OMMEngine(self.ordersets.pop(orderset_id), **self.MODEL_CONFIG)
            matcher.construct_params()
            matcher.match()

            # return matches
            matches = matcher.get_matches()
            total_matches = matches.n_matches

            if self.DEBUG_MODE:
                self._matchsets[orderset_id] = matches

            package_matches = lambda total_matches, batch_id, messagelist: {
                "batchId": batch_id, "totalMatches": total_matches, "messageSize": len(messagelist), "matches": messagelist
                }

            matchbatch = []
            for i, match in enumerate(matches.iter_matches()):
                matchdata = match.to_dict()
                matchbatch.append(matchdata)

                if (i+1) % self.MATCH_BATCH_SIZE:
                    data = {"type": "mate.match.batch", "message": package_matches(total_matches, orderset_id, matchbatch)}
                    print("sending: ", data)
                    await aws_sns_sqs_publish(self, data=data, topic="dev-field-fresh-api-sns")
                    matchbatch = []
            
            if len(matchbatch):
                data = {"type": "mate.match.batch", "message": package_matches(total_matches, orderset_id, matchbatch)}
                print("sending: ", data)
                await aws_sns_sqs_publish(self, data=data, topic="dev-field-fresh-api-sns")

            print(f"sent all responses: {matches.n_matches} matches")
            self.round_number += 1


    @tomodachi.schedule(interval=MATCHING_PERIOD_SECONDS, immediately=~DEBUG_MODE) # immediately means to also run on startup, disable when debugging
    async def request_orders(self) -> None:
        timestamp = int(datetime.utcnow().timestamp())
        msg = {
            "type":"mate.ready",
            "message": {"readyTimeUTCSeconds": timestamp, "round": self.round_number}
        }
        await aws_sns_sqs_publish(self, data=msg, topic="dev-field-fresh-api-sns")
        print('requested orders')   

