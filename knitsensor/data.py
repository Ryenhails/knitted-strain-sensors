"""Reading the raw recordings and the metadata (paper Section IV-B).

A recording is one CSV file: one sample measured in one session, 100 rows per
second, four columns:

  tensile   Segment, Cycle, Distance(mm), Port <n> resistance(ohm)
  bending   Segment, Cycle, Angle(deg),   Resistance_A<n>(ohm)

The metadata files are ';'-separated with decimal commas.
"""
import csv

import numpy as np

from . import config
from .designs import LETTERS


def read_recording(path):
    """Return the four columns as arrays: segment, cycle, position, resistance.

    Rows that are short or do not parse are skipped.  A negative resistance is
    the logger's mark for an invalid reading and becomes NaN.
    """
    segment, cycle, position, resistance = [], [], [], []
    with open(path, newline='', encoding='utf-8') as fh:
        reader = csv.reader(fh)
        next(reader)                                   # header
        for row in reader:
            if len(row) < 4:
                continue
            try:
                segment.append(int(row[0]))
                cycle.append(int(row[1]))
                position.append(float(row[2]))
                resistance.append(float(row[3]))
            except ValueError:
                continue
    resistance = np.asarray(resistance, float)
    resistance[resistance < 0] = np.nan
    return np.asarray(segment), np.asarray(cycle), np.asarray(position, float), resistance


def read_metadata(path):
    with open(path, newline='', encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh, delimiter=';'))


def tensile_recordings():
    """The 42 tensile recordings of the paper, as a list of dicts.

    Keys: path, sample (e.g. 'C2'), design ('C'), L0 (mm, length before the test).
    """
    present = {p.name: p for p in (config.TENSILE_DIR / 'data_raw').glob('*.csv')}
    out = []
    for row in read_metadata(config.TENSILE_DIR / 'Metadata.csv'):
        name, sample = row['Measurement_data_file'], row['Sample_ID']
        if name in present and sample[0] in LETTERS and sample not in config.TENSILE_EXCLUDED:
            out.append(dict(path=present[name], sample=sample, design=sample[0],
                            L0=float(row['Length_before (mm)'])))
    return sorted(out, key=lambda r: r['path'].name)


def bending_recordings():
    """The 28 bending recordings of the paper, as a list of dicts.

    Keys as for tensile_recordings(), plus history: 'new' for the sample that
    was never tensile-tested (it has an extra 'preconditioning only' row in the
    metadata) and 'tensile-tested' for the other sample of the design.
    """
    present = {p.name: p for p in (config.BENDING_DIR / 'data_raw').glob('*.csv')}
    rows = read_metadata(config.BENDING_DIR / 'Metadata_elbow.csv')
    new = {r['Sample_ID'] for r in rows if 'preconditioning' in r['Rate order'] and not r['Elbow_data_file']}
    out = []
    for row in rows:
        name, sample = row['Elbow_data_file'], row['Sample_ID']
        if name in present:
            out.append(dict(path=present[name], sample=sample, design=sample[0],
                            L0=float(row['Length_before (mm)']),
                            history='new' if sample in new else 'tensile-tested'))
    return sorted(out, key=lambda r: r['path'].name)


def room_conditions():
    """Temperature and humidity at the start and end of every analysed session:
    the 42 tensile sessions and all rows of the bending metadata (28 sessions
    and the 14 preconditioning runs).  Returns (temperatures, humidities)."""
    names = {r['path'].name for r in tensile_recordings()}
    rows = [r for r in read_metadata(config.TENSILE_DIR / 'Metadata.csv') if r['Measurement_data_file'] in names]
    rows += read_metadata(config.BENDING_DIR / 'Metadata_elbow.csv')

    def number(text):
        text = text.strip().replace(',', '.')
        return float(text) if text else np.nan

    temperature = [number(r[k]) for r in rows for k in ('Temperature_before (°C)', 'Temperature_after (°C)')]
    humidity = [number(r[k]) for r in rows for k in ('Humidity_before (%)', 'Humidity_after (%)')]
    return np.array(temperature), np.array(humidity)
