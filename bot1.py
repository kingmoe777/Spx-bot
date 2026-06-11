import requests
import time
from datetime import datetime
import yfinance as yf
import pandas as pd
import numpy as np

BOT_TOKEN = "8799775809:AAEpHdS1oUVU8wv74D19ndbGRfVMrD59PV0"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

offset = None
auto_users = set()

ASSETS = {
    "SPX": "^GSPC",
    "SPY": "SPY"
}

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    response = requests.get(url, params=params)
    return response.json()

def calculate_vwap(df):
    df = df.copy()
    df["TP"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["TPV"] = df["TP"] * df["Volume"]
    df["VWAP"] = df["TPV"].cumsum() / df["Volume"].cumsum()
    return df["VWAP"].iloc[-1]

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def get_orb(df):
    """Opening Range - أول 3 شموع (30 دقيقة)"""
    orb_candles = df.head(3)
    orb_high = orb_candles["High"].max()
    orb_low = orb_candles["Low"].min()
    return round(orb_high, 2), round(orb_low, 2)

def analyze(symbol, ticker_code):
    try:
        ticker = yf.Ticker(ticker_code)
        df = ticker.history(period="2d", interval="10m")

        if df.empty or len(df) < 10:
            return None

        close = df["Close"]
        price = round(close.iloc[-1], 2)

        vwap = round(calculate_vwap(df), 2)
        rsi = round(calculate_rsi(close).iloc[-1], 2)
        ema9 = round(calculate_ema(close, 9).iloc[-1], 2)
        ema21 = round(calculate_ema(close, 21).iloc[-1], 2)
        orb_high, orb_low = get_orb(df)

        # منطق الإشارة
        call_conditions = (
            price > vwap and
            price > orb_high and
            ema9 > ema21 and
            rsi < 70
        )

        put_conditions = (
            price < vwap and
            price < orb_low and
            ema9 < ema21 and
            rsi > 30
        )

        if call_conditions:
            signal = "CALL 📈"
            reason = "السعر فوق VWAP + كسر ORB للأعلى + EMA صاعد"
            stop = round(orb_high - (orb_high - orb_low) * 0.5, 2)
            target = round(price + (price - stop) * 2, 2)
            trade_info = f"\n✅ دخول: <b>{price}</b>\n🛑 وقف: <b>{stop}</b>\n🎯 هدف: <b>{target}</b>"
        elif put_conditions:
            signal = "PUT 📉"
            reason = "السعر تحت VWAP + كسر ORB للأسفل + EMA هابط"
            stop = round(orb_low + (orb_high - orb_low) * 0.5, 2)
            target = round(price - (stop - price) * 2, 2)
            trade_info = f"\n✅ دخول: <b>{price}</b>\n🛑 وقف: <b>{stop}</b>\n🎯 هدف: <b>{target}</b>"
        else:
            signal = "WAIT ⏳"
            reason = "الشروط غير مكتملة — انتظر تأكيد"
            trade_info = ""

        msg = f"""
🔔 <b>{symbol} Options Signal</b>
━━━━━━━━━━━━━━
💰 السعر: <b>{price}</b>
📊 VWAP: <b>{vwap}</b>
📈 EMA9: <b>{ema9}</b> | EMA21: <b>{ema21}</b>
🔢 RSI: <b>{rsi}</b>
🏁 ORB: <b>{orb_high}</b> / <b>{orb_low}</b>
━━━━━━━━━━━━━━
🎯 الإشارة: <b>{signal}</b>
💡 {reason}{trade_info}
━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%H:%M')}
⚠️ <i>للأغراض التعليمية فقط</i>
"""
        return msg

    except Exception as e:
        return f"⚠️ خطأ في {symbol}: {str(e)}"

def analyze_all():
    msgs = []
    for symbol, code in ASSETS.items():
        result = analyze(symbol, code)
        if result:
            msgs.append(result)
    return "\n".join(msgs)

def main():
    global offset
    print("✅ البوت شغال - ORB + VWAP + EMA")
    last_auto_run = -1

    while True:
        try:
            updates = get_updates(offset)

            for update in updates.get("result", []):
                offset = update["update_id"] + 1

                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    text = update["message"].get("text", "")

                    if text == "/start":
                        send_message(chat_id,
                            "👋 أهلاً! بوت <b>SPX/SPY Options</b>\n\n"
                            "📊 الاستراتيجية: <b>ORB + VWAP + EMA</b>\n"
                            "⏱ تحليل كل 10 دقائق\n\n"
                            "/signal — تحليل فوري\n"
                            "/auto — تلقائي كل 10 دقائق\n"
                            "/stop — إيقاف التلقائي"
                        )

                    elif text == "/signal":
                        send_message(chat_id, "⏳ جاري التحليل...")
                        send_message(chat_id, analyze_all())

                    elif text == "/auto":
                        auto_users.add(chat_id)
                        send_message(chat_id, "✅ تم تفعيل الإشارات التلقائية كل 10 دقائق!")

                    elif text == "/stop":
                        auto_users.discard(chat_id)
                        send_message(chat_id, "🛑 تم إيقاف الإشارات التلقائية")

            current_10min = datetime.now().minute // 10
            if current_10min != last_auto_run and auto_users:
                result = analyze_all()
                for uid in auto_users:
                    send_message(uid, result)
                last_auto_run = current_10min

            time.sleep(3)

        except Exception as e:
            print(f"خطأ: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
