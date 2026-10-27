"""The fourteen sensor designs: seven knit structures, each at two stitch sizes.

A design is identified by a letter A-N.  The letter is the first character of
every sample ID in the raw data (sample "C2" is the second specimen of design C).
Source: the fabrication record, confirmed 2026-09-07.

Two facts that are easy to get wrong:
  * Stitch size is not shared across structures.  Plain jersey and the
    conductive inlay were knitted at 10.5 and 11, the other five structures at
    10 and 10.5.  Only the smaller-vs-larger contrast inside a structure is
    defined (see STRUCTURES).
  * For the 2x1 rib the letters do not follow the stitch size: I is 10.5, J is 10.
"""

# letter: (structure, stitch size)
DESIGNS = {
    'A': ('Plain jersey', 10.5),
    'B': ('Plain jersey', 11.0),
    'C': ('1x1 rib', 10.0),
    'D': ('1x1 rib', 10.5),
    'E': ('Full cardigan', 10.0),
    'F': ('Full cardigan', 10.5),
    'G': ('Half cardigan', 10.0),
    'H': ('Half cardigan', 10.5),
    'I': ('2x1 rib', 10.5),
    'J': ('2x1 rib', 10.0),
    'K': ('Cond. inlay', 10.5),
    'L': ('Cond. inlay', 11.0),
    'M': ('Tuck rib', 10.0),
    'N': ('Tuck rib', 10.5),
}
LETTERS = 'ABCDEFGHIJKLMN'

# (structure, smaller stitch size, larger stitch size), in the order of the paper
STRUCTURES = [('Plain jersey', 'A', 'B'), ('1x1 rib', 'C', 'D'),
              ('Full cardigan', 'E', 'F'), ('Half cardigan', 'G', 'H'),
              ('2x1 rib', 'J', 'I'), ('Cond. inlay', 'K', 'L'),
              ('Tuck rib', 'M', 'N')]

# row order of Tables IV and V: structure by structure, smaller stitch size first
TABLE_ORDER = [d for _, lo, hi in STRUCTURES for d in (lo, hi)]


def structure(d):
    return DESIGNS[d][0]


def stitch(d):
    return DESIGNS[d][1]


def label(d):
    """'2x1 rib 10.5'."""
    return '%s %g' % DESIGNS[d]
