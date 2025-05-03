import time
import threading
from telegram_bot import telegram_updater, get_bot_status, get_trade_config, send_trade_report, send_scan_status
from strategy import check_multi_tf_signals
from okx_api import place_order, get_balance, log_trade, get_consecutive_losses, reset_consecutive_losses, increase_loss_count
from trade_logger import save_trade_to_excel

# Danh sách 10 cặp coin
SYMBOLS = ["BTC", "ETH", "SOL", "TRX", "XPR", "ADA", "LINK", "XLM", "BCH", "LTC"]
TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

# Biến cờ để kiểm tra đã gửi thông báo scan hay chưa
scan_notified = False

def run_bot():
    global scan_notified
    print("Auto-trading bot is running...")

    while True:
        if not get_bot_status():
            scan_notified = False
            time.sleep(3)
            continue

        config = get_trade_config()
        capital_limit = config['capital']
        use_demo = config['use_demo']
        percent = config['percent']
        priority_config = config.get('priority', {})

        # Gửi thông báo scan chỉ 1 lần sau khi bật bot
        if not scan_notified:
            for symbol in SYMBOLS:
                send_scan_status(symbol, TIMEFRAMES)
                time.sleep(0.5)
            scan_notified = True

        for symbol in SYMBOLS:
            signal, leverage = check_multi_tf_signals(symbol)
            if signal and leverage and get_consecutive_losses() < 3:
                balance = get_balance(use_demo)

                # Ưu tiên vốn riêng từng coin nếu có
                coin_cfg = priority_config.get(symbol)
                capital_to_use = capital_limit
                if coin_cfg:
                    if isinstance(coin_cfg, str) and coin_cfg.endswith("USDT"):
                        try:
                            capital_to_use = float(coin_cfg.replace("USDT", "").strip())
                        except: pass
                    else:
                        try:
                            coin_percent = float(coin_cfg)
                            if 0 < coin_percent <= 100:
                                capital_to_use = round(capital_limit * (coin_percent / 100), 2)
                        except: pass
                else:
                    if 0 < percent <= 100:
                        capital_to_use = round(capital_limit * (percent / 100), 2)

                if balance >= capital_to_use:
                    success, result = place_order(symbol, signal, capital_to_use, leverage, use_demo)
                    log_trade(symbol, signal, result)

                    if success:
                        entry_price = result.get("entry", 0)
                        exit_price = result.get("exit", 0)
                        pnl = result.get("pnl", 0)
                        tp = entry_price * (1.3 if signal == "long" else 0.7)
                        sl = entry_price * 0.85 if signal == "long" else entry_price * 1.15

                        send_trade_report(symbol, signal, entry_price, capital_to_use, leverage, tp, sl)
                        save_trade_to_excel(symbol, signal, entry_price, exit_price, capital_to_use, pnl, result['status'])

                    if result['status'] == 'loss':
                        increase_loss_count()
                    else:
                        reset_consecutive_losses()
                else:
                    print(f"Không đủ vốn cho {symbol} (còn {balance}, cần {capital_to_use})")
            time.sleep(2)

        time.sleep(10)

if __name__ == "__main__":
    trading_thread = threading.Thread(target=run_bot)
    trading_thread.start()
    telegram_updater()