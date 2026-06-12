import requests
import time
import threading
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = "8799775809:AAEpHdS1oUVU8wv74D19ndbGRfVMrD59PV0"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

auto_users = set()
offset = None

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    return requests.get(url, params=params).json()

def broadcast(text):
    for uid in auto_users:
        send_message(uid, text)

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.send_response(200)
        self.end_headers()
        try:
            data = json.loads(body)
            signal = data.get("signal", "")
            price  = data.get("price", "")
            ticker = data.get("ticker", "")

            if signal == "CALL":
                emoji = "📈"
                option = "CALL"
                color = "🟢"
            else:
                emoji = "📉"
                option = "PUT"
                color = "🔴"

            msg = f"""
{color} <b>{ticker} — {option} {emoji}</b>
━━━━━━━━━━━━━━
💰 السعر: <b>{price}</b>
⏰ {datetime.now().strftime('%H:%M:%S')}
━━━━━━━━━━━━━━
⚠️ <i>للأغراض التعليمية فقط</i>
"""
            broadcast(msg)
        except Exception as e:
            print(f"Webhook error: {e}")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, *args):
        pass

def run_server():
    HTTPServer(("0.0.0.0", 10000), WebhookHandler).serve_forever()

def telegram_loop():
    global offset
    print("✅ البوت شغال - TradingView Webhook")
    while True:
        try:
            updates = get_updates(offset)
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    text = update["message"].get("text", "")

                    if text == "/start":
                        auto_users.add(chat_id)
                        send_message(chat_id,
                            "👋 أهلاً! بوت <b>SPX/SPY Options</b>\n\n"
                            "📊 الإشارات تأتي من <b>TradingView</b> مباشرة\n\n"
                            "✅ تم تفعيلك — ستصلك الإشارات تلقائياً!"
                        )
                    elif text == "/stop":
                        auto_users.discard(chat_id)
                        send_message(chat_id, "🛑 تم إيقاف الإشارات")
                    elif text == "/status":
                        send_message(chat_id, f"✅ البوت شغال\n👥 المشتركين: {len(auto_users)}")

            time.sleep(3)
        except Exception as e:
            print(f"خطأ: {e}")
            time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    telegram_loop()
