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
    "kum": "Кум з села, розказує все по-своєму, з фольклорним гумором і примітивною логікою, використовуючи український народний жаргон."
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
    "kum": "🧅"
}

# інший код і функції лишаємо без змін