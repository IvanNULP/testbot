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
    "vsya_planeta": "Експерт всія планети.",
    "divan_expert": "Диванний експерт.",
    "zel_bot": "Бот Зеленського.",
    "balashov": "Свідок Балашова.",
    "vorchun": "Ворчун-бурчун.",
    "poder": "Лесь Подервʼянський-стайл: пафос, матюки, інтелектуальна сатира, гротеск і театр."
}

CURRENT_MODE = {"mode": "auto"}

async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return
    if not context.args:
        await update.message.reply_text("Доступні режими: " + ", ".join(MODES.keys()) + ", auto")
        return
    mode = context.args[0].strip().lower()
    if mode in MODES or mode == "auto":
        CURRENT_MODE["mode"] = mode
        await update.message.reply_text("Режим змінено на: " + mode)
    else:
        await update.message.reply_text("Невідомий режим.")

async def determine_best_mode(user_text: str) -> str:
    mode_prompt = f"""
На основі наступного повідомлення користувача обери, який стиль тролінгу краще підійде. 
Оберіть лише один із таких варіантів: rostv, deputat, batya_fb, futboll, polit_anal, superexpert, zrada, ukr_politdivan, vsya_planeta, divan_expert, zel_bot, balashov, vorchun, poder. 


Повідомлення користувача:
{user_text}


Відповідь — тільки одне слово: ключ стилю без лапок (наприклад: zrada)
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": mode_prompt}],
        temperature=0.5,
        max_tokens=10,
    )
    selected = response.choices[0].message.content.strip().lower()
    return selected if selected in MODES else "poder"

async def generate_reply(user_text: str, mode: str, replied_text: str = "", history: str = "") -> str:
    character_prompt = MODES.get(mode, MODES["superexpert"])
    prompt = (
        "Ти — український троль з характером. Ти звертаєшся до користувача виключно на 'ти'. "
        "Твоя задача — не просто відповісти, а опонувати: жорстко, дотепно, саркастично, з емоційним підколом. "
        "Ти маєш зачепитися за його фразу й зробити контркоментар. "
        "Реагуй точно на суть повідомлення. "
        "Формулюй відповідь грамотно, синтаксично і стилістично правильно. "
        f"Обраний стиль персонажа: {character_prompt}\n\n"
        f"Контекст чату (може бути порожнім):\n{history}\n\n"
        f"Якщо це відповідь на інше повідомлення, ось воно:\n{replied_text}\n\n"
        f"Користувач написав:\n{user_text}\n\n"
        "Сформулюй коротку, колючу відповідь (1-2 речення), у формі прямого звернення на 'ти'."
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.95,
        max_tokens=140,
    )
    return response.choices[0].message.content.strip()

async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message: Message = update.message
    if not message or update.effective_user.id != AUTHORIZED_USER_ID:
        return

    user_text = message.text or message.caption or "(Медіа або стікер)"
    replied_text = ""
    if message.reply_to_message:
        replied_text = message.reply_to_message.text or message.reply_to_message.caption or "(Медіа)"

    history = context.chat_data.get("last", "")
    context.chat_data["last"] = user_text

    try:
        if CURRENT_MODE["mode"] == "auto":
            selected_mode = await determine_best_mode(user_text)
        else:
            selected_mode = CURRENT_MODE["mode"]
        reply = await generate_reply(user_text, selected_mode, replied_text, history)
    except Exception:
        reply = "Та ти вже сам себе перегрузив. Перефразуй нормально 😉"

    await message.reply_text(f"🎭 Стиль: {selected_mode} — {MODES.get(selected_mode, 'Невідомо')}")
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
