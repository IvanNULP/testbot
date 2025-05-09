import os
import random
from collections import deque
from telegram import Update, Message
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)
from openai import OpenAI

# ENV VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
AUTHORIZED_USER_ID = 384210176
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OPENAI CLIENT
client = OpenAI(api_key=OPENAI_API_KEY)

# ЧАТ-ІСТОРІЯ
CHAT_HISTORY = dict()
MAX_HISTORY = 20

# РЕЖИМИ
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
    "rashn_tv": "Пропагандист із рашн тб — пафосно бреше про зовнішні загрози, вихваляє перемоги навіть із поразок, постійно кричить про ворогів і героїзм москалів, перекручує будь-які факти на користь своїх. Слова перемога, вороги, героїзм, своїх — це все в лапках, тобто перекручені факти."
}

# ЕМОДЖІ
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

# РЕЖИМ
CURRENT_MODE = {"mode": "auto"}

# ПЕРЕВІРКА ЗАВЕРШЕНОСТІ РЕЧЕННЯ
def is_sentence_complete(text: str) -> bool:
    return text.strip().endswith(('.', '!', '?'))

# ОБРОБНИК ПОВІДОМЛЕНЬ
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message = update.message
    user_text = message.text
    replied_text = message.reply_to_message.text if message.reply_to_message else None

    # Зберегти історію чату
    if chat_id not in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = deque(maxlen=MAX_HISTORY)
    CHAT_HISTORY[chat_id].append(message)

    history_text = "\n".join([m.text for m in CHAT_HISTORY[chat_id] if m.text])
    is_continuation = replied_text is None or replied_text in history_text

    try:
        # ========== ВИБІР РЕЖИМУ ========== #
        if user_id != AUTHORIZED_USER_ID:
            combined_text = f"Контекст: {history_text if is_continuation else ''}\nПовідомлення: {user_text}"

            # GPT обирає режим
            mode_selection_response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ти — аналітик. На основі повідомлення та контексту вибери один із наступних персонажів, "
                            "який найкраще підійде для тролінг-відповіді:\n\n" +
                            ", ".join(MODES.keys()) +
                            "\n\nНе пояснюй вибір. Просто поверни один з цих ключів точно без додаткових символів."
                        )
                    },
                    {"role": "user", "content": combined_text}
                ],
                temperature=0.3,
                max_tokens=10
            )

            mode = mode_selection_response.choices[0].message.content.strip()

            # Примусова вставка "poder" у 20% випадків
            if mode != "poder" and random.random() < 0.2:
                mode = "poder"
        else:
            mode = None  # Спеціальний prompt

        # ========== СТВОРЕННЯ ПРОМПТА ========== #
        if user_id == AUTHORIZED_USER_ID:
            prompt = (
                "Твоє завдання — троллінг-відповідь диванному експерту, який впевнений, що знає все краще за всіх. "
                "Не використовуй слово самозакоханий і всезнайко і їх синоніми проте перевіряй текст на грамматичні і стилістичні помилки. Пересвідчись, що текст логічний і має закінчення. "
                "Відповідай як контраргумент, будь інколи але не завжди цінічним. "
                "Твоя відповідь інколи може бути жорсткою але завжди з іронією, сатирою, можливо сарказмом, вмикай фантазію, роздумуй якщо треба, веди себе як людина яка відповідає такому опоненту, щоб пожартувати. Інколи можеш виступати як троллінг-провокатор. "
                "Звертайся на 'ти' або на 'ви' якщо від цього буде смішніше і воно пасує в контексті. Можеш пробувати щось пояснити але не виправдовуйся надмірно. Дозволяю використовувати матюки, матерні слова, українську лайку. "
                "Також можеш інколи, але не завжди, звертатись до автора за іменем — Зідан, Зіданга, Зіданус, Зідаун, Михайло, Місько, Михуїл, Міша та інші подібні похідні імена. Зіданга використовуй коли автор говорить про майбутнє як Ванга. "
                "Відповідь має бути не велика. Максимум на 3 речення. Якщо треба можеш використати смайлики або гіфку. "
                f"Контекст: {history_text if is_continuation else ''}\n"
                f"Якщо це відповідь на інше повідомлення: {replied_text or '—'}\n"
                f"Повідомлення: {user_text}"
            )
        else:
            prompt = (
                f"Ти — {MODES[mode]}. "
                "Твоє завдання — троллінг-відповідь. "
                "Не використовуй слово самозакоханий і всезнайко. Перевіряй текст на грамматичні і стилістичні помилки. "
                "Пересвідчись, що текст логічний і має закінчення. "
                "Відповідай як контраргумент. Можеш бути іронічним, цинічним, сатиричним, фантазійним. "
                "Інколи провокуй. Використовуй матюки, але не без причини. Максимум — 3 речення. "
                "Якщо не знаєш що сказати — інколи просто скажи 'йди нахуй'. "
                f"Контекст: {history_text if is_continuation else ''}\n"
                f"Попереднє повідомлення: {replied_text or '—'}\n"
                f"Повідомлення: {user_text}"
            )

        # ========== ВІДПОВІДЬ GPT ========== #
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.8,
            max_tokens=150
        )

        response_text = response.choices[0].message.content.strip()
        if not is_sentence_complete(response_text):
            response_text += "."

        emoji = EMOJIS.get(mode, "")
        await message.reply_text(f"{response_text} {emoji}")

    except Exception as e:
        await message.reply_text("⚠️ Сталася помилка: " + str(e))

# ========== ЗАПУСК ========== #
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
