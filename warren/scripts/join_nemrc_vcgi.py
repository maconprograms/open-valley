#!/usr/bin/env python3
"""Join the NEMRC assessment table with the VCGI GIS table.

Primary key: cleaned PARCID (digits/letters only) == NEMRC parcel_id  (~97%).
Fallback key: SPAN, for the few NEMRC rows whose id isn't in VCGI PARCID.

Produces warren_joined.csv: every NEMRC property (left join) + selected VCGI
columns (grand-list values, E911 address) + a WGS84 centroid (lon/lat) computed
from the matched parcel polygon. Full geometry stays in warren_parcels.geojson.
"""
import os, csv, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
VCGI_KEEP = ['MAPID', 'PARCID', 'OWNER1', 'OWNER2', 'E911ADDR', 'LOCAPROP',
             'ACRESGL', 'CAT', 'REAL_FLV', 'LAND_LV', 'IMPRV_LV',
             'HSITEVAL', 'DESCPROP']


def clean(s):
    return re.sub(r'[^0-9A-Za-z]', '', (s or ''))


def centroid(geom):
    if not geom:
        return None
    pts = []
    def walk(x):
        if (isinstance(x, list) and len(x) == 2
                and all(isinstance(v, (int, float)) for v in x)):
            pts.append(x)
        elif isinstance(x, list):
            for y in x:
                walk(y)
    walk(geom.get('coordinates') or [])
    if not pts:
        return None
    return (round(sum(p[0] for p in pts) / len(pts), 6),
            round(sum(p[1] for p in pts) / len(pts), 6))


def main():
    # index VCGI by cleaned PARCID and by SPAN; also keep centroid per feature
    by_parcid, by_span = {}, {}
    fc = json.load(open(os.path.join(HERE, 'warren_parcels.geojson')))
    for f in fc.get('features', []):
        p = f.get('properties') or {}
        rec = dict(p)
        rec['_centroid'] = centroid(f.get('geometry'))
        pc = clean(p.get('PARCID'))
        if pc:
            by_parcid.setdefault(pc, rec)
        sp = (p.get('SPAN') or '').strip()
        if sp:
            by_span.setdefault(sp, rec)

    nem = list(csv.DictReader(open(os.path.join(HERE, 'warren_properties.csv'))))
    out_cols = list(nem[0].keys()) + ['gis_match', 'gis_lon', 'gis_lat'] + \
        ['gis_' + c for c in VCGI_KEEP]

    n_parcid = n_span = n_none = 0
    with open(os.path.join(HERE, 'warren_joined.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=out_cols, extrasaction='ignore')
        w.writeheader()
        for r in nem:
            row = dict(r)
            g = by_parcid.get(clean(r['parcel_id']))
            how = 'parcid'
            if not g:
                sp = (r.get('SPAN') or '').strip()
                g = by_span.get(sp) if sp else None
                how = 'span' if g else 'none'
            if g:
                if how == 'parcid':
                    n_parcid += 1
                else:
                    n_span += 1
                row['gis_match'] = how
                for c in VCGI_KEEP:
                    row['gis_' + c] = g.get(c, '')
                c = g.get('_centroid')
                if c:
                    row['gis_lon'], row['gis_lat'] = c
            else:
                n_none += 1
                row['gis_match'] = 'none'
            w.writerow(row)

    print(f"NEMRC rows:        {len(nem)}")
    print(f"matched via PARCID: {n_parcid}")
    print(f"matched via SPAN:    {n_span}")
    print(f"no GIS match:        {n_none}")
    print(f"total matched:       {n_parcid + n_span} "
          f"({100*(n_parcid+n_span)//len(nem)}%)")
    print(f"columns:             {len(out_cols)}")


if __name__ == '__main__':
    main()
