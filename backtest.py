from strategy import fetch_ohlcv, get_signal
import pandas as pd

def backtest_symbol(symbol, capital=50, leverage=5):
    df = fetch_ohlcv(symbol)
    if df is None or len(df) < 30:
        return f"{symbol}: Không đủ dữ liệu."

    wins = 0
    losses = 0
    trades = 0
    pnl = 0

    for i in range(30, len(df) - 1):
        window = df.iloc[:i+1].copy()
        window['ma5'] = window['close'].rolling(window=5).mean()
        window['ma20'] = window['close'].rolling(window=20).mean()
        window['rsi'] = compute_rsi(window['close'], 14)
        last = window.iloc[-1]
        signal = None

        if (
            last['ma5'] > last['ma20'] and
            last['rsi'] < 30 and
            last['volume'] > window['volume'].rolling(10).mean().iloc[-1] * 1.5
        ):
            signal = "long"
        elif (
            last['ma5'] < last['ma20'] and
            last['rsi'] > 70 and
            last['volume'] > window['volume'].rolling(10).mean().iloc[-1] * 1.5
        ):
            signal = "short"

        if signal:
            entry = window['close'].iloc[-1]
            exit_price = df['close'].iloc[i+1]
            qty = (capital * leverage) / entry
            profit = qty * (exit_price - entry) if signal == "long" else qty * (entry - exit_price)
            pnl += profit
            trades += 1
            if profit >= 0:
                wins += 1
            else:
                losses += 1

    winrate = (wins / trades * 100) if trades else 0
    return f"{symbol} | Lệnh: {trades} | Winrate: {winrate:.1f}% | Lợi nhuận: {pnl:.2f} USDT"

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def run_backtest_all():
    results = []
    for symbol in ["BTC", "ETH", "SOL", "TRX", "XPR", "ADA", "LINK", "XLM", "BCH", "LTC"]:
        result = backtest_symbol(symbol)
        results.append(result)
    return "\n".join(results)

if __name__ == "__main__":
    print(run_backtest_all())