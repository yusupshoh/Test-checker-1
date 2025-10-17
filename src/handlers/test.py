import logging
from aiogram import Router, F, Bot, types 
from aiogram.types import (
    Message, 
    ReplyKeyboardRemove, 
    FSInputFile, 
    InputMediaPhoto, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery,
    InputMediaPhoto 
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import re
import uuid
import os
import time
import uuid
from src.filters.is_subscribed import IsSubscribed
from src.states.test_creation import TestStates, CheckStates
from src.keyboards.mainbtn import mainMenu
from src.database.test_data import add_new_test, get_test_by_id, deactivate_test
from src.database.results_data import add_new_result, get_test_results_with_users, get_unique_user_ids_for_test
from src.database.sign_data import add_new_user, get_user, check_is_admin, set_admin_status, get_admin_user_if_exists, get_all_users_data
import pandas as pd
from typing import List, Tuple, Dict
import os
from src.utils.excel_generator import create_full_participant_report_pandas


try:
    from src.sertifikat_generator import sertifikat_yaratish
    CERT_GENERATOR_AVAILABLE = True
except ImportError as e:
    logger.error(f"Sertifikat generatori importida xato yuz berdi. Fayl joylashuvi yoki 'python-pptx' ni tekshiring. Detal: {e}")
    CERT_GENERATOR_AVAILABLE = False


logger = logging.getLogger(__name__)
CERT_GENERATOR_AVAILABLE = 'sertifikat_yaratish' in globals() or 'sertifikat_yaratish' in locals()


router = Router()

def create_answer_dict_from_string(answer_key_raw: str) -> dict:
    pattern = r'(\d+[a-z])' 
    matches = re.findall(pattern, answer_key_raw.lower())
    result_dict = {}
    for pair in matches:
        result_dict[pair[:-1]] = pair[-1]
    return result_dict

def generate_test_id() -> str:
    unique_part = str(uuid.uuid4()).replace('-', '').upper()[:8]
    return unique_part 

@router.message(F.text == "/new_test")
@router.message(F.text == "➕ Test yaratish", IsSubscribed())
async def start_create_test_handler(message: Message, state: FSMContext):
    new_test_id = generate_test_id() 
    await state.update_data(test_id=new_test_id)  
    await state.clear()
    await message.answer("📃 Siz Test Yaratish bo'limidasiz.\n\n")
    await message.answer("✏️ test nomini kiriting: ",
         reply_markup=ReplyKeyboardRemove())
    await state.set_state(TestStates.waiting_for_name)
    logger.info(f"User {message.from_user.id} started test creation with ID: {new_test_id}")


@router.message(TestStates.waiting_for_name, F.text, IsSubscribed())
async def process_test_name(message: Message, state: FSMContext):
    test_title = message.text.strip()
    if len(test_title) < 3 or len(test_title) > 255:
        await message.answer("Uzunroq matn kiriting ‼️")
        return    
    await state.update_data(test_title=test_title)
    await message.answer("Endi savol-javob kalitini quyidagi usulda kiriting 📝:\n\n"
        "NAMUNA: <i>1a2b3c4d...</i> (Bo'sh joylarsiz!)"
    )

    await state.set_state(TestStates.waiting_for_answer_key)

@router.message(TestStates.waiting_for_answer_key, F.text, IsSubscribed())
async def save_new_test(
    message: Message, 
    state: FSMContext, 
    session_factory: async_sessionmaker[AsyncSession]
):
    answer_key = message.text.strip().lower()
    if not answer_key.isalnum() or len(answer_key) < 4:
        await message.answer("Qayta urining. Kalit faqat harf va raqamlardan iborat va kamida 4 belgi bo'lishi kerak. ‼️")
        return
        
    user_data = await state.get_data()
    test_title = user_data.get('test_title')
    creator_id = message.from_user.id
    new_test_id = generate_test_id()

    async with session_factory() as session:
        try:
            new_test = await add_new_test(
                session=session,
                test_id=new_test_id, 
                title=test_title,
                answer=answer_key, 
                creator_id=creator_id
            )

            await message.answer(
                f"Fan: <b>{test_title}</b>\n"
                f"Id: <i><code>{new_test.id}</code></i>\n\n"
                f"Foydalanuvchilar bu ID orqali testni ishlay olishadi.",
                parse_mode='HTML'
            )
            await state.clear()
            await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu) 
            
        except Exception as e:
            logger.error("Error creating test or saving to DB: %s", e)
            await message.answer(
                "Kechirasiz, testni saqlashda texnik xato yuz berdi. Iltimos, adminga murojaat qiling."
            )
            await state.clear()
            await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)


@router.message(F.text == "/check_test")
@router.message(F.text == "✅ Javoblarni tekshirish", IsSubscribed())
async def start_check_answers_handler(message: Message, state: FSMContext):
    await state.clear()
    
    await message.answer(
        "Siz Javoblarni tekshirish bo'limidasiz ☑️✅\n\n"
        "Tekshirish uchun test ID raqamini kiriting (masalan, 5A2C8F3D):", 
        reply_markup=ReplyKeyboardRemove()
    )
    
    await state.set_state(CheckStates.waiting_for_code)
    logger.info(f"User {message.from_user.id} started answer checking.")


@router.message(CheckStates.waiting_for_code, F.text)
async def process_test_code_for_check(
    message: Message, 
    state: FSMContext, 
    session_factory: async_sessionmaker[AsyncSession]
):
    
    test_code = message.text.strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{8}', test_code):
        await message.answer("Kod formati noto'g'ri. Qayta kiriting ‼️")
        return      
    async with session_factory() as session:
        test = await get_test_by_id(session, test_code)      
    if not test or not test.status: 
        await message.answer("Kechirasiz, bu kod bilan test topilmadi yoki u yakunlangan ‼️‼️")
        await state.clear()
        await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)
        return     
    await state.update_data(current_test_id=test.id, correct_answers=test.answer)  
    await message.answer(
        f"Fan: <b>{test.title}</b>.\n\n"
        f"Endi savol-javoblarni quyidagi usulda yozing\n"
        f"NAMUNA: <code>1a2b3c4d5b....</code> (Bo'sh joylarsiz!)",
        parse_mode='HTML' 
    )
    
    await state.set_state(CheckStates.waiting_for_user_answers)


@router.message(CheckStates.waiting_for_user_answers, F.text, IsSubscribed())
async def process_user_answers(message: Message, state: FSMContext, session_factory: async_sessionmaker[AsyncSession], bot: Bot):
    
    user_answers_raw = message.text.strip().lower()
    data = await state.get_data()
    test_id = data.get('current_test_id')
    correct_answers_key_raw = data.get('correct_answers')
    pattern = r'(\d+[a-z])' 
    correct_matches = re.findall(pattern, correct_answers_key_raw)
    user_matches = re.findall(pattern, user_answers_raw)
    
    
    if not user_matches:
        await message.answer(
            "Kiritilgan javoblar formati noto'g'ri. "
        )
        return
        
    def create_answer_dict(matches):
        result_dict = {}
        for pair in matches:
            question_num = pair[:-1] 
            answer_char = pair[-1]   
            result_dict[question_num] = answer_char
        return result_dict

    correct_dict = create_answer_dict(correct_matches)
    user_dict = create_answer_dict(user_matches)
    total_questions = len(correct_dict)
    correct_count = 0

    for question_num, correct_answer in correct_dict.items():
        if question_num in user_dict and user_dict[question_num] == correct_answer:
            correct_count += 1
            
    incorrect_count = total_questions - correct_count   
    creator_id = None
    registered_user_name = "Ro'yxatdan o'tmagan foydalanuvchi ‼️" 
    test_title = "Noma'lum test"

    async with session_factory() as session:
        test_info = await get_test_by_id(session, test_id)
        if test_info:
            creator_id = test_info.creator_id
            test_title = test_info.title
        
        user_info = await get_user(session, message.from_user.id)
        if user_info and user_info.first_name:
            registered_user_name = f"{user_info.first_name} {user_info.last_name or ''}".strip()
        else:
            registered_user_name = message.from_user.full_name
            
        try:
            await add_new_result(
                session=session, 
                user_id=message.from_user.id,
                test_id=test_id,
                correct_count=correct_count,
                total_questions=total_questions
            )
        except Exception as e:
            logger.error("Error saving result to DB: %s", e)
            
    if creator_id:
        creator_notification_message = (
            f"<b> YANGI NATIJA </b> \n\n"
            f"Test kodi: <i>{test_id}</i> \n\n"
            f"Test nomi: <i>{test_title}</i> \n\n"
            f"<i>{registered_user_name} - {correct_count}/{total_questions}</i>"
        )
        try:
            await bot.send_message(chat_id=creator_id, text=creator_notification_message, parse_mode='HTML')
        except Exception as e:
            logger.error("Error sending notification to creator %s: %s", creator_id, e)

    
    if not 'test_title' in locals():
        test_title = test_info.title if test_info else "Noma'lum test"

    user_result_message = (
        f"Javoblar qabul qilindi! ✅\n\n"
        f"Natijalar test muallifiga yuborildi"
    )

    await message.answer(user_result_message)
    await state.clear()
    await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)


@router.message(F.text == "/end_test")
@router.message(F.text == "🏆 Testni yakunlash", IsSubscribed())
async def start_finish_test_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Iltimos, yakunlamoqchi bo'lgan testingizni ID kodini kiriting ✏️:",
        parse_mode='HTML',
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(CheckStates.waiting_for_finish_code)


@router.message(CheckStates.waiting_for_finish_code, F.text, IsSubscribed())
async def process_finish_test_code(
    message: Message, 
    state: FSMContext, 
    session_factory: async_sessionmaker[AsyncSession], 
    bot: Bot 
):
    test_code = message.text.strip().upper()

    # 1. ID formatini tekshirish
    if not re.fullmatch(r'[A-Z0-9]{8}', test_code):
        await message.answer("Kod formati noto'g'ri. O'qituvchingiz bergan id ni. Qayta kiriting. ‼️‼️")
        return

    # 2. DB bilan barcha ishlarni bitta blokda bajarish
    is_deactivated = False
    results = []
    user_ids_who_passed = []
    test_data = None
    creator_name = "Noma'lum"

    async with session_factory() as session:
        test_data = await get_test_by_id(session, test_code)
        
        # Test mavjudligi va muallifni tekshirish
        if not test_data or test_data.creator_id != message.from_user.id:
            await message.answer("Kechirasiz, bu kod bilan test topilmadi yoki siz uning muallifi emassiz.")
            await state.clear()
            await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)
            return

        # Status tekshiruvi: Agar test yakunlangan bo'lsa
        if not test_data.status: 
            await message.answer("❗️ Test allaqachon yakunlangan.")
            await state.clear()
            await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)
            return
            
        # 2a. Muallif ma'lumotini olish
        creator_user = await get_user(session, test_data.creator_id)
        creator_name = f"{creator_user.first_name} {creator_user.last_name or ''}".strip() if creator_user and creator_user.first_name else "Noma'lum"
        
        # 2b. Natijalarni olish
        try:
            results = await get_test_results_with_users(session, test_code)
            user_ids_who_passed = await get_unique_user_ids_for_test(session, test_code)
        except Exception as e:
            await message.answer("Natijalarni olishda xatolik yuz berdi ‼️")
            logger.error("DB Error getting results in process_finish_test_code: %s", e)
            await state.clear()
            await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)
            return

        # 2c. Testni yakunlash (status=False qilish)
        is_deactivated = await deactivate_test(session, test_code)


    # 3. Natijalarni hisoblash va formatlash (DB tashqarisida)

    # O'rinlarni hisoblash mantiqi
    result_list = []
    current_rank = 0
    last_correct_count = -1
    rank_count = 0

    for user_id_res, first_name, last_name, phone_number, correct, total in results:
        rank_count += 1
        if correct != last_correct_count:
            current_rank = rank_count
            last_correct_count = correct

        full_name = f"{first_name} {last_name or ''}".strip()
        result_list.append(f"<i>{current_rank}: {full_name} - {correct}/{total}</i>")


    correct_answers_dict = create_answer_dict_from_string(test_data.answer)
    formatted_answers = []
    sorted_questions = sorted(correct_answers_dict.keys(), key=lambda x: int(x))

    for q_num in sorted_questions:
        answer = correct_answers_dict[q_num]
        formatted_answers.append(f"{q_num}{answer}") # 1a 2b 3c formatida

    # 4. Yakunlash xabarini shakllantirish (Final Report)
    final_report = (
        f"✅ Test muvaffaqiyatli yakunlandi!\n\n"
        f"👤 Test muallifi: <b>{creator_name}</b>\n\n"
        f"📝 Test nomi: <b>{test_data.title}</b>\n"
        f"🏷 Test kodi: <i><code>{test_code}</code></i>\n"
        f"❓ Savollar soni: <b>{len(sorted_questions)} ta</b>\n" # Har bir juftlik bitta savol emas, bu yerda savol raqami.
        f"👥 Jami ishlaganlar: <b>{len(results)} ta</b>\n"
        f"--- Natijalar ro'yxati ---\n\n"
    )

    if result_list:
        final_report += "\n".join(result_list)
    else:
        final_report += "Testni hali hech kim ishlamagan."

    final_report += (
        f"\n\n🔑 To'g'ri javoblar kaliti: "
        f"<code>{' '.join(formatted_answers)}</code>"
    )


    # Statega ma'lumotlarni saqlash
    await state.update_data(
        all_results=results, 
        all_user_ids=user_ids_who_passed, 
        test_title=test_data.title,
        test_code=test_code,
        creator_name=creator_name,
        final_report=final_report,

    )

    # Birinchi shablonni ko'rsatish
    current_index = 0
    
    await message.answer(
        f"Test muvaffaqiyatli yakunlandi. Natijalar 👇\n\n{final_report}",
        parse_mode='HTML'
    )
    
    
    if is_deactivated:

        excel_path = create_full_participant_report_pandas(
            test_title=test_data.title,
            results=results, 
            creator_name=creator_name
        )

        if excel_path and os.path.exists(excel_path):
            try:
                await bot.send_document(
                    chat_id=message.from_user.id, # Muallifning Telegram ID'si
                    document=FSInputFile(excel_path),
                    caption=f"📝 '{test_data.title}' testi bo'yicha ishtirokchilarning to'liq hisoboti.",
                    parse_mode='HTML'
                )
                logger.info(f"Excel report for test {test_code} sent to creator {message.from_user.id}.")
    
                os.remove(excel_path)
                logger.info(f"Excel report file removed: {excel_path}")
                
            except Exception as e:
                await message.answer("Hisobot faylini yuborishda xatolik yuz berdi ‼️")
                logger.error(f"Error sending Excel report: {e}")
            

    else:
        await message.answer("Hisobot faylini yaratishda xatolik yuz berdi. Iltimos, adminga murojaat qiling.")

    
    await state.set_state(CheckStates.waiting_for_template_selection)


@router.message(Command("menu"))
async def start_create_test_handler(message: Message):
    await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)

