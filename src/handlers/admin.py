from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile, InputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.database.test_data import get_inactive_tests, delete_test_by_id
from src.database.results_data import delete_results_by_test_id
from src.database.sign_data import check_is_admin, set_admin_status, get_admin_user_if_exists, get_all_users_ids, get_all_users_data, get_new_users_count_since, get_all_users_creation_dates
from src.states.admin_state import AdminFSM
from src.keyboards.admin_btn import adminMenu, setting
from src.keyboards.mainbtn import mainMenu
import asyncio
import pandas as pd
import io
from io import BytesIO
import datetime
from datetime import timezone
import matplotlib.pyplot as plt
import calendar
import html

router = Router()


def generate_monthly_growth_chart(data: dict) -> io.BytesIO:
    months_names = data['months']
    user_counts = data['counts']

    # Grafika yaratish
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.bar(months_names, user_counts, color='#307AB7')

    # Har bir ustun ustiga qiymatini yozish (rasmingizdagi kabi)
    for bar in bars:
        yval = bar.get_height()
        # Qiymati 0 bo'lsa yozmaslik
        if yval > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, yval + (max(user_counts) * 0.01), int(yval), ha='center',
                    va='bottom', fontsize=10)

    ax.set_title("1yillik o'sish grafikasi", fontsize=14)
    ax.set_xlabel("Oylar", fontsize=12)
    ax.set_ylabel("Yangi qo'shilganlar soni", fontsize=12)
    max_count = max(user_counts) if user_counts else 10
    ax.set_yticks(range(0, int(max_count) + 5, 5))
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)

    return buffer


async def get_monthly_growth_data(session: AsyncSession, months: int = 12) -> dict:
    all_dates = await get_all_users_creation_dates(session)
    monthly_counts = {}
    now = datetime.datetime.now(timezone.utc)
    one_year_ago = now - datetime.timedelta(days=365)

    for date in all_dates:
        if date and date > one_year_ago:
            month_year_key = date.strftime("%Y-%m")
            monthly_counts[month_year_key] = monthly_counts.get(month_year_key, 0) + 1

    final_data_for_chart = {}

    current = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for i in range(months):
        month_year_key = current.strftime("%Y-%m")
        month_name = calendar.month_abbr[current.month]
        chart_label = month_name
        count = monthly_counts.get(month_year_key, 0)
        final_data_for_chart[chart_label] = count
        current = (current - datetime.timedelta(days=1)).replace(day=1)
    chart_months = list(final_data_for_chart.keys())
    chart_counts = list(final_data_for_chart.values())

    # Ma'lumotlarni teskari aylantirish (eski oy --> yangi oy)
    return {
        'months': chart_months[::-1],
        'counts': chart_counts[::-1]
    }


@router.message(Command("panel"))
async def admin_panel_start(message: Message, session_factory: async_sessionmaker[AsyncSession]):
    user_id = message.from_user.id
    async with session_factory() as session:
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
async def start_add_admin(message: Message, state: FSMContext, session_factory: async_sessionmaker[AsyncSession]):
    async with session_factory() as session:
        if not await get_admin_user_if_exists(session, message.from_user.id):
            await message.answer("❌ Uzr, siz Admin emassiz yoki ruxsatingiz yo'q.")
            return
    
    
    await message.answer("Qaysi foydalanuvchiga Admin huquqini bermoqchisiz? Iltimos, uning Telegram ID raqamini kiriting:")
    await state.set_state(AdminFSM.waiting_for_admin_id)


@router.message(AdminFSM.waiting_for_admin_id)
async def process_new_admin_id(
    message: Message, 
    state: FSMContext, 
    session_factory: async_sessionmaker[AsyncSession] 
):
    
    if not message.text.isdigit():
        await message.answer("Noto'g'ri format! Iltimos, faqat raqamlardan iborat Telegram ID kiriting.")
        return

    target_id = int(message.text)
    sender_id = message.from_user.id

    async with session_factory() as session:
        if not await get_admin_user_if_exists(session, sender_id):
            await message.answer("❌ Uzr, siz Admin huquqini bermoqchi emas edingiz.")
            await state.clear()
            return
            
        if target_id == sender_id:
            await message.answer("O'zingizni admin qila olmaysiz.")
            await state.clear()
            return

        success = await set_admin_status(session, target_id, is_admin=True)
    
        if success:
            await message.answer(
                f"✅ {target_id} ID egasiga Admin huquqi berildi"
            )
        else:
            await message.answer(
                f"❌ {target_id} ID topilmadi yoki u allaqachon Admin."
            )


    await state.clear()


@router.message(F.text == "📬 Reklama yuborish") 
async def start_broadcast(message: Message, state: FSMContext, session_factory: async_sessionmaker[AsyncSession]):
    

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
    
    async with session_factory() as session:
        if not await get_admin_user_if_exists(session, message.from_user.id):
            await message.answer("❌ Uzr, siz Admin emassiz")
            return

    await message.answer(
        "O'chirish uchun Adminning Telegram ID raqamini yuboring.\n\n",
        parse_mode='Markdown'
    )
    await state.set_state(AdminFSM.waiting_for_deadmin_id)


@router.message(AdminFSM.waiting_for_deadmin_id)
async def process_deadmin_id(message: Message, state: FSMContext, session_factory: async_sessionmaker[AsyncSession]):
    user_id = message.from_user.id
    
    if not message.text or not message.text.isdigit():
        await message.answer("❌ Noto'g'ri format. Iltimos, faqat raqamli Telegram ID kiriting.")
        return

    target_id = int(message.text)

    if target_id == user_id:
        await message.answer("❌ O'zingizni Adminlikdan o'chira olmaysiz.")
        await state.clear()
        return


    async with session_factory() as session:
        success = await set_admin_status(session, target_id, is_admin=False)

    if success:
        await message.answer(
            f"✅ {target_id} ID raqamli foydalanuvchidan Admin huquqi olib tashlandi. (Role: False)"
        )
    else:
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
        first_name=config.tg_bot.admin_contact_name.split()[0], 
        last_name=" ".join(config.tg_bot.admin_contact_name.split()[1:]) if len(config.tg_bot.admin_contact_name.split()) > 1 else None, 
    )
    
    await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)


@router.message(F.text == "🗑️ Ma'lumotlarni tozalash")
async def start_data_cleanup(message: Message, session_factory: async_sessionmaker[AsyncSession], state: FSMContext):
    
    user_id = message.from_user.id

    async with session_factory() as session:
        if not await get_admin_user_if_exists(session, user_id):
            await message.answer("❌ Uzr, siz Admin emassiz yoki ruxsatingiz yo'q.")
            return

    await message.answer("⚠️ DIQQAT! Bu amal yakunlangan testlarni va ularning natijalarini butunlay o'chirib yuboradi.\n\n"
                         "Davom etishni tasdiqlaysizmi? (Ha/Yo'q)", parse_mode='Markdown')

    await state.set_state(AdminFSM.waiting_for_cleanup_confirmation)


@router.message(AdminFSM.waiting_for_cleanup_confirmation, F.text.in_({'Ha', 'Yo\'q', 'Yoq', 'ha'}))
async def process_data_cleanup(message: Message, state: FSMContext, session_factory: async_sessionmaker[AsyncSession]):
    
    if message.text.lower() in ('yo\'q', 'yoq'):
        await message.answer("Tozalash amali bekor qilindi.")
        await state.clear()
        return

    await message.answer("⏳ Noaktiv testlar va ularning natijalarini tozalash boshlandi...")
    
    user_id = message.from_user.id
    cleanup_count = 0
    
    try:
        async with session_factory() as session:
            if not await get_admin_user_if_exists(session, user_id):
                await message.answer("❌ Xatolik: Admin huquqi topilmadi. Tozalash bekor qilindi.")
                await state.clear()
                return

            inactive_tests = await get_inactive_tests(session) 

            if not inactive_tests:
                await message.answer("✅ Bazada tozalanadigan noaktiv testlar topilmadi.")
                await state.clear()
                return

            for test in inactive_tests:
                test_code = test.id
                await delete_results_by_test_id(session, test_code)
                await delete_test_by_id(session, test_code)
                cleanup_count += 1
            await session.commit()    
        
        await message.answer(
            f"✅ Tozalash Yakunlandi!\n"
            f"Jami {cleanup_count} ta noaktiv test va ularning barcha natijalari bazadan butunlay o'chirildi.",
            parse_mode='Markdown'
        )

    except Exception as e:
        await message.answer(f"❌ Tozalash vaqtida kutilmagan xato yuz berdi: {e}")


    await state.clear()


@router.message(F.text == "📊 Statistika")
async def send_statistics_report(message: Message, session_factory: async_sessionmaker[AsyncSession]):
    user_id = message.from_user.id

    async with session_factory() as session:
        # 1. Admin tekshiruvi
        if not await get_admin_user_if_exists(session, user_id):
            await message.answer("❌ Uzr, siz Admin emassiz yoki ruxsatingiz yo'q.")
            return

        await message.answer("⏳ Statistik ma'lumotlar hisoblanmoqda...")

        try:
            # 2. Umumiy foydalanuvchilar sonini olish
            all_users_ids = await get_all_users_ids(session)
            total_users = len(all_users_ids)

            # 3. Davrlarni aniqlash (Hozirgi vaqtdan boshlab)
            now_utc = datetime.datetime.now(timezone.utc)

            # Har bir davr uchun timedelta hisoblash
            periods = {
                "1 hafta": datetime.timedelta(weeks=1),
                "1 oy": datetime.timedelta(days=30),
                "3 oy": datetime.timedelta(days=3 * 30),
                "6 oy": datetime.timedelta(days=6 * 30),
            }

            stats_results = {}

            # 4. Har bir davr uchun yangi foydalanuvchilar sonini olish
            for period_name, delta in periods.items():
                since_date = now_utc - delta
                # sign_data.py dan import qilingan funksiya
                count = await get_new_users_count_since(session, since_date)
                stats_results[period_name] = count

            monthly_data = await get_monthly_growth_data(session, months=12)
            chart_buffer = generate_monthly_growth_chart(monthly_data)

            chart_file = BufferedInputFile(chart_buffer.getvalue(), filename="foydalanuvchilar_osishi.png")
            await message.answer_photo(
                photo=chart_file,
                caption="📈 Oxirgi 12 oy davomidagi foydalanuvchilar o'sishi grafikasi."
            )

            response_text = (
                f"📈 Bot Statistikasi \n\n"
                f"👥 Jami obunachilar `{total_users}` ta\n\n"

                f"👤 Oxirgi 1 hafta ichida: `{stats_results['1 hafta']}` ta foydalanuvchi\n"
                f"👤 Oxirgi 1 oy ichida: `{stats_results['1 oy']}` ta foydalanuvchi\n"
                f"👤 Oxirgi 3 oy ichida: `{stats_results['3 oy']}` ta foydalanuvchi\n"
                f"👤 Oxirgi 6 oy ichida: `{stats_results['6 oy']}` ta foydalanuvchi"
            )

            await message.answer(
                response_text,
                parse_mode='Markdown',
            )

        except Exception as e:
            await message.answer(f"❌ Statistikani hisoblashda xato yuz berdi: {e}")


@router.message(F.text == "⚙️ Bot sozlamalari")
async def set_hand(msg:Message):
    await msg.answer("🛠️ Bot sozlamalariga xo`sh kelibsiz. Nimani sozlamoqchisiz", reply_markup=setting)

@router.message(F.text == "ℹ️ Botning ta`rifi")
async def start_change_description(message: Message, state: FSMContext,
                                   session_factory: async_sessionmaker[AsyncSession]):

    user_id = message.from_user.id

    async with session_factory() as session:
        if not await get_admin_user_if_exists(session, user_id):
            await message.answer("❌ Uzr, siz Admin emassiz yoki ruxsatingiz yo'q.")
            return

    await message.answer(
        "📝 **Botning yangi ta'rifini yuboring.**\n\n"
        "Siz yuborgan matn/rasm/media botning 'Bot Info' qismidagi ta'rifiga (Description) aylanadi. \n"
        "Agar siz rasm yuborsangiz, rasmning **caption** qismi bot ta'rifi bo'ladi. Matn yuborish kifoya.\n\n"
        "Bekor qilish uchun /panel buyrug'ini yuboring.",
        parse_mode='Markdown'
    )
    await state.set_state(AdminFSM.waiting_for_new_description)


@router.message(AdminFSM.waiting_for_new_description)
async def process_new_description(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    new_description_text = None

    if message.text:
        new_description_text = message.text
    elif message.caption:
        new_description_text = message.caption
    elif message.photo or message.video or message.document:
        await message.answer(
            "❌ Ta'rifni o'zgartirish uchun yuborilgan rasm yoki media'da **matn (caption)** bo'lishi shart, yoki faqat matn yuboring."
        )
        return

    if not new_description_text:
        await message.answer(
            "❌ Ta'rifni o'zgartirish uchun matn topilmadi. Iltimos, faqat matn yoki caption'li media yuboring.")
        return

    try:

        await bot.set_my_description(
            description=new_description_text,
            language_code=message.from_user.language_code  # Yoki 'uz'
        )

        await message.answer(
            f"✅ Botning ta'rifi (Description) muvaffaqiyatli o'zgartirildi:\n\n"
            f"```\n{new_description_text[:200]}...\n```",
            parse_mode='Markdown',
            reply_markup=adminMenu
        )

    except Exception as e:
        await message.answer(f"❌ Bot ta'rifini o'zgartirishda xato yuz berdi: {e}")

    finally:
        await state.clear()


# src/handlers/admin.py (mavjud kodning davomi)

# ... (Boshqa handlerlar) ...

@router.message(F.text == "📝 Tarjimayi hol")
async def start_change_about(message: Message, state: FSMContext, session_factory: async_sessionmaker[AsyncSession]):
    user_id = message.from_user.id

    async with session_factory() as session:
        if not await get_admin_user_if_exists(session, user_id):
            await message.answer("❌ Uzr, siz Admin emassiz yoki ruxsatingiz yo'q.")
            return

    await message.answer(
        "📜 **Botning yangi Tarjimayi holini (About) yuboring.**\n\n"
        "Siz yuborgan matn bot profilidagi qisqa ma'lumot (About) bo'ladi. Bu matn **120 belgidan oshmasligi** kerak. \n\n"
        "Bekor qilish uchun /panel buyrug'ini yuboring.",
        parse_mode='Markdown'
    )
    await state.set_state(AdminFSM.waiting_for_new_about)


@router.message(AdminFSM.waiting_for_new_about)
async def process_new_about(message: Message, state: FSMContext, bot: Bot):

    new_about_text = message.text or message.caption

    if not new_about_text:
        await message.answer(
            "❌ Tarjimayi holni o'zgartirish uchun matn topilmadi. Iltimos, faqat matn yoki caption'li media yuboring."
        )
        await state.clear()
        return

    try:
        await bot.set_my_short_description(
            short_description=new_about_text
        )

        await message.answer(
            f"✅ Botning Tarjimayi holi (About) muvaffaqiyatli o'zgartirildi:\n\n"
            f"```\n{new_about_text[:120]}...\n```",
            parse_mode='Markdown',
            reply_markup=adminMenu
        )

    except Exception as e:
        error_message = str(e)
        if "short description is too long" in error_message:
            error_text = "Tarjimayi hol juda uzun (120 belgidan kam bo'lishi kerak)."
        else:
            error_text = f"Kutilmagan xato: {error_message}"

        await message.answer(f"❌ Tarjimayi holni o'zgartirishda xato yuz berdi:\n\n{error_text}")

    finally:
        # 5. Holatni tozalash
        await state.clear()
