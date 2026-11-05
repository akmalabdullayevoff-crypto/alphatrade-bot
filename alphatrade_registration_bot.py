
import os
import sqlite3
import threading
import csv
import io

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = 671517993

NAME, PHONE, CONSENT = range(3)
DB_NAME = "registrations.db"


# Ma'lumotlar bazasi
def init_db():
    with sqlite3.connect(DB_NAME) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT
            )
        """)


def save(name, phone):
    with sqlite3.connect(DB_NAME) as db:
        db.execute(
            "INSERT INTO users (name, phone) VALUES (?, ?)",
            (name, phone)
        )


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


# Faqat admin uchun
def is_admin(update):
    return update.effective_user.id == ADMIN_ID


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    await update.message.reply_text(
        "🔐 ADMIN PANEL\n\n"
        "/count — Qatnashchilar soni\n"
        "/list — Qatnashchilar ro‘yxati\n"
        "/export — Excel uchun CSV fayl"
    )


async def count_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    with sqlite3.connect(DB_NAME) as db:
        total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    await update.message.reply_text(
        f"👥 Jami ro‘yxatdan o‘tganlar: {total} ta"
    )


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    with sqlite3.connect(DB_NAME) as db:
        users = db.execute(
            "SELECT id, name, phone FROM users ORDER BY id DESC LIMIT 30"
        ).fetchall()

    if not users:
        await update.message.reply_text("Hozircha qatnashchilar yo‘q.")
        return

    for start in range(0, len(users), 10):
        part = users[start:start + 10]
        message = "📋 QATNASHCHILAR RO‘YXATI\n\n"

        for user_id, name, phone in part:
            message += (
                f"#{user_id}\n"
                f"👤 {name}\n"
                f"📞 {phone}\n\n"
            )

        await update.message.reply_text(message)


async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    with sqlite3.connect(DB_NAME) as db:
        users = db.execute(
            "SELECT id, name, phone FROM users ORDER BY id"
        ).fetchall()

    if not users:
        await update.message.reply_text("Eksport qilish uchun ma'lumot yo‘q.")
        return

    text_file = io.StringIO()
    writer = csv.writer(text_file)
    writer.writerow(["ID", "Ism-familiya", "Telefon raqami"])
    writer.writerows(users)

    file_data = io.BytesIO(text_file.getvalue().encode("utf-8-sig"))
    file_data.name = "qatnashchilar.csv"

    await update.message.reply_document(
        document=file_data,
        filename="qatnashchilar.csv",
        caption="📥 Qatnashchilar ro‘yxati"
    )


# Oddiy foydalanuvchi bo‘limi
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
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
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
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return CONSENT


async def consent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text

    if answer == "❌ Bekor qilish":
        context.user_data.clear()
        await update.message.reply_text(
            "Ro‘yxatdan o‘tish bekor qilindi.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    if answer != "✅ Roziman":
        await update.message.reply_text("Tugmalardan birini tanlang.")
        return CONSENT

    save(context.user_data["name"], context.user_data["phone"])
    context.user_data.clear()

    await update.message.reply_text(
        "🎉 Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz!\n\n"
        "📅 29-noyabr 2026-yil\n"
        "📍 Denov shahri\n"
        "AlphaTrade Academy sizni kutadi!",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN sozlanmagan!")

    init_db()

    threading.Thread(
        target=start_web_server,
        daemon=True
    ).start()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("count", count_users))
    app.add_handler(CommandHandler("list", list_users))
    app.add_handler(CommandHandler("export", export_users))

    conv = ConversationHandler(
        entry_points=[CommandHandler("register", register)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.CONTACT, get_phone)],
            CONSENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, consent)]
        },
        fallbacks=[]
    )

    app.add_handler(conv)

    print("Telegram bot ishga tushdi!")
    app.run_polling()


if __name__ == "__main__":
    main()
