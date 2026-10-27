"""Common look of the paper figures: Times-like serif, thin grey axes, print size."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from . import config  # noqa: E402

SMALL, LARGE = '#1c5cab', '#d95926'      # smaller / larger stitch size
INK, GREY, LIGHT = '0.07', '0.55', '0.86'
LABELS = {'R0': '$R_0$', 'GF': 'gauge factor', 'WR': 'working range', 'LR': 'linear range',
          'H': 'hysteresis', 'stab': 'cyclic stability'}


def paper_style():
    available = {f.name for f in font_manager.fontManager.ttflist}
    serif = [f for f in ('TeX Gyre Termes', 'Times New Roman', 'Nimbus Roman', 'STIXGeneral') if f in available]
    plt.rcParams.update({
        'font.family': 'serif', 'font.serif': serif + ['DejaVu Serif'], 'mathtext.fontset': 'stix',
        'font.size': 7, 'axes.titlesize': 7.5, 'axes.labelsize': 7,
        'xtick.labelsize': 6.5, 'ytick.labelsize': 6.5,
        'axes.edgecolor': '0.33', 'axes.linewidth': 0.5,
        'xtick.color': '0.33', 'ytick.color': '0.33', 'xtick.labelcolor': '0.3', 'ytick.labelcolor': '0.3',
        'xtick.major.width': 0.5, 'ytick.major.width': 0.5,
        'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42})


def save(fig, name):
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    for ext in ('pdf', 'png'):
        path = config.FIGURES / ('%s.%s' % (name, ext))
        fig.savefig(path, dpi=300, bbox_inches='tight')
        print('  wrote', path)
    plt.close(fig)
