from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

# Kanal URL'i (Bu statik bo'lib qoladi, agar config dan kelmasa)
CHANNEL_URL = "https://t.me/Prezident_Maktabiga_Tayyarlov_1" 


CHECK_SUB_CALLBACK = "check_subscription"

def get_subscribe_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Kanalga obuna bo'lish", url=CHANNEL_URL)
    builder.adjust(1)    
    return builder.as_markup()