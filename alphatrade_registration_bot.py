
import os
import sqlite3
import threading
import csv
import io

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = 671517993
DB_NAME = "registrations.db"

NAME, PHONE, CONSENT, TRADING, SOURCE = range(5)


# Ma'lumotlar bazasi va eski bazani yangilash
def init_db():
    with sqlite3.connect(DB_NAME) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT
            )
        """)

        columns = [
            row[1] for row in db.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        ]

        if "trading" not in columns:
            db.execute("ALTER TABLE users ADD COLUMN trading TEXT")

        if "source" not in columns:
            db.execute("ALTER TABLE users ADD COLUMN source TEXT")


def save(name, phone, trading, source):
    with sqlite3.connect(DB_NAME) as db:
        db.execute(
            """INSERT INTO users
            (name, phone, trading, source)
            VALUES (?, ?, ?, ?)""",
            (name, phone, trading, source)
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
    server = ThreadingHTTPServer(
        ("0.0.0.0", port), HealthHandler
    )
    server.serve_forever()


async def set_commands(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Botni boshlash"),
        BotCommand("register", "Ro‘yxatdan o‘tish"),
        BotCommand("admin", "Admin panel"),
        BotCommand("count", "Qatnashchilar soni"),
        BotCommand("list", "Qatnashchilar ro‘yxati"),
        BotCommand("export", "Ro‘yxatni faylga olish"),
        BotCommand("cancel", "Ro‘yxatdan chiqish"),
    ])


def is_admin(update):
    return update.effective_user.id == ADMIN_ID


# ADMIN PANEL
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    keyboard = [
        ["👥 Qatnashchilar soni"],
        ["📋 Qatnashchilar ro‘yxati"],
        ["📥 Excel uchun fayl"],
    ]

    await update.message.reply_text(
        "🔐 ADMIN PANEL\nKerakli bo‘limni tanlang:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True
        )
    )


async def count_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    with sqlite3.connect(DB_NAME) as db:
        total = db.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

    await update.message.reply_text(
        f"👥 Jami ro‘yxatdan o‘tganlar: {total} ta"
    )


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    with sqlite3.connect(DB_NAME) as db:
        users = db.execute(
            """SELECT id, name, phone, trading, source
            FROM users ORDER BY id DESC LIMIT 100"""
        ).fetchall()

    if not users:
        await update.message.reply_text("Hozircha qatnashchilar yo‘q.")
        return

    for start in range(0, len(users), 5):
        message = "📋 QATNASHCHILAR RO‘YXATI\n\n"

        for user in users[start:start + 5]:
            uid, name, phone, trading, source = user
            message += (
                f"#{uid}\n"
                f"👤 {name}\n"
                f"📞 {phone}\n"
                f"📈 Treyding bilimi: {trading or '—'}\n"
                f"📍 Manba: {source or '—'}\n\n"
            )

        await update.message.reply_text(message)


async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    with sqlite3.connect(DB_NAME) as db:
        users = db.execute(
            """SELECT id, name, phone, trading, source
            FROM users ORDER BY id"""
        ).fetchall()

    if not users:
        await update.message.reply_text("Eksport uchun ma'lumot yo‘q.")
        return

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Ism-familiya", "Telefon",
        "Treyding bilimi", "Qayerdan bildi"
    ])
    writer.writerows(users)

    file_data = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    file_data.name = "qatnashchilar.csv"

    await update.message.reply_document(
        document=file_data,
        filename="qatnashchilar.csv",
        caption="📥 Qatnashchilar ro‘yxati"
    )


# ADMIN TUGMALARI
async def admin_count_button(update, context):
    await count_users(update, context)


async def admin_list_button(update, context):
    await list_users(update, context)


async def admin_export_button(update, context):
    await export_users(update, context)


# FOYDALANUVCHI RO‘YXATDAN O‘TISHI
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "📈 TREYDINGDA DAROMAD\n"
        "🎓 Bepul oflayn vebinar\n"
        "📅 29-noyabr 2026-yil\n"
        "📍 Denov shahri\n"
        "🏢 AlphaTrade Academy\n\n"
        "Ro‘yxatdan o‘tish uchun tugmani bosing.",
        reply_markup=ReplyKeyboardMarkup(
            [["📝 Ro‘yxatdan o‘tish"]],
            resize_keyboard=True
        )
    )


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ism-familiyangizni yozing:",
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()

    keyboard = [[
        KeyboardButton(
            "📱 Telefon raqamni yuborish",
            request_contact=True
        )
    ]]

    await update.message.reply_text(
        "Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True
        )
    )
    return PHONE


async def phone_again(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Iltimos, pastdagi telefon raqamini yuborish tugmasini bosing."
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
        "Ma'lumotlaringiz vebinarni tashkil qilish va "
        "tashkiliy xabarlar uchun ishlatilishiga rozimisiz?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True
        )
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

    keyboard = [
        ["✅ Ha, tushuncham bor"],
        ["🆕 Yo‘q, yangi boshlovchiman"]
    ]

    await update.message.reply_text(
        "📈 Treyding haqida tushunchangiz bormi?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True
        )
    )
    return TRADING


async def get_trading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text

    if answer == "✅ Ha, tushuncham bor":
        context.user_data["trading"] = "Tushuncham bor"
    elif answer == "🆕 Yo‘q, yangi boshlovchiman":
        context.user_data["trading"] = "Yangi boshlovchi"
    else:
        await update.message.reply_text("Iltimos, tugmalardan birini tanlang.")
        return TRADING

    keyboard = [
        ["✈️ Telegram", "📸 Instagram"],
        ["▶️ YouTube", "👥 Do‘st yoki tanish"],
        ["📢 Reklama", "🔎 Boshqa"]
    ]

    await update.message.reply_text(
        "📍 AlphaTrade Academy vebinari haqida qayerdan bildingiz?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True
        )
    )
    return SOURCE


async def get_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text

    allowed = [
        "✈️ Telegram",
        "📸 Instagram",
        "▶️ YouTube",
        "👥 Do‘st yoki tanish",
        "📢 Reklama",
        "🔎 Boshqa"
    ]

    if answer not in allowed:
        await update.message.reply_text("Iltimos, tugmalardan birini tanlang.")
        return SOURCE

    context.user_data["source"] = answer

    save(
        context.user_data["name"],
        context.user_data["phone"],
        context.user_data["trading"],
        context.user_data["source"]
    )

    context.user_data.clear()

    await update.message.reply_text(
        "🎉 Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz!\n\n"
        "📅 29-noyabr 2026-yil\n"
        "📍 Denov shahri\n"
        "AlphaTrade Academy sizni kutadi!",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Ro‘yxatdan o‘tish bekor qilindi.",
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

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(set_commands)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("count", count_users))
    app.add_handler(CommandHandler("list", list_users))
    app.add_handler(CommandHandler("export", export_users))

    app.add_handler(MessageHandler(
        filters.Regex("^📝 Ro‘yxatdan o‘tish$"), register
    ))

    app.add_handler(MessageHandler(
        filters.Regex("^👥 Qatnashchilar soni$"), admin_count_button
    ))
    app.add_handler(MessageHandler(
        filters.Regex("^📋 Qatnashchilar ro‘yxati$"), admin_list_button
    ))
    app.add_handler(MessageHandler(
        filters.Regex("^📥 Excel uchun fayl$"), admin_export_button
    ))

    conv = ConversationHandler(
        entry_points=[CommandHandler("register", register)],
        states={
            NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)
            ],
            PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, phone_again)
            ],
            CONSENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, consent)
            ],
            TRADING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_trading)
            ],
            SOURCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_source)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)

    print("Telegram bot ishga tushdi!")
    app.run_polling()


if __name__ == "__main__":
    main()
