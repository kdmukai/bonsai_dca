import base64
import datetime
import decimal
import json
import hashlib
import hmac
import math
import requests
import time

from decimal import Decimal

from models import Order



class GeminiRequestException(Exception):
    def __init__(self, status_code, response_json):
        self.status_code = status_code
        self.response_json = response_json
        super().__init__(json.dumps(self.response_json))



class GeminiApiConnection(object):

    def __init__(self, client_key: str, client_secret: str):
        self.client_key = client_key
        self.client_secret = client_secret.encode()


    def _make_public_request(self, endpoint: str):
        base_url = "https://api.gemini.com/v1"
        url = base_url + endpoint

        r = requests.get(url)

        if r.status_code == 200:
            return r.json()
        else:
            raise GeminiRequestException(r.status_code, r.json())


    def _make_authenticated_request(self, verb: str, endpoint: str, payload: dict = {}):
        base_url = "https://api.gemini.com/v1"
        url = base_url + endpoint

        t = datetime.datetime.now()

        # Include microsecond precision to avoid InvalidNonce errors for duplicate nonces
        #   on consecutive calls.
        payload["nonce"] = str(int(time.mktime(t.timetuple()) * 1000 + t.microsecond / 1000))
        payload["request"] = "/v1" + endpoint

        encoded_payload = json.dumps(payload).encode()
        b64 = base64.b64encode(encoded_payload)
        signature = hmac.new(self.client_secret, b64, hashlib.sha384).hexdigest()

        request_headers = { 'Content-Type': "text/plain",
                            'Content-Length': "0",
                            'X-GEMINI-APIKEY': self.client_key,
                            'X-GEMINI-PAYLOAD': b64,
                            'X-GEMINI-SIGNATURE': signature,
                            'Cache-Control': "no-cache" }

        r = requests.post(url,
                          data=None,
                          headers=request_headers)

        if r.status_code == 200:
            return r.json()
        else:
            raise GeminiRequestException(r.status_code, r.json())


    """ **************************** Public Market Data **************************** """
    def symbol_details(self, market: str):
        """
            {
                'symbol': 'BTCUSD',
                'base_currency': 'BTC',
                'quote_currency': 'USD',
                'tick_size': 0.00000001,
                'quote_increment': 0.01,
                'min_order_size': '0.00001',
                'status': 'open'
            }
        """
        return self._make_public_request(f"/symbols/details/{market}")


    def current_order_book(self, market: str):
        """
            {
                "bids": [
                    {
                        "price": "3607.85",
                        "amount": "6.643373",
                        "timestamp": "1547147541"
                    },
                    ...,
                ],
                "asks": [
                    {
                        "price": "3607.86",
                        "amount": "14.68205084",
                        "timestamp": "1547147541"
                    },
                    ...,
                ]
            }
        """
        return self._make_public_request(f"/book/{market}")



    """ **************************** Authenticated Requests **************************** """
    def new_order(self, market: str, side: str, amount: Decimal, price: Decimal):
        if side not in ["buy", "sell"]:
            raise Exception(f"Invalid 'side': {side}")

        payload = {
            "symbol": market,
            "amount": str(amount),
            "price": str(price),
            "side": side,
            "type": "exchange limit",
            "options": ["maker-or-cancel"]  
        }
        return self._make_authenticated_request("POST", "/order/new", payload=payload)


    def order_status(self, order_id: str):
        payload = {
            "order_id": order_id,
            "include_trades": False,
        }
        return self._make_authenticated_request("POST", "/order/status", payload=payload)



class GeminiExchange(object):
    from models import APICredential
    exchange = APICredential.EXCHANGE__GEMINI

    def __init__(self, api_credential):
        self.api_credential = api_credential
        self.api_conn = GeminiApiConnection(client_key=api_credential.client_key, client_secret=api_credential.client_secret)


    def initialize_market(self, market_name, amount_currency, order_side):
        self.market_name = market_name
        self.amount_currency = amount_currency
        self.order_side = order_side
        symbol_details = self.api_conn.symbol_details(market_name)

        self.base_currency = symbol_details.get("base_currency")
        self.quote_currency = symbol_details.get("quote_currency")
        self.base_min_size = Decimal(str(symbol_details.get("min_order_size"))).normalize()
        self.base_increment = Decimal(str(symbol_details.get("tick_size"))).normalize()
        self.quote_increment = Decimal(str(symbol_details.get("quote_increment"))).normalize()

        if amount_currency == self.quote_currency:
            self.amount_currency_is_quote_currency = True
        elif amount_currency == self.base_currency:
            self.amount_currency_is_quote_currency = False
        else:
            raise Exception(f"amount_currency {amount_currency} not in market {self.market_name}")


    def calculate_order_price(self):
        order_book = self.api_conn.current_order_book(self.market_name)

        bid = Decimal(order_book.get('bids')[0].get('price')).quantize(self.quote_increment)
        ask = Decimal(order_book.get('asks')[0].get('price')).quantize(self.quote_increment)

        # Avg the bid/ask but round to nearest quote_increment
        if self.order_side == "buy":
            midmarket_price = (math.floor((ask + bid) / Decimal('2.0') / self.quote_increment) * self.quote_increment).quantize(self.quote_increment, decimal.ROUND_DOWN)
        else:
            midmarket_price = (math.floor((ask + bid) / Decimal('2.0') / self.quote_increment) * self.quote_increment).quantize(self.quote_increment, decimal.ROUND_UP)
        print(f"ask: ${ask}")
        print(f"bid: ${bid}")
        print(f"midmarket_price: ${midmarket_price}")

        return midmarket_price


    def place_limit_order(self, amount, price):
        try:
            if self.amount_currency_is_quote_currency:
                result = self.api_conn.new_order(
                    market=self.market_name,
                    side=self.order_side,
                    amount=float((amount / price).quantize(self.base_increment)),
                    price=price
                )
            else:
                result = self.api_conn.new_order(
                    market=self.market_name,
                    side=self.order_side,
                    amount=float(amount.quantize(self.base_increment)),
                    price=price
                )
        except GeminiRequestException as e:
            # sns.publish(
            #     TopicArn=sns_topic,
            #     Subject=f"ERROR placing {self.base_currency} {order_side} order: {e.response_json.get('reason')}",
            #     Message=json.dumps(e.response_json, indent=4)
            # )
            print(json.dumps(e.response_json, indent=4))
            exit()
        return result


    def place_order(self, market_name, order_side, amount, amount_currency, schedule=None):
        self.initialize_market(market_name, amount_currency, order_side)
        price = self.calculate_order_price()
        result = self.place_limit_order(amount, price)
        print(json.dumps(result, indent=4))

        order = Order.create(
            schedule=schedule,
            credential=self.api_credential,
            exchange=GeminiExchange.exchange,
            order_id=result.get("order_id"),
            market_name=market_name,
            order_side=order_side,
            amount=amount,
            amount_currency=amount_currency,
            raw_data=result
        )

        # Sometimes orders are rejected because the order book moved
        if result.get("is_cancelled") and "reason" in result and result.get("reason") == "MakerOrCancelWouldTake":
            order.status = Order.STATUS__REJECTED
            order.is_live = False
            order.save()

            # Reset the schedule so it runs again
            if schedule:
                schedule.undo_last_run()

        return order


    def place_scheduled_order(self, schedule):
        return self.place_order(
            schedule.market_name,
            schedule.order_side,
            schedule.amount,
            schedule.amount_currency,
            schedule=schedule
        )


    def update_order(self, order):
        result = self.api_conn.order_status(order.order_id)

        if result.get("is_cancelled"):
            order.status = Order.STATUS__CANCELLED
            order.is_live = False
        elif not result.get("is_live"):
            order.status = Order.STATUS__COMPLETE
            order.is_live = False

        order.raw_data = result
        order.save()


