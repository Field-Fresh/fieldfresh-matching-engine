class OrderMatchingModel(gp.Model):

    '''The following is a mapping from model notation to code notation
    Sets
    U -> BUY Orders
    V -> SELL Orders

    Parameters
    p_u - price upper bound (For a Buyers)
    p_v - price lower bound (For a Sellers)
    
    q_u - quantity ordered (By a Buyer)
    q_v - quantity supplied (By a Sellers)

    c_uv - Fixed transaction cost between a Buyer and a Seller

    f_uv - Feasibility indicator (Same product? and fasible time iterval? 1, else 0 for each UV combo)

    Extras
    Vinfo - seller_id and product_id for each sell order { v: (seller_id, product_id) } : only used for validation metrics
    Uinfo - buyer_id and product_id for each buy order { u: (buyer_id, product_id) } : only used for validation metrics

    '''

    def __init__(
        self,
        BUYORDERS: List[int],
        SELLORDERS: List[int],
        p_u: Dict[int, float],
        p_v: Dict[int, float],
        q_u: Dict[int, float],
        q_v: Dict[int, float],
        c_uv: Dict[Tuple[int, int], float],
        f_uv: Dict[Tuple[int, int], int],
        Vinfo: Dict[int, Tuple[int, int]],
        Uinfo: Dict[int, Tuple[int, int]]):

        super().__init__('order-matching-model')

        ## decision variables
        self.__x_uv = x_uv = self.addVars(BUYORDERS, SELLORDERS, name='x_uv')
        self.__w_uv = w_uv = self.addVars(BUYORDERS, SELLORDERS, vtype=GRB.BINARY, name='w_uv')
        self.__y_u = y_u = self.addVars(BUYORDERS, vtype=GRB.BINARY, name='y_u' )

        self.__BUYORDERS = BUYORDERS
        self.__SELLORDERS = SELLORDERS
        self.__p_u = p_u
        self.__p_v = p_v
        self.__q_u = q_u
        self.__q_v = q_v
        self.__c_uv = c_uv
        self.__f_uv = f_uv
        self.__Vinfo = Vinfo
        self.__Uinfo = Uinfo

        ## objective: maximize total seller profits

        #obj = sum(x[u,v]*((0.5*(p_u[u] + p_v[v]))- c_uv[u,v]*w_uv[u,v] for u in BUYORDERS for v in SELLORDERS)

        ## objective: maximize total surplus

        obj = sum(x_uv[u,v]*(p_u[u] - p_v[v]) for u in BUYORDERS for v in SELLORDERS)

        
        #supply constraint: The quantity fulfilled cannot overexceed the available supply.
        self.addConstrs( (x_uv.sum('*', v) <= q_v[v] for v in SELLORDERS ), "(1) supply limit")

        #demand constraint: The quantity supplied cannot partially fulfill an order. It is all or nothing.
        self.addConstrs( (x_uv.sum(u, '*') == q_u[u]*y_u[u] for u in BUYORDERS ), "(2) demand requirement")

        #bind w_uv to x_uv: Ensure w_uv is 1 if BUY/SELL orders u-v match for a specific quantity, 0 if u-v not matched.
        self.addConstrs( (x_uv[u,v] <= big_M*w_uv[u,v] for u in BUYORDERS for v in SELLORDERS ), "(3) binding w_uv")

        #positive seller surplus: 
        #self.addConstrs( (x_uv[u,v]*profitFunc(p_u[u],p_v[v]) - c_uv[u,v]*w_uv[u,v] >= 0 for u in BUYORDERS for v in SELLORDERS ), "(4.1) function-based seller surplus")
        
        self.addConstrs( (x_uv[u,v]*(0.5*(p_u[u] + p_v[v])) - c_uv[u,v]*w_uv[u,v] >= 0 for u in BUYORDERS for v in SELLORDERS ), "(4.2) specific instance seller surplus")

        #feasibility contraint: If BUYORDER u is paired with SELLORDER v
        self.addConstrs( (x_uv[u,v] <= big_M*f_uv[u,v] for u in BUYORDERS for v in SELLORDERS ), "(5) feasibility requirment")


        self.setObjective(obj, GRB.MAXIMIZE)

    def getVars(self) -> dict:
        return {
            'x_uv' : self.__x_uv,
            'w_uv' : self.__w_uv,
            'y_u' : self.__y_u,

            'BUYORDERS' : self.__BUYORDERS,
            'SELLORDERS' : self.__SELLORDERS,

            'p_u' : self.__p_u,
            'p_v' : self.__p_u,
            'q_u' : self.__q_u,
            'q_v' : self.__q_v,
            'c_uv' : self.__c_uv,
            'f_uv' : self.__f_uv,
        }

    def summary_stats(self) -> dict:

        x_uv = self.__x_uv
        w_uv = self.__w_uv
        y_u = self.__y_u

        BUYORDERS = self.__BUYORDERS
        SELLORDERS = self.__SELLORDERS
        p_u = self.__p_u
        p_v = self.__p_v
        q_u = self.__q_u
        q_v = self.__q_v
        c_uv = self.__c_uv
        f_uv = self.__f_uv
        Vinfo = self.__Vinfo
        Uinfo = self.__Uinfo


        # generate mapping of agent -> order (with all info). This will be used to generate distributions over agents
        BUYERS = {}
        SELLERS = {}

        for u in BUYORDERS:
            buyer, product = Uinfo[u]
            if not (buyer in BUYERS):
                BUYERS[buyer] = [u]
            else:
                BUYERS[buyer].append(u)

        for v in SELLERS:
            seller, product = Uinfo[u]
            if not (seller in SELLERS):
                SELLERS[buyer] = [v]
            else:
                SELLERS[buyer].append(v)


        used_sell_orders = {
            v: x_uv.sum('*', v)
            for v in SELLORDERS
            if (x_uv.sum('*', v) > 0)
        }

        used_buy_orders = {
            u: x_uv.sum(u, '*')
            for u in BUYORDERS
            if (x_uv.sum(u, '*') > 0)
        }
        
        order_remaining_q = lambda order, quantityset, orderset: (quantityset[order] - orderset[order]) if order in orderset else quantityset[order]

        buyer_unsat_demand = {
            j: [order_remaining_q(u, q_u, used_buy_orders) for u in BUYERS[j] ]
            for j in BUYERS
        }

        seller_unsold_supply = {
            i: [order_remaining_q(v, q_v, used_sell_orders) for v in SELLERS[i] ]
            for i in SELLERS
        }


        used_sellers = {
            i: [v for v in SELLERS[i] if v in used_sell_orders]
            for i in SELLERS
        }

        used_buyers = {
            j: [u for u in BUYERS[j] if u in used_buy_orders]
            for j in BUYERS
        }


        buyer_surplus_dist = {
            j: sum([ sum([.5*(p_u[u] - p_v[v])*x_uv[u, v] for v in SELLORDERS ]) for u in BUYERS[j]])
            for j in BUYERS
        }

        seller_surplus_dist = {
            i: sum([ sum([.5*(p_u[u] - p_v[v])*x_uv[u, v] - c_uv[u, v]*w_uv[u,v] for u in BUYORDERS ]) for v in SELLERS[j]])
            for i in SELLERS
        }


        return {
            'buyer_unsat_demand': buyer_unsat_demand,
            'seller_unsold_supply': seller_unsold_supply,
            'used_sellers': used_sellers,
            'used_buyers': used_buyers,
            'buyer_surplus_dist': buyer_surplus_dist,
            'seller_surplus_dist': seller_surplus_dist,
        }
