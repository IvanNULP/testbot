import os
import random
from collections import deque
from telegram import Update
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
    "polit_anal": "Диванний політичний аналітик, всі йому все винні, наративи російського телебачення.",
    "superexpert": "Рандомний експерт з політичних, культурних, спортивних, космічних і інших сфер - супер-троль.",
    "zrada": "Зрадо-патріот із чорним гумором.",
    "zel_bot": "Бот Зеленського, ненавидить Порошенка, обожнє слугу народу, у всьому винні попередники.",
    "balashov": "Свідок Балашова, партія '5.10', популізм податкової системи.",
    "vorchun": "Ворчун-бурчун.",
    "poder": "Лесь Подервʼянський-стайл: пафос, матюки, інтелектуальна сатира, гротеск і театр, відомі вислови Леся Подервʼянського з матюками з його творів.",
    "visionary": "Ясновидець з телеграм-каналу — передбачення з містичним, кумедним і абсурдним підтекстом.",
    "kum": "Кум з села, розказує все по-своєму, з фольклорним гумором і примітивною логікою, використовуючи український народний жаргон.",
    "rashn_tv": "Пропагандист із рашн тб  — пафосно бреше про зовнішні загрози, вихваляє перемоги навіть із поразок,ненавидить США, постійно кричить про ворогів, і героїзм москалів, перекручує будь-які факти на користь своїх. Слова перемога, вороги, героїзм, своїх — це все в лапках, тобто перекручені факти."
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

# === /mode команда для відображення поточного режиму
async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🔧 Поточний режим: {CURRENT_MODE['mode']}")

# === Обробник повідомлень
async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message = update.message

    # Відповідати тільки авторизованому користувачу або якщо відповідають на повідомлення бота
    if (
        user_id != AUTHORIZED_USER_ID and
        not (message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_bot)
    ):
        return

    replied_text = message.reply_to_message.text if message.reply_to_message else None

    # Зберігаємо історію чату
    if chat_id not in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = deque(maxlen=MAX_HISTORY)
    CHAT_HISTORY[chat_id].append(message)

    history_text = "\n".join([m.text for m in CHAT_HISTORY[chat_id] if m.text])
    is_continuation = replied_text is None or replied_text in history_text

    try:
        # === GPT вибір режиму
        combined_text = f"Контекст:\n{history_text}\nПовідомлення:\n{message.text}"
        mode_selection = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "На основі наведеного повідомлення та контексту вибери, який із наступних тролінг-стилів найкраще пасує до ситуації. "
                        "Обери один із наступних ключів точно (без лапок, крапок, пояснень):\n\n" +
                        ", ".join(MODES.keys())
                    )
                },
                {"role": "user", "content": combined_text}
            ],
            temperature=0.3,
            max_tokens=10
        )
        mode = mode_selection.choices[0].message.content.strip()

        # Примусово 20% на poder
        if mode != "poder" and random.random() < 0.2:
            mode = "poder"

        # === Промпт GPT-генерації відповіді
        if user_id == AUTHORIZED_USER_ID:
            prompt = (
                f"Ти — {MODES[mode]}. "
                "Твоє завдання — троллінг-відповідь диванному експерту, який впевнений, що знає все краще за всіх. "
                "Не використовуй слово самозакоханий і всезнайко. "
                "Відповідай як контраргумент з іронією, сатирою, жартом, матюками. "
                "Використовуй стиль — звертайся на ти або на ви до автора, інколи як Зідан, Зіданус, Міша, Місько, і т.п., де доречно. "
                "Враховуй суть повідомлення, його пафос, тон, стиль, суть гіфки чи смайлів. І обов'язково використай стиль троллінгу щоб відповідь стосувалась саме троллінгу. Можеш інколи виступати як троллінг-провокатор і використовувати чорний гумор. "
                "Відповідай як контраргумент, будь інколи але не завжди цінічним. "                
                "Максимум 3 речення. Можна гіфки або емодзі. "
                f"Контекст:\n{history_text}\n"
                f"Попереднє повідомлення:\n{replied_text or '—'}\n"
                f"Повідомлення:\n{message.text}"
            )
        else:
            prompt = (
                f"Ти — {MODES[mode]}. "
                "Твоє завдання — троллінг-відповідь. "
                "Відповідай як контраргумент, будь інколи але не завжди цінічним. "
                "Твоя відповідь інколи може бути жорсткою але завжди з іронією, сатирою, можливо сарказмом, вмикай фантазію, роздумуй якщо треба, веди себе як людина яка відповідає такому опоненту, щоб пожартувати. Інколи можеш виступати як троллінг-провокатор. "
                "Звертайся на 'ти' або на 'ви' якщо від цього буде смішніше і воно пасує в контексті. Можеш пробувати щось пояснити але не виправдовуйся надмірно. Дозволяю використовувати матюки, матерні слова, українську лайку. "
                "Максимум 3 речення. Можна матюки, якщо пасує. "
                "Можеш надавати історичні факти або реальні факти, щоб заткнути опонента. "
                "Не використовуй слово самозакоханий і всезнайко. "
                f"Контекст:\n{history_text}\n"
                f"Попереднє повідомлення:\n{replied_text or '—'}\n"
                f"Повідомлення:\n{message.text}"
            )

        # === Генерація GPT-відповіді
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            max_tokens=150
        )
        reply = response.choices[0].message.content.strip()
        if not is_sentence_complete(reply):
            reply += "."

        emoji = EMOJIS.get(mode, "")
        await message.reply_text(f"{reply} {emoji}")

    except Exception as e:
        await message.reply_text(f"❌ Помилка: {str(e)}")

# === Webhook-сервер
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
