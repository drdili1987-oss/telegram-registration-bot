import os
import json
import logging
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Konstantlar ──────────────────────────────────────────────────────────────
BOT_TOKEN  = "8786044719:AAFtnwchKGuFua4Du89LSz4NPB4SbuoCECI"   # @BotFather dan olingan token

# ❗ ADMIN_CHAT_ID ni olish uchun @userinfobot ga /start yuboring
# Yoki @getmyid_bot ga yozing — u sizning ID raqamingizni beradi
ADMIN_CHAT_ID = 156664   # <- bu yerga o'z Telegram ID raqamingizni yozing

DATA_FILE     = "students.json"
PASSPORTS_DIR = "passportlar"

# ConversationHandler bosqichlari
FIO, PHONE, PASSPORT = range(3)


# ─── Yordamchi funksiyalar ─────────────────────────────────────────────────────

def ensure_dirs():
    os.makedirs(PASSPORTS_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_students() -> list:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_students(students: list):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(students, f, ensure_ascii=False, indent=2)


def add_student(record: dict):
    students = load_students()
    students.append(record)
    save_students(students)


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_CHAT_ID


# ─── Admin bildirishnomasi ─────────────────────────────────────────────────────

async def notify_admin(context: ContextTypes.DEFAULT_TYPE, record: dict, photo_path: str):
    """Yangi o'quvchi ro'yxatdan o'tganda adminga xabar va passport rasmi yuborish."""
    students = load_students()
    total = len(students)

    caption = (
        "🆕 *Yangi o'quvchi ro'yxatdan o'tdi!*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *F.I.O:* {record['fio']}\n"
        f"📞 *Telefon:* {record['phone']}\n"
        f"🔗 *Username:* @{record['username'] or 'yoq'}\n"
        f"🆔 *Telegram ID:* `{record['id']}`\n"
        f"🗓 *Sana:* {record['registered_at']}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Jami ro'yxatdan o'tganlar:* {total} nafar"
    )

    with open(photo_path, "rb") as photo_file:
        await context.bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=photo_file,
            caption=caption,
            parse_mode="Markdown",
        )


# ─── /start ───────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    message = update.effective_message
    if not message:
        return ConversationHandler.END

    await message.reply_text(
        "👋 Assalomu alaykum!\n\n"
        "Kursga ro'yxatdan o'tish uchun bir necha savollarga javob bering.\n\n"
        "Iltimos, to'liq *Ism-Familiyangizni* kiriting:\n"
        "_(Masalan: Karimov Jasur Baxtiyorovich)_",
        parse_mode="Markdown",
    )
    return FIO



# ─── FIO ──────────────────────────────────────────────────────────────────────

async def get_fio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    if not message or not message.text:
        return FIO
        
    fio = message.text.strip()

    if len(fio.split()) < 2:
        await message.reply_text(
            "Iltimos, to'liq ism-sharifingizni kiriting "
            "(kamida ism va familiya)."
        )
        return FIO


    context.user_data["fio"] = fio

    contact_button = KeyboardButton("Raqamni yuborish", request_contact=True)
    keyboard = ReplyKeyboardMarkup(
        [[contact_button]], resize_keyboard=True, one_time_keyboard=True
    )

    await message.reply_text(
        f"Rahmat, *{fio}*!\n\n"
        "Endi telefon raqamingizni yuboring.\n"
        "Quyidagi tugmani bosing yoki raqamni qo'lda kiriting "
        "_(+998901234567 formatida)_:",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return PHONE



# ─── PHONE ────────────────────────────────────────────────────────────────────

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    if not message:
        return PHONE

    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone
    elif message.text:
        phone = message.text.strip()
        digits = phone.replace("+", "").replace(" ", "").replace("-", "")
        if not digits.isdigit() or len(digits) < 9:
            await message.reply_text(
                "Telefon raqam noto'g'ri formatda. Iltimos qaytadan kiriting.\n"
                "_(Masalan: +998901234567)_",
                parse_mode="Markdown",
            )
            return PHONE
    else:
        return PHONE


    context.user_data["phone"] = phone

    await message.reply_text(
        "Telefon raqam qabul qilindi!\n\n"
        "*Pasportingizning rasmini* yuboring:\n"
        "_(Passport barcha ma'lumotlari aniq ko'rinib turishi kerak)_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return PASSPORT



# ─── PASSPORT ─────────────────────────────────────────────────────────────────

async def get_passport(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    if not message or not message.photo:
        await message.reply_text(
            "Iltimos, faqat *rasm* yuboring (hujjat emas).",
            parse_mode="Markdown",
        )
        return PASSPORT

    photo     = message.photo[-1]

    file      = await context.bot.get_file(photo.file_id)
    user_id   = update.effective_user.id
    fio_slug  = context.user_data["fio"].replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"{fio_slug}_{user_id}_{timestamp}.jpg"
    filepath  = os.path.join(PASSPORTS_DIR, filename)

    await file.download_to_drive(filepath)

    record = {
        "id":            user_id,
        "username":      update.effective_user.username or "",
        "fio":           context.user_data["fio"],
        "phone":         context.user_data["phone"],
        "passport_img":  filepath,
        "registered_at": datetime.now().isoformat(timespec="seconds"),
    }
    add_student(record)
    logger.info("Yangi o'quvchi: %s", record["fio"])

    # Foydalanuvchiga tasdiqlash
    await message.reply_text(
        "*Tabriklaymiz!* Ro'yxatdan muvaffaqiyatli o'tdingiz.\n\n"
        f"*Ism:* {record['fio']}\n"
        f"*Telefon:* {record['phone']}\n"
        f"*Sana:* {record['registered_at']}\n\n"
        "Tez orada siz bilan bog'lanamiz!",
        parse_mode="Markdown",
    )


    # Adminga bildirishnoma + passport rasmi
    try:
        await notify_admin(context, record, filepath)
    except Exception as e:
        logger.error("Admin ga xabar yuborishda xatolik: %s", e)

    context.user_data.clear()
    return ConversationHandler.END


# ─── Admin buyruqlari ──────────────────────────────────────────────────────────

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/list — barcha ro'yxatdan o'tganlarni ko'rish (faqat admin)."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Bu buyruq faqat admin uchun.")
        return

    students = load_students()
    if not students:
        await update.message.reply_text("Hali hech kim ro'yxatdan o'tmagan.")
        return

    lines = [f"*Royxatdan otganlar ({len(students)} nafar):*\n"]
    for i, s in enumerate(students, 1):
        username = f"@{s['username']}" if s["username"] else "—"
        lines.append(
            f"{i}. *{s['fio']}*\n"
            f"   {s['phone']} | {username}\n"
            f"   {s['registered_at']}\n"
        )

    text = "\n".join(lines)
    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/count — nechta odam ro'yxatdan o'tganini ko'rish (faqat admin)."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Bu buyruq faqat admin uchun.")
        return

    students = load_students()
    await update.message.reply_text(
        f"Jami royxatdan otganlar: *{len(students)} nafar*",
        parse_mode="Markdown",
    )


async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/export — students.json faylini yuklash (faqat admin)."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Bu buyruq faqat admin uchun.")
        return

    students = load_students()
    if not students:
        await update.message.reply_text("Malumotlar bazasi bosh.")
        return

    with open(DATA_FILE, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename="students.json",
            caption=f"Jami: {len(students)} nafar o'quvchi",
        )


# ─── Cancel ───────────────────────────────────────────────────────────────────

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    message = update.effective_message
    if message:
        await message.reply_text(
            "Ro'yxatdan o'tish bekor qilindi.\n"
            "Qaytadan boshlash uchun /start buyrug'ini yuboring.",
            reply_markup=ReplyKeyboardRemove(),
        )
    return ConversationHandler.END


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Noma'lum buyruq kelganda javob berish."""
    if update.effective_message:
        await update.effective_message.reply_text("Kechirasiz, bunday buyruqni bilmayman. Iltimos /start buyrug'idan foydalaning.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xatoliklarni log qilish."""
    logger.error("Update '%s' caused error '%s'", update, context.error)




# ─── Health Check Server ───────────────────────────────────────────────────────

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, format, *args):
        # Loglarni kamaytirish uchun bo'sh qoldiramiz
        return

def run_health_check():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"Health check server started on port {port}")
    server.serve_forever()

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    ensure_dirs()
    
    # Render uchun health check serverni alohida thread da ishga tushiramiz
    threading.Thread(target=run_health_check, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FIO:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fio)],
            PHONE:    [MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), get_phone)],
            PASSPORT: [MessageHandler(filters.PHOTO, get_passport)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("list",   cmd_list))
    app.add_handler(CommandHandler("count",  cmd_count))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    app.add_error_handler(error_handler)

    logger.info("Bot ishga tushdi... Toqtatish uchun Ctrl+C bosing.")


    # Python 3.14 uchun event loop fix
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run_polling()


if __name__ == "__main__":
    main()
