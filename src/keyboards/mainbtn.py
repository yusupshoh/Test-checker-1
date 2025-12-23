from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

mainMenu = ReplyKeyboardMarkup(
	keyboard=[
		[
			KeyboardButton(text="➕ Test yaratish"),
			KeyboardButton(text="✅ Javoblarni tekshirish")
		],
		[
			KeyboardButton(text="🏆 Testni yakunlash")
		],
		[
			KeyboardButton(text="📝 Profilni tahrirlash")
		],
		[
			KeyboardButton(text="☎️ Admin bilan bo`g`lanish")
		]
		], 
	resize_keyboard=True
	)

contact_button = KeyboardButton(text="📞 Raqamni yuborish", request_contact=True)


requestContactKB = ReplyKeyboardMarkup(
    keyboard=[[contact_button]],
    resize_keyboard=True,
    one_time_keyboard=True 
)

cancelKB = ReplyKeyboardMarkup(
	keyboard=[
		[
			KeyboardButton(text="❌ Bekor qilish")
		]
		],
	resize_keyboard=True
	)

