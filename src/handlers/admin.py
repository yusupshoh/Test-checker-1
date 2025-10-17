from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, BufferedInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.database.test_data import get_inactive_tests, delete_test_by_id
from src.database.results_data import delete_results_by_test_id
from src.database.sign_data import check_is_admin, set_admin_status, get_admin_user_if_exists, get_all_users_ids, get_all_users_data, get_new_users_count_since 
from src.states.admin_state import AdminFSM
from src.keyboards.admin_btn import adminMenu
from src.keyboards.mainbtn import mainMenu
import asyncio
from aiogram.enums.content_type import ContentType
from aiogram.filters import StateFilter
import pandas as pd
from io import BytesIO
import datetime
from datetime import timezone
import openpyxl


router = Router()

# Router fayli

async def start_broadcasting_task(
    admin_id: int,
    messages: list[Message],
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession]
):
    # 1. Barcha ID'larni bazadan olish
    async with session_factory() as session:
        user_ids = await get_all_users_ids(session)

    successful_sends = 0
    failed_sends = 0
    
    # Adminni xabardor qilish
    await bot.send_message(admin_id, f"🔄 Reklama tarqatish {len(user_ids)} ta foydalanuvchiga boshlandi...")

    # 2. Har bir foydalanuvchiga xabarlar ketma-ketligini yuborish
    for user_id in user_ids:
        try:
            for msg_part in messages:
                await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=admin_id, # Xabarni adminning chatidan nusxalash
                    message_id=msg_part.message_id
                )
                await asyncio.sleep(0.05) 
            successful_sends += 1
            await asyncio.sleep(0.1)            
        except Exception as e:
            failed_sends += 1

    await bot.send_message(
        admin_id,
        f"✅ Reklama yuborish yakunlandi:\n"
        f"  - Yuborilgan xabarlar soni: {len(messages)} ta\n"
        f"  - Muvaffaqiyatli yetkazilgan: {successful_sends} ta\n",
        parse_mode='Markdown'
    )

@router.message(Command("panel"))
async def admin_panel_start(message: Message, session_factory: async_sessionmaker[AsyncSession]):
    
    user_id = message.from_user.id
    
    async with session_factory() as session:
        # DB dan saqlangan Admin User ob'ektini olish
        admin_user = await get_admin_user_if_exists(session, user_id)
        
        if admin_user:
            db_first_name = admin_user.first_name or "Admin" 
            
            await message.answer(
                f"Assalomu alaykum, <b><i>{db_first_name}</i></b>! 👋\n"
                f"Admin panelga xo`sh kelibsiz 👇", 
                reply_markup=adminMenu 
            )
        else:
            await message.answer(
                "🚫 Uzr, Admin panelga kirish uchun sizda ruxsat yo'q."
            )

@router.message(F.text == "👤 Admin qo`shish ➕")
# ⚠️ O'zgarish: session_factory ni qabul qilamiz
async def start_add_admin(message: Message, state: FSMContext, session_factory: async_sessionmaker[AsyncSession]):
    
    # Ruxsatni tekshirish uchun session_factory dan foydalanamiz
    async with session_factory() as session:
        if not await get_admin_user_if_exists(session, message.from_user.id):
            await message.answer("❌ Uzr, siz Admin emassiz yoki ruxsatingiz yo'q.")
            return
    
    # Agar admin bo'lsa, davom etamiz
    await message.answer("Qaysi foydalanuvchiga Admin huquqini bermoqchisiz? Iltimos, uning Telegram ID raqamini kiriting:")
    
    # FSM holatini o'rnatish
    await state.set_state(AdminFSM.waiting_for_admin_id)


@router.message(AdminFSM.waiting_for_admin_id)
async def process_new_admin_id(
    message: Message, 
    state: FSMContext, 
    session_factory: async_sessionmaker[AsyncSession] # ⚠️ O'zgarish: session_factory ni qabul qilamiz
):
    # Kiritilgan qiymatni tekshirish (oldingi kod kabi)
    if not message.text.isdigit():
        await message.answer("Noto'g'ri format! Iltimos, faqat raqamlardan iborat Telegram ID kiriting.")
        return

    target_id = int(message.text)
    sender_id = message.from_user.id

    # 1. Ruxsatni tekshirish (Bu yerda ham admin ekanligini qayta tekshirish muhim)
    async with session_factory() as session:
        if not await get_admin_user_if_exists(session, sender_id):
            await message.answer("❌ Uzr, siz Admin huquqini bermoqchi emas edingiz.")
            await state.clear()
            return
            
        # O'zini o'zi admin qilishni tekshirish (ixtiyoriy)
        if target_id == sender_id:
            await message.answer("O'zingizni admin qila olmaysiz.")
            await state.clear()
            return

        # 2. DB orqali admin statusini True qilib o'rnatish
        success = await set_admin_status(session, target_id, is_admin=True)
    
        # 3. Natijani yuborish
        if success:
            await message.answer(
                f"✅ {target_id} ID egasiga Admin huquqi berildi"
            )
        else:
            await message.answer(
                f"❌ {target_id} ID topilmadi yoki u allaqachon Admin."
            )

    # 4. FSM holatini tozalash
    await state.clear()


@router.message(F.text == "📬 Reklama yuborish") 
async def start_broadcast(message: Message, state: FSMContext, session_factory: async_sessionmaker[AsyncSession]):
    
    # Ruxsatni tekshirish
    async with session_factory() as session:
        if not await get_admin_user_if_exists(session, message.from_user.id):
            await message.answer("❌ Uzr, siz Admin emassiz yoki ruxsatingiz yo'q.")
            return

    await message.answer(
        "Reklama uchun xabar (rasm, matn) yuboring.",
        parse_mode='Markdown'
    )
    await state.set_state(AdminFSM.waiting_for_broadcast_message)

@router.message(AdminFSM.waiting_for_broadcast_message)
async def process_broadcast_message(
    message: Message, 
    state: FSMContext, 
    bot: Bot, 
    session_factory: async_sessionmaker[AsyncSession] 
):
    user_id = message.from_user.id
    async with session_factory() as session:
        if not await get_admin_user_if_exists(session, user_id):
            await message.answer("❌ Xabar tarqatish bekor qilindi, chunki siz Admin emassiz.")
            await state.clear()
            return
            
        user_ids = await get_all_users_ids(session) 

    await message.answer(f"🔄 Reklama {len(user_ids)} ta foydalanuvchiga yuborish boshlandi...")

    successful_sends = 0
    failed_sends = 0
    
    for target_user_id in user_ids:
        try:
            await message.copy_to(chat_id=target_user_id)
            successful_sends += 1
            await asyncio.sleep(0.05) 

        except Exception as e:
            failed_sends += 1

    await message.answer(
        f"✅ Reklama yuborish yakunlandi:\n"
        f"  - Muvaffaqiyatli yetkazildi: {successful_sends} ta\n",
        parse_mode='Markdown'
    )
    
    await state.clear()

@router.message(F.text == "❌ Adminni o'chirish")
async def start_deadmin(message: Message, state: FSMContext, session_factory: async_sessionmaker[AsyncSession]):
    
    # 1. Admin ruxsatini tekshirish
    async with session_factory() as session:
        if not await get_admin_user_if_exists(session, message.from_user.id):
            await message.answer("❌ Uzr, siz Admin emassiz")
            return

    # 2. FSM holatiga o'tkazish
    await message.answer(
        "O'chirish uchun Adminning Telegram ID raqamini yuboring.\n\n",
        parse_mode='Markdown'
    )
    await state.set_state(AdminFSM.waiting_for_deadmin_id)


# Admin ID'sini qabul qilish va o'chirish
@router.message(AdminFSM.waiting_for_deadmin_id)
async def process_deadmin_id(message: Message, state: FSMContext, session_factory: async_sessionmaker[AsyncSession]):
    
    # Admin tekshiruvi (o'zini o'zi o'chirishni oldini olish mumkin)
    user_id = message.from_user.id
    
    # Matn raqam ekanligini tekshirish
    if not message.text or not message.text.isdigit():
        await message.answer("❌ Noto'g'ri format. Iltimos, faqat raqamli Telegram ID kiriting.")
        return

    target_id = int(message.text)

    # 1. O'zini o'zi o'chirishni taqiqlash (ixtiyoriy)
    if target_id == user_id:
        await message.answer("❌ O'zingizni Adminlikdan o'chira olmaysiz.")
        await state.clear()
        return


    async with session_factory() as session:
        # set_admin_status funksiyasini chaqiramiz. is_admin=False beramiz.
        success = await set_admin_status(session, target_id, is_admin=False)

    # 4. Natijani yuborish
    if success:
        await message.answer(
            f"✅ {target_id} ID raqamli foydalanuvchidan Admin huquqi olib tashlandi. (Role: False)"
        )
    else:
        # success False qaytarsa, bu ID bazada mavjud emas yoki u allaqachon Admin emas (ya'ni Role: False)
        await message.answer(
            f"❌ {target_id} ID topilmadi yoki u allaqachon Oddiy Foydalanuvchi (Role: False)."
        )

    await state.clear()

@router.message(F.text == "👥 Foydalanuvchilar")
async def send_user_list_excel(message: Message, session_factory: async_sessionmaker[AsyncSession]):
    
    user_id = message.from_user.id
    
    async with session_factory() as session:
        if not await get_admin_user_if_exists(session, user_id):
            await message.answer("❌ Uzr, siz Admin emassiz yoki ruxsatingiz yo'q.")
            return

    await message.answer("⏳ Foydalanuvchilar ro'yxatini shakllantirmoqdaman...")
    
    try:
        # 2. Bazadan ma'lumotlarni olish
        async with session_factory() as session:
            users_data = await get_all_users_data(session)

        if not users_data:
            await message.answer("Bazada foydalanuvchilar topilmadi.")
            return

        df = pd.DataFrame(users_data)
        
        excel_file = BytesIO()

        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Foydalanuvchilar', index=False)
            
        excel_file.seek(0) 
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"foydalanuvchilar_royxati_{timestamp}.xlsx"
        
        await message.answer_document(
            document=BufferedInputFile(excel_file.getvalue(), filename=file_name),
            caption=f"✅ Jami {len(users_data)} ta foydalanuvchi ma'lumoti bilan Excel fayl."
        )

    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {e}")
    
@router.message(F.text == "☎️ Admin bilan bo`g`lanish") 
async def send_telegram_contact_object(message: Message, bot: Bot, config):
    await bot.send_contact(
        chat_id=message.chat.id,
        phone_number=config.tg_bot.admin_phone,
        first_name=config.tg_bot.admin_contact_name.split()[0], # Ism
        last_name=" ".join(config.tg_bot.admin_contact_name.split()[1:]) if len(config.tg_bot.admin_contact_name.split()) > 1 else None, 
    )
    
    await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)


@router.message(F.text == "🗑️ Ma'lumotlarni tozalash")
async def start_data_cleanup(message: Message, session_factory: async_sessionmaker[AsyncSession], state: FSMContext):
    
    user_id = message.from_user.id
    
    # 1. Admin ruxsatini tekshirish
    async with session_factory() as session:
        if not await get_admin_user_if_exists(session, user_id):
            await message.answer("❌ Uzr, siz Admin emassiz yoki ruxsatingiz yo'q.")
            return

    await message.answer("⚠️ **DIQQAT!** Bu amal yakunlangan testlarni va ularning natijalarini butunlay o'chirib yuboradi.\n\n"
                         "Davom etishni tasdiqlaysizmi? (Ha/Yo'q)", parse_mode='Markdown')

    # FSM holatini tasdiqlash uchun o'rnatish
    await state.set_state(AdminFSM.waiting_for_cleanup_confirmation)


@router.message(AdminFSM.waiting_for_cleanup_confirmation, F.text.in_({'Ha', 'Yo\'q', 'Yoq', 'ha'}))
async def process_data_cleanup(message: Message, state: FSMContext, session_factory: async_sessionmaker[AsyncSession]):
    
    # ... (Bekor qilish qismi o'zgarishsiz) ...
    if message.text.lower() in ('yo\'q', 'yoq'):
        await message.answer("Tozalash amali bekor qilindi.")
        await state.clear()
        return

    # 2. Tozalashni Boshlash (Tasdiqlangan)
    await message.answer("⏳ Noaktiv testlar va ularning natijalarini tozalash boshlandi...")
    
    user_id = message.from_user.id
    cleanup_count = 0
    
    try:
        async with session_factory() as session:
            # 2.1. Admin ruxsatini qayta tekshirish (o'zgarishsiz)
            if not await get_admin_user_if_exists(session, user_id):
                await message.answer("❌ Xatolik: Admin huquqi topilmadi. Tozalash bekor qilindi.")
                await state.clear()
                return

            # 2.2. Noaktiv testlar ro'yxatini olish (o'zgarishsiz)
            inactive_tests = await get_inactive_tests(session) 

            if not inactive_tests:
                await message.answer("✅ Bazada tozalanadigan noaktiv testlar topilmadi.")
                await state.clear()
                return

            # 2.3. Har bir testni tozalash (o'zgarishsiz)
            for test in inactive_tests:
                test_code = test.id
                await delete_results_by_test_id(session, test_code)
                await delete_test_by_id(session, test_code)
                cleanup_count += 1
            await session.commit()    
        # 3. Yakuniy hisobot (o'zgarishsiz)
        await message.answer(
            f"✅ Tozalash Yakunlandi!\n"
            f"Jami {cleanup_count} ta noaktiv test va ularning barcha natijalari bazadan butunlay o'chirildi.",
            parse_mode='Markdown'
        )

    except Exception as e:
        await message.answer(f"❌ Tozalash vaqtida kutilmagan xato yuz berdi: {e}")


    await state.clear()

@router.message(F.text == "📊 Statistika")
async def send_statistics(message: Message, session_factory: async_sessionmaker[AsyncSession]):
    
    user_id = message.from_user.id
    
    async with session_factory() as session:
        # 1. Admin ruxsatini tekshirish
        if not await get_admin_user_if_exists(session, user_id):
            await message.answer("❌ Uzr, siz Admin emassiz yoki ruxsatingiz yo'q.")
            return


        now = datetime.datetime.now(timezone.utc) 
        one_week_ago = now - datetime.timedelta(weeks=1)
        one_month_ago = now - datetime.timedelta(days=30)
        three_months_ago = now - datetime.timedelta(days=90)
        six_months_ago = now - datetime.timedelta(days=180)
        custom_min_date = datetime.datetime(2025, 10, 10, 0, 0, 0, tzinfo=timezone.utc)
        
        try:
            total_users_count = await get_new_users_count_since(session, custom_min_date) 
            last_week_count = await get_new_users_count_since(session, one_week_ago)
            last_month_count = await get_new_users_count_since(session, one_month_ago)
            last_three_months_count = await get_new_users_count_since(session, three_months_ago)
            last_six_months_count = await get_new_users_count_since(session, six_months_ago)

        except Exception as e:
            await message.answer(f"❌ Statistikani olishda xatolik yuz berdi: {e}")
            return
            

    report = (
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 <b>Jami ro'yxatdan o'tganlar:</b> {total_users_count} ta\n\n"
        f"📆 Oxirgi 1 hafta ichida: <i>{last_week_count} ta </i> yangi foydalanuvchi\n"
        f"🗓 Oxirgi 1 oy ichida: <i>{last_month_count} ta </i> yangi foydalanuvchi\n"
        f"📅 Oxirgi 3 oy ichida: <i>{last_three_months_count}</i> ta yangi foydalanuvchi\n"
        f"⏳ Oxirgi 6 oy ichida: <i>{last_six_months_count}</i> ta yangi foydalanuvchi"
    )

    await message.answer(report)