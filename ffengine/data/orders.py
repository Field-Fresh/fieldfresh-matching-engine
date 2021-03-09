from dataclasses import dataclass
from typing import List, Iterator 

@dataclass
class SellOrder:
    order_id: str
    seller_id: str
    product_id: str
    
    min_price_cents: int
    quantity: int
    time_activation: int
    time_expiry: int
    service_range: float
    lat: float
    long: float
        
    int_order_id: int = None
    int_seller_id: int = None
    int_product_id: int = None

@dataclass
class BuyOrder:
    order_id: str
    buyer_id: str
    product_id: str

    max_price_cents: int
    quantity: int
    time_activation: int
    time_expiry: int
    lat: float
    long: float

    int_order_id: int = None
    int_buyer_id: int = None
    int_product_id: int = None

class OrderSet:
    def __init__(self):
        self._buy_orders = []
        self._sell_orders = []
        self._buyers = {}
        self._sellers = {}
        self._products = {}

        self.n_sell_orders = 0
        self.n_buy_orders = 0
        self.n_sellers = 0
        self.n_buyers = 0
        self.n_products = 0
    

    def add_buy_order(self, order: BuyOrder):
    
        new_int_id = len(self._buy_orders)
        new_int_agent = len(self._buyers)
        new_int_product = len(self._products)

        self.n_buy_orders += 1
        self._buy_orders.append(order)

        agent = order.buyer_id
        product = order.product_id

        if not (agent in self._buyers):
            self._buyers[agent] = new_int_agent
            self.n_buyers += 1
        if not (product in self._products):
            self._products[product] = new_int_product
            self.n_products += 1
        
        order.int_order_id = new_int_id
        order.int_buyer_id = self._buyers[agent]
        order.int_product_id = self._products[product]


    def add_sell_order(self, order: SellOrder):

        new_int_id = len(self._sell_orders)
        new_int_agent = len(self._sellers)
        new_int_product = len(self._products)

        self._sell_orders.append(order)
        self.n_sell_orders += 1

        agent = order.seller_id
        product = order.product_id

        if not (agent in self._sellers):
            self._sellers[agent] = new_int_agent
            self.n_sellers += 1
        if not (product in self._products):
            self._products[product] = new_int_product
            self.n_products += 1
        
        order.int_order_id = new_int_id
        order.int_buyer_id = self._sellers[agent]
        order.int_product_id = self._products[product]


    def iter_buy_orders(self) -> Iterator[BuyOrder]:
        for u in self._buy_orders:
            yield u

    
    def iter_sell_orders(self) -> Iterator[SellOrder]:
        for v in self._sell_orders:
            yield v

