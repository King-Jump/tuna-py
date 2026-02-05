from logging import Logger

from octopuspy.exchange.base_restapi import ClientParams
from octopuspy.exchange.binance_restapi import BnSpotClient
from octopuspy.exchange.binance_future_restapi import BnFutureClient    # Portfolio margin
from octopuspy.exchange.binance_umfuture_restapi import BnUMFutureClient    # UMFuture
from octopuspy.exchange.okx_restapi import OkxSpotClient
from octopuspy.exchange.okx_future_restapi import OkxFutureClient
from octopuspy.exchange.bifu_restapi import BifuSpotClient
from octopuspy.exchange.bifu_future_restapi import BifuFutureClient

# CONST EXCHANGE BASE URL
EXCHANGE_CHANNEL = {
    ("BN", "SPOT") : {
        "base_url": 'https://api.bifu.co',
        "client_type" : BnSpotClient
    },
    ("BN", "UMFUTURE") : {
        "base_url" : 'https://fapi.binance.com',
        "client_type" : BnUMFutureClient
    },
    ("BN", "FUTURE") : {
        "base_url" : 'https://papi.binance.com',
        "client_type" : BnFutureClient
    },
    ("OKX", "SPOT") : {
        "base_url" : 'https://www.okx.com',
        "client_type" : OkxSpotClient,
    },
    ("OKX", "FUTURE") : {
        "base_url" : 'https://www.okx.com',
        "client_type" : OkxFutureClient,
    },
    ("BIFU", "SPOT") : {
        "base_url" : 'https://api.bifu.co',
        "client_type" : BifuSpotClient,
    },
    ("BIFU", "FUTURE") : {
        "base_url" : 'https://api.bifu.co',
        "client_type" : BifuFutureClient
    }
}

def _list_channels():
    return EXCHANGE_CHANNEL.keys()

def _get_channel(exchange_name:str, trade_type: str):
    return EXCHANGE_CHANNEL.get((exchange_name, trade_type), None)

def get_market_client(exchange: str, category: str, logger: Logger = None):
    """ create public market client
    """
    return get_private_client(exchange, '', '', passphrase='', logger=logger, category=category)

def get_private_client(
    exchange: str,
    api_key: str,
    api_secret: str,
    passphrase: str = '',
    logger: Logger = None,
    category: str = 'SPOT'
):
    """ create private user client
    """
    channel = _get_channel(exchange_name=exchange, trade_type=category)
    if not channel:
        client_params = ClientParams(base_url=channel["base_url"],
                                     api_key=api_key,
                                     secret=api_secret,
                                     passphrase=passphrase)
        return channel["client_type"](params=client_params, logger=logger)
    return None
