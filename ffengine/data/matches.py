from dataclasses import dataclass
from typing import Iterator

from .orders import BuyOrder, SellOrder

@dataclass
class Match:
    buy_order: BuyOrder
    sell_order: SellOrder
    price_cents: int
    quantity: int
    match_id: int=None

    def to_dict(self):
        return {
            "matchId": self.match_id,
            "buyOrder": self.buy_order.order_id,
            "sellOrder": self.sell_order.order_id,
            "volume": self.quantity,
            "priceCents": self.price_cents
        }


class MatchSet:
    def __init__(self):
        self._matches = []
        self.n_matches = 0
    
    def add_match(self, match: Match):
        match.match_id = self.n_matches
        self._matches.append(match)
        self.n_matches += 1

    def iter_matches(self) -> Iterator:
        for m in self._matches:
            yield m

