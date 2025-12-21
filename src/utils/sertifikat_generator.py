from PIL import Image, ImageDraw, ImageFont
import os
import uuid

import logging

logger = logging.getLogger(__name__)


class BaseCertificateGenerator:
    _fonts_cache = {}

    def _get_font(self, font_path, size):
        cache_key = f"{font_path}_{size}"
        if cache_key not in self._fonts_cache:
            try:
                self._fonts_cache[cache_key] = ImageFont.truetype(font_path, size)
                # logger.info(f"Shrift yuklandi: {font_path}") # Test uchun
            except IOError:
                self._fonts_cache[cache_key] = ImageFont.load_default()
        return self._fonts_cache[cache_key]

    def _wrap_and_center_text(self,
                              draw: ImageDraw.ImageDraw,
                              text: str,
                              font: ImageFont.ImageFont,
                              img_width: int,
                              max_width: int,
                              start_y: int,
                              line_spacing: int,
                              fill_color: str):
        words = text.split()
        wrapped_lines = []
        current_line = []

        for word in words:
            line_bbox = draw.textbbox((0, 0), ' '.join(current_line + [word]), font=font)
            line_width = line_bbox[2] - line_bbox[0]

            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    wrapped_lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            wrapped_lines.append(' '.join(current_line))

        current_y = start_y
        for line in wrapped_lines:
            if not line:
                continue

            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_width = line_bbox[2] - line_bbox[0]

            center_x = (img_width - line_width) / 2

            draw.text((center_x, current_y), line, fill=fill_color, font=font)
            current_y += line_spacing

    def generate_certificate(self, full_name: str, subject: str, result_percent: float,
                             rank: int, teacher_name: str, output_name: str):
        try:
            img = Image.open(self.TEMPLATE_FILE)
            draw = ImageDraw.Draw(img)
            img_width, _ = img.size

            rank_text = f"{rank}"
            congrats_text_final = (
                f"Telegram botimiz orqali {subject} fanidan o`tkazilgan "
                f"testimizdan {result_percent}% natija ko'rsatgani uchun {teacher_name} tomonidan "
                f"{rank_text}-o'rin bilan taqdirlandi"
            )

            # OLD: student_font = ImageFont.truetype(self.STUDENT_FONT_FILE, self.STUDENT_FONT_SIZE)
            # NEW (Keshdan foydalanish):
            student_font = self._get_font(self.STUDENT_FONT_FILE, self.STUDENT_FONT_SIZE)

            text_bbox = draw.textbbox((0, 0), full_name, font=student_font)
            text_width = text_bbox[2] - text_bbox[0]
            student_position = ((img_width - text_width) / 2, self.STUDENT_POSITION_Y)
            draw.text(student_position, full_name, fill=self.STUDENT_TEXT_COLOR, font=student_font)

            # O'qituvchi va tabrik matni uchun ham keshdan foydalanamiz:
            teacher_font = self._get_font(self.TEACHER_FONT_FILE, self.TEACHER_FONT_SIZE)
            draw.text(self.TEACHER_POSITION_XY, teacher_name, fill=self.TEACHER_TEXT_COLOR, font=teacher_font)

            congrats_font = self._get_font(self.CONGRATS_FONT_FILE, self.CONGRATS_FONT_SIZE)
            self._wrap_and_center_text(
                draw, congrats_text_final, congrats_font, img_width,
                self.CONGRATS_MAX_WIDTH, self.CONGRATS_POSITION_Y,
                self.LINE_SPACING, self.CONGRATS_TEXT_COLOR
            )

            img.save(output_name,
                     optimize=True,
                     quality=80,)

        except Exception as e:
            raise Exception(f"Sertifikat yaratishda xato: {e}")


class CertificateGenerator1(BaseCertificateGenerator):
    def __init__(self, template_file="sertifikatlar/sertifikat1.png"):
        self.TEMPLATE_FILE = template_file
        self.STUDENT_FONT_FILE = "sertifikatlar/sertifikat1_ism.ttf"
        self.STUDENT_FONT_SIZE = 100
        self.STUDENT_TEXT_COLOR = "#865b34"
        self.STUDENT_POSITION_Y = 550
        self.TEACHER_FONT_FILE = "sertifikatlar/sertifikat1_matn.ttf"
        self.TEACHER_FONT_SIZE = 40
        self.TEACHER_TEXT_COLOR = "#865b34"
        self.TEACHER_POSITION_XY = (1215, 1050)
        self.CONGRATS_FONT_FILE = "sertifikatlar/sertifikat1_matn.ttf"
        self.CONGRATS_FONT_SIZE = 30
        self.CONGRATS_TEXT_COLOR = "black"
        self.CONGRATS_POSITION_Y = 690
        self.CONGRATS_MAX_WIDTH = 850
        self.LINE_SPACING = 40


class CertificateGenerator2(BaseCertificateGenerator):
    def __init__(self, template_file="sertifikatlar/sertifikat2.png"):
        self.TEMPLATE_FILE = template_file
        self.STUDENT_FONT_FILE = "sertifikatlar/sertifikat2_ism.otf"
        self.STUDENT_FONT_SIZE = 100
        self.STUDENT_TEXT_COLOR = "#543c19"
        self.STUDENT_POSITION_Y = 550
        self.TEACHER_FONT_FILE = "sertifikatlar/sertifikat2_teacher.ttf"
        self.TEACHER_FONT_SIZE = 40
        self.TEACHER_TEXT_COLOR = "#543c19"
        self.TEACHER_POSITION_XY = (1100, 1150)
        self.CONGRATS_FONT_FILE = "sertifikatlar/sertifikat2_matn.ttf"
        self.CONGRATS_FONT_SIZE = 30
        self.CONGRATS_TEXT_COLOR = "black"
        self.CONGRATS_POSITION_Y = 700
        self.CONGRATS_MAX_WIDTH = 850
        self.LINE_SPACING = 40


class CertificateGenerator3(BaseCertificateGenerator):
    def __init__(self, template_file="sertifikatlar/sertifikat3.png"):
        self.TEMPLATE_FILE = template_file
        self.STUDENT_FONT_FILE = "sertifikatlar/sertifikat3_ism.ttf"
        self.STUDENT_FONT_SIZE = 100
        self.STUDENT_TEXT_COLOR = "#b27409"
        self.STUDENT_POSITION_Y = 650
        self.TEACHER_FONT_FILE = "sertifikatlar/sertifikat3_teacher.ttf"
        self.TEACHER_FONT_SIZE = 40
        self.TEACHER_TEXT_COLOR = "#b27409"
        self.TEACHER_POSITION_XY = (1100, 1058)
        self.CONGRATS_FONT_FILE = "sertifikatlar/sertifikat3_matn.ttf"
        self.CONGRATS_FONT_SIZE = 30
        self.CONGRATS_TEXT_COLOR = "black"
        self.CONGRATS_POSITION_Y = 770
        self.CONGRATS_MAX_WIDTH = 850
        self.LINE_SPACING = 40


class CertificateGenerator4(BaseCertificateGenerator):
    def __init__(self, template_file="sertifikatlar/sertifikat4.png"):
        self.TEMPLATE_FILE = template_file
        self.STUDENT_FONT_FILE = "sertifikatlar/sertifikat4_ism.ttf"
        self.STUDENT_FONT_SIZE = 100
        self.STUDENT_TEXT_COLOR = "#b27409"
        self.STUDENT_POSITION_Y = 530
        self.TEACHER_FONT_FILE = "sertifikatlar/sertifikat4_matn.ttf"
        self.TEACHER_FONT_SIZE = 40
        self.TEACHER_TEXT_COLOR = "#a27430"
        self.TEACHER_POSITION_XY = (1175, 1058)
        self.CONGRATS_FONT_FILE = "sertifikatlar/sertifikat4_matn.ttf"
        self.CONGRATS_FONT_SIZE = 30
        self.CONGRATS_TEXT_COLOR = "#a27430"
        self.CONGRATS_POSITION_Y = 680
        self.CONGRATS_MAX_WIDTH = 850
        self.LINE_SPACING = 40

GENERATORS_POOL = {
    1: CertificateGenerator1(),
    2: CertificateGenerator2(),
    3: CertificateGenerator3(),
    4: CertificateGenerator4()
}

def create_certificate(generator_id: int,
                       full_name: str,
                       subject: str,
                       result_percent: float,
                       rank: int,
                       teacher_name: str) -> str:
    OUTPUT_DIR = "temp_certs"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = "".join([c for c in full_name if c.isalnum() or c in (' ', '_')]).rstrip()
    output_filename = os.path.join(OUTPUT_DIR, f"cert_{rank}_{uuid.uuid4().hex[:5]}.png")

    try:
        # Yangi klass yaratish o'rniga, tayyor pool dan olamiz
        generator = GENERATORS_POOL.get(generator_id)

        if not generator:
            return "❌ Noto'g'ri generator ID."

        # Tayyor obyekt orqali metodni chaqiramiz
        generator.generate_certificate(
            full_name=full_name,
            subject=subject,
            result_percent=result_percent,
            rank=rank,
            teacher_name=teacher_name,
            output_name=output_filename
        )

        return output_filename

    except Exception as e:
        logger.error(f"Sertifikat generatsiyasida xato: {e}")
        return f"❌ Xato: {e}"