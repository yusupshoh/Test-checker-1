from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

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
			KeyboardButton(text="🗑️ Ma'lumotlarni tozalash")
		]], 
	resize_keyboard=True
	)

