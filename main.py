import os
import random
from aiohttp import web
from telegram import Update, Message
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
AUTHORIZED_USER_ID = 412991871
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

MODES = {
    "rostv": "Пропагандист з росТБ.",
    "deputat": "Самозакоханий депутат облради.",
    "batya_fb": "Батя з Facebook, 'все раніше було краще'.",
    "futboll": "Футбольний коментатор із дивану.",
    "polit_anal": "Політичний диванний експерт.",
    "superexpert": "Універсальний експерт з усього.",
    "zrada": "Зрадо-патріот із чорним гумором.",
    "ukr_politdivan": "Український політичний диванний марафонець.",
    "random": "Випадковий стиль з усіх доступних."
}

CURRENT_MODE = {"mode": "rostv"}

async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return
    if not context.args or context.args[0] not in MODES:
        await update.message.reply_text(f"Доступні режими: {', '.join(MODES.keys())}")
        return
    CURRENT_MODE["mode"] = context.args[0]
    await update.message.reply_text(f"Режим змінено на: {context.args[0]}")

def get_mode_description(mode: str):
    if mode == "random":
        mode = random.choice([m for m in MODES if m != "random"])
    return MODES.get(mode, MODES["rostv"])

async def generate_reply(text: str, mode: str) -> str:
    character_prompt = get_mode_description(mode)
    prompt = f"""
Ти троллячий AI. Стиль — чорний гумор, політична сатира, сарказм. Образ: {character_prompt}

Повідомлення користувача:
"{text}"

Надай троллячу відповідь у стилі (1-2 речення).
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.98,
        max_tokens=120,
    )
    return response.choices[0].message.content.strip()

async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message: Message = update.message
    if not message or update.effective_user.id != AUTHORIZED_USER_ID:
        return

    user_text = ""
    if message.text:
        user_text = message.text
    elif message.caption:
        user_text = f"(Медіа з підписом): {message.caption}"
    elif message.sticker:
        user_text = "(Надіслано стікер)"
    elif message.animation:
        user_text = "(Надіслано GIF)"
    elif message.video:
        user_text = "(Надіслано відео)"
    elif message.photo:
        user_text = "(Надіслано фото)"
    else:
        user_text = "(Невідоме медіа)"

    if message.reply_to_message and message.reply_to_message.text:
        replied = message.reply_to_message.text
        user_text = f"Відповідь на чужий текст: "{replied}"
Користувач написав: {user_text}"

    try:
        reply = await generate_reply(user_text, CURRENT_MODE["mode"])
    except Exception:
        reply = "Вибач, я завис від твоєї унікальної подачі медіа."

    await message.reply_text(reply)

application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("mode", set_mode))
application.add_handler(MessageHandler(filters.ALL, handle_all))

app = web.Application()

async def on_startup(app: web.Application):
    await application.initialize()
    webhook_url = os.getenv("RENDER_EXTERNAL_URL") + "/webhook"
    await application.bot.set_webhook(webhook_url)
    print(f"📡 Webhook встановлено: {webhook_url}")
    app["application"] = application

async def handle_webhook(request: web.Request):
    data = await request.json()
    print("🔔 Отримано запит на /webhook:")
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

app.router.add_post("/webhook", handle_webhook)
app.on_startup.append(on_startup)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Запуск сервера на порту {port}")
    web.run_app(app, host="0.0.0.0", port=port)
