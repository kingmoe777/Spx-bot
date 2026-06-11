import requests
import time
from datetime import datetime
import yfinance as yf
import pandas as pd

# ضع توكنك هنا
BOT_TOKEN = "8799775809:AAEpHdS1oUVU8wv74D19ndbGRfVMrD59PV0"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
offset = None
auto_users = set()

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    response = requests.get(url, params=params)
    return response.json()

def analyze_spx():
    try:
        ticker = yf.Ticker("ES=F")  # SPX Futures
        df = ticker.history(period="5d", interval="1h")

        if df.empty:
            return "⚠️ تعذر جلب البيانات، حاول لاحقاً"

        close = df["Close"]

        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = round(rsi.iloc[-1], 2)

        # Moving Averages
        ma20 = round(close.rolling(20).mean().iloc[-1], 2)
        ma50 = round(close.rolling(50).mean().iloc[-1], 2)
        price = round(close.iloc[-1], 2)

        # Signal Logic
        if rsi_val < 35 and ma20 > ma50:
            signal = "BUY 📈"
            reason = "RSI منخفض + MA20 فوق MA50"
        elif rsi_val > 65 and ma20 < ma50:
            signal = "SELL 📉"
            reason = "RSI مرتفع + MA20 تحت MA50"
        else:
            signal = "WAIT ⏳"
            reason = "السوق في منطقة محايدة"

        msg = f"""
🔔 <b>SPX Futures Signal</b>
━━━━━━━━━━━━━━
💰 السعر: <b>{price}</b>
📊 RSI: <b>{rsi_val}</b>
📈 MA20: <b>{ma20}</b>
📉 MA50: <b>{ma50}</b>
━━━━━━━━━━━━━━
🎯 الإشارة: <b>{signal}</b>
💡 السبب: {reason}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}
━━━━━━━━━━━━━━
⚠️ <i>للأغراض التعليمية فقط</i>
        """
        return msg

    except Exception as e:
        return f"⚠️ خطأ: {str(e)}"

def main():
    global offset
    print("✅ البوت شغال...")
    last_auto_hour = -1

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
                            "👋 أهلاً! أنا بوت إشارات <b>SPX Futures</b>\n\n"
                            "الأوامر:\n"
                            "/signal — إشارة الآن\n"
                            "/auto — تفعيل إشارات تلقائية كل ساعة\n"
                            "/stop — إيقاف الإشارات التلقائية",
                        )

                    elif text == "/signal":
                        send_message(chat_id, "⏳ جاري التحليل...")
                        send_message(chat_id, analyze_spx())

                    elif text == "/auto":
                        auto_users.add(chat_id)
                        send_message(chat_id, "✅ تم تفعيل الإشارات التلقائية كل ساعة!")

                    elif text == "/stop":
                        auto_users.discard(chat_id)
                        send_message(chat_id, "🛑 تم إيقاف الإشارات التلقائية")

            # إرسال تلقائي كل ساعة
            current_hour = datetime.now().hour
            if current_hour != last_auto_hour and auto_users:
                signal_msg = analyze_spx()
                for uid in auto_users:
                    send_message(uid, signal_msg)
                last_auto_hour = current_hour

            time.sleep(3)

        except Exception as e:
            print(f"خطأ: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
