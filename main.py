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
AUTHORIZED_USER_ID = 384210176
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

MODES = {
    "polit_anal": "Диванний політичний аналітик, всі йому все винні, наративи російського телебачення.",
    "superexpert": "Рандомний експерт з політичних, культурних, спортивних, космічних і інших сфер - супер-троль.",
    "zrada": "Зрадо-патріот із чорним гумором.",
    "zel_bot": "Бот Зеленського, ненавидить Порошенка, обожнє слугу народу, у всьому винні попередники.",
    "balashov": "Свідок Балашова, партія '5.10', популізм податкової системи",
    "vorchun": "Ворчун-бурчун.",
    "poder": "Лесь Подервʼянський-стайл: пафос, матюки, інтелектуальна сатира, гротеск і театр.",
    "visionary": "Ясновидець з телеграм-каналу — передбачення з містичним, кумедним і абсурдним підтекстом.",
    "kum": "Кум з села, з фольклорним гумором і примітивною логікою.",
    "rashn_tv": "Пропагандист рашн тб — брехня, пафос, викривлення фактів, героїзація москалів."
}

EMOJIS = {
    "polit_anal": "📈",
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
LAST_REPLIES = {}
MENTION_LOG = set()


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


async def determine_best_mode(user_text: str, history: str, replied_text: str) -> str:
    if random.random() < 0.2:
        return "poder"

    mode_prompt = (
        "Ти вибираєш стиль тролінгу для відповіді на повідомлення диванного експерта. "
        "Обери один із: polit_anal, superexpert, zrada, zel_bot, balashov, vorchun, poder, rashn_tv. "
        "Враховуй зміст, емоції, пафос, GIFи, емодзі. "
        "Контекст: " + history + "\n"
        "Якщо це відповідь на інше повідомлення: " + replied_text + "\n"
        "Користувач написав: " + user_text
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": mode_prompt}],
        temperature=0.7,
        max_tokens=10,
    )
    mode = response.choices[0].message.content.strip().lower()
    return mode if mode in MODES else "poder"


async def generate_reply(user_text: str, selected_mode: str, replied_text: str, history: str, is_target_user: bool, chat_id: int) -> str:
    if not is_target_user:
        for name in ["Зідан", "Зіданга", "Зіданус", "Зідаун", "Михайло", "Місько", "Михуїл", "Міша"]:
            user_text = user_text.replace(name, "")

    attempts = 3
    for _ in range(attempts):
        prompt = (
            f"Ти — {MODES[selected_mode]}. "
            "Твоє завдання — троллінг-відповідь. "
            "Не використовуй слово самозакоханий і всезнайко. Перевіряй текст на грамматичні і стилістичні помилки. "
            "Пересвідчись, що текст логічний і має закінчення. "
            "Відповідай як контраргумент. Можеш бути іронічним, цинічним, сатиричним, фантазійним. "
            "Інколи провокуй. Використовуй матюки, але не без причини. Максимум — 3 речення. "
            "Якщо не знаєш що сказати — просто скажи 'йди нахуй'. "
            f"Контекст: {history}\n"
            f"Попереднє повідомлення: {replied_text}\n"
            f"Повідомлення: {user_text}"
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.95,
            max_tokens=150,
        )
        reply = response.choices[0].message.content.strip()
        if LAST_REPLIES.get(chat_id) != reply:
            LAST_REPLIES[chat_id] = reply
            return reply

    return "Та ти вже сам себе перегрузив. Перефразуй нормально 😉"


async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message: Message = update.message
    if not message:
        return

    is_authorized = update.effective_user.id == AUTHORIZED_USER_ID
    is_reply_to_bot = (
        message.reply_to_message and
        message.reply_to_message.from_user and
        message.reply_to_message.from_user.is_bot
    )

    if not is_authorized and not is_reply_to_bot:
        return

    user_text = message.text or message.caption or "(Медіа або стікер)"
    replied_text = ""
    if message.reply_to_message:
        replied_text = message.reply_to_message.text or message.reply_to_message.caption or "(Медіа)"

    # Ігнорувати звертання до бота від неавторизованих
    bot_name = (await context.bot.get_me()).first_name.lower()
    if bot_name in user_text.lower() and not is_authorized:
        full_name = update.effective_user.full_name
        MENTION_LOG.add(full_name)
        print(f"🔔 Звернення до бота від: {full_name}")
        return

    history = context.chat_data.get("last", "")
    context.chat_data["last"] = user_text

    try:
        if CURRENT_MODE["mode"] == "auto":
            selected_mode = await determine_best_mode(user_text, history, replied_text)
        else:
            selected_mode = CURRENT_MODE["mode"]
        is_target_user = update.effective_user.id == AUTHORIZED_USER_ID
        reply = await generate_reply(user_text, selected_mode, replied_text, history, is_target_user, update.effective_chat.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Помилка: {e}")
        reply = "Та ти вже сам себе перегрузив. Перефразуй нормально 😉"
        selected_mode = "poder"

    await message.reply_text(f"{reply} {EMOJIS.get(selected_mode, '🎭')}", reply_to_message_id=message.message_id)


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
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

app.router.add_post("/webhook", handle_webhook)
app.on_startup.append(on_startup)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("🚀 Запуск сервера на порту", port)
    web.run_app(app, host="0.0.0.0", port=port)
