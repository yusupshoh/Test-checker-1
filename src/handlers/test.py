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
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import re
import uuid
import os
import shutil
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
from src.utils.sertifikat_generator import create_certificate
from PIL import Image


logger = logging.getLogger(__name__)

CERTIFICATE_TEMPLATES = {
    1: {"file": "sertifikatlar/sertifikat_shablon1.png", "desc": "Shablon 1 (Prof. Navoiy)"},
    2: {"file": "sertifikatlar/sertifikat_shablon2.png", "desc": "Shablon 2 (M. Zulfiqorova 1)"},
    3: {"file": "sertifikatlar/sertifikat_shablon3.png", "desc": "Shablon 3 (M. Zulfiqorova 2)"},
    4: {"file": "sertifikatlar/sertifikat_shablon4.png", "desc": "Shablon 4 (Yangi Dizayn)"},
}
CERT_IDS = sorted(CERTIFICATE_TEMPLATES.keys()) 
MAX_CERT_INDEX = len(CERT_IDS) - 1

router = Router()

def get_cert_pagination_kb(current_index: int): 
    current_cert_id = CERT_IDS[current_index] 
    total_certs = len(CERT_IDS)
    
    keyboard = [
        [
            InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"cert_nav:prev:{current_index}"),
            InlineKeyboardButton(text=f"Tanlash ({current_cert_id}/{total_certs})", callback_data=f"cert_select:{current_cert_id}"),
            InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"cert_nav:next:{current_index}"),
        ],
        [
            InlineKeyboardButton(text="❌ Sertifikatsiz yakunlash", callback_data="cert_select:0"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def send_cert_template(bot: Bot, chat_id: int, current_index: int, msg_id: int = None):
    cert_id = CERT_IDS[current_index]
    template_data = CERTIFICATE_TEMPLATES[cert_id]
    photo_path = template_data['file']
    caption = f"🖼 Sertifikat shabloni {cert_id} / {MAX_CERT_INDEX + 1}\n\n"
    caption += "Iltimos, test ishtirokchilari uchun sertifikat shablonini tanlang:"
    keyboard = get_cert_pagination_kb(current_index)
    photo = FSInputFile(photo_path)
    
    if msg_id:

        await bot.delete_message(chat_id, msg_id)
        
    sent_message = await bot.send_photo(
        chat_id=chat_id,
        photo=photo,
        caption=caption,
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    return sent_message.message_id

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
                f"test nomi: <b>{test_title}</b>\n"
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
        f"Test nomi: <b>{test.title}</b>.\n\n"
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
        "Iltimos, yakunlamoqchi bo'lgan testingizni ID kodini kiriting (masalan: A1B2C3D4) ✏️:",
        parse_mode='Markdown',
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

    if not re.fullmatch(r'[A-Z0-9]{8}', test_code):
        await message.answer("Kod formati noto'g'ri. O'qituvchingiz bergan id ni. Qayta kiriting. ‼️‼️")
        return

    results = []
    user_ids_who_passed = []
    test_data = None
    creator_name = "Noma'lum"

    async with session_factory() as session:
        test_data = await get_test_by_id(session, test_code)
        
        if not test_data or test_data.creator_id != message.from_user.id:
            await message.answer("Kechirasiz, bu kod bilan test topilmadi yoki siz uning muallifi emassiz.")
            await state.clear()
            await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)
            return

        if not test_data.status: 
            await message.answer("❗️ Test allaqachon yakunlangan.")
            await state.clear()
            await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)
            return
            
        creator_user = await get_user(session, test_data.creator_id)
        creator_name = f"{creator_user.first_name} {creator_user.last_name or ''}".strip() if creator_user and creator_user.first_name else "Noma'lum"
        
        try:
            results = await get_test_results_with_users(session, test_code)
            user_ids_who_passed = await get_unique_user_ids_for_test(session, test_code)
        except Exception as e:
            await message.answer("Natijalarni olishda xatolik yuz berdi ‼️")
            logger.error("DB Error getting results in process_finish_test_code: %s", e)
            await state.clear()
            await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)
            return

        is_deactivated = await deactivate_test(session, test_code)

    result_list = []
    current_rank = 0
    last_correct_count = -1
    rank_count = 0
    sorted_results_for_ranking = sorted(results, key=lambda x: x[4], reverse=True)

    for user_id_res, first_name, last_name, phone_number, correct, total in sorted_results_for_ranking:
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
        formatted_answers.append(f"{q_num}{answer}")

    final_report = (
        f"✅ Test muvaffaqiyatli yakunlandi!\n\n"
        f"👤 Test muallifi: <b>{creator_name}</b>\n\n"
        f"📝 Test nomi: <b>{test_data.title}</b>\n"
        f"🏷 Test kodi: <i><code>{test_code}</code></i>\n"
        f"❓ Savollar soni: <b>{len(sorted_questions)} ta</b>\n"
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

    if is_deactivated: 
        excel_path = create_full_participant_report_pandas(
            test_title=test_data.title,
            results=results, 
            creator_name=creator_name
        )

        if excel_path and os.path.exists(excel_path):
            try:
                await bot.send_document(
                    chat_id=message.from_user.id,
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

    await message.answer(
        f"Test muvaffaqiyatli yakunlandi. Natijalar 👇\n\n{final_report}",
        parse_mode='HTML'
    )

    await state.update_data(
        all_results=results, 
        all_user_ids=user_ids_who_passed, 
        test_title=test_data.title,
        test_code=test_code,
        creator_name=creator_name, 
        final_report=final_report,
    )

    if results:
        await message.answer(
            "Endi ishtirokchilarga yuboriladigan sertifikat shablonini tanlang. 👇",
            parse_mode='Markdown'
        )

        await state.set_state(CheckStates.waiting_for_pagination)
        new_msg_id = await send_cert_template(
            bot=bot, 
            chat_id=message.chat.id, 
            current_index=0
        )
        
        await state.update_data(
            current_cert_index=0, 
            cert_msg_id=new_msg_id
        )
    else:
        await message.answer("Testni hech kim ishlamaganligi sababli sertifikat yaratilmadi.", reply_markup=mainMenu)
        await state.clear()

@router.callback_query(F.data.startswith("cert_nav"), CheckStates.waiting_for_pagination)
async def handle_cert_navigation(callback: CallbackQuery, state: FSMContext, bot: Bot):
    parts = callback.data.split(":")

    if len(parts) != 3:
        await callback.answer("Xato: Noto'g'ri navigatsiya ma'lumoti.")
        return
        
    action, direction, current_index_raw = parts

    current_index = int(current_index_raw)
    data = await state.get_data()
    cert_msg_id = data.get('cert_msg_id')
    new_index = current_index
    
    if direction == "prev":
        new_index = (current_index - 1) % len(CERT_IDS) 
    elif direction == "next":
        new_index = (current_index + 1) % len(CERT_IDS)
        
    if new_index != current_index:
        
        try:
            new_msg_id = await send_cert_template(
                bot=bot, 
                chat_id=callback.message.chat.id, 
                current_index=new_index, 
                msg_id=cert_msg_id
            )

            await state.update_data(
                current_cert_index=new_index,
                cert_msg_id=new_msg_id
            )

            await callback.answer(f"Shablon {CERT_IDS[new_index]} ko'rsatildi")
        except Exception as e:
            logger.error(f"Sertifikat navigatsiyasida xato yuz berdi: {e}")
            await callback.answer("Rasmni yangilashda xato.")
    else:
        await callback.answer()


@router.callback_query(F.data.startswith("cert_select"), CheckStates.waiting_for_pagination)
async def handle_cert_selection(callback: CallbackQuery, state: FSMContext, bot: Bot): 
    selected_cert_id_raw = callback.data.split(":")[1]
    selected_cert_id = int(selected_cert_id_raw)
    data = await state.get_data()
    cert_msg_id = data.get('cert_msg_id')

    try:
        await bot.delete_message(callback.message.chat.id, cert_msg_id)
    except Exception as e:
        logger.error(f"Xabarni o'chirishda xato: {e}")
        
    await callback.answer("Tanlov qabul qilindi...")

    if selected_cert_id == 0:
        await state.clear()
        await callback.message.answer("Sertifikat yaratish bekor qilindi.", reply_markup=mainMenu)
        return

    results: List[Tuple] = data.get('all_results', [])
    test_title: str = data.get('test_title', "Test nomi")
    creator_name: str = data.get('creator_name', "Noaniq O'qituvchi")
    
    await callback.message.answer(
        f"⏳ {selected_cert_id}-shablon bo'yicha {len(results)} ta sertifikat yaratilmoqda. Iltimos, kuting..."
    )
    
    sorted_results = sorted(results, key=lambda x: (x[4], x[4]/x[5] if x[5] else 0), reverse=True)
    created_certs = []
    
    for rank_idx, res in enumerate(sorted_results):
        user_id_res, first_name, last_name, _, correct, total = res
        full_name = f"{first_name} {last_name or ''}".strip()
        result_percent = round((correct / total) * 100) if total else 0
        rank = rank_idx + 1 
        
        try:
            cert_path = create_certificate(
                generator_id=selected_cert_id,
                full_name=full_name,
                subject=test_title,
                result_percent=result_percent,
                rank=rank,                     
                teacher_name=creator_name      
            )
            
            if cert_path and not cert_path.startswith('❌'):
                created_certs.append((user_id_res, cert_path))
            else:
                logger.error(f"Sertifikat yaratishda xato: {cert_path}")
            
        except Exception as e:
            logger.error(f"Sertifikat yaratishda kutilmagan xato: {e}. Ism: {full_name}")
            
    
    if created_certs:
        
        await callback.message.answer(f"✅ Jami {len(created_certs)} ta sertifikat yaratildi. Muallifga yuborilmoqda.")
        
        sent_count = 0

        list_of_png_paths = []

        for user_id_res, cert_path in created_certs:
            try:
                await bot.send_document(
                    chat_id=user_id_res, 
                    document=FSInputFile(cert_path),
                    caption=f"🏆 Tabriklaymiz! Siz {test_title} bo'yicha test sertifikatiga ega bo'ldingiz.",
                    parse_mode='Markdown'
                )
                sent_count += 1
                list_of_png_paths.append(cert_path)
            except Exception as e:
                logger.error(f"Sertifikatni user {user_id_res} ga yuborishda xato: {e}")

        await callback.message.answer(
            f"Sertifikatlar {sent_count} ta ishtirokchiga muvaffaqiyatli yuborildi.", 
            reply_markup=mainMenu
        )

        temp_dir = "temp_certs"
        pdf_path = os.path.join(temp_dir, f"Sertifikatlar_{data.get('test_code')}.pdf")

        if list_of_png_paths:
            try:
                
                img1 = Image.open(list_of_png_paths[0])
                
                if len(list_of_png_paths) > 1:
                    images_list = [Image.open(p) for p in list_of_png_paths[1:]]
                else:
                    images_list = []

                img1.save(
                    pdf_path, 
                    "PDF", 
                    resolution=100.0, 
                    save_all=True, 
                    append_images=images_list
                )
                
                await bot.send_document(
                    chat_id=callback.from_user.id,
                    document=FSInputFile(pdf_path),
                    caption=f"📄 Barcha {len(list_of_png_paths)} ta sertifikatlar {test_title} testi uchun bitta PDF faylda."
                )
                logger.info(f"PDF certificate archive sent to creator {callback.from_user.id}")

            except Exception as e:
                logger.error(f"PDF yaratish yoki yuborishda xato: {e}")
                await callback.message.answer("PDF arxivni yaratishda xato yuz berdi.")

        if os.path.exists(temp_dir):
             try:
                 shutil.rmtree(temp_dir)
                 logger.info(f"Temp certs directory removed: {temp_dir}")
             except Exception as e:
                 logger.error(f"Vaqtinchalik papkani o'chirishda xato: {e}")

    else:
        await callback.message.answer("Natijalar bo'yicha sertifikat yaratilmadi. Ehtimol xato yuz berdi.", reply_markup=mainMenu)

    await state.clear()


@router.message(Command("menu"))
async def start_create_test_handler(message: Message):
    await message.answer("👇 Asosiy menyu 👇", reply_markup=mainMenu)

