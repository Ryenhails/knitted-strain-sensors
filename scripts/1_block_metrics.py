"""Step 1 - paper Section IV-C (analysis protocol): metrics of every rate block.

Reads the 42 tensile and 28 bending recordings and writes to results/blocks/:

  tensile_blocks.csv    42 samples x 3 rate blocks: R0, WR, LR, GF, H, cyclic stability, ...
  tensile_settling.csv  42 samples x 4 blocks: change of R0 and GF inside the block
  bending_blocks.csv    28 samples x 3 rate blocks (strain axis)
  curves.csv            averaged loading curve of the medium-rate block of every sample

    python scripts/1_block_metrics.py            (about 5 CPU-minutes)
    python scripts/1_block_metrics.py --jobs 8   (run 8 recordings in parallel)
"""
import argparse
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # makes `knitsensor` importable
from knitsensor import blocks, config, data  # noqa: E402
from knitsensor.tables import write_csv  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--jobs', type=int, default=4, help='recordings processed in parallel (default 4)')
    args = parser.parse_args()

    tensile, bending = data.tensile_recordings(), data.bending_recordings()
    print('analysing %d tensile and %d bending recordings ...' % (len(tensile), len(bending)))
    with Pool(args.jobs) as pool:
        tensile_results = pool.map(blocks.analyse_tensile, tensile)
        bending_results = pool.map(blocks.analyse_bending, bending)

    write_csv(config.BLOCKS / 'tensile_blocks.csv', [b for r in tensile_results for b in r['blocks']])
    write_csv(config.BLOCKS / 'tensile_settling.csv', [s for r in tensile_results for s in r['settling']])
    write_csv(config.BLOCKS / 'bending_blocks.csv', [b for r in bending_results for b in r['blocks']])

    curves = []
    for rig, recs, results in (('tensile', tensile, tensile_results), ('bending', bending, bending_results)):
        for rec, res in zip(recs, results):
            grid, dRR0 = res['curve']
            curves += [dict(rig=rig, sample=rec['sample'], history=rec.get('history', ''),
                            strain='%.1f' % g, dRR0=v) for g, v in zip(grid, dRR0) if v == v]
    write_csv(config.BLOCKS / 'curves.csv', curves)


if __name__ == '__main__':
    main()
