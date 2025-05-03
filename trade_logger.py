import os
import pandas as pd
from datetime import datetime

EXCEL_FILE = "Trade_History.xlsx"

def save_trade_to_excel(symbol, side, entry, exit_price, capital, pnl, status):
    date_str = datetime.now().strftime('%Y-%m-%d')
    time_str = datetime.now().strftime('%H:%M:%S')
    sheet_name = date_str
    pnl_percent = round((pnl / capital) * 100, 2) if capital > 0 else 0

    new_row = {
        "Thời gian": time_str,
        "Coin": symbol,
        "Chiều": side.upper(),
        "Vốn": capital,
        "Entry": entry,
        "Exit": exit_price,
        "PnL ($)": round(pnl, 2),
        "PnL (%)": pnl_percent,
        "Trạng thái": "Win" if pnl > 0 else "Loss"
    }

    if os.path.exists(EXCEL_FILE):
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
            try:
                df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
            except:
                df = pd.DataFrame()

            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Thống kê cuối ngày
            if len(df) > 0:
                total_pnl = df["PnL ($)"].sum()
                wins = df[df["PnL ($)"] > 0].shape[0]
                losses = df[df["PnL ($)"] <= 0].shape[0]
                winrate = round(100 * wins / (wins + losses), 2) if (wins + losses) > 0 else 0

                summary_df = pd.DataFrame({
                    "Tổng Lãi ($)": [total_pnl],
                    "Win": [wins],
                    "Loss": [losses],
                    "Tỷ lệ thắng (%)": [winrate]
                })
                summary_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=len(df) + 2)
    else:
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
            df = pd.DataFrame([new_row])
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            summary_df = pd.DataFrame({
                "Tổng Lãi ($)": [new_row["PnL ($)"]],
                "Win": [1 if pnl > 0 else 0],
                "Loss": [1 if pnl <= 0 else 0],
                "Tỷ lệ thắng (%)": [100 if pnl > 0 else 0]
            })
            summary_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=2)

    # Cập nhật thống kê tổng kết
    update_summary_sheet()


def update_summary_sheet():
    try:
        xls = pd.ExcelFile(EXCEL_FILE)
        summary_data = []

        for sheet in xls.sheet_names:
            if sheet == "Tổng Kết":
                continue
            df = pd.read_excel(xls, sheet_name=sheet)
            df = df[~df["Thời gian"].isnull()]
            if df.empty: continue

            pnl_total = df["PnL ($)"].sum()
            wins = df[df["PnL ($)"] > 0].shape[0]
            losses = df[df["PnL ($)"] <= 0].shape[0]
            winrate = round(wins / (wins + losses) * 100, 2) if (wins + losses) > 0 else 0
            summary_data.append([sheet, pnl_total, wins, losses, winrate])

        summary_df = pd.DataFrame(summary_data, columns=["Ngày", "Tổng PnL ($)", "Win", "Loss", "Winrate (%)"])
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            summary_df.to_excel(writer, sheet_name="Tổng Kết", index=False)
    except Exception as e:
        print("Lỗi tạo sheet tổng kết:", e)