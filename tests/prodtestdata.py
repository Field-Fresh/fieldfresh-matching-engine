import pandas as pd
from ffengine.simulation import TestCase
from ffengine.simulation._utils import exp_discount_lb_fn
from ffengine.optim.engines import OMMEngine
import numpy as np


size_I = 8 #1856
size_J = 5 #5262
size_K = 10 #29

productdata = pd.read_csv('RealData/ProductData.csv')
sellerdata = pd.read_csv('RealData/SellerData.csv')
buyerdata = pd.read_csv('RealData/BuyerData.csv')

productdata['P_K'] *= 100 # convert dollars to cents

## additional config

productdata = productdata.iloc[:size_K]
productdata['Q_K'] /= productdata['Q_K'].sum()

sellerdata['s_subsize'] = size_K - 3
##

Q_K = productdata['Q_K'].to_dict()
P_K = productdata['P_K'].to_dict()

D_scap_p = sellerdata['D_scap_p'].to_dict()
D_dcap_p = buyerdata['D_dcap_p'].to_dict()

SUPP_SCALE = 10
s_bounds = lambda c: (sellerdata['s_bounds_min'].loc[c] * SUPP_SCALE, sellerdata['s_bounds_max'].loc[c] * SUPP_SCALE)
d_bounds = lambda c: (buyerdata['d_bounds_min'].loc[c], buyerdata['d_bounds_max'].loc[c])

s_subsize = sellerdata['s_subsize'].to_dict()

lb_fn = exp_discount_lb_fn(max_q=sellerdata['s_bounds_max'].max()/2, discount=.1)
ub_fn = exp_discount_lb_fn(max_q=buyerdata['d_bounds_max'].max()/2, discount=-.1)

dist_bounds = (16.5, 100)

sampleData = TestCase(
    size_I=size_I, size_J=size_J, size_K=size_K,
    Q_K=Q_K, P_K=P_K,
    D_scap_p=D_scap_p, D_dcap_p=D_dcap_p,
    s_bounds=s_bounds, d_bounds=d_bounds,
    s_subsize=s_subsize,
    lb_fn=lb_fn, ub_fn=ub_fn,
    dist_bounds=dist_bounds,
    random_seed = 0,
    unit_tcost = 300
)