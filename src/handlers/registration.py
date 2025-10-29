import logging

from aiogram import Router, F, Bot
from aiogram.types import Message, BotCommand
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.states.re_state import RS, PS
from src.database.sign_data import add_new_user, get_user, update_user_info, get_all_admin_ids
from src.keyboards.mainbtn import mainMenu, requestContactKB, cancelKB
from src.utils.excel_generator import create_full_participant_report_pandas
import os 
import time

logger = logging.getLogger(__name__)
router = Router()

async def set_default_commands(bot: Bot):

    
    commands = [
        BotCommand(command="start", description="🤖 Botni ishga tushirish"),
        BotCommand(command="new_test", description="➕ Yangi test yaratishni boshlash"),
        BotCommand(command="check_test", description="✅ Testni tekshirish"),
        BotCommand(command="end_test", description="🏆 Testni yakunlash"),
        BotCommand(command="menu", description="📄 Asosiy menyu"),
        BotCommand(command="panel", description="Admin panelga kirish")
    ]
    
    await bot.set_my_commands(commands)

@router.message(F.text == "/start")
async def cmd_start(
    message: Message, 
    state: FSMContext, 
    session_factory: async_sessionmaker[AsyncSession],
    bot:Bot):
    
    user_id = message.from_user.id
    async with session_factory() as session:
        user = await get_user(session, user_id)
        
        if user:
            await message.answer("<b>Assalomu alaykum!</b> 🙂\n")
            await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)
            await state.clear()
            return
    
    await state.clear()
    await state.update_data(tg_id=user_id) 
    await message.answer("<b>Assalomu alaykum!</b> 🙂\n")
    await message.answer("Ro'yxatdan o'tish uchun ismingizni kiriting ✏️")
    await state.set_state(RS.waiting_for_first_name)
    await set_default_commands(bot)

@router.message(RS.waiting_for_first_name, F.text)
async def process_first_name(message: Message, state: FSMContext):
    first_name = message.text.strip()
    
    if len(first_name) < 2 or len(first_name) > 255:
        await message.answer("Iltimos, qayta kiriting ‼️")
        return

    await state.update_data(first_name=first_name)
    
    await message.answer("✏️ Familiyangizni kiriting:")
    await state.set_state(RS.waiting_for_last_name)

@router.message(RS.waiting_for_last_name, F.text)
async def process_last_name(message: Message, state: FSMContext):
    last_name = message.text.strip()
    
    if len(last_name) < 2 or len(last_name) > 255:
        await message.answer("Iltimos, qayta kiriting ‼️")
        return

    await state.update_data(last_name=last_name)
    await message.answer(
        "📞 Iltimos, pastdagi tugma orqali raqamingizni yuboring",
        reply_markup=requestContactKB 
    )
    await state.set_state(RS.waiting_for_phone_number)

@router.message(RS.waiting_for_phone_number, F.contact) 
async def process_phone_number_from_contact(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
    bot: Bot 
):
    phone_number = message.contact.phone_number 
    user_data = await state.get_data()
    tg_id = user_data.get('tg_id')
    first_name = user_data.get('first_name')
    last_name = user_data.get('last_name')
    
    async with session_factory() as session:
        try:
            new_user, is_new = await add_new_user(
                session=session,
                user_id=tg_id,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number 
            )
            if is_new:
                admin_ids = await get_all_admin_ids(session) 
                
                new_user_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
                
                notification_message = (
                    "🔔 Yangi foydalanuvchi!\n\n"
                    f"ID: <i><code>{tg_id}</code></i>\n"
                    f"Ismi: {first_name} {last_name or ''}\n"
                    f"Raqam: {phone_number}\n"
                )
                
                for admin_id in admin_ids:
                    try:
                        await bot.send_message(chat_id=admin_id, text=notification_message, parse_mode='HTML')
                        await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)
                        logger.info("New user registered with contact: %s", new_user)

                    except Exception as e:
                        logger.error(f"Admin {admin_id}ga xabar yuborishda xato: {e}")
            await state.clear()
            await message.answer(f"✅ Ro'yxatdan o'tish yakunlandi")
            await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)
            logger.info("New user registered with contact: %s", new_user)
        except Exception as e:
            
            logger.error("Ro'yxatdan o'tish va DBga saqlash jarayonida xato yuz berdi: %s", e)
            await message.answer(
                "‼️ Kechirasiz, ma'lumotlarni saqlashda texnik xato yuz berdi. "
                "Iltimos, qayta /start bosing yoki adminga murojaat qiling.",
                reply_markup=mainMenu
            )
            await state.clear() 

@router.message(F.text == "📝 Profilni tahrirlash")
async def start_profile_edit(message: Message, state: FSMContext, session_factory: async_sessionmaker[AsyncSession]):
    
    tg_id = message.from_user.id
    async with session_factory() as session:
        user = await get_user(session, tg_id)
        
    if not user:
        await message.answer("Siz ro'yxatdan o'tmagansiz. Iltimos, /start bosing.")
        return
    await state.update_data(
        tg_id=tg_id,
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number
    )
    await message.answer(
        f"<b>Ism tahriri:</b> Hozirgi qiymat: <code>{user.first_name}</code>\n"
        f"Yangi ismingizni kiriting:",
        parse_mode='HTML',
        reply_markup=cancelKB 
    )
    await state.set_state(PS.editing_first_name)


@router.message(PS.editing_first_name, F.text, ~F.text.in_({"❌ Bekor qilish"}))
async def process_edit_first_name(message: Message, state: FSMContext):
    new_first_name = message.text.strip()
    
    if len(new_first_name) < 2 or len(new_first_name) > 255:
        await message.answer("Qayta kiriting.")
        return

    await state.update_data(first_name=new_first_name)
    user_data = await state.get_data()
    
    await message.answer(
        f"<b>Familiya tahriri:</b> Hozirgi qiymat: <code>{user_data['last_name']}</code>\n"
        f"Yangi familiyangizni kiriting:",
        parse_mode='HTML'
    )
    await state.set_state(PS.editing_last_name)

@router.message(PS.editing_last_name, F.text, ~F.text.in_({"❌ Bekor qilish"}))
async def process_edit_last_name(message: Message, state: FSMContext):
    new_last_name = message.text.strip()
    
    if len(new_last_name) < 2 or len(new_last_name) > 255:
        await message.answer("Familiya noto'g'ri. Qayta kiriting.")
        return
        
    await state.update_data(last_name=new_last_name)
    user_data = await state.get_data()
    
    await message.answer(
        f"<b>Telefon raqami tahriri:</b> Hozirgi raqam: <code>{user_data['phone_number']}</code>\n"
        f"Yangi raqamni pastdagi tugma orqali yuboring:",
        parse_mode='HTML',
        reply_markup=requestContactKB
    )
    await state.set_state(PS.editing_phone_number)

@router.message(PS.editing_phone_number, F.contact)
async def process_edit_phone_number(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession]
):
    new_phone_number = message.contact.phone_number
    user_data = await state.get_data()
    tg_id = user_data['tg_id']
    async with session_factory() as session:
        updated = await update_user_info( 
            session=session,
            tg_id=tg_id,
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            phone_number=new_phone_number
        )

    await state.clear()
    
    if updated:
        await message.answer("✅ Profil ma'lumotlari muvaffaqiyatli yangilandi!", reply_markup=mainMenu)
    else:
        await message.answer("‼️ Ma'lumotlarni yangilashda xatolik yuz berdi.", reply_markup=mainMenu)

@router.message(PS.editing_phone_number)
async def handle_wrong_phone_input(message: Message):
    await message.answer(
        "Iltimos, telefon raqamini faqat pastdagi tugma orqali yuboring yoki '❌ Bekor qilish'ni bosing.",
        reply_markup=requestContactKB
    )


@router.message(F.text == "❌ Bekor qilish")
async def cancel_editing(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("Tahrirlash bekor qilindi.", reply_markup=mainMenu)