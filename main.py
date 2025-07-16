
# ai_smart_meme_bot_v2.py

import time
import requests
import datetime
import hmac
import hashlib
import json
import urllib.parse
import random

# === CONFIG ===
API_KEY = "RQe7vdBeSfclsPqlHHbz3lzZ8WnpLp"
API_SECRET = "UQrDDgYEZMKT1CeizBd86JS9QywDYjAUgp3riWNE4G7tOFgjw1ftzfoX2Bxb"
BASE_URL = "https://testnet-api.delta.exchange"

CAPITAL = 2000
LEVERAGE = 4
MIN_MARGIN = 200
SCAN_INTERVAL = 60  # seconds

MEME_COINS = ["DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "FLOKIUSDT", "BONKUSDT"]

# === UTILITIES ===
def get_timestamp():
    d = datetime.datetime.utcnow()
    return str(int(d.timestamp()))

def sign_request(secret, message):
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

def body_string(body):
    return json.dumps(body, separators=(',', ':')) if body else ''

def query_string(query):
    if not query:
        return ''
    return '?' + '&'.join(f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in query.items())

def request(method, path, payload=None, query=None, auth=False):
    url = BASE_URL + path
    headers = {'Content-Type': 'application/json'}
    if auth:
        ts = get_timestamp()
        signature_data = method + ts + path + query_string(query) + body_string(payload)
        signature = sign_request(API_SECRET, signature_data)
        headers.update({
            'api-key': API_KEY,
            'timestamp': ts,
            'signature': signature
        })
    response = requests.request(method, url, headers=headers, params=query, data=body_string(payload))
    return response.json()

# === BOT LOGIC ===
def get_trend_strength(symbol):
    return random.randint(30, 100)  # Placeholder AI logic

def get_product_info():
    result = request("GET", "/v2/products")
    product_map = {}
    for product in result.get("result", []):
        symbol = product["symbol"]
        product_map[symbol] = {
            "price": float(product["spot_price"]),
            "contract_value": float(product["contract_value"]),
            "min_order_size": int(float(product.get("min_order_size", 1)))
        }
    return product_map

def calculate_lot(symbol, price, contract_value):
    value = (CAPITAL / len(MEME_COINS)) * LEVERAGE
    lot_size = value / (price * contract_value)
    return max(int(lot_size), 1)

def place_order(symbol, side, size):
    payload = {
        "product_symbol": symbol,
        "side": side,
        "size": size,
        "order_type": "market_order"
    }
    res = request("POST", "/v2/orders", payload=payload, auth=True)
    print("ORDER RESPONSE:", res)

def should_exit(entry_price, current_price, highest_price):
    trail_percent = 0.2
    if current_price < highest_price * (1 - trail_percent):
        return True
    return False

def run_bot():
    product_info = get_product_info()
    while True:
        print("\n[SCAN]", datetime.datetime.utcnow())
        entries = []
        for symbol in MEME_COINS:
            if symbol not in product_info:
                print(f"[SKIP] {symbol} not available in Delta Exchange")
                continue
            info = product_info[symbol]
            trend = get_trend_strength(symbol)
            if trend >= 60:
                entries.append((symbol, trend, info))

        if entries:
            entries.sort(key=lambda x: -x[1])
            top_symbol, trend, info = entries[0]
            price = info["price"]
            contract_value = info["contract_value"]
            lot = calculate_lot(top_symbol, price, contract_value)

            margin = lot * price * contract_value / LEVERAGE
            if margin < MIN_MARGIN:
                print(f"[SKIP] Not enough margin for {top_symbol}")
                time.sleep(SCAN_INTERVAL)
                continue

            if lot < info["min_order_size"]:
                print(f"[SKIP] Lot size {lot} < minimum order size {info['min_order_size']}")
                time.sleep(SCAN_INTERVAL)
                continue

            print(f"[ENTRY] {top_symbol} @ {price} | Trend: {trend} | Lot: {lot}")
            place_order(top_symbol, "buy", lot)
            entry_price = price
            highest = price

            while True:
                time.sleep(10)
                updated_info = get_product_info().get(top_symbol, {})
                new_price = updated_info.get("price", price)
                if new_price > highest:
                    highest = new_price
                if should_exit(entry_price, new_price, highest):
                    print(f"[EXIT] {top_symbol} @ {new_price} | Profit locked")
                    place_order(top_symbol, "sell", lot)
                    break
        else:
            print("No strong trend coins found.")
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    run_bot()
