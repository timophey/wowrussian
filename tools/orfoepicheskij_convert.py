#!/usr/bin/env python3
"""
Конвертер орфоэпического словаря русского языка из PDF в JSON и Excel.
Извлекает записи словаря, начиная со страницы 13.

Особенности:
- Индикатор прогресса с tqdm
- Обработка ударений (акут)
- Игнорирование строк без запятых и строк с только ударениями
- Сохранение форм как единой строки (сохраняет вложенные запятые и скобки)
"""

import pdfplumber
import json
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import sys
import gc

def remove_accents(text):
    """Убирает знаки ударения (акут)."""
    return text.replace('\u0301', '').replace('́', '')

def is_only_accents(text):
    """Проверяет, состоит ли строка только из символов ударения."""
    stripped = text.strip()
    if not stripped:
        return False
    return all(c == '́' or c == '\u0301' for c in stripped)

def extract_dictionary(pdf_path, start_page=13, max_pages=None, max_entries=None):
    """
    Извлекает записи словаря из PDF.
    Возвращает список словарей: {word, forms, full_line, page_num}
    """
    entries = []
    bold_fontname = 'TimesNewRomanPS-BoldMT'

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_process = total_pages - start_page + 1
            if max_pages:
                pages_to_process = min(pages_to_process, max_pages)

            print(f"PDF: {pdf_path.name}")
            print(f"Всего страниц: {total_pages}")
            print(f"Начинаем со страницы: {start_page}")
            print(f"Страниц для обработки: {pages_to_process}")

            # Определяем диапазон страниц (0-based индексация)
            start_idx = start_page - 1
            end_idx = start_idx + pages_to_process

            # Создаем итератор с прогресс-баром, обрабатываем страницы лениво
            pages_range = range(start_idx, end_idx)
            pages_iter = tqdm(
                pages_range,
                total=len(pages_range),
                desc="Обработка страниц",
                unit="стр",
                dynamic_ncols=True
            )

            for page_idx in pages_iter:
                page = pdf.pages[page_idx]
                page_num = page_idx + 1

                # Извлекаем символы с информацией о шрифтах
                chars = page.chars

                # Группируем символы по строкам (по координате top)
                lines_dict = {}
                for char in chars:
                    top_key = round(char['top'], 1)
                    if top_key not in lines_dict:
                        lines_dict[top_key] = []
                    lines_dict[top_key].append(char)

                # Сортируем строки сверху вниз
                sorted_tops = sorted(lines_dict.keys())

                for top in sorted_tops:
                    line_chars = sorted(lines_dict[top], key=lambda c: c['x0'])
                    line_text = ''.join(c['text'] for c in line_chars).strip()

                    if not line_text:
                        continue

                    # Пропускаем строки, состоящие только из символов ударения
                    if is_only_accents(line_text):
                        continue

                    # Проверяем, есть ли в строке запятая (базовая эвристика)
                    comma_pos = line_text.find(',')
                    if comma_pos == -1:
                        continue

                    # Находим жирные сегменты в строке
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

                    if not bold_segments:
                        continue

                    word_raw = bold_segments[0].strip()
                    if not word_raw:
                        continue

                    # Убираем ударения из слова
                    word_clean = remove_accents(word_raw)

                    # Все, что после первого жирного сегмента
                    after_word = line_text.split(word_raw, 1)[-1].strip()

                    # Убираем запятую в начале если есть
                    if after_word.startswith(','):
                        after_word = after_word[1:].strip()

                    # Сохраняем forms как одну строку (весь оставшийся текст)
                    forms = [after_word] if after_word else []

                    entries.append({
                        'word': word_clean,
                        'forms': forms,
                        'full_line': line_text,
                        'page_num': page_num
                    })

                    # Проверка на лимит записей
                    if max_entries and len(entries) >= max_entries:
                        pages_iter.close()
                        return entries

                # Освобождаем память после обработки страницы
                del page
                if page_num % 100 == 0:
                    gc.collect()

    except FileNotFoundError:
        print(f"Ошибка: файл не найден: {pdf_path}")
        return []
    except Exception as e:
        print(f"Ошибка при обработке PDF: {e}")
        import traceback
        traceback.print_exc()
        return []

    return entries

def save_to_json(entries, output_path):
    """Сохраняет записи в JSON файл."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"Сохранено в JSON: {output_path} ({len(entries)} записей)")

def save_to_excel(entries, output_path):
    """Сохраняет записи в Excel файл."""
    data = []
    for entry in entries:
        data.append({
            'Слово': entry['word'],
            'Формы': ', '.join(entry['forms']),
            'Количество форм': len(entry['forms']),
            'Страница': entry.get('page_num', '')
        })

    df = pd.DataFrame(data)
    df.to_excel(output_path, index=False)
    print(f"Сохранено в Excel: {output_path} ({len(data)} строк)")

def main():
    base_dir = Path(__file__).parent
    pdf_path = base_dir / 'orfoepicheskij_slovar.pdf'

    if not pdf_path.exists():
        print(f"Ошибка: файл не найден: {pdf_path}")
        print(f"Убедитесь, что orfoepicheskij_slovar.pdf находится в папке tools/")
        return 1

    # Параметры для тестирования
    test_mode = False  # Полная конвертация
    max_pages = None   # Обрабатываем все страницы
    max_entries = None

    if test_mode:
        print("\n=== РЕЖИМ ТЕСТИРОВАНИЯ ===\n")
        print(f"Обрабатываем только первые {max_pages} страниц для проверки\n")
    else:
        print("\n=== ПОЛНАЯ КОНВЕРТАЦИЯ ===\n")

    # Извлекаем записи
    print("\n=== НАЧАЛО ИЗВЛЕЧЕНИЯ ===\n")
    entries = extract_dictionary(
        pdf_path,
        start_page=13,
        max_pages=max_pages,
        max_entries=max_entries
    )

    if not entries:
        print("Записи не найдены!")
        return 1

    # Показываем статистику
    print(f"\n=== СТАТИСТИКА ===")
    print(f"Всего извлечено записей: {len(entries)}")

    # Показываем примеры
    print(f"\nПервые {min(15, len(entries))} записей:")
    for i, entry in enumerate(entries[:15], 1):
        forms_display = entry['forms'][0] if entry['forms'] else ''
        # Ограничиваем длину для отображения
        if len(forms_display) > 60:
            forms_display = forms_display[:57] + '...'
        print(f"  {i:3}. {entry['word']:30} -> {forms_display}")

    # Сохраняем в JSON
    json_path = base_dir / 'orfoepicheskij_dictionary.json'
    save_to_json(entries, json_path)

    # Сохраняем в Excel
    excel_path = base_dir / 'orfoepicheskij_dictionary.xlsx'
    save_to_excel(entries, excel_path)

    print("\n=== ГОТОВО ===")
    return 0

if __name__ == '__main__':
    sys.exit(main())
