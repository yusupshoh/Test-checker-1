import pandas as pd
from typing import List, Tuple, Dict, Any
import os
import logging
import time

logger = logging.getLogger(__name__)


def create_full_participant_report_pandas(
        test_title: str,
        # Tuple tipi endi user_answers_key (str) ni ham o'z ichiga oladi
        results: List[Tuple[int, str, str, str, int, int, str]],
        creator_name: str
) -> str:
    output_dir = 'reports'
    os.makedirs(output_dir, exist_ok=True)

    # 2. Fayl nomini yaratish
    safe_title = "".join([c for c in test_title if c.isalnum() or c in (' ', '_')]).rstrip()
    if not safe_title:
        safe_title = "Natijalar_Hisoboti"

    timestamp = int(time.time())
    file_path = os.path.join(output_dir, f"{safe_title}_Ishtirokchilar_{timestamp}.xlsx")

    try:
        # 3. Ma'lumotlarni DataFramening qabul qiladigan formatiga o'tkazish
        data_list = []

        for row_num, (user_id, first_name, last_name, phone_number, correct_count, total_questions,
                      user_answers_key) in enumerate(
                results):
            full_name = f"{first_name} {last_name or ''}".strip()
            # Foizni hisoblash
            percentage = round((correct_count / total_questions) * 100, 1) if total_questions else 0

            data_list.append({
                'F.I.Sh.': full_name,
                'Telefon raqami': phone_number,
                'To\'g\'ri javoblar': correct_count,
                'Jami savollar': total_questions,
                'Foiz (%)': percentage,
                'Telegram ID': user_id,
                # Javob kalitini qo'shish (Majburiy emas, lekin hisobot uchun foydali)
                'Javob kaliti': user_answers_key
            })

        df = pd.DataFrame(data_list)

        # ----------------------------------------------------------------------
        # !!! YANGI MANTIQ: FILTRATSIYA VA REYTINGNI TO'G'RILASH !!!
        # ----------------------------------------------------------------------

        # 1. 🗑️ FILTRATSIYA: Ma'lumoti to'liq bo'lmagan "ko'rinmas" qatorlarni o'chirish.
        # Bu, ism-familiyasi bo'sh bo'lgan, ammo DBda qolib ketgan yozuvlarni o'chiradi.
        # Bu "o'rni band bo'lgan" muammoni hal qiladi.
        df = df[df['F.I.Sh.'].str.strip().astype(bool)]

        # Agar filtratsiyadan keyin DataFrame bo'sh bo'lsa
        if df.empty:
            logger.warning(f"No valid participants found for test: {test_title}")
            return None

            # 2. 🔀 SARALASH: Ballar va foiz bo'yicha saralash
        df = df.sort_values(by=['To\'g\'ri javoblar', 'Foiz (%)'], ascending=[False, False])

        # 3. 🥇 O'RINNI HISOBLASH (T/r ustunini yangilash)
        # 'dense' usuli bilan o'rin raqami uzilishlarsiz hisoblanadi (1, 2, 3, 3, 4, 5...)
        # Bu 17 dan keyin 19 kelishi muammosini hal qiladi.
        df['T/r'] = df['To\'g\'ri javoblar'].rank(method='dense', ascending=False).astype(int)

        # Sertifikat generatori uchun maxsus 'rank' ustunini yaratish
        # (Agar u 'T/r' emas, balki 'rank' ustunini kutsa)
        df['rank'] = df['T/r']

        # ----------------------------------------------------------------------

        # Excel faylini yaratish mantiqi
        writer = pd.ExcelWriter(file_path, engine='openpyxl')

        info_df = pd.DataFrame({
            'Ma\'lumot': [f'Test: {test_title}', f'Muallif: {creator_name}',
                          f'Yaratilgan vaqti: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}',
                          f'Ishtirokchilar soni: {len(df)}']  # Ishtirokchilar sonini yangilash
        })

        info_df.to_excel(writer, sheet_name='Ishtirokchilar', startrow=0, startcol=0, header=False, index=False)

        # Yangilangan 'T/r' ustunini Excelga birinchi ustun qilib qo'shish uchun:
        # Ustunlar tartibini belgilash
        columns_order = ['T/r', 'F.I.Sh.', 'Telefon raqami', 'To\'g\'ri javoblar', 'Jami savollar', 'Foiz (%)',
                         'Telegram ID', 'Javob kaliti']
        df_sorted = df[columns_order]

        df_sorted.to_excel(writer, sheet_name='Ishtirokchilar', startrow=4, startcol=0, header=True, index=False)

        workbook = writer.book
        worksheet = writer.sheets['Ishtirokchilar']

        # Ustun kengligini sozlash
        for i, col in enumerate(df_sorted.columns):
            max_len = max(df_sorted[col].astype(str).str.len().max(), len(col)) + 2
            # Excel ustunlari A, B, C...
            worksheet.column_dimensions[chr(ord('A') + i)].width = max_len

        writer.close()

        logger.info(f"Pandas Excel report created successfully at {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Error creating Pandas Excel file: {e}")
        return None