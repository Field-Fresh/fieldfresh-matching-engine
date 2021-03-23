import gurobipy as gp
from gurobipy import GRB
import numpy as np
from typing import List, Dict, Tuple

big_M = 1e7

class OrderMatchingModel(gp.Model):

    '''The following is a mapping from model notation to code notation

    Objective function: maximize seller profit

    Sets
    U -> BUY Orders
    V -> SELL Orders

    Parameters
    p_u - price upper bound (For a Buy Order) (this is an integer indicating cents)
    p_v - price lower bound (For a Sell Order) (this is an integer indicating cents)
    
    q_u - quantity ordered (By a Buy Order) (this is an integer indicating pounds)
    q_v - quantity supplied (By a Sell Order) (this is an integer indicating pounds)

    c_uv - Fixed transaction cost between a Buyer and a Seller (this is also an integer indicating cents)

    f_uv - Feasibility indicator (Same product? and fasible time iterval? 1, else 0 for each UV combo)

    Extras
    Vinfo - seller_id and product_id for each sell order { v: (seller_id, product_id) } : only used for validation metrics
    Uinfo - buyer_id and product_id for each buy order { u: (buyer_id, product_id) } : only used for validation metrics

    '''

    def __init__(
        self,
        BUYORDERS: List[int],
        SELLORDERS: List[int],
        p_u: Dict[int, int],
        p_v: Dict[int, int],
        q_u: Dict[int, int],
        q_v: Dict[int, int],
        c_uv: Dict[Tuple[int, int], int],
        f_uv: Dict[Tuple[int, int], int]):

        super().__init__('order-matching-model')

        ## decision variables
        self.__x_uv = x_uv = self.addVars(BUYORDERS, SELLORDERS, vtype=GRB.INTEGER, name='x_uv')
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

        ## objective: maximize total seller profits

        obj = sum(x_uv[u,v]*self.price(p_u[u], p_v[v])-  c_uv[u,v]*w_uv[u,v] for u in BUYORDERS for v in SELLORDERS)

        ## objective: maximize total surplus

        # obj = sum(x_uv[u,v]*(p_u[u] - p_v[v]) for u in BUYORDERS for v in SELLORDERS)

        
        #supply constraint: The quantity fulfilled cannot overexceed the available supply.
        self.addConstrs( (x_uv.sum('*', v) <= q_v[v] for v in SELLORDERS ), "(1) supply limit")

        #demand constraint: The quantity supplied cannot partially fulfill an order. It is all or nothing.
        self.addConstrs( (x_uv.sum(u, '*') == q_u[u]*y_u[u] for u in BUYORDERS ), "(2) demand requirement")

        #bind w_uv to x_uv: Ensure w_uv is 1 if BUY/SELL orders u-v match for a specific quantity, 0 if u-v not matched.
        self.addConstrs( (x_uv[u,v] <= big_M*w_uv[u,v] for u in BUYORDERS for v in SELLORDERS ), "(3) binding w_uv")

        #positive seller profit
        self.addConstrs( (x_uv[u,v]*self.price(p_u[u], p_v[v]) - c_uv[u,v]*w_uv[u,v] >= 0 for u in BUYORDERS for v in SELLORDERS ), "(4.2) specific instance seller profit")

        #feasibility contraint: If BUYORDER u is paired with SELLORDER v
        self.addConstrs( (x_uv[u,v] <= big_M*f_uv[u,v] for u in BUYORDERS for v in SELLORDERS ), "(5) feasibility requirment")


        self.setObjective(obj, GRB.MAXIMIZE)

    def price(self, p_u, p_v):
        return np.ceil((p_u + p_v)/2) # ensure that final price is an integer

    def getVars(self) -> dict:
        return {
            'x_uv' : self.__x_uv,
            'w_uv' : self.__w_uv,
            'y_u' : self.__y_u,

            'BUYORDERS' : self.__BUYORDERS,
            'SELLORDERS' : self.__SELLORDERS,

            'p_u' : self.__p_u,
            'p_v' : self.__p_v,
            'q_u' : self.__q_u,
            'q_v' : self.__q_v,
            'c_uv' : self.__c_uv,
            'f_uv' : self.__f_uv,
        }
