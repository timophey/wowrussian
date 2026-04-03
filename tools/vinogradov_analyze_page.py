#!/usr/bin/env python3
"""
Анализ структуры страницы 9 PDF для понимания формата словаря.
"""

import pdfplumber
from pathlib import Path

def analyze_page(pdf_path, page_num=9):
    """Анализирует указанную страницу."""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num - 1]

        # Извлекаем символы
        chars = page.chars
        print(f"Страница {page_num}: всего символов: {len(chars)}")

        # Группируем по строкам
        lines_dict = {}
        for char in chars:
            top_key = round(char['top'], 1)
            if top_key not in lines_dict:
                lines_dict[top_key] = []
            lines_dict[top_key].append(char)

        sorted_tops = sorted(lines_dict.keys())
        print(f"Всего строк: {len(sorted_tops)}")

        # Анализируем первые 20 строк
        for i, top in enumerate(sorted_tops[:20], 1):
            line_chars = sorted(lines_dict[top], key=lambda c: c['x0'])
            line_text = ''.join(c['text'] for c in line_chars)

            # Ищем жирные сегменты
            bold_fontname = 'TimesNewRomanPS-BoldMT'
            bold_segments = []
            current_segment = []
            for char in line_chars:
                fontname = char.get('fontname', '')
                is_bold = bold_fontname in fontname
                if is_bold:
                    current_segment.append(char['text'])
                else:
                    if current_segment:
                        bold_segments.append(''.join(current_segment))
                        current_segment = []
            if current_segment:
                bold_segments.append(''.join(current_segment))

            has_comma = ',' in line_text
            print(f"{i:2}. top={top:.1f} | bold={len(bold_segments)} | comma={has_comma} | {repr(line_text[:80])}")

if __name__ == '__main__':
    base_dir = Path(__file__).parent
    pdf_path = base_dir / 'orfograficheskij_slovar.pdf'
    analyze_page(pdf_path, 9)