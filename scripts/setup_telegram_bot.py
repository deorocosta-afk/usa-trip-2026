import os
import json
import urllib.request
import urllib.error

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
WEB_APP_URL = "https://deorocosta-afk.github.io/usa-trip-2026/"

def tg_api(method, data=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))

def setup_bot():
    if not BOT_TOKEN:
        print("Ошибка: Переменная окружения TELEGRAM_BOT_TOKEN не задана!")
        return

    me = tg_api("getMe")
    print(f"Бот авторизован: @{me['result']['username']} ({me['result']['first_name']})")

    # 1. Установка кнопки Web App в меню (setChatMenuButton)
    menu_payload = {
        "menu_button": {
            "type": "web_app",
            "text": "📖 Открыть журнал",
            "web_app": {"url": WEB_APP_URL}
        }
    }
    res_menu = tg_api("setChatMenuButton", menu_payload)
    if res_menu.get("ok"):
        print(f"Кнопка меню Web App успешно настроена на: {WEB_APP_URL}")

    # 2. Отправка приветственного сообщения с прямой инлайн-кнопкой (sendMessage)
    if CHAT_ID:
        msg_payload = {
            "chat_id": CHAT_ID,
            "text": (
                "🚗 <b>Экспедиция: Калифорния и США 2026</b>\n\n"
                "Интерактивный журнал путешествия готов к просмотру!\n"
                "Нажмите кнопку ниже или используйте постоянную кнопку меню «📖 Открыть журнал»."
            ),
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": "🚗 Смотреть путешествие",
                            "web_app": {"url": WEB_APP_URL}
                        }
                    ]
                ]
            }
        }
        res_msg = tg_api("sendMessage", msg_payload)
        if res_msg.get("ok"):
            print(f"Приветственное сообщение отправлено в чат {CHAT_ID} (ID: {res_msg['result']['message_id']})")

if __name__ == "__main__":
    setup_bot()
