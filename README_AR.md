# بوت القيادة لتحسين الصور

نسخة معدلة من البوت للعمل على Render بوضع Worker + Polling.

## المزايا
- 🚀 تحسين 4K
- 👑 تحسين 8K
- 🎨 8 فلاتر
- 🤖 إنشاء صور بالذكاء الاصطناعي عند توفر مفتاح Gemini
- 🔐 لوحة مالك
- 🔎 الأمر `/status` لفحص مفاتيح التشغيل

## متغيرات Render المطلوبة
- `BOT_TOKEN` = توكن البوت من BotFather
- `ADMIN_USER_ID` = رقم حساب المالك، يمكن معرفته بالأمر `/id`
- `ADMIN_PIN` = رمز لوحة المالك
- `REPLICATE_API_TOKEN` = مطلوب لـ 4K/8K
- `GEMINI_API_KEY` = مطلوب لإنشاء الصور بالذكاء الاصطناعي
- `GEMINI_MODEL` = اسم نموذج Gemini

## التشغيل
`render.yaml` يشغل:
`python bot.py`

لا يحتاج البوت إلى Webhook أو دومين، لأنه يستخدم Polling.

### ملاحظة مهمة
الفلاتر المحلية تعمل بدون Replicate وبدون Gemini. أما تحسين 4K/8K الحقيقي فيحتاج `REPLICATE_API_TOKEN`.
