#!/usr/bin/env python3
"""
Sanitize the modified demo dataset (ostereo_demo_v1.json)

1. Remove error log text from field values
2. Blank header-like values (values that equal field names)
3. Preserve row structure (don't delete rows)
"""

import json
import sys
from pathlib import Path

ERROR_PATTERNS = [
    '//[AUTO] Contract failed to load',
    'Reason: timeout',
    'Suggestion: Request timed out',
    '[AUTO] Contract failed',
]

def load_dataset(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_dataset(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def collect_all_headers(data):
    headers = set()
    for sheet_data in data.get('sheets', {}).values():
        headers.update(sheet_data.get('headers', []))
    return headers

def contains_error_pattern(value):
    if not isinstance(value, str):
        return False
    for pattern in ERROR_PATTERNS:
        if pattern in value:
            return True
    return False

def sanitize_dataset(data):
    all_headers = collect_all_headers(data)
    
    stats = {
        'error_patterns_removed': 0,
        'header_values_blanked': 0,
        'sheets_processed': 0,
        'rows_processed': 0,
    }
    
    for sheet_name, sheet_data in data.get('sheets', {}).items():
        stats['sheets_processed'] += 1
        rows = sheet_data.get('rows', [])
        
        for i, row in enumerate(rows):
            if not row:
                continue
            stats['rows_processed'] += 1
            
            for key in list(row.keys()):
                val = row[key]
                
                if contains_error_pattern(val):
                    row[key] = ''
                    stats['error_patterns_removed'] += 1
                elif isinstance(val, str) and val in all_headers:
                    row[key] = ''
                    stats['header_values_blanked'] += 1
    
    return data, stats

def main():
    input_path = Path('examples/datasets/ostereo_demo_v1.json')
    
    if not input_path.exists():
        print(f'Error: {input_path} not found')
        sys.exit(1)
    
    print(f'Loading dataset from {input_path}...')
    data = load_dataset(input_path)
    
    print('Sanitizing dataset...')
    data, stats = sanitize_dataset(data)
    
    print(f'Saving sanitized dataset to {input_path}...')
    save_dataset(data, input_path)
    
    print('\nSanitization complete:')
    print(f'  - Sheets processed: {stats["sheets_processed"]}')
    print(f'  - Rows processed: {stats["rows_processed"]}')
    print(f'  - Error patterns removed: {stats["error_patterns_removed"]}')
    print(f'  - Header values blanked: {stats["header_values_blanked"]}')

if __name__ == '__main__':
    main()
