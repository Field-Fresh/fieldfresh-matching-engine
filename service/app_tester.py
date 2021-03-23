from .app import MatchingEngineService
from .ffapi import APITester

from ffengine.simulation import TestCase
from ffengine.optim.engines import OMMEngine
from ffengine.data import MatchSet, Match

import tomodachi
import json

class TestMatchingEngineService(MatchingEngineService):

    @tomodachi.http("GET", r"/health")
    async def health_check(self, request):
        return 200, json.dumps({"status": "healthy - testing mode"})

    
    @tomodachi.schedule(immediately=True)
    def api_test(self):

        self.DEBUG_MODE = True # NOTE: if this is not set, assertion endpoints will fail (currently this enables logging of matches)
        api_test_config = json.load(open("service/api_test_config.json"))

        ## setup: create test data
        
        # define sets for test case
        I1 = list(range(5))
        J1 = list(range(5))
        K1 = list(range(3))

        self.MODEL_CONFIG['unit_tcost'] = 1 ## Any parameters that the model needs should be set here

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
            unit_tcost=self.MODEL_CONFIG['unit_tcost']
        )

        ## setup API for test
        print("SETTING UP API")
        api = APITester(api_test_config)

        # setup and signin
        api.set_test_user_id("u_34enPEkffuV9dJdMhabaMT")
        api.init_test_user_proxy()
        api.signin()

        # create orders
        api.fill_test_data(test_case1.order_set)

        # run matches
        stats, matches = test_case1.run(OMMEngine) # This should be done after API setup so that test case order_ids can be updated with API ids

        self.TRUE_MATCHES = matches


    @tomodachi.http("GET", r"/test-results-data")
    async def test_results_data(self, request):
        '''get detailed matches for comparison if assertion fails'''
        true_matches = self.TRUE_MATCHES
        # while matching_not_done -> spin
        true_results = { match.match_id: match.to_dict() for match in true_matches.iter_matches()}
        orderset_id = list(self._matchsets.keys())[-1]
        print(orderset_id, type(orderset_id))
        # get matches from api, assume round 0 is the one we want
        results = { match.match_id: match.to_dict() for match in self._matchsets[orderset_id].iter_matches()}

        return 200, json.dumps({"true": true_results, "api": results})


    @tomodachi.http("GET", r"/test-result")
    async def test_result(self, request):
        '''Assert that matches are the same before passing to API and after'''
        import pandas as pd
        true_matches = self.TRUE_MATCHES
        # while matching_not_done -> spin
        true_results = { match.match_id: match.to_dict() for match in true_matches.iter_matches()}
        orderset_id = list(self._matchsets.keys())[-1]

        # get matches from api, assume round 0 is the one we want
        results = { match.match_id: match.to_dict() for match in self._matchsets[orderset_id].iter_matches()}

        dfTrue = pd.DataFrame(true_results).T.set_index(['buyOrder', 'sellOrder']).rename(lambda colname: colname + '_true', axis=1)
        dfActual = pd.DataFrame(results).T.set_index(['buyOrder', 'sellOrder'])

        comparer = pd.concat([dfActual, dfTrue], axis=1).drop(['matchId'], axis=1)

        test_pass = (comparer['volume'] == comparer['volume_true']).all() and (comparer['priceCents'] == comparer['priceCents_true']).all()
        return 200, json.dumps({"test-result": str(test_pass)})

