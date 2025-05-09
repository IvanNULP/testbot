import os
import random
from collections import deque
from telegram import Update, Message
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from openai import OpenAI
from aiohttp import web

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AUTHORIZED_USER_ID = 384210176
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

client = OpenAI(api_key=OPENAI_API_KEY)
CHAT_HISTORY = dict()
MAX_HISTORY = 20

MODES = {
    "polit_anal": "Диванний політичний аналітик...",
    "superexpert": "Рандомний експерт з усіх сфер...",
    "zrada": "Зрадо-патріот із чорним гумором.",
    "zel_bot": "Бот Зеленського...",
    "balashov": "Свідок Балашова...",
    "vorchun": "Ворчун-бурчун.",
    "poder": "Лесь Подервʼянський-стайл...",
    "visionary": "Ясновидець з телеграм-каналу...",
    "kum": "Кум з села...",
    "rashn_tv": "Пропагандист із рашн тб..."
}

EMOJIS = {
    "polit_anal": "📊",
    "superexpert": "🧠",
    "zrada": "🇺🇦",
    "zel_bot": "🤖",
    "balashov": "💸",
    "vorchun": "🧓",
    "poder": "🎭",
    "visionary": "🔮",
    "kum": "🧅",
    "rashn_tv": "📺"
}

CURRENT_MODE = {"mode": "auto"}

def is_sentence_complete(text: str) -> bool:
    return text.strip().endswith(('.', '!', '?'))

# === Команда /mode ===
async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = CURRENT_MODE["mode"]
    await update.message.reply_text(f"🔧 Поточний режим: {mode}")

# === Основний обробник ===
async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message = update.message

    # ❗ Відповідаємо лише якщо:
    # 1. Це таргетований користувач
    # 2. АБО це відповідь на повідомлення бота
    if (
        user_id != AUTHORIZED_USER_ID and
        not (message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_bot)
    ):
        return  # Ігноруємо інші випадки

    replied_text = message.reply_to_message.text if message.reply_to_message else None

    if chat_id not in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = deque(maxlen=MAX_HISTORY)
    CHAT_HISTORY[chat_id].append(message)

    history_text = "\n".join([m.text for m in CHAT_HISTORY[chat_id] if m.text])
    is_continuation = replied_text is None or replied_text in history_text

    try:
        # === Вибір режиму GPT ===
        if user_id != AUTHORIZED_USER_ID:
            combined_text = f"Контекст: {history_text if is_continuation else ''}\nПовідомлення: {message.text}"
            mode_selection = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ти — аналітик. На основі повідомлення та контексту вибери один із наступних персонажів:\n\n"
                            + ", ".join(MODES.keys()) +
                            "\n\nПоверни лише ключ, без зайвих символів."
                        )
                    },
                    {"role": "user", "content": combined_text}
                ],
                temperature=0.3,
                max_tokens=10
            )
            mode = mode_selection.choices[0].message.content.strip()
            if mode != "poder" and random.random() < 0.2:
                mode = "poder"
        else:
            mode = None  # Спец режим для таргетованого користувача

        # === Побудова промпта GPT ===
        if user_id == AUTHORIZED_USER_ID:
            prompt = (
                "Твоє завдання — троллінг-відповідь диванному експерту. "
                "Не використовуй слово самозакоханий і всезнайко. "
                "Завжди перевіряй логіку, граматику, і завершення. Використовуй сатиру, іронію, жарти, матюки. "
                f"Контекст: {history_text if is_continuation else ''}\n"
                f"Відповідь на: {replied_text or '—'}\n"
                f"Повідомлення: {message.text}"
            )
        else:
            prompt = (
                f"Ти — {MODES[mode]}. "
                "Твоє завдання — троллінг-відповідь. "
                "Максимум 3 речення. Можна матюки. "
                "Не використовуй 'самозакоханий' і 'всезнайко'. "
                f"Контекст: {history_text if is_continuation else ''}\n"
                f"Відповідь на: {replied_text or '—'}\n"
                f"Повідомлення: {message.text}"
            )

        # === Відповідь GPT ===
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.8,
            max_tokens=150
        )

        reply = response.choices[0].message.content.strip()
        if not is_sentence_complete(reply):
            reply += "."

        emoji = EMOJIS.get(mode, "")
        await message.reply_text(f"{reply} {emoji}")

    except Exception as e:
        await message.reply_text("❌ Помилка: " + str(e))

# === Webhook запуск ===
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("mode", set_mode))
application.add_handler(MessageHandler(filters.ALL, handle_all))

app = web.Application()

async def on_startup(app: web.Application):
    await application.initialize()
    webhook_url = RENDER_EXTERNAL_URL.rstrip("/") + "/webhook"
    await application.bot.set_webhook(webhook_url)
    print("📡 Webhook встановлено:", webhook_url)
    app["application"] = application

async def handle_webhook(request: web.Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

app.router.add_post("/webhook", handle_webhook)
app.on_startup.append(on_startup)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Запуск на порту {port}")
    web.run_app(app, host="0.0.0.0", port=port)
