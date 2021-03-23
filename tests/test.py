from ffengine.simulation import TestCase
from ffengine.simulation import TestCaseMetrics
from ffengine.optim.engines import OMMEngine


## define sets for test case
I1 = list(range(5))
J1 = list(range(5))
K1 = list(range(3))


test_case1 = TestCase(
    size_I=len(I1), size_J=len(J1), size_K=len(K1),
    Q_K={k: 1/len(K1) for k in K1}, P_K={0: 5, 1:2, 2: 1},
    D_scap_p={0: .7, 1: .3}, D_dcap_p={0: 1},
    s_bounds=lambda c: (1,10) if c == 0 else (10, 20),
    d_bounds=lambda c: (3, 7),
    s_subsize={i: len(K1) for i in I1},
    lb_fn= lambda k, i: i - int(i > 1),
    ub_fn= lambda c, p: p + 1,
    dist_bounds= (3, 10),
    unit_tcost=1
)


stats, matches = test_case1.run(OMMEngine)

metrics = TestCaseMetrics({
    'omm': stats
})

metrics.surplus_plot('Buyer')
metrics.surplus_plot('Seller')