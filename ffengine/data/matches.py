from dataclasses import dataclass
from typing import Iterator

from typing import List

from .orders import BuyOrder, SellOrder

@dataclass
class Match:
    match_id: int
    buy_order: BuyOrder
    sell_order: SellOrder
    price_cents: int
    quantity: int

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
        self._matches.append(match)
        self.n_matches += 1

    def iter_matches(self) -> Iterator:
        for m in self._matches:
            yield m

    def get_matched_buyers(self) -> List[int]: pass

    def get_matched_sellers(self) -> List[int]: pass
