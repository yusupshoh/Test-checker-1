import logging
from typing import Union

from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery, ChatMember
from aiogram.enums import ChatMemberStatus

from config import Config
from src.keyboards.check import get_subscribe_keyboard 

logger = logging.getLogger(__name__)

class IsSubscribed(BaseFilter):
    
    is_required: bool = True  

    async def __call__(
        self, 
        event: Union[Message, CallbackQuery], 
        bot: Bot, 
        config: Config  
    ) -> bool:
        
        CHANNEL_ID = config.tg_bot.channel_id

        user_id = event.from_user.id
        
        try:
            member: ChatMember = await bot.get_chat_member(
                chat_id=CHANNEL_ID,
                user_id=user_id
            )
            
            is_subscribed = member.status in [
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.CREATOR
            ]
            
        except Exception as e:
            logger.error("Channel check error for user %s: %s", user_id, e)
            is_subscribed = True  

        if not is_subscribed and self.is_required:
            
            subscribe_keyboard = get_subscribe_keyboard()
            
            message_text = "<b>Botdan foydalanish uchun</b>, iltimos, quyidagi kanalga obuna bo'ling va bo'limga kirish tugmasini qayta bosing "
            
            if isinstance(event, Message):
                await event.answer(message_text, reply_markup=subscribe_keyboard)
                
            elif isinstance(event, CallbackQuery):
                await bot.edit_message_text(
                    chat_id=event.message.chat.id,
                    message_id=event.message.message_id,
                    text=message_text,
                    reply_markup=subscribe_keyboard
                )
                await event.answer()  
                
            return False  
            
        return True 