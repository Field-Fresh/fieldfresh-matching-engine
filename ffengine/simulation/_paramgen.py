import numpy as np
import gurobipy as gp
from typing import Dict, Callable, Tuple, Iterable

from ffengine.optim.engines import Engine

import ffengine.simulation._utils as utils

from ffengine.data.orders import SellOrder, BuyOrder, OrderSet

class TestCase:
    '''
    Q_K - pmf of product k (aggregate demand distribution for product k) {product: demand}
    P_K - "fair" price per product k (can be true equilbirum price) {product: price}
    D_scap_p - pmf of *s*upply *cap*acity *p*arameter {parameter: probability}
    D_dcap_p - pmf of *d*emand *cap*acity *p*arameter {parameter: probability}
    s_bounds - function: (capacity_paramter) -> (min, max) where min and max are used as parameters for a uniform distribution to sample for capacity
    d_bounds - function: (capacity_paramter) -> (min, max) where min and max are used as parameters for a uniform distribution to sample for capacity
    s_subsize - size subset of product set K that supplier s will supply/produce {supplier: subset_size} (This is based on theta_i)
    lb_fn - function: (seller_capacity, product_price) -> seller lower bound price
    ub_fn - function: (buyer_capacity, product_price) -> buyer upper bound price
    dist_bounds - (min, max) minimum and maximum distance between buyers/sellers

    See https://www.dropbox.com/scl/fi/td4qd68uiwjkxmhivz6f5/Simulation-Strategy.paper?dl=0&rlkey=lylhvexxwjedxgv90h1kkgzl8 for more info
    '''

    def __init__(
        self,
        size_I: int,
        size_J: int,
        size_K: int,
        Q_K: Dict[int, float],
        P_K: Dict[int, float],
        D_scap_p: Dict[int, float],
        D_dcap_p: Dict[int, float],
        s_bounds: Callable[[int], Tuple[int, int]],
        d_bounds: Callable[[int], Tuple[int, int]],
        s_subsize: Dict[int, int],
        lb_fn: Callable[[int, float], float],
        ub_fn: Callable[[int, float], float],
        dist_bounds: Tuple[float, float],
        random_seed: int = 0
    ):
        np.random.seed(random_seed)
        # assertions
        assert len(Q_K) == size_K, f'Q_K does not have {size_K} elements according to parameter `size_K`'
        assert len(P_K) == size_K, f'P_K does not have {size_K} elements according to parameter `size_K`'
        assert utils.non_zero(P_K), f'P_K has negative or 0 prices'
        # assert s_subsize.keys() == set(range(size_I)), f's_subsize has wrong keys, either incomplete or with non existent seller IDs'
        assert np.all([i <= size_K for i in s_subsize.values()]), f'subset size for a seller cannot be larger than `size_K`: {size_K}'
        assert dist_bounds[0] >=0 and dist_bounds[1] >=0, f'cannot have negative distances. Must be (+,+)'

        # try Callables and assert I/O types??

        # should these be replaced with np.random.multinomial?

        # 4.
        D_scap_p, D_dcap_p = utils.DiscreteSampler(
            D_scap_p), utils.DiscreteSampler(D_dcap_p)
        param_i, param_j = [D_scap_p() for i in range(size_I)], [
            D_dcap_p() for j in range(size_J)]


        # 4 a), b)
        cap_i, cap_j = [np.random.uniform(*s_bounds(theta_i)) for theta_i in param_i], [
            np.random.uniform(*d_bounds(theta_j)) for theta_j in param_j]

        # 5.
        products_i = [utils.dist_subset(Q_K, keys=np.random.choice(list(
            Q_K.keys()), size=s_subsize[theta_i], replace=False)) for theta_i in param_i]
        
        ## Ignore everything above this

        # {seller_id: {product_id : quantity_supplied}}
        s_ik = {
            i: dict(zip(
                products_i[i].keys(), np.random.multinomial(
                    n=cap_i[i], pvals=list(products_i[i].values()), size=1)[0]
            ))
            for i in range(size_I)
        }

        # 5 a)
        # {buyer_id: {product_id : quantity_demanded}}
        d_jk = {
            j: dict(zip(
                Q_K.keys(), np.random.multinomial(
                    n=cap_j[j], pvals=list(Q_K.values()), size=1)[0]
            ))
            for j in range(size_J)
        }

        # 6.
        # {seller_id: {product_id : min_price}}
        l_ik = {
            i: {k: lb_fn(cap_i[i], P_K[k]) for k in P_K} ## this iterates through all products... this should only be for products for that seller
            for i in range(size_I)
        }
        # 6 a)
        # {buyer_id: {product_id : max_price}}
        u_jk = {
            j: {k: ub_fn(cap_j[j], P_K[k]) for k in P_K}
            for j in range(size_J)
        }

        c_ij = {(i,j): np.random.uniform(*dist_bounds) for i in range(size_I) for j in range(size_J)}

        # assume lat/long, activeTimes, and ServiceRange

        #Loop throught buyers to create BuyOrders

        tempOrderSet = OrderSet()

        tempSentry = 0

        #Buy Order Loop!

        for b in range(size_J):

            for p in range(size_K):

                tempBuyOrder = BuyOrder(
                    int_buyer_id= b,
                    int_order_id= tempSentry,
                    int_product_id=p,

                    lat = 110.1,
                    long = 120.5,
                    
                    quantity = d_jk[b][p],
                    max_price_cents = u_jk[b][p],

                    time_activation = 1200000,
                    time_expiry = 1300000,

                    order_id = 'BuyOrder-' + str(tempSentry),
                    product_id = 'Product-' + str(p),
                    buyer_id = 'Buyer-' + str(b)

                )
                

                #if the buy order is 0, we are not going to add it to the orderset. 
                if(d_jk[b][p] >= 0):
                    tempOrderSet.add_buy_order(tempBuyOrder)
                    tempSentry += 1

        tempSentry = 0

        #Sell Order Loop

        for s in range(size_I):

            for p in range(size_K):

                tempSellOrder = SellOrder(
                    int_seller_id= s,
                    int_order_id= tempSentry,
                    int_product_id=p,

                    lat = 110.1,
                    long = 120.5,
                    
                    quantity = s_ik[s][p],
                    min_price_cents = l_ik[s][p],

                    time_activation = 1200000,
                    time_expiry = 1300000,
                    service_range = 100,

                    order_id = 'SellOrder-' + str(tempSentry),
                    product_id = 'Product-' + str(p),
                    seller_id = 'Seller-' + str(s)

                )

                tempOrderSet.add_sell_order(tempSellOrder)

                tempSentry += 1



        # format into `Orders`
        # SellOrder: (supply, supplier, price, product, availbility, expiry, service range)
        # (supply, supplier, product)
        # (price, supplier, product)

        # your task here: given s_ik, d_jk, l_ik, u_jk (as well as generating other info) => [(agent_id, quantity, price, ...)]
        # construct an OrderSet with this data (should be able to just pass to the constructor) and save it to this object
        # self.Orders = OrderSet(info)

        self.order_set = tempOrderSet

    
    def run(self, engine: Engine):

        # pass self.Orders to engine

        matcher = engine(self.order_set)
        matcher.construct_params()
        matcher.match()

        tempMatchSet = matcher.get_matches()

        listOfMatches = tempMatchSet._matches
        numOfMatches = tempMatchSet.n_matches

        buyer_summary = {}
        seller_summary = {}

        for b in range(self.order_set.n_buy_orders):

            order = self.order_set._buy_orders[b]
            buyer_id = order.buyer_id
            product_id = order.product_id
            product_price = order.max_price_cents
            product_quantity = order.quantity

            buyer_summary[buyer_id][product_id]['Price'] = product_price
            buyer_summary[buyer_id][product_id]['Quantity'] = product_quantity

            buyer_summary[buyer_id]["Buyer-Profit"] = 0
            buyer_summary[buyer_id][product_id]['Match-Price'] = 0
            buyer_summary[buyer_id][product_id]['Match-Quantity'] = 0
            buyer_summary[buyer_id][product_id]['Unmatched-Demand'] = product_quantity


        for s in range(self.order_set.n_sell_orders):

            order = self.order_set._sell_orders[s-order]
            seller_id = order.seller_id
            product_id = order.product_id
            product_price = order.min_price_cents
            product_quantity = order.quantity

            seller_summary[seller_id][product_id]['Price'] = product_price
            seller_summary[seller_id][product_id]['Quantity'] = product_quantity

            seller_summary[seller_id]["Seller-Surplus"] = 0
            seller_summary[seller_id][product_id]['Match-Quantity'] = 0
            seller_summary[seller_id][product_id]['Match-Quantity'] = 0
            seller_summary[seller_id][product_id]['Unsold-Supply'] = product_quantity


        for m in range(numOfMatches):

            match = listOfMatches[m]
            matchBuyer = match.buy_order
            matchSeller = match.sell_order

            buyer_id = matchBuyer.buyer_id
            seller_id = matchSeller.seller_id
            product_id = matchBuyer.product_id

            matchPrice = match.price_cents
            matchQuantity = match.quantity

            seller_price = matchSeller.min_price_cents
            buyer_price = matchBuyer.max_price_cents

            buyer_profit = (matchPrice - buyer_price) * matchQuantity
            seller_surplus = (seller_price - matchPrice) * matchQuantity

            buyer_summary[buyer_id][product_id]['Match-Quantity'] += matchQuantity
            buyer_summary[buyer_id][product_id]['Unmatched-Demand'] -= matchQuantity
            buyer_summary[buyer_id]["Buyer-Profit"] += buyer_profit

            seller_summary[seller_id][product_id]['Match-Quantity'] += matchQuantity
            seller_summary[seller_id][product_id]['Unsold-Supply'] -= matchQuantity
            seller_summary[seller_id]["Seller-Surplus"] += seller_surplus

        usedBuyers = tempMatchSet.get_matched_buyers
        usedSellers = tempMatchSet.get_matched_sellers

        # retreive MatchSet from engine

        pass  