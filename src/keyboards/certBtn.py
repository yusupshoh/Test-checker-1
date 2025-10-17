from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_cert_keyboard(current_index: int, total_images: int) -> InlineKeyboardMarkup:
    """Rasm o'tkazish uchun inline tugmalar yaratadi."""
    
    # ... (Qolgan kod avvalgidek, faqat ushbu funksiyani ko'chiramiz)
    buttons = [
        InlineKeyboardButton(
            text="◀️ Orqaga", 
            callback_data=f"cert_nav:prev:{current_index}"
        ) if current_index > 0 else InlineKeyboardButton(text=" ", callback_data="ignore"),
        
        InlineKeyboardButton(
            text="✅ Tanlash", 
            callback_data=f"cert_nav:select:{current_index}"
        ),
        
        InlineKeyboardButton(
            text="▶️ Keyingisi", 
            callback_data=f"cert_nav:next:{current_index}"
        ) if current_index < total_images - 1 else InlineKeyboardButton(text=" ", callback_data="ignore"),
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=[[
        buttons[0], buttons[1], buttons[2]
    ]])