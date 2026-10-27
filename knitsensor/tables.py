"""Small helpers for writing results: CSV and JSON files, mean and SD."""
import csv
import json

import numpy as np


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, 'w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, restval='')
        writer.writeheader()
        writer.writerows(rows)
    print('  wrote', path)


def read_csv(path):
    """Rows as dicts; every value that looks like a number becomes a float."""
    def value(v):
        try:
            return float(v) if v != '' else np.nan
        except ValueError:
            return v
    with open(path, newline='') as fh:
        return [{k: value(v) for k, v in row.items()} for row in csv.DictReader(fh)]


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, default=lambda x: x.item()) + '\n')  # .item(): numpy -> Python number
    print('  wrote', path)


def mean_sd(values):
    """Mean and sample SD (ddof=1) of the finite values."""
    v = np.array([x for x in values if np.isfinite(x)], float)
    return float(v.mean()), float(v.std(ddof=1)) if len(v) > 1 else 0.0
