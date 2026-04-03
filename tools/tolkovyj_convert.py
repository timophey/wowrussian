#!/usr/bin/env python3
"""
Конвертер толкового словаря с поддержкой многоколоночной верстки и межстраничных продолжений.
Оптимизированное потребление памяти.
"""

import pdfplumber
import json
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import sys
import gc
import re

def remove_accents(text):
    return text.replace('\u0301', '').replace('́', '')

def clean_word(word):
    word = remove_accents(word)
    return re.sub(r'[^А-Яа-я\-]', '', word).strip()

def is_only_accents(text):
    s = text.strip()
    if not s: return False
    return all(c in '́\u0301' for c in s)

def cluster_chars(chars, threshold=40):
    if not chars: return []
    sc = sorted(chars, key=lambda c: c['x0'])
    clusters = []
    cur = [sc[0]]
    for i in range(1, len(sc)):
        if sc[i]['x0'] - sc[i-1]['x0'] > threshold:
            clusters.append(cur)
            cur = [sc[i]]
        else:
            cur.append(sc[i])
    if cur: clusters.append(cur)
    return clusters

def is_word_start(cluster, font='CIDFont+F2'):
    for c in cluster:
        if c.get('fontname') == font:
            t = c['text']
            if t.isalpha() and t.isupper():
                return True
            return False
    return False

def extract_word(cluster, font='CIDFont+F2'):
    letters = []
    found = False
    for c in cluster:
        if c.get('fontname') == font:
            t = c['text']
            if not found:
                if t.isalpha() and t.isupper():
                    found = True
                    letters.append(t)
            else:
                letters.append(t)
        elif found:
            break
    if not found: return None
    w = clean_word(''.join(letters)).rstrip(',.')
    return w if w else None

def extract_forms(cluster):
    t = ''.join(c['text'] for c in cluster).strip()
    p = t.find(',')
    return t[p+1:].strip() if p != -1 else ''

def get_total_pages(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)

def process_pdf(pdf_path, start_page=1, max_pages=None):
    entries = []
    font = 'CIDFont+F2'
    last_by_col = {}
    
    total_pages = get_total_pages(pdf_path)
    pages_to = total_pages - start_page + 1
    if max_pages:
        pages_to = min(pages_to, max_pages)
        total_pages = start_page + pages_to - 1
    
    for page_idx in tqdm(range(start_page - 1, total_pages), desc="Страницы", unit="стр", dynamic_ncols=True):
        pnum = page_idx + 1
        
        # Открываем только одну страницу
        with pdfplumber.open(pdf_path, pages=[pnum]) as pdf:
            if not pdf.pages:
                break
            page = pdf.pages[0]
            chars = page.chars
        
        # Группируем по top
        lines_dict = {}
        for ch in chars:
            top = round(ch['top'], 1)
            lines_dict.setdefault(top, []).append(ch)
        
        sorted_tops = sorted(lines_dict.keys())
        
        # Собираем кластеры
        items = []
        for top in sorted_tops:
            clusters = cluster_chars(lines_dict[top], threshold=40)
            for idx, cl in enumerate(clusters):
                txt = ''.join(c['text'] for c in cl).strip()
                if not txt or is_only_accents(txt):
                    continue
                is_start = is_word_start(cl, font)
                x0_center = sum(c['x0'] for c in cl) / len(cl)
                items.append({
                    'top': top,
                    'col_id': idx,
                    'x0': x0_center,
                    'cluster': cl,
                    'text': txt,
                    'is_start': is_start,
                    'page': pnum
                })
        
        # Сортировка
        items.sort(key=lambda x: (x['top'], x['x0']))
        
        # Обработка
        i = 0
        while i < len(items):
            it = items[i]
            cid = it['col_id']
            
            if cid in last_by_col and not it['is_start']:
                last = last_by_col[cid]
                cont = it['text']
                if last['forms']:
                    last['forms'][0] += ' ' + cont
                else:
                    last['forms'] = [cont]
                i += 1
                continue
            
            if it['is_start']:
                word = extract_word(it['cluster'], font)
                if not word:
                    i += 1
                    continue
                forms_parts = []
                frm = extract_forms(it['cluster'])
                if frm:
                    forms_parts.append(frm)
                j = i + 1
                while j < len(items):
                    nxt = items[j]
                    if nxt['col_id'] != cid or nxt['is_start']:
                        break
                    forms_parts.append(nxt['text'])
                    j += 1
                forms = [' '.join(forms_parts).strip()] if forms_parts else []
                entry = {
                    'word': word,
                    'forms': forms,
                    'full_line': it['text'],
                    'page_num': pnum
                }
                entries.append(entry)
                last_by_col[cid] = entry
                i = j
            else:
                i += 1
        
        # Принудительная сборка мусора
        del page, chars, items
        gc.collect()
    
    return entries

def main():
    base = Path(__file__).parent
    pdf_files = [
        base / 'tolkovyj_slovar_chast1_A-N.pdf',
        base / 'tolkovyj_slovar_chast2_O-Ja.pdf'
    ]
    for f in pdf_files:
        if not f.exists():
            print(f'Файл не найден: {f}')
            return 1
    
    test = False  # Изменить на False для полной конвертации
    max_pages = None if test else None
    
    if test:
        print("\n=== ТЕСТ ===\n")
    else:
        print("\n=== ПОЛНЫЙ ===\n")
    
    all_entries = []
    for fp in pdf_files:
        print(f"\nОбработка: {fp.name}")
        ents = process_pdf(fp, start_page=1, max_pages=max_pages)
        print(f"Извлечено: {len(ents)} записей")
        all_entries.extend(ents)
        if ents:
            print("Примеры:")
            for i, e in enumerate(ents[:5], 1):
                frm = e['forms'][0][:60] if e['forms'] else ''
                print(f"  {i}. {e['word']:25} -> {frm}...")
    
    if not all_entries:
        print("\nНичего не извлечено!")
        return 1
    
    print(f"\nВСЕГО: {len(all_entries)} записей, уникальных слов: {len(set(e['word'] for e in all_entries))}")
    
    # Сохранение
    base_dir = Path(__file__).parent
    jpath = base_dir / 'tolkovyj_dictionary.json'
    with open(jpath, 'w', encoding='utf-8') as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)
    print(f"JSON: {jpath}")
    
    xpath = base_dir / 'tolkovyj_dictionary.xlsx'
    df = pd.DataFrame([{
        'Слово': e['word'],
        'Формы': ', '.join(e['forms']),
        'Количество форм': len(e['forms']),
        'Страница': e['page_num']
    } for e in all_entries])
    df.to_excel(xpath, index=False)
    print(f"Excel: {xpath}")
    
    print("\n=== Готово ===")
    return 0

if __name__ == '__main__':
    sys.exit(main())
