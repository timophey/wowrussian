#!/usr/bin/env python3
"""
Тестовый конвертер для толкового словаря.
"""

import pdfplumber
from pathlib import Path
from collections import Counter

def test_extract(pdf_path, start_page=1, max_pages=2):
    """Тестовое извлечение для понимания структуры."""
    entries = []
    bold_font = 'CIDFont+F2'  # Шрифт для слов (лемм)
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        pages_to_process = min(max_pages or total_pages, total_pages - start_page + 1)
        
        print(f"PDF: {pdf_path.name}")
        print(f"Всего страниц: {total_pages}")
        print(f"Обрабатываем страницы {start_page}-{start_page + pages_to_process - 1}\n")
        
        for page_idx in range(start_page - 1, start_page + pages_to_process - 2):
            page_num = page_idx + 1
            page = pdf.pages[page_idx]
            chars = page.chars
            
            # Группируем по строкам
            lines_dict = {}
            for char in chars:
                top_key = round(char['top'], 1)
                if top_key not in lines_dict:
                    lines_dict[top_key] = []
                lines_dict[top_key].append(char)
            
            sorted_tops = sorted(lines_dict.keys())
            
            print(f"=== Страница {page_num} ===")
            
            for top in sorted_tops[:30]:  # Первые 30 строк
                line_chars = sorted(lines_dict[top], key=lambda c: c['x0'])
                line_text = ''.join(c['text'] for c in line_chars).strip()
                
                if not line_text:
                    continue
                
                # Пропускаем строки без запятых
                if ',' not in line_text:
                    continue
                
                # Находим последовательность символов с шрифтом bold_font в начале строки
                word_chars = []
                rest_chars = []
                found_bold = False
                
                for char in line_chars:
                    fontname = char.get('fontname', '')
                    if fontname == bold_font and not word_chars:
                        # Начинаем собирать слово
                        word_chars.append(char['text'])
                    elif word_chars and not found_bold:
                        # Первый не-жирный символ - конец слова
                        rest_chars.append(char['text'])
                        found_bold = True
                    elif found_bold:
                        # Остальные не-жирные символы
                        rest_chars.append(char['text'])
                    # Если word_chars пуст и это не bold_font - пропускаем (не начало слова)
                
                if word_chars:
                    word_raw = ''.join(word_chars).strip()
                    after_word = ''.join(rest_chars).strip() if rest_chars else ''
                    
                    # Убираем ударения
                    word_clean = word_raw.replace('\u0301', '').replace('́', '')
                    
                    # Убираем запятую в начале after_word если есть
                    if after_word.startswith(','):
                        after_word = after_word[1:].strip()
                    
                    print(f"Слово: '{word_clean}'")
                    print(f"  Полная строка: {line_text[:80]}")
                    print(f"  Forms: {after_word[:60] if after_word else '(пусто)'}")
                    print()
                    
                    entries.append({
                        'word': word_clean,
                        'forms': [after_word] if after_word else [],
                        'full_line': line_text,
                        'page_num': page_num
                    })
    
    return entries

if __name__ == '__main__':
    base_dir = Path(__file__).parent
    pdf1 = base_dir / 'tolkovyj_slovar_chast1_A-N.pdf'
    pdf2 = base_dir / 'tolkovyj_slovar_chast2_O-Ja.pdf'
    
    if pdf1.exists():
        entries = test_extract(pdf1, start_page=1, max_pages=2)
        print(f"\nИзвлечено записей (тест): {len(entries)}")
    else:
        print(f"Файл не найден: {pdf1}")
