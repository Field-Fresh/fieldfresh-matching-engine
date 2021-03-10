import numpy as np
from typing import Dict, Callable, Tuple, Iterable

EARTH_RADIUS = 6371

def exp_discount_lb_fn(max_q=1, discount=.1) -> Callable[[float, float], float]:
    # NOTE: this will converge exponentially wrt q... should this have a different convergence time? make use of max_q maybe?
    return lambda q,p: discount*p*np.exp(-q/max_q) + (1-discount)*p


#==============================================================================================================
# Helper functions
#==============================================================================================================

def flatten_dict(d: Dict[int, Dict[int, float]]) -> dict:
    flatdict = {}
    for i, subd in d.items():
        flatdict.update( {(i, k): subd[k] for k in subd})

    return flatdict

def non_zero(d: dict) -> bool:
    '''check dict values are non-zero'''
    return (np.array(list(d.values())) > 0).all()


def dist_subset(d: dict, keys: Iterable) -> dict:
    '''take a subset of a discrete distribution and normalizes (setting P (values not in subset) = 0 )
    i.e create a new discrete distribution from a subset of an existing one'''
    new_dist = {k: d[k] for k in keys}
    scale = sum(new_dist.values())
    new_dist = {k: v/scale for k, v in new_dist.items()}
    zero_keys = {k: 0 for k in d if (k not in keys)} ## set probability of excluded keys to 0
    new_dist.update(zero_keys)

    assert new_dist.keys() == d.keys(), 'dist subset failed' # ensure new dist and old dist have same key set
    return new_dist


class DiscreteSampler:
    '''takes in a probability distribution (as a dict) and returns sampler'''

    def __init__(self, d: dict):

        assert self.is_dist(d), f'argument is not a probability mass function'
        #sort probability dict by value
        els = sorted(list(d.keys()))
        probs = [d[i] for i in els]

        #generate inverse cdf (a.k.a quantile distribution function)
        probs = [sum(probs[:i+1]) for i in range(len(probs))]
        assert np.isclose(probs[-1], 1)  # make sure the distrbution adds up to 1
        self.qdf = dict(zip(probs, els))
        self.__table = d


    def is_dist(self, d: dict) -> bool:
        '''check if dict is a valid discrete distribution'''
        return np.isclose(sum(d.values()), 1.0) and ((np.array(list(d.values())) > 0).all())

    def __call__(self):
        #get random number from uniform distribution
        rn = np.random.uniform(0, 1)
        #find first quantile that is >= the random number generated
        for prob in self.qdf:
            if rn <= prob:
                return self.qdf[prob]


def arcconvert(arclen, radius=EARTH_RADIUS):
    theta_rad = arclen / radius
    deg = np.degrees(theta_rad) % 360 # just in case of bad inputs, make sure angle is in [0, 360]
    return abs(deg - 180) - 90

