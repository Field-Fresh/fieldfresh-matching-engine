import json
from typing import Any, Dict, Tuple, Union
from ffengine.data import BuyOrder, SellOrder

PROTOCOL_VERSION = "custom-order-json--1.0.0"


class OrderJson(object):
    @classmethod
    async def build_message(cls, service: Any, topic: str, data: Any, **kwargs: Any) -> str:
        return json.dumps(data)

    @classmethod
    async def parse_message(cls, payload: str, **kwargs: Any) -> Union[Dict, Tuple]:
        data = json.loads(payload)

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

        order=None
        if order_type == "buyOrder.created":
            price = order_info["maxPriceCents"]

            order = BuyOrder(
                order_id=order_id, buyer_id=agent_id, product_id=product_id,
                max_price_cents=price, quantity=quantity,
                time_activation=activ_time, time_expiry=expir_time,
                lat=lat, long=long
            )
        
        elif order_type == "sellOrder.created":
            price = order_info["minPriceCents"]
            service_range = order_info["serviceRadius"]

            order = SellOrder(
                order_id=order_id, seller_id=agent_id, product_id=product_id,
                min_price_cents=price, quantity=quantity,
                time_activation=activ_time, time_expiry=expir_time,
                lat=lat, long=long, service_range=service_range
            )

        print("success!")

        return (
            {
                "order": order,
                "order_type": order_type,
                "batch_info": {
                    "totalMessageCount": total_orders,
                    "batchId": orderset_id
                }
            },
            None,
            None,
        )
