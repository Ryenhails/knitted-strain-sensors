"""Step 0 - check that data/raw/ holds exactly the input files the paper used.

Every file in data/manifest.csv (2 metadata files, 42 tensile and 28 bending
recordings) is compared by size and MD5 checksum.

    python scripts/0_check_data.py
"""
import csv
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # makes `knitsensor` importable
from knitsensor import config, data  # noqa: E402


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    folders = {'tensile_tests': config.TENSILE_DIR, 'elbow_robot_tests': config.BENDING_DIR}
    with open(config.REPO / 'data' / 'manifest.csv', newline='') as fh:
        manifest = list(csv.DictReader(fh))
    problems = 0
    for row in manifest:
        folder, rest = row['path'].split('/', 1)
        path = folders[folder] / rest
        if not path.exists():
            problem = 'missing'
        elif path.stat().st_size != int(row['bytes']) or md5(path) != row['md5']:
            problem = 'different content'
        else:
            continue
        print('  %-18s %s' % (problem, row['path']))
        problems += 1
    print('%d of %d input files are as expected' % (len(manifest) - problems, len(manifest)))
    if problems:
        sys.exit('Fix data/raw/ first (README section 2).')

    tensile, bending = data.tensile_recordings(), data.bending_recordings()
    print('tensile recordings analysed: %d' % len(tensile))
    print('bending recordings analysed: %d (%d new, %d tensile-tested)' % (
        len(bending), sum(r['history'] == 'new' for r in bending), sum(r['history'] != 'new' for r in bending)))


if __name__ == '__main__':
    main()
