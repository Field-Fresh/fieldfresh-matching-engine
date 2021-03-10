import os
from typing import Any

import tomodachi
from tomodachi import aws_sns_sqs, aws_sns_sqs_publish
from tomodachi.discovery import AWSSNSRegistration
from tomodachi.envelope import JsonBase

from ffengine.data import OrderSet, BuyOrder, SellOrder
from ffengine.optim.engines import OMMEngine
import json

aws_credentials = json.load(open('aws_credentials.json'))

class MatchingEngineService(tomodachi.Service):
    name = "matching-engine-service"
    log_level = "INFO"
    uuid = str(os.environ.get("SERVICE_UUID") or "")

    # Build own "discovery" functions, to be run on start and stop
    # See tomodachi/discovery/aws_sns_registration.py for example
    discovery = [AWSSNSRegistration]

    message_envelope = JsonBase

    # Some options can be specified to define credentials, used ports, hostnames, access log, etc.
    options = {
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

    MATCH_BATCH_SIZE = 3

    ordersets = {}
    processed_flags = {}

    @aws_sns_sqs("dev-field-fresh-mate-sns", queue_name="stage-field-fresh-matching-engine-sqs_1")
    async def recvSystemOrders(self, data: dict) -> None:
        '''Receive new orders sent to MATE. Preprocess them (asynchronously?) and store the parameters
        '''

        order_type = data["type"]
        total_orders = data["message"]["totalMessageCount"]
        orderset_id = data["message"]["batchId"]
        order_info = data["message"]["message"]

        order_id = order_info["id"]
        agent_id = order_info["proxyId"]
        product_id = order_info["productId"]
        quantity = order_info["volume"]
        activ_time = order_info["earliestDate"]["seconds"]
        expir_time = order_info["latestDate"]["seconds"]
        lat, long = order_info["lat"], order_info["long"]

        print(f"recvd order !!!: (type, id, batchId, totalOrders) {order_type, order_id, orderset_id, total_orders}")

        if not orderset_id in self.ordersets:
            print("adding new orderset")
            self.ordersets[orderset_id] = OrderSet()
            self.processed_flags[orderset_id] = {'buy' : False, 'sell' : True}

        if order_type == "buyOrder.created":
            price = order_info["maxPriceCents"]
            self.ordersets[orderset_id].add_buy_order(BuyOrder(
                order_id=order_id, buyer_id=agent_id, product_id=product_id,
                max_price_cents=price, quantity=quantity,
                time_activation=activ_time, time_expiry=expir_time,
                lat=lat, long=long
            ))
            print('added buy order')
            self.processed_flags[orderset_id]['buy'] = (total_orders == self.ordersets[orderset_id].n_buy_orders)
        elif order_type == "sellOrder.created":
            price = order_info["minPriceCents"]
            service_range = order_info["serviceRadius"]
            self.ordersets[orderset_id].add_sell_order(SellOrder(
                order_id=order_id, seller_id=agent_id, product_id=product_id,
                min_price_cents=price, quantity=quantity,
                time_activation=activ_time, time_expiry=expir_time,
                lat=lat, long=long, service_range=service_range
            ))
            print('added sell order')
            self.processed_flags[orderset_id]['sell'] = (total_orders == self.ordersets[orderset_id].n_sell_orders)

        print(len(self.ordersets[orderset_id]), total_orders)
        print(self.processed_flags[orderset_id])
        if self.processed_flags[orderset_id]['buy'] and self.processed_flags[orderset_id]['sell']:
            
            print(f"Order set len: {len(self.ordersets[orderset_id])}")
            print(f"buy orders: {self.ordersets[orderset_id].n_buy_orders}")
            print(f"sell orders: {self.ordersets[orderset_id].n_sell_orders}")

            # start matching
            matcher = OMMEngine(self.ordersets[orderset_id])
            matcher.construct_params()
            matcher.match()

            # return matches
            matches = matcher.get_matches()
            total_matches = matches.n_matches

            package_matches = lambda total_matches, batch_id, messagelist: {
                "batchId": batch_id, "totalMatches": total_matches, "messageSize": len(messagelist), "matches": messagelist
                }

            matchbatch = []
            for i, match in enumerate(matches.iter_matches()):
                matchdata = match.to_dict()
                matchbatch.append(matchdata)

                if (i+1) % self.MATCH_BATCH_SIZE:
                    data = package_matches(total_matches, orderset_id, matchbatch)
                    await aws_sns_sqs_publish(self, data=data, topic="dev-field-fresh-api-sns")
                    matchbatch = []
            
            if len(matchbatch):
                data = package_matches(total_matches, orderset_id, matchbatch)
                await aws_sns_sqs_publish(self, data=data, topic="dev-field-fresh-api-sns")

            print("sent all responses")


