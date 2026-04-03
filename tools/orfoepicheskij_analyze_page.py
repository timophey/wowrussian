#!/usr/bin/env python3
"""
Анализ структуры страниц PDF для понимания формата словаря.
Анализирует указанные страницы, начиная с page_start (по умолчанию 13).
"""

import pdfplumber
from pathlib import Path

def analyze_page(pdf_path, page_num, bold_fontname=None):
    """Анализирует указанную страницу."""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num - 1]

        # Извлекаем символы
        chars = page.chars
        print(f"\n=== Страница {page_num}: всего символов: {len(chars)} ===")

        # Группируем по строкам
        lines_dict = {}
        for char in chars:
            top_key = round(char['top'], 1)
            if top_key not in lines_dict:
                lines_dict[top_key] = []
            lines_dict[top_key].append(char)

        sorted_tops = sorted(lines_dict.keys())
        print(f"Всего строк: {len(sorted_tops)}")

        # Анализируем все строки
        for i, top in enumerate(sorted_tops, 1):
            line_chars = sorted(lines_dict[top], key=lambda c: c['x0'])
            line_text = ''.join(c['text'] for c in line_chars)

            # Ищем жирные сегменты
            if bold_fontname is None:
                # Показываем информацию о шрифтах для определения жирного
                fonts = {}
                for char in line_chars:
                    font = char.get('fontname', 'Unknown')
                    fonts[font] = fonts.get(font, 0) + 1
                font_info = ', '.join(f'{f}({c})' for f, c in fonts.items())
            else:
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
                font_info = f"bold={len(bold_segments)}"

            has_comma = ',' in line_text
            print(f"{i:3}. top={top:.1f} | {font_info:30} | comma={has_comma} | {repr(line_text[:100])}")

def main():
    base_dir = Path(__file__).parent
    pdf_path = base_dir / 'orfoepicheskij_slovar.pdf'

    if not pdf_path.exists():
        print(f"Ошибка: файл не найден: {pdf_path}")
        print(f"Убедитесь, что orfoepicheskij_slovar.pdf находится в папке tools/")
        return 1

    # Анализируем несколько страниц, начиная с 13
    start_page = 13
    num_pages = 3

    print(f"Анализ PDF: {pdf_path}")
    print(f"Статистика PDF (всего страниц):")
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"  Всего страниц: {len(pdf.pages)}")
    
    # Сначала определим, какой шрифт используется для жирного текста
    print(f"\nОпределяем шрифт для жирного текста на странице {start_page}...")
    analyze_page(pdf_path, start_page, bold_fontname=None)
    
    # После просмотра первой страницы, пользователь должен определить шрифт
    # Пока что, предложим ввести его вручную или использовать стандартный
    bold_fontname = input("\nВведите название жирного шрифта (например, TimesNewRomanPS-BoldMT) или нажмите Enter для использования стандартного: ").strip()
    if not bold_fontname:
        bold_fontname = 'TimesNewRomanPS-BoldMT'
        print(f"Используется шрифт по умолчанию: {bold_fontname}")
    
    # Анализируем несколько страницы с известным шрифтом
    for page_offset in range(num_pages):
        page_num = start_page + page_offset
        if page_num <= len(pdf.pages):
            analyze_page(pdf_path, page_num, bold_fontname=bold_fontname)
        else:
            break

    print("\n=== АНАЛИЗ ЗАВЕРШЕН ===")
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
