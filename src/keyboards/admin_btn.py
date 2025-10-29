from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

adminMenu = ReplyKeyboardMarkup(
	keyboard=[
		[
			KeyboardButton(text="❌ Adminni o'chirish"),
			KeyboardButton(text="👤 Admin qo`shish ➕")
		],
		[
			KeyboardButton(text="👥 Foydalanuvchilar"),
			KeyboardButton(text="📬 Reklama yuborish")
		],
		[
			KeyboardButton(text="📊 Statistika"),
			KeyboardButton(text="🗑️ Ma'lumotlarni tozalash"),
		],
        [
            KeyboardButton(text="⚙️ Bot sozlamalari")
        ]
	], 
	resize_keyboard=True
)

setting = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="ℹ️ Botning ta`rifi"),
        ],
        [
            KeyboardButton(text="📝 Tarjimayi hol"),
        ],
    ], resize_keyboard=True
)

