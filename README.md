# 🎬 MinoTV — Telegram Kino Boti (MVP)

MinoTV — bu Python va **aiogram 3** freymvorki yordamida yaratilgan, **SQLite** ma'lumotlar bazasiga asoslangan Telegram kino botining MVP versiyasi.

Loyiha videolarni server xotirasiga yuklab olmasdan ishlaydi. Barcha video fayllar yopiq (yoki ochiq) Telegram kanalida saqlanadi va bot `copyMessage` metodi orqali ularni to'g'ridan-to'g'ri foydalanuvchiga yetkazib beradi.

---

## 🛠 Texnologiyalar

- **Python**: 3.11+
- **aiogram**: 3.x (asinxron Telegram Bot API)
- **aiosqlite**: Asinxron SQLite drayveri
- **python-dotenv**: Muhit o'zgaruvchilarini (`.env`) boshqarish
- **pytest & pytest-asyncio**: Unit va integratsion testlar

---

## 📁 Loyiha Tuzilishi

```text
MinoTV/
├── handlers/
│   ├── __init__.py
│   ├── admin.py            # Admin paneli (kino qo'shish, tahrirlash, o'chirish, statistika)
│   └── user.py             # Foydalanuvchi interfeysi (kino kodi, janrlar, qidiruv, yordam)
├── tests/
│   ├── test_config_and_auth.py  # Konfiguratsiya, xavfsizlik va xatoliklar testi
│   ├── test_database.py         # SQLite CRUD, pagination, qidiruv va statistika testlari
│   └── test_handlers_and_fsm.py # Aiogram 3 handlerlari, FSM va forward tekshiruvi
├── .env.example            # Muhit o'zgaruvchilari namunasi
├── .gitignore              # Maxfiy va vaqtinchalik fayllarni chetlatish
├── config.py               # Loyiha sozlamalari va admin huquqlarini tekshirish
├── database.py             # SQLite asinxron modeli va barcha SQL so'rovlar
├── filters.py              # Admin huquqini tekshiruvchi IsAdminFilter
├── keyboards.py            # Reply va Inline tugmalar hamda CallbackData modellari
├── main.py                 # Botni ishga tushiruvchi asosiy kirish nuqtasi
├── pytest.ini              # Pytest sozlamalari
├── README.md               # To'liq hujjatlashtirish va yo'riqnoma
└── requirements.txt        # Kerakli Python kutubxonalari
```

---

## ⚙️ O'rnatish va Ishga Tushirish (Windows PowerShell)

### 1. Repozitoriy / Papkaga o'tish
```powershell
cd d:\MinoTv
```

### 2. Virtual muhitni (venv) yaratish va faollashtirish (Tavsiya etiladi)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Kerakli kutubxonalarni o'rnatish
```powershell
pip install -r requirements.txt
```

### 4. Konfiguratsiya faylini (`.env`) yaratish
`.env.example` nusxasidan `.env` faylini yarating:
```powershell
Copy-Item .env.example .env
```

`.env` faylini ochib, kerakli qiymatlarni to'ldiring:
```env
# Telegram Bot Token (@BotFather orqali olingan token)
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ

# Admin Telegram ID(lar)i (vergul bilan ajratilgan)
ADMIN_IDS=123456789,987654321

# Manba kanal IDsi (ixtiyoriy, masalan: -1001234567890)
SOURCE_CHANNEL_ID=-1001234567890

# SQLite fayl yo'li (standart: minotv.db)
DB_PATH=minotv.db
```

> ⚠️ **DIQQAT:** Hech qachon bot tokeningizni GitHub yoki ommaviy chatlarga chiqarmang! `.env` fayli `.gitignore` orqali himoyalangan.

### 5. Botni ishga tushirish
```powershell
python main.py
```

---

## 🔑 Muhim Qo'llanma: Token, Admin ID va Kanal Sozlamalari

### 1. BotFather orqali Token olish
1. Telegramda [@BotFather](https://t.me/BotFather) botiga kiring.
2. `/newbot` buyrug'ini yuboring va botingizga nom hamda username bering.
3. BotFather sizga API token beradi (masalan: `7123456789:AAH...`).
4. Ushbu tokenni `.env` faylidagi `BOT_TOKEN` maydoniga joylashtiring.

### 2. Admin Telegram ID sini olish
1. Telegramda [@userinfobot](https://t.me/userinfobot) ga `/start` yuboring.
2. Bot sizning raqamli `Id` raqamingizni ko'rsatadi (masalan: `543216789`).
3. Ushbu raqamni `.env` faylidagi `ADMIN_IDS` ga yozing.

### 3. Yopiq Kanalga Botni Ulash (Kino Saqlash Kanali)
1. Kinolar yuklanadigan kanal oching (yoki mavjud kanaldan foydalaning).
2. Botni kanalingizga **Admin (Administrator)** sifatida qo'shing.
   - Botga kamida **"Xabarlarni ko'rish / post qilish"** huquqi berilishi shart.
3. **Nega bu kerak?**
   - Bot kinolarni serverga yuklab olmaydi; foydalanuvchiga kanal xabarini `copyMessage` orqali yuboradi. Agar bot kanal a'zosi yoki admini bo'lmasa, Telegram API `Chat not found` xatosini qaytaradi.
4. **Content Protection (Kontent himoyasi) haqida muhim ogohlantirish:**
   - Agar kanalingizda *"Restrict saving content"* (Kontentni saqlash/nusxalashni taqiqlash) parametri yoqilgan bo'lsa, Telegram API `copyMessage` orqali video nusxasini foydalanuvchiga yuborishni bloklaydi.
   - Shuning uchun kino saqlanadigan kanalda bu parametr o'chirilgan bo'lishi tavsiya etiladi.

---

## 🧪 Avtomatlashtirilgan Testlarni Ishga Tushirish

Barcha testlar Telegram tokensiz ham mustaqil ishlaydi (SQLite bazasi, janrlar, muqovalar, migratsiya, FSM va filtrlar):

```powershell
pytest -v
```

Natijada barcha 30 ta test muvaffaqiyatli o'tadi (`PASSED`).

---

## 🎯 Bot Imkoniyatlari

### 👤 Oddiy Foydalanuvchi:
- **🔢 Kino kodi orqali:** Kino kodini (masalan: `1001`) yuborgan zahoti kino muqovasi (poster) va ma'lumotlari (`send_photo`) hamda original video (`copy_message`) foydalanuvchiga uzatiladi.
- **🖼 Muqovali va professional dizayn:** Qalin sarlavhalar (`<b>...</b>`), emoji va tartibli ma'lumotlar kartochkasi.
- **🎭 Janrlar:** 11 ta asosiy janr bo'yicha sahifalangan katalog (har sahifada 10 tadan kino, qulay tugmalar).
- **🔍 Kino qidirish:** Kino nomining bir qismi bo'yicha bazadan asinxron LIKE qidiruvi.
- **ℹ️ Yordam:** Botdan foydalanish bo'yicha to'liq qo'llanma.

### 👑 Admin Panel (`/admin`):
- **➕ Kino qo'shish:**
  1. Yopiq kanaldagi postni botga «Forward» qilish (`aiogram 3` ning `MessageOriginChannel` orqali xavfsiz o'qiladi).
  2. Kino nomini kiritish.
  3. Kino kodi: admin o'z kodi yoki `/auto` orqali avtomatik unikal kod generatsiya qilish.
  4. Janr tanlash (inline tugmalar).
  5. Yili (`/skip` imkoniyati bilan).
  6. Tavsif (`/skip` imkoniyati bilan).
  7. Muqova (Poster) rasmi (`/skip` imkoniyati bilan).
  8. Tasdiqlash kartochkasi orqali saqlash.
- **📚 Kinolar ro'yxati:** Sahifalangan ro'yxat, har bir kinoning to'liq ma'lumotlari va muqova holati.
- **✏️ Tahrirlash:** Nom, kod, janr, yil, tavsif va muqovani (yangi rasm yoki `/remove`) o'zgartirish.
- **🟢/🔴 Holat:** Kinoni bir bosishda faol yoki nofaol qilish (nofaol kinolar foydalanuvchilarga ko'rinmaydi).
- **🗑 O'chirish:** Tasodifiy bosishdan himoyalangan tasdiqlash tugmasi bilan o'chirish.
- **📊 Statistika:** Jami kinolar, faol/nofaol kinolar, janrlar bo'yicha taqsimot va ro'yxatdan o'tgan jami foydalanuvchilar soni.
