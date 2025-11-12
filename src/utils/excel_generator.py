import pandas as pd
from typing import List, Tuple, Dict, Any
import os
import logging
import time

logger = logging.getLogger(__name__)


def create_full_participant_report_pandas(
        test_title: str,
        # Tuple tipi endi 7 ta qiymatni qamrab olishi kerak (oxirgi int o'rniga str bo'ladi, bu user_answers_key)
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

        # !!! FAKAT SHU YER O'ZGARTIRILDI !!!
        # 7-chi qiymat (user_answers_key) uchun qo'shimcha '_' qo'shildi
        for row_num, (user_id, first_name, last_name, phone_number, correct_count, total_questions, _) in enumerate(
                results):
            full_name = f"{first_name} {last_name or ''}".strip()
            # Foizni hisoblash
            percentage = round((correct_count / total_questions) * 100, 1) if total_questions else 0

            data_list.append({
                'T/r': row_num + 1,
                'F.I.Sh.': full_name,
                'Telefon raqami': phone_number,
                'To\'g\'ri javoblar': correct_count,
                'Jami savollar': total_questions,
                'Foiz (%)': percentage,
                'Telegram ID': user_id
            })

        df = pd.DataFrame(data_list)

        # ... qolgan kod (Excel faylini yaratish mantiqi)

        writer = pd.ExcelWriter(file_path, engine='openpyxl')

        info_df = pd.DataFrame({
            'Ma\'lumot': [f'Test: {test_title}', f'Muallif: {creator_name}',
                          f'Yaratilgan vaqti: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}']
        })

        info_df.to_excel(writer, sheet_name='Ishtirokchilar', startrow=0, startcol=0, header=False, index=False)
        df.to_excel(writer, sheet_name='Ishtirokchilar', startrow=4, startcol=0, header=True, index=False)

        workbook = writer.book
        worksheet = writer.sheets['Ishtirokchilar']

        # Ustun kengligini sozlash
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
            worksheet.column_dimensions[chr(ord('A') + i)].width = max_len

        writer.close()

        logger.info(f"Pandas Excel report created successfully at {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Error creating Pandas Excel file: {e}")
        return None