import os, io, asyncio, logging
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.constants import ChatAction
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0") or 0)
ADMIN_PIN = os.getenv("ADMIN_PIN", "2468").strip()
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-image").strip()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("image-command-bot")
STATE = {}

WELCOME = """✨ أهلاً بك في «بوت القيادة لتحسين الصور»

🖼️ ارفع صورتك واختر:
• 🚀 تحسين 4K
• 👑 تحسين 8K
• 🎨 فلاتر احترافية
• 🤖 إنشاء صورة بالذكاء الاصطناعي

اختر من القائمة بالأسفل وابدأ."""

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 تحسين الصورة", callback_data="upscale")],
        [InlineKeyboardButton("🎨 الفلاتر الاحترافية", callback_data="filters")],
        [InlineKeyboardButton("🤖 إنشاء صورة بالذكاء الاصطناعي", callback_data="ai")],
        [InlineKeyboardButton("ℹ️ طريقة الاستخدام", callback_data="help")],
        [InlineKeyboardButton("⚙️ لوحة المالك", callback_data="admin")],
    ])

def upscale_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 تحسين إلى 4K", callback_data="scale:4")],
        [InlineKeyboardButton("👑 تحسين إلى 8K", callback_data="scale:8")],
        [InlineKeyboardButton("⬅️ الرئيسية", callback_data="home")],
    ])

def filter_keyboard():
    items = [
        ("✨ تحسين ذكي", "f:smart"), ("🎬 سينمائي", "f:cinema"),
        ("🌅 دافئ", "f:warm"), ("❄️ بارد", "f:cool"),
        ("🖤 أبيض وأسود", "f:bw"), ("📼 كلاسيكي", "f:vintage"),
        ("💎 حاد وواضح", "f:sharp"), ("🌸 ناعم", "f:soft"),
    ]
    rows = [items[i:i+2] for i in range(0, len(items), 2)]
    rows.append([("⬅️ الرئيسية", "home")])
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(a, callback_data=b) for a, b in r] for r in rows]
    )

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الإحصاءات", callback_data="admin:stats")],
        [InlineKeyboardButton("📣 رسالة جماعية (قيد الإعداد)", callback_data="admin:broadcast")],
        [InlineKeyboardButton("⬅️ الرئيسية", callback_data="home")],
    ])

def get_user_state(uid):
    return STATE.setdefault(uid, {"mode": None, "image": None, "pin_ok": False})

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user:
        STATE.setdefault(update.effective_user.id, {"mode": None, "image": None, "pin_ok": False})
    await update.message.reply_text(WELCOME, reply_markup=main_keyboard())

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🆔 معرّفك في تيليجرام:\n`{update.effective_user.id}`",
        parse_mode="Markdown"
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    checks = [
        ("BOT_TOKEN", bool(BOT_TOKEN)),
        ("REPLICATE_API_TOKEN", bool(REPLICATE_API_TOKEN)),
        ("GEMINI_API_KEY", bool(GEMINI_API_KEY)),
        ("ADMIN_USER_ID", ADMIN_USER_ID > 0),
    ]
    lines = ["🔎 حالة البوت:"]
    for name, ok in checks:
        lines.append(f"{'✅' if ok else '❌'} {name}")
    lines.append("\nملاحظة: الفلاتر تعمل بدون مفاتيح API، بينما 4K/8K تحتاج REPLICATE_API_TOKEN.")
    await update.message.reply_text("\n".join(lines))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📘 *طريقة الاستخدام*\n\n"
        "1) اضغط «تحسين الصورة» ثم أرسل صورة.\n"
        "2) اختر 4K أو 8K.\n"
        "3) ستصلك النسخة المحسّنة كملف قابل للتنزيل.\n\n"
        "🎨 للفلاتر: اختر «الفلاتر الاحترافية» ثم أرسل صورة واختر الفلتر.\n\n"
        "🤖 للإنشاء: اضغط «إنشاء صورة بالذكاء الاصطناعي» ثم اكتب وصف الصورة.\n\n"
        "🔐 لوحة المالك محمية برقم المعرّف + PIN."
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    st = get_user_state(uid)
    data = q.data

    if data == "home":
        st["mode"] = None
        await q.edit_message_text(WELCOME, reply_markup=main_keyboard())

    elif data == "upscale":
        st["mode"] = "upscale"
        st["image"] = None
        await q.edit_message_text(
            "🚀 اختر الدقة المطلوبة، ثم أرسل الصورة:",
            reply_markup=upscale_keyboard()
        )

    elif data == "filters":
        st["mode"] = "filters"
        st["image"] = None
        await q.edit_message_text(
            "🎨 أرسل الصورة أولاً، ثم اختر أحد الفلاتر الاحترافية:",
            reply_markup=filter_keyboard()
        )

    elif data == "ai":
        st["mode"] = "ai"
        await q.edit_message_text(
            "🤖 أرسل الآن وصف الصورة بالتفصيل.\n\n"
            "مثال: «رجل عربي أنيق في مكتب تصميم فاخر، إضاءة سينمائية، تصوير إعلاني واقعي، 4K»"
        )

    elif data == "help":
        await q.edit_message_text(
            "📘 أرسل صورة ← اختر 4K/8K أو فلتر.\n\n"
            "🤖 ويمكنك إنشاء صورة من وصف نصي باستخدام Gemini.",
            reply_markup=main_keyboard()
        )

    elif data == "admin":
        if uid != ADMIN_USER_ID:
            await q.edit_message_text(
                "🔒 هذه اللوحة خاصة بمالك البوت.\nأرسل /id لمعرفة معرّف حسابك."
            )
        else:
            st["mode"] = "admin_pin"
            st["pin_ok"] = False
            await q.edit_message_text("🔐 أدخل رمز لوحة المالك الآن:")

    elif data.startswith("scale:"):
        if not st.get("image"):
            await q.answer("أرسل الصورة أولاً.", show_alert=True)
            return
        scale = int(data.split(":")[1])
        await q.edit_message_text(f"⏳ جارٍ تجهيز نسخة {scale}K...")
        try:
            out = await upscale_image(st["image"], scale)
            await send_document(q.message, out, f"🖼️ الصورة المحسّنة {scale}K")
        except Exception:
            log.exception("upscale failed")
            await q.message.reply_text(
                "❌ تعذر تحسين الصورة الآن.\n"
                "تأكد من أن REPLICATE_API_TOKEN مضبوط بشكل صحيح في الاستضافة."
            )

    elif data.startswith("f:"):
        if not st.get("image"):
            await q.answer("أرسل الصورة أولاً.", show_alert=True)
            return
        kind = data.split(":")[1]
        await q.edit_message_text("🎨 جارٍ تطبيق الفلتر...")
        try:
            out = apply_filter(st["image"], kind)
            await send_document(q.message, out, "🎨 الصورة بعد الفلتر")
        except Exception:
            log.exception("filter failed")
            await q.message.reply_text("❌ تعذر تطبيق الفلتر على الصورة.")

    elif data == "admin:stats":
        if uid != ADMIN_USER_ID or not st.get("pin_ok"):
            await q.answer("🔒 غير مصرح.", show_alert=True)
            return
        users = len(STATE)
        images = sum(1 for x in STATE.values() if x.get("image"))
        await q.edit_message_text(
            f"📊 الإحصاءات\n\n👤 المستخدمون: {users}\n🖼️ جلسات بها صور: {images}",
            reply_markup=admin_keyboard()
        )

    elif data == "admin:broadcast":
        await q.answer("هذه الوظيفة محجوزة للتطوير القادم.", show_alert=True)

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    st = get_user_state(uid)
    text = (update.message.text or "").strip()

    if st.get("mode") == "admin_pin" and uid == ADMIN_USER_ID:
        if text == ADMIN_PIN:
            st["pin_ok"] = True
            st["mode"] = "admin"
            await update.message.reply_text("✅ تم فتح لوحة المالك.", reply_markup=admin_keyboard())
        else:
            await update.message.reply_text("❌ الرمز غير صحيح.")
        return

    if st.get("mode") == "ai":
        if not GEMINI_API_KEY:
            await update.message.reply_text(
                "⚠️ ميزة إنشاء الصور تحتاج GEMINI_API_KEY في إعدادات التشغيل."
            )
            return
        await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
        await update.message.reply_text("🤖 جاري إنشاء الصورة... قد يستغرق الأمر قليلًا.")
        try:
            data = await gemini_generate(text)
            await update.message.reply_document(
                InputFile(io.BytesIO(data), filename="ai_image.png"),
                caption="✨ تم إنشاء الصورة بالذكاء الاصطناعي"
            )
        except Exception:
            log.exception("gemini failed")
            await update.message.reply_text(
                "❌ تعذر إنشاء الصورة الآن. تأكد من GEMINI_API_KEY وإعدادات النموذج."
            )
        return

    await update.message.reply_text(
        "اختر ميزة من القائمة أولاً.", reply_markup=main_keyboard()
    )

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    st = get_user_state(uid)
    if st.get("mode") not in ("upscale", "filters"):
        await update.message.reply_text(
            "📌 اختر أولاً «تحسين الصورة» أو «الفلاتر الاحترافية».",
            reply_markup=main_keyboard()
        )
        return

    photo = update.message.photo[-1]
    tg_file = await context.bot.get_file(photo.file_id)
    bio = io.BytesIO()
    await tg_file.download_to_memory(bio)
    bio.seek(0)
    st["image"] = bio.getvalue()

    if st["mode"] == "upscale":
        await update.message.reply_text(
            "✅ وصلت الصورة. اختر الدقة:", reply_markup=upscale_keyboard()
        )
    else:
        await update.message.reply_text(
            "✅ وصلت الصورة. اختر الفلتر:", reply_markup=filter_keyboard()
        )

async def receive_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not (doc.mime_type or "").startswith("image/"):
        return
    uid = update.effective_user.id
    st = get_user_state(uid)
    if st.get("mode") not in ("upscale", "filters"):
        await update.message.reply_text(
            "اختر ميزة الصور أولاً.", reply_markup=main_keyboard()
        )
        return

    f = await context.bot.get_file(doc.file_id)
    bio = io.BytesIO()
    await f.download_to_memory(bio)
    st["image"] = bio.getvalue()
    await update.message.reply_text(
        "✅ وصلت الصورة.",
        reply_markup=upscale_keyboard() if st["mode"] == "upscale" else filter_keyboard()
    )

async def send_document(message, data, caption):
    await message.reply_document(
        InputFile(io.BytesIO(data), filename="enhanced_image.png"),
        caption=caption
    )

def apply_filter(data: bytes, kind: str) -> bytes:
    im = Image.open(io.BytesIO(data)).convert("RGB")
    if kind == "smart":
        im = ImageEnhance.Contrast(im).enhance(1.12)
        im = ImageEnhance.Color(im).enhance(1.12)
        im = ImageEnhance.Sharpness(im).enhance(1.45)
    elif kind == "cinema":
        im = ImageEnhance.Contrast(im).enhance(1.20)
        im = ImageEnhance.Color(im).enhance(0.88)
        im = ImageEnhance.Sharpness(im).enhance(1.25)
    elif kind == "warm":
        r, g, b = im.split()
        r = r.point(lambda p: min(255, int(p * 1.06)))
        b = b.point(lambda p: int(p * 0.92))
        im = Image.merge("RGB", (r, g, b))
    elif kind == "cool":
        r, g, b = im.split()
        r = r.point(lambda p: int(p * 0.92))
        b = b.point(lambda p: min(255, int(p * 1.07)))
        im = Image.merge("RGB", (r, g, b))
    elif kind == "bw":
        im = ImageOps.grayscale(im).convert("RGB")
        im = ImageEnhance.Contrast(im).enhance(1.15)
    elif kind == "vintage":
        im = ImageEnhance.Color(im).enhance(0.72)
        im = ImageEnhance.Contrast(im).enhance(0.92)
        r, g, b = im.split()
        r = r.point(lambda p: min(255, int(p * 1.05)))
        b = b.point(lambda p: int(p * 0.90))
        im = Image.merge("RGB", (r, g, b))
    elif kind == "sharp":
        im = ImageEnhance.Contrast(im).enhance(1.10)
        im = ImageEnhance.Sharpness(im).enhance(2.0)
        im = im.filter(ImageFilter.UnsharpMask(radius=1.3, percent=140, threshold=3))
    elif kind == "soft":
        blur = im.filter(ImageFilter.GaussianBlur(0.6))
        im = Image.blend(im, blur, 0.25)

    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()

async def upscale_image(data: bytes, target_k: int) -> bytes:
    if target_k not in (4, 8):
        raise RuntimeError("دقة غير مدعومة")
    if not REPLICATE_API_TOKEN:
        raise RuntimeError("REPLICATE_API_TOKEN غير مضبوط")

    img = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = img.size
    target_long = 3840 if target_k == 4 else 7680
    scale_needed = target_long / max(w, h)

    if scale_needed <= 1:
        result = img
    else:
        result = await replicate_esrgan(data, min(4, max(2, scale_needed)))

    rw, rh = result.size
    ratio = target_long / max(rw, rh)
    if abs(ratio - 1) > 0.01:
        result = result.resize(
            (max(1, int(rw * ratio)), max(1, int(rh * ratio))),
            Image.Resampling.LANCZOS
        )

    out = io.BytesIO()
    result.save(out, format="PNG", optimize=True)
    return out.getvalue()

async def replicate_esrgan(data: bytes, scale: float) -> Image.Image:
    import base64
    b64 = base64.b64encode(data).decode()
    data_url = "data:image/png;base64," + b64
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": {
            "image": data_url,
            "scale": scale,
            "face_enhance": True
        }
    }

    # Correct Replicate model endpoint. The generic endpoint expects a
    # version hash; this endpoint accepts owner/model directly.
    r = requests.post(
        "https://api.replicate.com/v1/models/nightmareai/real-esrgan/predictions",
        headers=headers, json=payload, timeout=60
    )
    r.raise_for_status()
    pred = r.json()
    rid = pred["id"]

    for _ in range(120):
        await asyncio.sleep(2)
        rr = requests.get(
            f"https://api.replicate.com/v1/predictions/{rid}",
            headers=headers, timeout=30
        )
        rr.raise_for_status()
        p = rr.json()

        if p["status"] == "succeeded":
            url = p["output"]
            if isinstance(url, list):
                url = url[0]
            raw = requests.get(url, timeout=120).content
            return Image.open(io.BytesIO(raw)).convert("RGB")

        if p["status"] in ("failed", "canceled"):
            raise RuntimeError(p.get("error") or "Replicate failed")

    raise RuntimeError("انتهت مهلة المعالجة.")

async def gemini_generate(prompt: str) -> bytes:
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "model": GEMINI_MODEL,
        "input": prompt,
        "response_format": {"type": "image", "image_size": "4K"}
    }
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    r.raise_for_status()
    obj = r.json()

    import base64
    for key in ("image", "output", "outputs"):
        val = obj.get(key)
        if isinstance(val, dict):
            val = [val]
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    for k in ("data", "b64_json", "base64"):
                        if item.get(k):
                            return base64.b64decode(item[k])

    def scan(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("data", "b64_json", "base64") and isinstance(v, str) and len(v) > 100:
                    try:
                        return base64.b64decode(v)
                    except Exception:
                        pass
                z = scan(v)
                if z:
                    return z
        elif isinstance(x, list):
            for v in x:
                z = scan(v)
                if z:
                    return z
        return None

    data = scan(obj)
    if data:
        return data
    raise RuntimeError("لم أجد بيانات الصورة في استجابة Gemini.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Unhandled error", exc_info=context.error)

def run():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is missing")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("id", myid))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, receive_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text))
    app.add_error_handler(error_handler)
    print("Image Command Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    run()
