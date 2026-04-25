# Telegram Kurs Ro'yxatdan O'tish Boti

Ushbu bot o'quvchilarni kursga ro'yxatdan o'tkazish uchun mo'ljallangan. 
Bot foydalanuvchidan F.I.O, telefon raqami va passport rasmolarni so'raydi.

## Xususiyatlari
- F.I.O ni tekshirish (kamida 2 ta so'z)
- Telefon raqamini tugma orqali yoki qo'lda kiritish
- Passport rasmini yuklash va saqlash
- Adminga yangi ro'yxatdan o'tganlar haqida bildirishnoma yuborish
- Admin uchun maxsus buyruqlar (/list, /count, /export)

## O'rnatish

1. Kutubxonalarni o'rnating:
   ```bash
   pip install -r requirements.txt
   ```

2. `bot.py` faylidagi `BOT_TOKEN` va `ADMIN_CHAT_ID` ni o'zgartiring.

3. Botni ishga tushiring:
   ```bash
   python bot.py
   ```

## Fayllar tuzilishi
- `bot.py`: Asosiy kod
- `requirements.txt`: Kerakli kutubxonalar
- `students.json`: Ma'lumotlar bazasi (avtomatik yaratiladi)
- `passportlar/`: Passport rasmlari saqlanadigan papka (avtomatik yaratiladi)
