# 🤖 Mustafa Bot - Gold Trading Signals

بوت تلجرام متخصص في إرسال إشارات تداول الذهب (XAU/USD) بالذكاء الاصطناعي.

## ⚙️ التقنيات

| التقنية | الوصف |
|---------|-------|
| 🏛️ **SMC + ICT** | استراتيجية Smart Money Concepts + Inner Circle Trader |
| 🧠 **3 نماذج AI** | DeepSeek + Gemini + ChatGPT (نظام إجماع ثلاثي) |
| 📊 **TradingView** | بيانات أسعار حية متعددة الأطر الزمنية |
| 🔍 **فلترة 5 مراحل** | من مئات الإعدادات → أفضل إشارة واحدة |
| 📱 **Telegram Bot** | إشارات تلقائية مع تحليل مفصل |

## 🚀 التشغيل السريع

### 1. تثبيت المكتبات
```bash
pip install -r requirements.txt
```

### 2. إعداد المتغيرات
```bash
cp .env.example .env
# عدّل .env وأضف مفاتيح API الخاصة بك
```

### 3. تشغيل البوت
```bash
python main.py
```

## 📋 أوامر البوت

| الأمر | الوظيفة |
|-------|---------|
| `/start` | بدء البوت ورسالة الترحيب |
| `/signal` | طلب إشارة تداول فورية |
| `/analysis` | تحليل شامل لسوق الذهب |
| `/predict` | توقع السعر المستقبلي |
| `/status` | إحصائيات البوت |
| `/help` | المساعدة |

## 📁 هيكل المشروع

```
├── main.py              # نقطة الدخول
├── config.py            # الإعدادات
├── data/                # جلب البيانات (TradingView)
├── analysis/            # محرك SMC/ICT
├── ai/                  # نماذج AI الثلاثة
├── signals/             # مولّد وفلتر الإشارات
├── bot/                 # بوت تلجرام
└── utils/               # أدوات مساعدة
```

## 🔑 المفاتيح المطلوبة

- `TELEGRAM_BOT_TOKEN` - من [@BotFather](https://t.me/BotFather)
- `TELEGRAM_CHAT_ID` - معرف القناة/المجموعة
- `DEEPSEEK_API_KEY` - من [DeepSeek](https://platform.deepseek.com)
- `GEMINI_API_KEY` - من [Google AI Studio](https://aistudio.google.com)
- `OPENAI_API_KEY` - من [OpenAI](https://platform.openai.com)

## 🚢 النشر على Railway

1. Fork هذا المستودع
2. اذهب إلى [railway.app](https://railway.app)
3. New Project → Deploy from GitHub
4. أضف متغيرات البيئة في Variables
5. Deploy! 🚀

## ⚠️ إخلاء مسؤولية

هذا البوت أداة تحليلية فقط وليس نصيحة مالية. التداول ينطوي على مخاطر عالية.

---

**Mustafa Bot** | SMC + ICT + AI | Made with ❤️
