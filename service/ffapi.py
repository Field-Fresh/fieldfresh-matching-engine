import requests
from ffengine.data import OrderSet, BuyOrder, SellOrder
from ffengine.simulation import TestCase

from datetime import datetime

SUCCESS_STATUS = 200

timestamp_convert = lambda i: datetime.fromtimestamp(i).isoformat()

class APITester:
    '''Provides an interface to the FieldFresh API. Is intialized with test user credentials
    Note: make sure to called .signin() before trying anything else '''

    def __init__(self, config: dict):
        assert ("api-url" in config and "test-user" in config and "test-user-pwd" in config), "Incomplete test configuration: api-url, test-user or test-user-pwd is missing"

        self.API_URL = config["api-url"]
        self.TEST_USER = config["test-user"]
        self.TEST_USER_PWD = config["test-user-pwd"]

        self.endpoint_signin = self.API_URL + "/auth/signin"
        self.endpoint_proxy_create = self.API_URL + "/proxy/new"
        self.endpoint_buy_create = self.API_URL + "/orders/buy"
        self.endpoint_sell_create = self.API_URL + "/orders/sell"

        _r = requests.get(self.API_URL+"/products")
        assert _r.status_code == SUCCESS_STATUS, "API not setup or products DB not intialized properly or api-url is wrong"
        self.products = {i: d['id'] for i, d in enumerate(_r.json()['products'])}

    # TODO: remove this when API auth is fixed
    def set_test_user_id(self, test_user_id):
        '''temporary - should be removed once API auth is fixed'''
        self.test_userId = test_user_id

    # TODO: remove this when API auth is fixed
    def init_test_user_proxy(self):
        requests.post(url=self.endpoint_proxy_create, json={
                            "userId": self.test_userId,
                            "name": "test-proxy-init-0",
                            "streetAddress": "TEST",
                            "city": "TEST",
                            "province": "TEST",
                            "country": "TEST",
                            "postalCode": "TEST",
                            "lat": 0,
                            "long": 0
                        } )
    
    def signin(self):
        signin_resp = requests.post(
            url=self.endpoint_signin,
            json={
                "email": self.TEST_USER,
                "password": self.TEST_USER_PWD
            }
        ).json()

        self.test_userToken = signin_resp['cognitoJWT']['access_token']
        self.test_userId = signin_resp['user']['profileId']
    
    def create_proxy(self, proxy_name: str, lat: float, lon: float):
        create_proxy_resp = requests.post(url=self.endpoint_proxy_create, json={
            "userId": self.test_userId,
            "name": proxy_name,
            "streetAddress": "TEST",
            "city": "TEST",
            "province": "TEST",
            "country": "TEST",
            "postalCode": "TEST",
            "lat": lat,
            "long": lon
        } ).json()

        return create_proxy_resp["id"]
    
    def create_buy_order(self, proxy_id: str, buyorder: BuyOrder):
        response = requests.post(url=self.endpoint_buy_create, json={
            "proxyId": proxy_id,
            "buyProducts": [{
                "earliestDate": timestamp_convert(buyorder.time_activation),
                "latestDate": timestamp_convert(buyorder.time_expiry),
                "maxPriceCents": buyorder.max_price_cents,
                "volume": buyorder.quantity,
                "productId": self.products[buyorder.int_product_id]
            }]
        },
        headers={'Authorization': f'Bearer {self.test_userToken}'}
        )

        assert response.status_code == SUCCESS_STATUS, 'create buy order failed'

        # print(response.json())
        
        return response.json()['buyProducts'][0]["id"]
    
    def create_sell_order(self, proxy_id: str, sellorder: BuyOrder):
        response = requests.post(url=self.endpoint_sell_create, json={
            "proxyId": proxy_id,
            "sellProducts": [{
                "earliestDate": timestamp_convert(sellorder.time_activation),
                "latestDate": timestamp_convert(sellorder.time_expiry),
                "minPriceCents": sellorder.min_price_cents,
                "volume": sellorder.quantity,
                "productId": self.products[sellorder.int_product_id],
                "serviceRadius": sellorder.service_range
            }]
        },
        headers={'Authorization': f'Bearer {self.test_userToken}'}
        )

        assert response.status_code == SUCCESS_STATUS, 'create sell order failed'

        return response.json()["sellProducts"][0]["id"]

    
    def fill_test_data(self, orderset: OrderSet):
        n_products = len(self.products)

        new_order_set = OrderSet()
        
        # fill buy orders
        buy_proxies = {}
        for buyorder in orderset.iter_buy_orders():
            assert buyorder.int_product_id < n_products, "Bad test case, cannot use more products than there are in DB. Add test products to DB or use test case with less products"

            if not (buyorder.int_buyer_id in buy_proxies):
                proxy_id = self.create_proxy(
                    proxy_name="TEST-" + buyorder.buyer_id,
                    lat=buyorder.lat, lon=buyorder.long)

                buy_proxies[buyorder.int_buyer_id] = proxy_id
            
            proxy_id = buy_proxies[buyorder.int_buyer_id]
            product_id = self.products[buyorder.int_product_id]
            order_id = self.create_buy_order(proxy_id, buyorder)

            buyorder.buyer_id = proxy_id
            buyorder.product_id = product_id
            buyorder.order_id = order_id

            # new_order_set.add_buy_order(buyorder)
            
        # fill sell orders
        sell_proxies = {}
        for sellorder in orderset.iter_sell_orders():
            assert sellorder.int_product_id < n_products, "Bad test case, cannot use more products than there are in DB. Add test products to DB or use test case with less products"

            if not (sellorder.int_seller_id in sell_proxies):
                proxy_id = self.create_proxy(
                    proxy_name="TEST-" + sellorder.seller_id,
                    lat=sellorder.lat, lon=sellorder.long)

                sell_proxies[sellorder.int_seller_id] = proxy_id  
            
            proxy_id = sell_proxies[sellorder.int_seller_id]
            product_id = self.products[sellorder.int_product_id]
            order_id = self.create_sell_order(proxy_id, sellorder)

            sellorder.seller_id = proxy_id
            sellorder.product_id = product_id
            sellorder.order_id = order_id

            # new_order_set.add_sell_order(sellorder)
            




def test_it_up():
    import json
    api_test_config = json.load(open("service/api_test_config.json"))

    from ffengine.simulation import TestCase

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

    print("SETTING UP API")
    api = APITester(api_test_config)

    # setup and signin
    api.set_test_user_id("u_34enPEkffuV9dJdMhabaMT")
    api.init_test_user_proxy()
    api.signin()

    api.fill_test_data(test_case1.order_set)

    return api, test_case1.order_set
    


    
