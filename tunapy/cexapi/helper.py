from logging import Logger

from octopuspy.exchange.base_restapi import ClientParams
from octopuspy.exchange.binance_restapi import BnSpotClient
from octopuspy.exchange.binance_future_restapi import BnFutureClient    # Portfolio margin
from octopuspy.exchange.binance_umfuture_restapi import BnUMFutureClient    # UMFuture
from octopuspy.exchange.okx_restapi import OkxSpotClient
from octopuspy.exchange.okx_future_restapi import OkxFutureClient
from octopuspy.exchange.bifu_restapi import BifuSpotClient
from octopuspy.exchange.bifu_future_restapi import BifuFutureClient

# CONST EXCHANGE CLIENT TYPE
EXCHANGE_CHANNEL = {
    "binance_spot" : BnSpotClient,
    "binance_UMFuture" : BnUMFutureClient,
    "binance_portfolio_margin" : BnFutureClient,
    "okx_spot" : OkxSpotClient,
    "okx_future" : OkxFutureClient,
    "bifu_spot" : BifuSpotClient,
    "bifu_future" : BifuFutureClient
}

def _list_channels():
    return EXCHANGE_CHANNEL.keys()

def _get_channel(exchange_name:str):
    return EXCHANGE_CHANNEL.get(exchange_name, None)

def get_market_client(exchange: str, logger: Logger = None):
    """ create public market client
    """
    return get_private_client(exchange, '', '', passphrase='', logger=logger)

def get_private_client(
    exchange: str,
    api_key: str,
    api_secret: str,
    passphrase: str = '',
    logger: Logger = None
):
    """ create private user client
    """
    client_type = _get_channel(exchange_name=exchange)
    if not client_type:
        client_params = ClientParams(base_url="",
                                     api_key=api_key,
                                     secret=api_secret,
                                     passphrase=passphrase)
        return client_type(params=client_params, logger=logger)
    return None
