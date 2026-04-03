#!/usr/bin/env python3
"""
Детальный анализ шрифтов толкового словаря.
Показывает fontname для первых символов каждой строки.
"""

import pdfplumber
from pathlib import Path

def detailed_analyze(pdf_path, num_pages=5):
    """Детальный анализ шрифтов в строках."""
    print(f"\n=== Детальный анализ: {pdf_path.name} ===\n")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
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
                
                # Анализируем первые 20 строк
                line_count = 0
                for top in sorted_tops[:20]:
                    line_chars = sorted(lines_dict[top], key=lambda c: c['x0'])
                    line_text = ''.join(c['text'] for c in line_chars).strip()
                    
                    if not line_text:
                        continue
                    
                    # Показываем первые 5 символов с их шрифтами
                    print(f"\n  Строка: {line_text[:80]}")
                    print(f"    Первые 5 символов:")
                    for i, char in enumerate(line_chars[:5]):
                        fontname = char.get('fontname', 'NO_FONT')
                        print(f"      [{i}] '{char['text']}' -> {fontname}")
                    
                    # Определяем, есть ли в строке жирные символы
                    has_bold = any('Bold' in c.get('fontname', '') or 'bold' in c.get('fontname', '') 
                                  for c in line_chars if c.get('fontname'))
                    print(f"    Жирные символы в строке: {'ДА' if has_bold else 'НЕТ'}")
                    
                    line_count += 1
                    if line_count >= 15:
                        break
                
                print()
                
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    base_dir = Path(__file__).parent
    pdf1 = base_dir / 'tolkovyj_slovar_chast1_A-N.pdf'
    pdf2 = base_dir / 'tolkovyj_slovar_chast2_O-Ja.pdf'
    
    if pdf1.exists():
        detailed_analyze(pdf1, num_pages=3)
    else:
        print(f"Файл не найден: {pdf1}")
    
    if pdf2.exists():
        detailed_analyze(pdf2, num_pages=3)
    else:
        print(f"Файл не найден: {pdf2}")
