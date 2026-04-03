#!/usr/bin/env python3
import pdfplumber
from pathlib import Path

def analyze_specific_lines(pdf_path, page_num=1):
    """Анализирует конкретную страницу и показывает все строки с деталями."""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num - 1]
        chars = page.chars
        
        # Группируем по строкам
        lines_dict = {}
        for char in chars:
            top_key = round(char['top'], 1)
            if top_key not in lines_dict:
                lines_dict[top_key] = []
            lines_dict[top_key].append(char)
        
        sorted_tops = sorted(lines_dict.keys())
        
        print(f"=== Страница {page_num} - все строки (первые 50) ===\n")
        
        for i, top in enumerate(sorted_tops[:50], 1):
            line_chars = sorted(lines_dict[top], key=lambda c: c['x0'])
            line_text = ''.join(c['text'] for c in line_chars).strip()
            
            if not line_text:
                continue
            
            # Показываем все символы строки с их шрифтами
            print(f"{i:2}. ", end='')
            for char in line_chars[:40]:  # Первые 40 символов
                fontname = char.get('fontname', '')
                # Сокращаем имя шрифта для читаемости
                short_font = fontname.split('/')[-1] if '/' in fontname else fontname
                print(f"{char['text']}({short_font[-4:]})", end=" ")
            print()
            
            # Проверяем, содержит ли строка запятую и начинается ли с заглавной
            has_comma = ',' in line_text
            first_char = line_chars[0]['text'] if line_chars else ''
            is_upper = first_char.isupper() if first_char else False
            
            print(f"   Запятая: {has_comma}, Первая заглавная: {is_upper}, Длина: {len(line_text)}")
            print()

if __name__ == '__main__':
    base_dir = Path(__file__).parent
    pdf1 = base_dir / 'tolkovyj_slovar_chast1_A-N.pdf'
    if pdf1.exists():
        analyze_specific_lines(pdf1, page_num=1)
