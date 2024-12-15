from binance.client import Client
from store_order import *
from load_config import *
from collections import defaultdict
from datetime import datetime
import time
import threading
import os

# loads local configuration
config = load_config('config.yml')

# Initialize Binance Futures Client
client = Client(api_key=config['binance']['api_key'], api_secret=config['binance']['api_secret'], testnet=config['TRADE_OPTIONS']['TEST'])


def get_all_coins():
    """
    Returns all coins from Binance Futures.
    """
    return client.futures_ticker()


def generate_coin_seen_dict(all_coins):
    """
    Generate a dictionary of all coins currently listed.
    """
    coin_seen_dict = defaultdict(bool)
    for old_coin in all_coins:
        coin_seen_dict[old_coin['symbol']] = True
    return coin_seen_dict


def get_new_coins(coin_seen_dict, all_coins_recheck):
    """
    Detect new coins added to Binance Futures.
    """
    result = []
    for new_coin in all_coins_recheck:
        if not coin_seen_dict[new_coin['symbol']]:
            result.append(new_coin)
            coin_seen_dict[new_coin['symbol']] = True
    return result


def get_price(symbol):
    """
    Get the latest price for a symbol.
    """
    return float(client.futures_symbol_ticker(symbol=symbol)['price'])


def create_futures_order(symbol, volume, side, leverage=10):
    """
    Create a Futures order on Binance.
    :param symbol: The trading pair symbol (e.g., BTCUSDT)
    :param volume: The quantity to trade
    :param side: "SELL" for Short, "BUY" for Long
    :param leverage: Leverage for the trade
    """
    # Set leverage for the trading pair
    client.futures_change_leverage(symbol=symbol, leverage=leverage)

    # Place the order
    order = client.futures_create_order(
        symbol=symbol,
        side=side,
        type='MARKET',
        quantity=volume
    )
    return order


def main():
    """
    Main function to manage short trading logic.
    """
    # Load trade configuration
    tp = config['TRADE_OPTIONS']['TP']
    sl = config['TRADE_OPTIONS']['SL']
    enable_tsl = config['TRADE_OPTIONS']['ENABLE_TSL']
    tsl = config['TRADE_OPTIONS']['TSL']
    pairing = config['TRADE_OPTIONS']['PAIRING']
    qty = config['TRADE_OPTIONS']['QUANTITY']
    test_mode = config['TRADE_OPTIONS']['TEST']
    leverage = config['TRADE_OPTIONS']['LEVERAGE']

    # Initialize tracking for listed coins
    all_coins = get_all_coins()
    coin_seen_dict = generate_coin_seen_dict(all_coins)

    while True:
        try:
            # Load current orders
            if os.path.isfile('order.json'):
                order = load_order('order.json')
            else:
                order = {}

            # Check if new coins are listed
            all_coins_updated = get_all_coins()
            new_coins = get_new_coins(coin_seen_dict, all_coins_updated)

            if len(new_coins) > 0:
                print(f"New coins detected: {new_coins}")
                for coin in new_coins:
                    symbol = coin['symbol']
                    if pairing in symbol:
                        print(f"Preparing to short {symbol}")
                        price = get_price(symbol)
                        volume = qty / price  # Calculate quantity based on config

                        try:
                            if not test_mode:
                                short_order = create_futures_order(symbol, volume, side="SELL", leverage=leverage)
                                print(f"Short position opened: {short_order}")
                                order[symbol] = {
                                    'symbol': symbol,
                                    'price': price,
                                    'volume': volume,
                                    'time': datetime.timestamp(datetime.now()),
                                    'tp': tp,
                                    'sl': sl
                                }
                                store_order('order.json', order)
                            else:
                                print(f"Test mode: Simulated short order for {symbol}")
                                order[symbol] = {
                                    'symbol': symbol,
                                    'price': price,
                                    'volume': volume,
                                    'time': datetime.timestamp(datetime.now()),
                                    'tp': tp,
                                    'sl': sl
                                }
                        except Exception as e:
                            print(f"Error placing short order: {e}")

            # Manage active orders (e.g., closing based on SL/TP)
            for coin, details in list(order.items()):
                last_price = get_price(coin)
                stored_price = details['price']

                # Close short if SL or TP is hit
                if last_price > stored_price + (stored_price * sl / 100):
                    print(f"Stop-loss hit for {coin}. Closing position.")
                    try:
                        if not test_mode:
                            close_order = create_futures_order(coin, details['volume'], side="BUY")
                            print(f"Closed short position: {close_order}")
                        else:
                            print(f"Test mode: Simulated closing of short position for {coin}")
                        order.pop(coin)
                        store_order('order.json', order)
                    except Exception as e:
                        print(f"Error closing short position: {e}")

                elif last_price < stored_price - (stored_price * tp / 100):
                    print(f"Take-profit reached for {coin}. Closing position.")
                    try:
                        if not test_mode:
                            close_order = create_futures_order(coin, details['volume'], side="BUY")
                            print(f"Closed short position: {close_order}")
                        else:
                            print(f"Test mode: Simulated closing of short position for {coin}")
                        order.pop(coin)
                        store_order('order.json', order)
                    except Exception as e:
                        print(f"Error closing short position: {e}")

        except Exception as e:
            print(f"Error in main loop: {e}")

        time.sleep(config['TRADE_OPTIONS']['RUN_EVERY'])


if __name__ == '__main__':
    print('Starting Binance Futures Short Trading Bot...')
    main()
