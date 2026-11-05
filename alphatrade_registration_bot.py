
import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NAME, PHONE, CONSENT = range(3)


# Render uchun HTTP server
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, format, *args):
        pass


def start_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


def save(name, phone):
    with sqlite3.connect("registrations.db") as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                phone TEXT
            )"""
        )
        db.execute(
            "INSERT INTO users (name, phone) VALUES (?, ?)",
            (name, phone),
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "📈 TREYDINGDA DAROMAD\n"
        "🎓 Bepul oflayn vebinar\n"
        "📅 29-noyabr 2026-yil\n"
        "📍 Denov shahri\n"
        "🏢 AlphaTrade Academy\n\n"
        "Ro‘yxatdan o‘tish uchun /register bosing."
    )


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ism-familiyangizni yozing:")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()

    keyboard = [[
        KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
    ]]

    await update.message.reply_text(
        "Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        ),
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact

    if not contact or (
        contact.user_id and contact.user_id != update.effective_user.id
    ):
        await update.message.reply_text(
            "Iltimos, o‘z telefon raqamingizni yuboring."
        )
        return PHONE

    context.user_data["phone"] = contact.phone_number

    keyboard = [["✅ Roziman"], ["❌ Bekor qilish"]]

    await update.message.reply_text(
        "Ma'lumotlaringiz vebinar tashkiliy xabarlari uchun "
        "ishlatilishiga rozimisiz?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        ),
    )
    return CONSENT


async def consent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text

    if answer == "❌ Bekor qilish":
        context.user_data.clear()
        await update.message.reply_text(
            "Ro‘yxatdan o‘tish bekor qilindi.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    if answer != "✅ Roziman":
        await update.message.reply_text("Tugmalardan birini tanlang.")
        return CONSENT

    save(
        context.user_data["name"],
        context.user_data["phone"],
    )
    context.user_data.clear()

    await update.message.reply_text(
        "🎉 Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz!\n\n"
        "📅 29-noyabr 2026-yil\n"
        "📍 Denov shahri\n"
        "AlphaTrade Academy sizni kutadi!",
        reply_markup=ReplyKeyboardRemove(),
    )

    return ConversationHandler.END


def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN sozlanmagan!")

    # Render portini ochamiz
    threading.Thread(
        target=start_web_server,
        daemon=True
    ).start()

    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("register", register)],
        states={
            NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)
            ],
            PHONE: [
                MessageHandler(filters.CONTACT, get_phone)
            ],
            CONSENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, consent)
            ],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)

    print("Telegram bot ishga tushmoqda...")
    app.run_polling()


if __name__ == "__main__":
    main()
