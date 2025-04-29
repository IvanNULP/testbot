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
    "poder": "Лесь Подервʼянський-стайл: пафос, матюки, інтелектуальна сатира, гротеск і театр, відомі вислови Леся Подервʼянського з матюками з його творів.",
    "visionary": "Ясновидець з телеграм-каналу — передбачення з містичним, кумедним і абсурдним підтекстом.",
    "kum": "Кум з села, розказує все по-своєму, з фольклорним гумором і примітивною логікою, використовуючи український народний жаргон.",
    "rashn_tv": "Пропагандист із рашн тб  — пафосно бреше про зовнішні загрози, вихваляє перемоги навіть із поразок, постійно кричить про ворогів і героїзм москалів, перекручує будь-які факти на користь своїх. Слова перемога, вороги, героїзм, своїх — це все в лапках, тобто перекручені факти."
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
    # Підвищуємо шанс подерв’янського до 20%
    if random.random() < 0.2:
        return "poder"
    
    mode_prompt = (
        "Ти вибираєш стиль тролінгу для відповіді на повідомлення диванного експерта, "
        "який вважає себе дуже розумним. Обери стиль з наступних: polit_anal, superexpert, zrada, zel_bot, balashov, vorchun, poder, rashn_tv "
        "Враховуй суть повідомлення, його пафос, тон, стиль, суть гіфки чи смайлів. І обов'язково використай стиль троллінгу щоб відповідь стосувалась саме троллінгу. Можеш інколи виступати як троллінг-провокатор і використовувати чорний гумор. "
        "Контекст і попередні відповіді можуть допомогти зрозуміти ситуацію. "
        "Пояснюй нічого не треба, просто поверни назву режиму.\n\n"
        f"Контекст чату: {history}\n"
        f"Якщо це відповідь на інше повідомлення: {replied_text}\n"
        f"Користувач написав: {user_text}"
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": mode_prompt}],
        temperature=0.7,
        max_tokens=10,
    )
    mode = response.choices[0].message.content.strip().lower()
    return mode if mode in MODES else "poder"

async def generate_reply(user_text: str, selected_mode: str, replied_text: str, history: str) -> str:
    prompt = (
        f"Ти — {MODES[selected_mode]}. "
        "Твоє завдання — троллінг-відповідь диванному експерту, який впевнений, що знає все краще за всіх. "
"Не використовуй слово самозакоханий і всезнайко і їх синоніми проте перевіряй текст на грамматичні і стилістичні помилки. Пересвідчись, що текст логічний і має закінчення. "
"Відповідай як контраргумент, будь інколи але не завжди цінічним. "
        "Твоя відповідь інколи може бути жорсткою але завжди з іронією, сатирою, можливо сарказмом, вмикай фантазію, роздумуй якщо треба, веди себе як людина яка відповідає такому опоненту, щоб пожартувати. Інколи можеш виступати як троллінг-провокатор. "
        "Звертайся на 'ти' або на 'ви' якщо від цього буде смішніше і воно пасує в контексті. Можеш пробувати щось пояснити але не виправдовуйся надмірно. Дозволяю використовувати матюки, матерні слова, українську лайку. Також можеш інколи, але не завжди, звертатись до автора за іменем- Зідан, Зіданга, Зіданус, Зідаун, Михайло, Місько, Михуїл, Міша та інші подібні похідні імена. Зіданга використовуй коли автор говорить про майбутнє як Ванга. "
        "Відповідь має бути не велика. Максимум на 3 речення. Якщо треба можеш використати смайлики або гіфку. "
        f"Контекст: {history}\n"
        f"Якщо це відповідь на інше повідомлення: {replied_text}\n"
        f"Повідомлення: {user_text}"
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.95,
        max_tokens=150,
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
            selected_mode = await determine_best_mode(user_text, history, replied_text)
        else:
            selected_mode = CURRENT_MODE["mode"]
        reply = await generate_reply(user_text, selected_mode, replied_text, history)
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
