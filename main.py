from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
import logging
import asyncio
import httpx
import json
import os

# Tokenlar
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
ADMIN_IDS = [2067045779]  # Admin Telegram ID-larini shu yerga qo‘shing

# Logging
logging.basicConfig(level=logging.INFO)

# Foydalanuvchilar statistikasi fayli
STATS_FILE = "users.json"

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    return {}

def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Menga xabar yuboring, men javob beraman 😊")

# OpenRouter API orqali so‘rov yuborish
async def get_openrouter_reply(message: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourdomain.com",  # o'zgartiring
        "X-Title": "telegram-gpt-bot"
    }
    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": message}
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']

# Foydalanuvchi xabari
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    stats = load_stats()
    stats[user_id] = stats.get(user_id, 0) + 1
    save_stats(stats)

    user_message = update.message.text
    try:
        reply = await get_openrouter_reply(user_message)
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("Xatolik: " + str(e))

# /stats komandasi (faqat admin)
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Ruxsat yo'q.")
    stats = load_stats()
    total_users = len(stats)
    total_requests = sum(stats.values())
    msg = f"📊 Statistika:\n👤 Foydalanuvchilar: {total_users}\n📨 So‘rovlar: {total_requests}"
    await update.message.reply_text(msg)

# /broadcast komandasi (admin xabar yuboradi)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Ruxsat yo'q.")
    if not context.args:
        return await update.message.reply_text("Xabar matnini yuboring: /broadcast Salom!")

    stats = load_stats()
    message = " ".join(context.args)
    success = 0
    for uid in stats:
        try:
            await context.bot.send_message(chat_id=int(uid), text=message)
            success += 1
        except:
            continue
    await update.message.reply_text(f"✅ {success} foydalanuvchiga yuborildi.")

# Botni ishga tushirish
if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot ishga tushdi. Kutyapmiz...")
    app.run_polling()
