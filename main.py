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
    "deputat": "Депутат з пафосом і бздуром.",
    "batya_fb": "Батя, що скучив за СРСР.",
    "futboll": "Футбольний коментатор з дивану.",
    "polit_anal": "Диванний політичний аналітик.",
    "superexpert": "Все знає, нічого не розуміє.",
    "zrada": "Зрадо-патріот із чорним гумором.",
    "ukr_politdivan": "Марафонщик-коментатор із ТБ.",
    "random": "Режим вибирається випадково.",
}

CURRENT_MODE = {"mode": "rostv"}

async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return
    if not context.args or context.args[0] not in MODES:
        await update.message.reply_text("Доступні режими: " + ", ".join(MODES.keys()))
        return
    CURRENT_MODE["mode"] = context.args[0]
    await update.message.reply_text("Режим тролінгу змінено на: " + context.args[0])

def get_mode_description(mode: str):
    if mode == "random":
        mode = random.choice([m for m in MODES if m != "random"])
    return MODES.get(mode, MODES["rostv"])

async def generate_reply(user_text: str, mode: str, replied_text: str = "", history: str = "") -> str:
    character_prompt = get_mode_description(mode)
    prompt = (
        "Ти — український троль з характером. Ти звертаєшся до користувача виключно на "ти". "
        "Твоя задача — не просто відповісти, а опонувати: жорстко, дотепно, саркастично, з емоційним підколом. "
        "Ти маєш зачепитися за його фразу й зробити контркоментар. "
        "Не загладжуй, не узагальнюй, не уникай особистого звернення. "
        "Реагуй точно на суть повідомлення, ніби ти його опонент в розмові, який завжди має останнє слово.

"
        f"Обраний стиль персонажа: {character_prompt}

"
        f"Контекст чату (може бути порожнім):
{history}

"
        f"Якщо це відповідь на інше повідомлення, ось воно:
{replied_text}

"
        f"Користувач написав:
{user_text}

"
        "Сформулюй коротку, колючу відповідь (1-2 речення), обов'язково у формі прямого звернення на "ти". "
        "Не давай загальних відповідей. Якщо користувач грубить — приший ще жорсткіше, але без матюків."
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.99,
        max_tokens=140,
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

    replied_text = ""
    if message.reply_to_message:
        if message.reply_to_message.text:
            replied_text = message.reply_to_message.text
        elif message.reply_to_message.caption:
            replied_text = "(Підпис до медіа): " + message.reply_to_message.caption
        elif message.reply_to_message.sticker:
            replied_text = "(Стікер)"
        elif message.reply_to_message.photo:
            replied_text = "(Зображення)"
        elif message.reply_to_message.video:
            replied_text = "(Відео)"

    history = context.chat_data.get("last", "")
    context.chat_data["last"] = user_text

    try:
        reply = await generate_reply(user_text, CURRENT_MODE["mode"], replied_text, history)
    except Exception:
        reply = "Та ти вже сам себе перегрузив. Перефразуй нормально 😉"

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
