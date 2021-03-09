from ._models import OrderMatchingModel
from ffengine.data import MatchSet, Match, OrderSet
from ._utils import distance
import abc

class Engine(abc.ABC):
    
    @abc.abstractmethod
    def get_orderset(self)->OrderSet:
        pass

    @abc.abstractmethod
    def construct_params(self):
        pass

    @abc.abstractmethod
    def match(self):
        pass

    @abc.abstractmethod
    def get_matches(self) -> MatchSet:
        pass


class OMMEngine(Engine):

    def __init__(self, orderset: OrderSet):
        self.orderset = orderset
        self._params = {}

    def get_orderset(self):
        return self.orderset

    def construct_params(self):
        ''' Constructs the parameters for OMM based on the given OrderSet. This must be run before `match`
        straightforward approach: O(U*V + U + V)'''

        self._params['BUYORDERS'] = range(self.orderset.n_buy_orders)
        self._params['SELLORDERS'] = range(self.orderset.n_sell_orders)

        self._params['p_u'] = {}
        self._params['p_v'] = {}
        self._params['q_u'] = {}
        self._params['q_v'] = {}

        self._params['f_uv'] = {}
        self._params['c_uv'] = {}

        for u in self.orderset.iter_buy_orders():
            self._params['p_u'][u.int_order_id] = u.max_price_cents
            self._params['q_u'][u.int_order_id] = u.quantity

        for v in self.orderset.iter_sell_orders():
            self._params['p_v'][v.int_order_id] = v.min_price_cents
            self._params['q_v'][v.int_order_id] = v.quantity

        
        ## construct uv params
        for u in self.orderset.iter_buy_orders():
            for v in self.orderset.iter_sell_orders():
                d = distance(
                    (u.lat, u.long),
                    (v.lat, v.long)
                )

                self._params['c_uv'][
                    (u.int_order_id, v.int_order_id)
                ] = d

                ## able to match criteria:
                # 1) same product
                is_same_prod = (u.int_product_id == v.int_product_id)
                # 2) available at same time
                is_available = (u.time_expiry >= v.time_activation) & (v.time_expiry >= u.time_activation)
                # 3) distance is within service region
                is_serviceable = (d <= v.service_range)

                # 1 if all conditions are met, 0 otherwise
                self._params['f_uv'][(
                    u.int_order_id, v.int_order_id
                )] = int(is_same_prod & is_available & is_serviceable)

    def match(self):
        solver = OrderMatchingModel(**self._params)
        solver.optimize()
        self._solved_model = solver


    def get_matches(self) -> MatchSet:

        matches = MatchSet()

        model_vars = self._solved_model.getVars()
        x_uv = model_vars['x_uv']
        
        for buy_order in self.orderset.iter_buy_orders():
            for sell_order in self.orderset.iter_sell_orders():
                u, v = buy_order.int_order_id, sell_order.int_order_id

                quantity = float(x_uv[u,v])

                if quantity > 0:

                    # is this assertion necessary? We can likely remove this after some testing
                    assert (
                        (buy_order.max_price_cents == model_vars['p_u'][u]) and (sell_order.min_price_cents == model_vars['p_v'][v])
                        ), "Critical assertion failed! Order IDs have got mixed up... data is wrong"
                    
                    price = self._solved_model.price(model_vars['p_u'], model_vars['p_v'])
                    

                    matches.add_match(
                        Match(buy_order=buy_order, sell_order=sell_order, price_cents=price, quantity=quantity)
                    )

        self.matchset = matches
        
        return matches



