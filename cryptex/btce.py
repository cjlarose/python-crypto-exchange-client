import datetime

import pytz

from cryptex.exchange import Exchange
from cryptex.trade import Trade
from cryptex.order import Order
from cryptex.single_endpoint import SingleEndpoint, SignedSingleEndpoint
from cryptex.exception import APIException

class BTCEBase(object):
    @staticmethod
    def _format_timestamp(timestamp):
        return pytz.utc.localize(datetime.datetime.utcfromtimestamp(
            timestamp))

    @staticmethod
    def _pair_to_market(pair):
        return tuple([c.upper() for c in pair.split('_')])

    @staticmethod
    def _market_to_pair(market):
        return '_'.join((market[0].lower(), market[1].lower()))


class BTCEPublic(BTCEBase, SingleEndpoint):
    '''
    BTC-e public API https://btc-e.com/api/3/documentation
    All information is cached for 2 seconds on the server

    TODO: Add local caching to prevent frequent requests
    TODO: Format market pairs in output
    '''
    API_ENDPOINT = 'https://btc-e.com/api/3/'

    def _get_market_info(self, method, market, limit=0):
        params = {}
        if limit:
            if limit > 2000:
                raise ValueError('Maximum limit is 2000')
            params['limit'] = limit
        pair = BTCEPublic._market_to_pair(market)
        j = self.perform_get_request('/'.join((method, pair)), params=params)
        return j[pair]

    def get_info(self):
        '''
        Information about currently active pairs,
        such as the maximum number of digits after the decimal point in the auction,
        the minimum price, maximum price, minimum quantity purchase / sale,
        hidden=1whether the pair and the pair commission.
        '''
        j = self.perform_get_request('info')
        j['server_time'] = BTCEPublic._format_timestamp(j['server_time'])
        return j

    def get_ticker(self, market):
        '''
        Information about bidding on a pair, such as:
        the highest price, lowest price, average price, trading volume,
        trading volume in the currency of the last deal, the price of buying and selling.

        All information is provided in the last 24 hours.
        FIXME: What does that mean?
        '''
        j = self._get_market_info('ticker', market)
        j['updated'] = BTCEPublic._format_timestamp(j['updated'])
        return j

    def get_depth(self, market, limit=150):
        '''
        Information on active warrants pair.
        Takes an optional parameter limit which indicates how many orders you want to display (default 150, max 2000).
        '''
        return self._get_market_info('depth', market, limit)

    def get_trades(self, market, limit=150):
        '''
        Information on the latest deals.
        Takes an optional parameter limit which indicates how many orders you want to display (default 150, max 2000).
        '''
        j = self._get_market_info('trades', market, limit)
        for t in j:
            t['timestamp'] = BTCEPublic._format_timestamp(t['timestamp'])
        return j


class BTCE(BTCEBase, Exchange, SignedSingleEndpoint):
    API_ENDPOINT = 'https://btc-e.com/tapi'
    def __init__(self, key, secret):
        self.key = key
        self.secret = secret
        self.public = BTCEPublic()
    
    def perform_request(self, method, data={}):
        try:
            return super(BTCE, self).perform_request(method, data)
        except APIException as e:
            if e.message == 'no orders':
                return {}
            else:
                raise e

    @staticmethod
    def _format_trade(trade_id, trade):
        if trade['type'] == 'buy':
            trade_type = Trade.BUY
        else:
            trade_type = Trade.SELL

        base, counter = BTC._pair_to_market(order['pair'])

        return Trade(
            trade_id = trade_id,
            trade_type = trade_type,
            base_currency = base.upper(),
            counter_currency = counter.upper(),
            time = BTCE._format_timestamp(trade['timestamp']),
            order_id = trade['order_id'],
            amount = trade['amount'],
            price = trade['rate']
        )

    def get_my_trades(self):
        trades = self.perform_request('TradeHistory')
        return [BTCE._format_trade(t_id, t) for t_id, t in trades.iteritems()]

    @staticmethod
    def _format_order(order_id, order):
        if order['type'] == 'buy':
            order_type = Trade.BUY
        else:
            order_type = Trade.SELL

        base, counter = BTC._pair_to_market(order['pair'])

        return Order(
            order_id = order_id,
            order_type = order_type,
            base_currency = base.upper(),
            counter_currency = counter.upper(),
            time = BTCE._format_timestamp(order['timestamp_created']),
            amount = order['amount'],
            price = order['rate']
        )

    def get_my_open_orders(self):
        orders = self.perform_request('ActiveOrders')
        return [BTCE._format_order(o_id, o) for o_id, o in orders.iteritems()]

    def cancel_order(self, order_id):
        self.perform_request('CancelOrder', {'order_id': order_id})
        return None

    def get_markets(self):
        return [
            BTC._pair_to_market(pair)
            for pair in self.public.get_info()
        ]

    def _create_order(self, market, order_type, quantity, price):
        params = {
            'pair': BTC._market_to_pair(market),
            'type': order_type,
            'amount': quantity,
            'rate': price
        }
        return self.perform_request('Trade', params)

    def buy(self, market, quantity, price):
        response = self._create_order(market, 'buy', quantity, price)
        return response['order_id']

    def sell(self, market, quantity, price):
        response = self._create_order(market, 'sell', quantity, price)
        return response['order_id']
