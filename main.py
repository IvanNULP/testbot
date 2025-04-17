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
    "rostv": "Пропагандист російських каналів: агресивний, емоційний, перекручений стиль.",
    "deputat": "Депутат обласної ради: говорить пафосно, з регламентами, але без сенсу.",
    "batya_fb": "Батько з Facebook: сумує за минулим, дає поради, має категоричну думку.",
    "futboll": "Футбольний коментатор з дивану: порівняння з матчами, сарказм, упередженість.",
    "polit_anal": "Диванний політичний аналітик: все куплено, всюди змови, у владі винні всі.",
    "superexpert": "Всеохопний експерт: коментує все — від фізики до котлет.",
    "zrada": "Патріотичний песиміст: бачить зраду в усьому, скиглить, але тримає фронт сарказмом.",
    "ukr_politdivan": "Український марафон-коментатор: завжди 'в темі', має сильні 'власні джерела'.",
    "random": "Кожного разу випадково обирається стиль з наявних вище."
}

CURRENT_MODE = {"mode": "rostv"}

async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return
    if not context.args or context.args[0] not in MODES:
        await update.message.reply_text("Доступні режими: " + ", ".join(MODES.keys()))
        return
    CURRENT_MODE["mode"] = context.args[0]
    await update.message.reply_text("Режим змінено на: " + context.args[0])

def get_mode_description(mode: str):
    if mode == "random":
        mode = random.choice([m for m in MODES if m != "random"])
    return MODES.get(mode, MODES["rostv"])

async def generate_reply(text: str, mode: str) -> str:
    character_prompt = get_mode_description(mode)
    prompt = (
        "Уяви себе критичним аналітиком із саркастичним розумом. "
        "Твоя задача — прокоментувати повідомлення користувача у вигляді дотепної, жорсткої, "
        "іронічної відповіді, з натяками, перебільшенням, емоційною насмішкою, але без прямих образ чи ненависті. "
        "Використовуй стиль: " + character_prompt + "\n\n"
        "Ось повідомлення користувача: "" + text + ""\n"
        "Сформулюй жорстку, саркастичну репліку у 1-2 реченнях."
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.99,
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
        user_text = "(Медіа з підписом): " + message.caption
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
        user_text = "Відповідь на чужий текст: "" + replied + ""\nКористувач написав: " + user_text

    try:
        reply = await generate_reply(user_text, CURRENT_MODE["mode"])
    except Exception:
        reply = "Схоже, моє почуття гумору зависло. Повтори ще раз."

    await message.reply_text(reply)

application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("mode", set_mode))
application.add_handler(MessageHandler(filters.ALL, handle_all))

app = web.Application()

async def on_startup(app: web.Application):
    await application.initialize()
    webhook_url = os.getenv("RENDER_EXTERNAL_URL") + "/webhook"
    await application.bot.set_webhook(webhook_url)
    print("📡 Webhook встановлено: " + webhook_url)
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
    print("🚀 Запуск сервера на порту", port)
    web.run_app(app, host="0.0.0.0", port=port)
