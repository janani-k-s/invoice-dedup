import os
import json
import glob
import csv
from datetime import datetime
from django.conf import settings

# Cache so we don't re-read all CSVs on every single upload
_ground_truth_cache = None


def _load_all_ground_truth():
    """
    Recursively finds every CSV under data/, reads it, and builds
    a dictionary mapping filename -> parsed JSON fields.
    Runs once, then caches the result in memory.
    """
    global _ground_truth_cache
    if _ground_truth_cache is not None:
        return _ground_truth_cache

    lookup = {}
    data_dir = os.path.join(settings.BASE_DIR, 'data')
    csv_paths = glob.glob(os.path.join(data_dir, '**', '*.csv'), recursive=True)

    for csv_path in csv_paths:
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                filename = row.get('File Name', '').strip()
                json_raw = row.get('Json Data', '')
                if not filename or not json_raw:
                    continue
                try:
                    parsed = json.loads(json_raw)
                    lookup[filename] = parsed
                except json.JSONDecodeError:
                    continue  # skip rows with broken JSON rather than crash

    _ground_truth_cache = lookup
    return lookup


def get_ground_truth(filename):
    """
    Given an image filename (e.g. 'batch1-0494.jpg'), returns a dict
    of extracted invoice fields, or None if not found in any CSV.
    """
    lookup = _load_all_ground_truth()
    data = lookup.get(filename)
    if not data:
        return None

    invoice = data.get('invoice', {})
    subtotal = data.get('subtotal', {})

    # Convert date format "02/23/2021" (MM/DD/YYYY) -> Django DateField format
    date_str = invoice.get('invoice_date', '')
    parsed_date = None
    if date_str:
        try:
            parsed_date = datetime.strptime(date_str, '%m/%d/%Y').date()
        except ValueError:
            parsed_date = None

    # total_amount: use subtotal.total, fall back to 0 if missing/blank
    total_str = subtotal.get('total', '')
    try:
        total_amount = float(total_str) if total_str else 0
    except ValueError:
        total_amount = 0

    return {
        'invoice_number': invoice.get('invoice_number', ''),
        'client_name': invoice.get('client_name', ''),
        'seller_name': invoice.get('seller_name', ''),
        'invoice_date': parsed_date,
        'total_amount': total_amount,
    }