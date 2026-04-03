#!/usr/bin/env python3
"""
Анализатор структуры PDF толкового словаря.
Изучает первые страницы, чтобы понять форматирование.
"""

import pdfplumber
from pathlib import Path
from collections import Counter

def analyze_pdf(pdf_path, num_pages=10):
    """Анализирует PDF и выводит информацию о шрифтах и структуре."""
    print(f"\n=== Анализ: {pdf_path.name} ===\n")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"Всего страниц: {total_pages}")
            print(f"Анализируем первые {min(num_pages, total_pages)} страниц\n")
            
            # Собираем статистику по шрифтам
            all_fonts = Counter()
            bold_fonts = Counter()
            
            pages_to_analyze = min(num_pages, total_pages)
            
            for page_idx in range(pages_to_analyze):
                page = pdf.pages[page_idx]
                chars = page.chars
                
                print(f"--- Страница {page_idx + 1} ---")
                
                # Группируем по строкам
                lines_dict = {}
                for char in chars:
                    top_key = round(char['top'], 1)
                    if top_key not in lines_dict:
                        lines_dict[top_key] = []
                    lines_dict[top_key].append(char)
                
                sorted_tops = sorted(lines_dict.keys())
                
                # Показываем первые 15 строк со шрифтами
                line_count = 0
                for top in sorted_tops[:15]:
                    line_chars = sorted(lines_dict[top], key=lambda c: c['x0'])
                    line_text = ''.join(c['text'] for c in line_chars).strip()
                    
                    if not line_text:
                        continue
                    
                    # Собираем информацию о шрифтах в строке
                    fonts_in_line = []
                    for char in line_chars[:50]:  # Первые 50 символов
                        fontname = char.get('fontname', '')
                        all_fonts[fontname] += 1
                        fonts_in_line.append(fontname)
                    
                    # Определяем, есть ли жирные символы
                    has_bold = any('Bold' in f or 'bold' in f for f in fonts_in_line if f)
                    
                    # Показываем пример строки
                    display_text = line_text[:60] if len(line_text) > 60 else line_text
                    print(f"  {display_text:<60} {'[ЖИРНЫЙ]' if has_bold else ''}")
                    
                    line_count += 1
                    if line_count >= 10:
                        break
                
                # Собираем статистику по шрифтам на странице
                page_fonts = Counter()
                for char in chars:
                    fontname = char.get('fontname', '')
                    page_fonts[fontname] += 1
                    if 'Bold' in fontname or 'bold' in fontname:
                        bold_fonts[fontname] += 1
                
                print(f"\n  Шрифты на странице (топ-5):")
                for font, count in page_fonts.most_common(5):
                    print(f"    {font}: {count} символов")
                
                print()
            
            print("=== Общая статистика по всем анализируемым страницам ===")
            print(f"\nВсе уникальные шрифты (топ-10):")
            for font, count in all_fonts.most_common(10):
                print(f"  {font}: {count} символов")
            
            print(f"\nШрифты, содержащие 'Bold' или 'bold' (топ-10):")
            for font, count in bold_fonts.most_common(10):
                print(f"  {font}: {count} символов")
            
            # Анализируем, на какой странице начинается словарный материал
            print(f"\n=== Поиск начала словарных статей ===")
            print("Ищем строки, начинающиеся с жирного шрифта и содержащие запятую...")
            
            for page_idx in range(min(20, total_pages)):
                page = pdf.pages[page_idx]
                chars = page.chars
                
                lines_dict = {}
                for char in chars:
                    top_key = round(char['top'], 1)
                    if top_key not in lines_dict:
                        lines_dict[top_key] = []
                    lines_dict[top_key].append(char)
                
                sorted_tops = sorted(lines_dict.keys())
                
                dictionary_lines = []
                for top in sorted_tops:
                    line_chars = sorted(lines_dict[top], key=lambda c: c['x0'])
                    line_text = ''.join(c['text'] for c in line_chars).strip()
                    
                    if not line_text:
                        continue
                    
                    # Проверяем, начинается ли строка с жирного символа
                    if line_chars:
                        first_font = line_chars[0].get('fontname', '')
                        is_bold_start = 'Bold' in first_font or 'bold' in first_font
                        
                        # Есть запятая?
                        has_comma = ',' in line_text
                        
                        if is_bold_start and has_comma:
                            dictionary_lines.append(line_text[:80])
                
                if dictionary_lines:
                    print(f"Страница {page_idx + 1}: найдено {len(dictionary_lines)} строк-статей")
                    for line in dictionary_lines[:3]:
                        print(f"  - {line}")
                    if len(dictionary_lines) > 3:
                        print(f"  ... и еще {len(dictionary_lines) - 3}")
                    print(f"  => Возможно, словарный материал начинается со страницы {page_idx + 1}")
                    break
            
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    base_dir = Path(__file__).parent
    pdf1 = base_dir / 'tolkovyj_slovar_chast1_A-N.pdf'
    pdf2 = base_dir / 'tolkovyj_slovar_chast2_O-Ja.pdf'
    
    if pdf1.exists():
        analyze_pdf(pdf1, num_pages=10)
    else:
        print(f"Файл не найден: {pdf1}")
    
    if pdf2.exists():
        analyze_pdf(pdf2, num_pages=10)
    else:
        print(f"Файл не найден: {pdf2}")
