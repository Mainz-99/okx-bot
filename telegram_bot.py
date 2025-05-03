# --- Bắt đầu shim cho imghdr (fix cho Python 3.13 trên Pydroid3) ---
import sys, importlib.util
if 'imghdr' not in sys.modules:
    spec = importlib.util.spec_from_loader('imghdr', loader=None)
    imghdr_mod = importlib.util.module_from_spec(spec)
    def what(file, h=None):
        if h is None:
            h = file.read(32)
            file.seek(0)
        if h.startswith(b'\xff\xd8'): return 'jpeg'
        if h.startswith(b'\x89PNG\r\n\x1a\n'): return 'png'
        if h[:6] in (b'GIF87a', b'GIF89a'): return 'gif'
        return None
    imghdr_mod.what = what
    sys.modules['imghdr'] = imghdr_mod
# --- Kết thúc shim ---

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import requests
from datetime import datetime

TELEGRAM_TOKEN = '7670311695:AAES35GUOlZjDx_reyteUm9vS87dnLtWXmc'
AUTHORIZED_USER_ID = 7842456904

bot_running = False
use_demo = True
capital_limit = 50
capital_percent = 100
leverage = 5

coin_allocation = {}  # Dạng { 'SOL': {'type': 'percent', 'value': 10}, 'BTC': {'type': 'usdt', 'value': 20} }

selected_symbols = ["BTC", "ETH", "SOL", "TRX", "XPR", "ADA", "LINK", "XLM", "BCH", "LTC"]
custom_symbols = []

# --- Hàm khởi động bot ---
def start(update: Update, context: CallbackContext):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        update.message.reply_text("Bạn không được cấp quyền sử dụng bot.")
        return
    update.message.reply_text("Chào mừng bạn đến với OKX Bot", reply_markup=get_menu_keyboard())
    send_capital_and_status()

# --- Giao diện menu chính ---
def get_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Lựa chọn", callback_data='options')],
        [InlineKeyboardButton("Bật Bot" if not bot_running else "Tắt Bot", callback_data='toggle_bot')],
        [InlineKeyboardButton("/start lại", callback_data='start_again')]
    ])

def get_capital_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Ưu tiên riêng từng coin", callback_data='input_coin_allocation')],
        [InlineKeyboardButton("Nhập số vốn giới hạn", callback_data='input_capital')],
        [InlineKeyboardButton("Nhập % vốn cho mỗi lệnh", callback_data='input_percent')]
    ])

def get_options_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Chuyển sang Giao dịch Thật" if use_demo else "Chuyển sang Demo", callback_data='toggle_demo')],
        [InlineKeyboardButton("Đặt Giới hạn Vốn", callback_data='set_capital')],
        [InlineKeyboardButton("Chạy Backtest", callback_data='run_backtest')],
        [InlineKeyboardButton("Xem Lệnh Đang Mở", callback_data='open_orders')],
        [InlineKeyboardButton("Chọn Coin", callback_data='select_coin')],
        [InlineKeyboardButton("Danh sách Coin", callback_data='manage_coins')]
    ])

def get_manage_coin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("THÊM", callback_data='add_coin')],
        [InlineKeyboardButton("XOÁ", callback_data='remove_coin')]
    ])

# --- Gửi thông báo trạng thái vốn và chế độ ---
def send_capital_and_status():
    coins = ', '.join(selected_symbols)
    extra = ""

    if coin_allocation:
        extra += "\nƯu tiên từng coin:"
        for k, v in coin_allocation.items():
            unit = "%" if v["type"] == "percent" else "USDT"
            extra += f"\n- {k}: {v['value']}{unit}"

    msg = (
        f"[Trạng thái Bot]\n"
        f"Giới hạn vốn: {capital_limit if capital_limit > 0 else 'Không giới hạn'} USDT\n"
        f"Sử dụng mỗi lệnh: {capital_percent}%\n"
        f"Chế độ: {'DEMO' if use_demo else 'THẬT'}\n"
        f"Cặp đang chọn: {coins}"
        f"{extra}"
    )
    send_telegram_message(msg)

# --- Xử lý các nút ---
def button_handler(update: Update, context: CallbackContext):
    global bot_running, use_demo
    query = update.callback_query
    query.answer()
    data = query.data

    if data == 'toggle_bot':
        bot_running = not bot_running
        query.edit_message_text(f"Bot hiện tại: {'ĐANG CHẠY' if bot_running else 'ĐÃ TẮT'}", reply_markup=get_menu_keyboard())
    elif data == 'toggle_demo':
        use_demo = not use_demo
        query.edit_message_text("Chế độ giao dịch đã chuyển.", reply_markup=get_options_keyboard())
    elif data == 'set_capital':
        query.message.reply_text("Chọn cách thiết lập vốn:", reply_markup=get_capital_keyboard())
    elif data == 'input_capital':
        context.user_data['awaiting_capital'] = True
        query.message.reply_text("Nhập số vốn giới hạn (USDT):")

    elif data == 'input_coin_allocation':
        context.user_data['awaiting_coin_allocation'] = True
        query.message.reply_text("Nhập theo định dạng: COIN 5 hoặc COIN 10USDT (0 để tắt ưu tiên). VD: SOL 5 hoặc BTC 15USDT")
    elif data == 'input_percent':
        context.user_data['awaiting_percent'] = True
        query.message.reply_text("Nhập phần trăm (%) số vốn dùng cho mỗi lệnh (VD: 5):")
    elif data == 'open_orders':
        from okx_api import get_open_orders
        result = get_open_orders(use_demo)
        query.message.reply_text(f"Lệnh đang mở:\n{result}")
    elif data == 'run_backtest':
        query.message.reply_text("Đang chạy backtest...")
        query.message.reply_text("Kết quả: Backtest giả định - Lãi 12.5% với 60% winrate.")
    elif data == 'options':
        query.edit_message_text("Tùy chọn nâng cao:", reply_markup=get_options_keyboard())
        send_capital_and_status()
    elif data == 'start_again':
        query.edit_message_text("Chào mừng bạn quay lại bot.", reply_markup=get_menu_keyboard())
        send_capital_and_status()
    elif data == 'manage_coins':
        query.message.reply_text("Chọn hành động với danh sách coin:", reply_markup=get_manage_coin_keyboard())
    elif data == 'add_coin':
        context.user_data['adding_coin'] = True
        query.message.reply_text("Nhập coin muốn thêm (VD: PEPE/USDT):")
    elif data == 'remove_coin':
        context.user_data['removing_coin'] = True
        query.message.reply_text("Nhập coin muốn xoá (VD: PEPE/USDT):")
    elif data == 'select_coin':
        full_list = ["BTC", "ETH", "SOL", "TRX", "XPR", "ADA", "LINK", "XLM", "BCH", "LTC"] + custom_symbols
        reply = "Danh sách cặp bạn có thể chọn:\n"
        for sym in full_list:
            reply += f"- {sym} {'✅' if sym in selected_symbols else '❌'}\n"
        query.message.reply_text(reply + "\nNhập tên coin để bật/tắt (VD: PEPE hoặc TRX)")
        context.user_data['selecting_symbol'] = True

# --- Xử lý tin nhắn văn bản từ người dùng ---
def message_handler(update: Update, context: CallbackContext):
    global capital_limit, capital_percent, selected_symbols, custom_symbols
    text = update.message.text.strip().upper()

    if context.user_data.get('awaiting_capital'):
        try:
            val = float(text)
            capital_limit = val
            if val <= 0:
                update.message.reply_text("Đã tắt giới hạn vốn.")
            else:
                update.message.reply_text(f"Giới hạn vốn đặt là {capital_limit} USDT")
            context.user_data['awaiting_capital'] = False
        except:
            update.message.reply_text("Vui lòng nhập số hợp lệ.")


    elif context.user_data.get('awaiting_coin_allocation'):
        try:
            parts = text.split()
            if len(parts) != 2:
                raise ValueError("Sai định dạng")
            coin = parts[0].upper()
            value_text = parts[1].upper()

            if value_text.endswith("USDT"):
                val = float(value_text.replace("USDT", ""))
                if val == 0:
                    coin_allocation.pop(coin, None)
                    update.message.reply_text(f"Đã tắt ưu tiên riêng cho {coin}")
                else:
                    coin_allocation[coin] = {"type": "usdt", "value": val}
                    update.message.reply_text(f"Đã ưu tiên {val} USDT cho mỗi lệnh {coin}")
            else:
                val = float(value_text)
                if val == 0:
                    coin_allocation.pop(coin, None)
                    update.message.reply_text(f"Đã tắt ưu tiên riêng cho {coin}")
                else:
                    coin_allocation[coin] = {"type": "percent", "value": val}
                    update.message.reply_text(f"Đã ưu tiên {val}% vốn cho mỗi lệnh {coin}")
        except:
            update.message.reply_text("Sai định dạng. Hãy nhập VD: SOL 5 hoặc BTC 10USDT")
        context.user_data['awaiting_coin_allocation'] = False

    elif context.user_data.get('awaiting_percent'):
        try:
            percent = float(text)
            capital_percent = max(0, min(percent, 100))
            update.message.reply_text(f"Đặt sử dụng {capital_percent}% vốn cho mỗi lệnh.")
            context.user_data['awaiting_percent'] = False
        except:
            update.message.reply_text("Vui lòng nhập phần trăm hợp lệ.")

    elif context.user_data.get('adding_coin'):
        if text not in custom_symbols:
            custom_symbols.append(text)
            update.message.reply_text(f"Đã thêm {text}.")
        else:
            update.message.reply_text("Đã tồn tại.")
        context.user_data['adding_coin'] = False

    elif context.user_data.get('removing_coin'):
        if text in custom_symbols:
            custom_symbols.remove(text)
            update.message.reply_text("Đã xoá.")
        else:
            update.message.reply_text("Không tìm thấy.")
        context.user_data['removing_coin'] = False

    elif context.user_data.get('selecting_symbol'):
        base = text.split("/")[0] if "/" in text else text
        if base in selected_symbols:
            selected_symbols.remove(base)
            update.message.reply_text(f"Bỏ chọn {base}.")
        else:
            selected_symbols.append(base)
            update.message.reply_text(f"Chọn {base}.")
        context.user_data['selecting_symbol'] = False

# --- Menu Telegram & cập nhật lệnh ---
def set_bot_commands(updater):
    commands = [
        BotCommand("start", "Khởi động bot"),
        BotCommand("menu", "Mở menu chính"),
        BotCommand("toggle", "Bật/Tắt bot"),
        BotCommand("options", "Hiện tuỳ chọn nâng cao")
    ]
    updater.bot.set_my_commands(commands)

# --- Chạy Telegram bot ---
def telegram_updater():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    set_bot_commands(updater)

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("menu", start))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))

    updater.start_polling()
    updater.idle()

# --- Gửi báo cáo giao dịch ---
def send_trade_report(symbol, side, entry_price, capital, leverage, tp_price, sl_price):
    message = (
        f"[AutoTrade BOT]\n"
        f"Coin: {symbol}/USDT\n"
        f"Direction: {side.upper()}\n"
        f"Leverage: {leverage}x\n"
        f"Capital: {capital} USDT\n\n"
        f"Entry: ${entry_price:.2f}\n"
        f"TP: ${tp_price:.2f}\n"
        f"SL: ${sl_price:.2f}\n\n"
        f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    send_telegram_message(message)

def send_scan_status(symbol, timeframe_list):
    timeframes = ', '.join(timeframe_list)
    message = f"[Bot Scan]\n{symbol}/USDT | Khung: {timeframes}"
    send_telegram_message(message)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = { "chat_id": AUTHORIZED_USER_ID, "text": text }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Lỗi gửi tin nhắn Telegram: {e}")

# --- Getter ---
def get_bot_status():
    return bot_running

def get_trade_config():
    return {
        "capital": capital_limit,
        "leverage": leverage,
        "use_demo": use_demo,
        "symbols": selected_symbols,
        "percent": capital_percent,
        "coin_allocation": coin_allocation
    }