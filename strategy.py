import requests
import pandas as pd
import numpy as np
import random

TRADABLE_SYMBOLS = [
    "BTC", "ETH", "SOL", "TRX", "XPR", "ADA", "LINK", "XLM", "BCH", "LTC"
]

TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

def fetch_ohlcv(symbol, timeframe="15m"):
    try:
        url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}-USDT-SWAP&bar={timeframe}&limit=100"
        response = requests.get(url)
        data = response.json()
        if 'data' not in data:
            return None

        df = pd.DataFrame(data['data'], columns=[
            "timestamp", "open", "high", "low", "close", "volume", "vol_ccy", "vol_usd", "confirm", "instType", "instId", "bar"
        ])
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        df = df.iloc[::-1].reset_index(drop=True)
        return df
    except:
        return None

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def compute_adx(df, period=14):
    df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
    df['plus_dm'] = df['high'].diff()
    df['minus_dm'] = df['low'].diff()
    df['plus_dm'] = np.where((df['plus_dm'] > df['minus_dm']) & (df['plus_dm'] > 0), df['plus_dm'], 0.0)
    df['minus_dm'] = np.where((df['minus_dm'] > df['plus_dm']) & (df['minus_dm'] > 0), df['minus_dm'], 0.0)
    tr14 = df['tr'].rolling(window=period).sum()
    plus_di14 = 100 * (df['plus_dm'].rolling(window=period).sum() / tr14)
    minus_di14 = 100 * (df['minus_dm'].rolling(window=period).sum() / tr14)
    dx = (abs(plus_di14 - minus_di14) / (plus_di14 + minus_di14)) * 100
    return dx.rolling(window=period).mean().iloc[-1]

def analyze_single_timeframe(df):
    if df is None or len(df) < 30:
        return None

    df['ma5'] = df['close'].rolling(window=5).mean()
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['rsi'] = compute_rsi(df['close'], 14)

    adx = compute_adx(df)
    last = df.iloc[-1]
    volume_spike = last['volume'] > df['volume'].rolling(10).mean().iloc[-1] * 1.5

    if adx > 20 and volume_spike:
        if last['ma5'] > last['ma20'] and last['rsi'] < 35:
            return "long"
        elif last['ma5'] < last['ma20'] and last['rsi'] > 65:
            return "short"
    return None

def assess_risk(df):
    rsi = compute_rsi(df['close'], 14).iloc[-1]
    volatility = df['close'].rolling(10).std().iloc[-1]
    vol_spike = df['volume'].iloc[-1] / df['volume'].rolling(10).mean().iloc[-1]

    if rsi < 20 or rsi > 80 or vol_spike > 2.0 or volatility > 0.05:
        return random.randint(3, 4)
    elif rsi < 30 or rsi > 70 or vol_spike > 1.5:
        return random.randint(5, 6)
    else:
        return random.randint(7, 8)

def check_multi_tf_signals(symbol):
    long_votes = 0
    short_votes = 0
    last_df = None

    for tf in TIMEFRAMES:
        df = fetch_ohlcv(symbol, tf)
        if df is not None:
            signal = analyze_single_timeframe(df)
            last_df = df
            if signal == "long":
                long_votes += 1
            elif signal == "short":
                short_votes += 1

    if long_votes >= 3:
        return "long", assess_risk(last_df)
    elif short_votes >= 3:
        return "short", assess_risk(last_df)
    return None, None

# Giữ nguyên để tương thích với main.py cũ
def should_place_order(symbol):
    signal, _ = check_multi_tf_signals(symbol)
    return signal is not None