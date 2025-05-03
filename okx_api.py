import requests
import time
import hmac
import base64
import json
import hashlib

# Cấu hình API key demo và real
API_KEYS = {
    "demo": {
        "api_key": "0dc2a4c1-212d-425b-82d8-ee5c863ca290",
        "api_secret": "D2888293351575A436B9306919C31710",
        "passphrase": "Nhokung5531@"
    },
    "real": {
        "api_key": "your_real_api_key",
        "api_secret": "your_real_api_secret",
        "passphrase": "your_real_passphrase"
    }
}

BASE_URLS = {
    "demo": "https://www.okx.com",
    "real": "https://www.okx.com"
}

consecutive_losses = 0

def get_timestamp():
    return time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())

def sign_request(timestamp, method, request_path, body, api_secret):
    message = f'{timestamp}{method.upper()}{request_path}{body}'
    mac = hmac.new(api_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

def send_signed_request(method, path, body_dict, use_demo):
    api = API_KEYS["demo"] if use_demo else API_KEYS["real"]
    url = BASE_URLS["demo"] + path
    timestamp = get_timestamp()
    body = json.dumps(body_dict) if body_dict else ""

    signature = sign_request(timestamp, method, path, body, api["api_secret"])

    headers = {
        "OK-ACCESS-KEY": api["api_key"],
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": api["passphrase"],
        "Content-Type": "application/json"
    }

    if use_demo:
        headers["x-simulated-trading"] = "1"

    response = requests.request(method, url, headers=headers, data=body)
    return response.json()

def get_current_price(symbol):
    url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}-USDT-SWAP"
    response = requests.get(url).json()
    return float(response['data'][0]['last']) if 'data' in response and response['data'] else 0

def get_instrument_details(symbol):
    url = f"https://www.okx.com/api/v5/public/instruments?instType=SWAP&uly={symbol}-USDT"
    response = requests.get(url).json()
    if "data" in response and response["data"]:
        return response["data"][0]
    return None

def round_qty_to_lot_size(qty, lot_size):
    steps = int(qty / lot_size)
    return round(steps * lot_size, 4)

def set_leverage(symbol, leverage, use_demo):
    data = {
        "instId": f"{symbol}-USDT-SWAP",
        "lever": str(leverage),
        "mgnMode": "isolated"
    }
    res = send_signed_request("POST", "/api/v5/account/set-leverage", data, use_demo)
    print("[Leverage] Thiết lập:", res)
    return res

def place_order(symbol, side, capital, leverage, use_demo):
    try:
        entry = get_current_price(symbol)
        if entry == 0:
            return False, {"status": "failed_to_fetch_price"}

        instrument = get_instrument_details(symbol)
        if not instrument:
            return False, {"status": "failed_to_fetch_instrument"}

        # Thiết lập đòn bẩy
        set_leverage(symbol, leverage, use_demo)

        lot_size = float(instrument["lotSz"])
        qty_raw = (capital * leverage) / entry
        qty = round_qty_to_lot_size(qty_raw, lot_size)

        if qty < lot_size:
            return False, {"status": "qty_too_small", "required_min_qty": lot_size}

        order_data = {
            "instId": f"{symbol}-USDT-SWAP",
            "tdMode": "isolated",
            "side": "buy" if side == "long" else "sell",
            "posSide": "long" if side == "long" else "short",
            "ordType": "market",
            "sz": str(qty)
        }

        response = send_signed_request("POST", "/api/v5/trade/order", order_data, use_demo)

        if "data" in response and response.get("code") == "0":
            return True, {
                "status": "order_placed",
                "entry": entry,
                "qty": qty,
                "leverage": leverage,
                "raw": response
            }
        else:
            return False, {"status": "order_failed", "detail": response}
    except Exception as e:
        return False, {"status": "error", "exception": str(e)}

def get_balance(use_demo):
    return 1000

def log_trade(symbol, side, result):
    print(f"[LOG] {symbol} - {side} - {result}")

def get_open_orders(use_demo):
    return "Chưa hỗ trợ xem lệnh mở"

def get_consecutive_losses():
    global consecutive_losses
    return consecutive_losses

def reset_consecutive_losses():
    global consecutive_losses
    consecutive_losses = 0

def increase_loss_count():
    global consecutive_losses
    consecutive_losses += 1