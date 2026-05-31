#!/usr/bin/env python3
"""Parse every cached camadetail page into a tidy relational dataset. Stdlib only.

Outputs:
  warren_properties.csv  - one row per parcel (owner, location, sales, values)
  warren_buildings.csv   - one row per building sub-record (long format)
  warren_land.csv        - one row per land sub-record (long format)
  warren_properties.json - full nested record per parcel (everything)
"""
import os, json, csv, glob, re
from parse_detail import parse

HERE = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(HERE, 'html')
SUMMARY = os.path.join(HERE, '_all_records_summary.html')
NEMRC = "https://nemrc.info/web_data/vtwarr/camadetailT.php?prop={}"

# parcel-level sections that go into the main one-row-per-parcel table
PARCEL_SECTIONS = ('Owner Information', 'Parcel Information',
                   'Sales Information', 'Parcel Value Information')


def load_summary():
    """The all-records results page has columns: View | ParcelID | Owner | St# | Street."""
    out = {}
    if not os.path.exists(SUMMARY):
        return out
    html = open(SUMMARY, encoding='utf-8', errors='replace').read()
    row_re = re.compile(
        r"camadetailT\.php\?prop=([0-9A-Za-z]+)'>\s*<b>View</b>\s*</a></td>"
        r"<td>[^<]*</td><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td>", re.S)
    strip = lambda s: ' '.join(re.sub(r'<[^>]+>', ' ', s).replace('&amp;', '&').split())
    for pid, owner, num, street in row_re.findall(html):
        num, street = strip(num), strip(street)
        loc = (num + ' ' + street).strip() if (num and num != '0') else street
        out[pid] = {'owner': strip(owner), 'location': loc}
    return out


def section_of(key):
    sec, lab = key.split(' / ', 1)
    base = re.sub(r' #\d+$', '', sec)
    m = re.search(r' #(\d+)$', sec)
    idx = int(m.group(1)) if m else 1
    return base, idx, lab


summary = load_summary()
records, full = [], []
buildings, lands = [], []
no_data = []

for f in sorted(glob.glob(os.path.join(HTML_DIR, '*.html'))):
    pid = os.path.splitext(os.path.basename(f))[0]
    raw = open(f, encoding='utf-8', errors='replace').read()
    if len(raw) < 200:            # retired/empty parcel pages (~27 bytes)
        no_data.append(pid)
    fields = parse(raw)

    full.append({'parcel_id': pid, 'nemrc_url': NEMRC.format(pid), **fields})

    s = summary.get(pid, {})
    main = {
        'parcel_id': pid,
        'owner': s.get('owner', ''),
        'location': s.get('location', ''),
        'owner_mailing': '',      # full "name | co-owner | street | city, st zip"
        'nemrc_url': NEMRC.format(pid),
    }
    nb = nl = 0
    for k, v in fields.items():
        if ' / ' not in k:
            continue
        base, idx, lab = section_of(k)
        if base in PARCEL_SECTIONS:
            if lab == 'Owner':
                main['owner_mailing'] = v
            elif lab == 'Location':
                main.setdefault('location_detail', v)
            else:
                main[lab] = v
        elif base == 'BUILDING':
            nb = max(nb, idx)
        elif base == 'LAND':
            nl = max(nl, idx)

    # fallbacks from detail page when the summary lacked the parcel
    if not main['owner'] and main['owner_mailing']:
        main['owner'] = main['owner_mailing'].split(' | ')[0]
    if not main['location']:
        main['location'] = main.get('location_detail', '')

    bmap, lmap = {}, {}
    for k, v in fields.items():
        if ' / ' not in k:
            continue
        base, idx, lab = section_of(k)
        if base == 'BUILDING':
            bmap.setdefault(idx, {'parcel_id': pid, 'building_no': idx})[lab] = v
        elif base == 'LAND':
            lmap.setdefault(idx, {'parcel_id': pid, 'land_no': idx})[lab] = v
    buildings.extend(bmap[i] for i in sorted(bmap))
    lands.extend(lmap[i] for i in sorted(lmap))

    main['num_buildings'] = nb
    main['num_land_records'] = nl
    main.pop('location_detail', None)
    records.append(main)


def write_csv(path, rows, lead):
    cols = list(lead)
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    return len(cols)


with open(os.path.join(HERE, 'warren_properties.json'), 'w', encoding='utf-8') as fh:
    json.dump(full, fh, indent=2, ensure_ascii=False)

c1 = write_csv(os.path.join(HERE, 'warren_properties.csv'), records,
               ['parcel_id', 'owner', 'location', 'owner_mailing', 'nemrc_url'])
c2 = write_csv(os.path.join(HERE, 'warren_buildings.csv'), buildings,
               ['parcel_id', 'building_no'])
c3 = write_csv(os.path.join(HERE, 'warren_land.csv'), lands,
               ['parcel_id', 'land_no'])

print(f"parcels:            {len(records)} rows, {c1} cols")
print(f"building records:   {len(buildings)} rows, {c2} cols")
print(f"land records:       {len(lands)} rows, {c3} cols")
print(f"empty/retired pages:{len(no_data)} -> {no_data}")
