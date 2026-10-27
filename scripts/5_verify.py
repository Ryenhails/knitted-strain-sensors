"""Step 5 - compare the regenerated numbers with the numbers printed in the paper.

  Table IV and Table V   every printed cell, formatted as in the paper
  Figs. 6 and 7          rho and both interval ends of every point (within 0.002),
                         as read from the published figure PDFs
  Text                   every number quoted in the text (reference/paper_text_values.csv)

Rows of paper_text_values.csv with a `known_issue` are places where the paper's
text itself is imprecise; they are listed separately.  The full list goes to
results/verification_report.md.

    python scripts/5_verify.py
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # makes `knitsensor` importable
from knitsensor import config  # noqa: E402

checks = []   # (section, item, paper, regenerated, status, note)


def read(path):
    with open(path, newline='') as fh:
        return list(csv.DictReader(fh))


def check(section, item, paper, regenerated, ok, note=''):
    status = 'match' if ok else ('known paper issue' if note else 'differs')
    checks.append((section, item, str(paper), str(regenerated), status, note if not ok else ''))


def decimals(text):
    """Number of decimals of a printed value such as '1.23±0.05', '10.6 [10.3, 11.0]', '43%'."""
    number = text.split('±')[0].split('[')[0].strip().rstrip('%×')
    return len(number.split('.')[1]) if '.' in number else 0


def numbers():
    out = {}
    for name in ('numbers_section5.json', 'numbers_section6.json'):
        out.update(json.loads((config.RESULTS / name).read_text()))
    return out


def check_table4(num):
    regenerated = {r['design']: r for r in read(config.TABLES / 'table4_electromechanical.csv')}
    for paper in read(config.REFERENCE / 'paper_table4.csv'):
        for column, printed in paper.items():
            if column == 'design' or not printed:
                continue
            k = decimals(printed)
            if paper['design'] == 'between/within SD':
                value = '%.*f×' % (k, num['Table IV']['between_within_sd_ratio'][column.split('_')[1]])
            else:
                r = regenerated[paper['design']]
                value = '%.*f±%.*f' % (k, float(r[column + '_mean']), k, float(r[column + '_sd']))
            check('Table IV', '%s %s' % (paper['design'], column), printed, value, value == printed)


def check_table5():
    regenerated = {r['design']: r for r in read(config.TABLES / 'table5_joint_angle.csv')}
    median = lambda c: sorted(float(r[c]) for r in regenerated.values())[6:8]
    for paper in read(config.REFERENCE / 'paper_table5.csv'):
        d = paper['design']
        for column, printed in paper.items():
            if column == 'design' or not printed:
                continue
            if column == 'mlp_rmse_ci' and d != 'median':
                r = regenerated[d]
                value = '%.1f [%.1f, %.1f]' % (float(r['mlp_rmse']), float(r['mlp_rmse_ci_lo']), float(r['mlp_rmse_ci_hi']))
            else:
                c = 'mlp_rmse' if column == 'mlp_rmse_ci' else column
                v = sum(median(c)) / 2 if d == 'median' else float(regenerated[d][c])
                value = '%.*f' % (decimals(printed), v) + ('%' if printed.endswith('%') else '')
            check('Table V', '%s %s' % (d, column), printed, value, value == printed)


def check_figures():
    for figure, ours, theirs, keys in (('Fig. 6', 'fig6_cross_rig.csv', 'paper_fig6.csv', ('metric', 'pairing')),
                                       ('Fig. 7', 'fig7_rq2.csv', 'paper_fig7.csv', ('metric', 'estimator', 'pairing'))):
        regenerated = {tuple(r[k] for k in keys): r for r in read(config.TABLES / ours)}
        for paper in read(config.REFERENCE / theirs):
            key = tuple(paper[k] for k in keys)
            for c in ('rho', 'ci_lo', 'ci_hi'):
                value = float(regenerated[key][c])
                check(figure, '%s %s' % ('/'.join(key), c), paper[c], '%.3f' % value,
                      abs(value - float(paper[c])) <= 0.002)


def check_text(num):
    for ref in read(config.REFERENCE / 'paper_text_values.csv'):
        value = num
        for part in ref['key'].split('.'):
            value = value[int(part)] if isinstance(value, list) else value[part]
        printed, mode = ref['printed'], ref['mode']
        if mode == 'num':
            tol = float(ref['tol']) if ref['tol'] else 0.5 * 10 ** -decimals(printed) + 1e-9
            ok, shown = abs(float(value) - float(printed)) <= tol, '%.4g' % value
        elif mode == 'lt':
            ok, shown = float(value) < float(printed), '%.4g' % value
        elif mode == 'eq':
            ok, shown = str(value) == printed, value
        elif mode == 'set':
            ok, shown = set(value) == set(printed.split('|')), '|'.join(sorted(value))
        else:                                                    # 'count'
            ok, shown = len(value) == int(printed), '%d: %s' % (len(value), '; '.join(value))
        check('Text', '%s (%s)' % (ref['id'], ref['location']), printed, shown, ok, ref['known_issue'])


def main():
    num = numbers()
    check_table4(num)
    check_table5()
    check_figures()
    check_text(num)

    sections = list(dict.fromkeys(c[0] for c in checks))
    summary = ['| section | checks | match | known paper issue | differs |', '|---|---|---|---|---|']
    for sec in sections:
        st = [c[4] for c in checks if c[0] == sec]
        summary.append('| %s | %d | %d | %d | %d |' % (sec, len(st), st.count('match'),
                                                     st.count('known paper issue'), st.count('differs')))
    report = ['# Regenerated numbers compared with the paper', ''] + summary
    for status in ('differs', 'known paper issue'):
        rows = [c for c in checks if c[4] == status]
        if rows:
            report += ['', '## ' + status, '', '| section | item | paper | regenerated | note |', '|---|---|---|---|---|']
            report += ['| %s | %s | %s | %s | %s |' % (c[0], c[1], c[2], c[3], c[5]) for c in rows]
    report += ['', '## All checks', '', '| section | item | paper | regenerated | status |', '|---|---|---|---|---|']
    report += ['| %s | %s | %s | %s | %s |' % c[:5] for c in checks]
    path = config.RESULTS / 'verification_report.md'
    path.write_text('\n'.join(report) + '\n')
    print('\n'.join(summary))
    print('details: %s' % path)


if __name__ == '__main__':
    main()
