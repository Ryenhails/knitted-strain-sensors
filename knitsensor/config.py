"""Where the data and results are, and the constants of the test protocol (paper Section IV)."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------- folders
# Put (or symlink) the two input folders here; see README section 2.
TENSILE_DIR = REPO / 'data' / 'raw' / 'tensile_tests'
BENDING_DIR = REPO / 'data' / 'raw' / 'elbow_robot_tests'

RESULTS = REPO / 'results'
BLOCKS = RESULTS / 'blocks'              # step 1: metrics of every rate block
PREDICTIONS = RESULTS / 'predictions'    # step 3: joint-angle predictions
TABLES = RESULTS / 'tables'
FIGURES = RESULTS / 'figures'
REFERENCE = REPO / 'reference'           # what the paper printed, for step 5

# ---------------------------------------------------------------- samples
# A1 and B1 were run without the rest before the first reference block and
# were replaced by A4 and B4.
TENSILE_EXCLUDED = {'A1', 'B1'}

# ---------------------------------------------------------------- protocol
FS = 100.0                     # both rigs sample at 100 Hz
MEDIUM = 'B'                   # rates are labelled A slow, B medium, C fast

# tensile rig: the rate is recognised from the clamp step per sample (mm)
TENSILE_RATE_BY_STEP = {0.03: 'A', 0.07: 'B', 0.14: 'C'}
TENSILE_RATE_MM_S = {'A': 3.0, 'B': 6.95, 'C': 14.4}
TENSILE_DROP_CYCLES = 50       # of the 200 cycles of a rate block, the first 50 are discarded

# bending rig: the rate is recognised from the angle step per sample (degrees)
BENDING_RATE_BY_STEP = {0.10: 'A', 0.20: 'B', 0.40: 'C'}
BENDING_RATE_DEG_S = {'A': 8.3, 'B': 18.5, 'C': 39.5}
BENDING_DROP_CYCLES = 10       # of the 30 cycles of a rate block, the first 10 are discarded
STROKE_DEG = 150.0
STROKE_MM = 61.0               # robot calibration: 0 -> 150 deg lengthens the sample by 61 mm

# ---------------------------------------------------------------- statistics
N_BOOT = 10000
BOOT_SEED_RMSE = 42            # bootstrap over test windows (Table V)
BOOT_SEED_RHO = 11             # bootstrap over designs (Figs. 6 and 7)
