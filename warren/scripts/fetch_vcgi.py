#!/usr/bin/env python3
"""Download Warren VT parcels (geometry + grand-list attributes) from the public
VCGI statewide standardized-parcels ArcGIS service. Stdlib only.

VCGI carries SPAN, the same key as the NEMRC data, so the two join cleanly.

Outputs:
  warren_parcels.geojson    - parcel polygons (WGS84) + all 56 VCGI attributes
  warren_parcels_gis.csv    - attribute table (no geometry), joinable on SPAN
"""
import os, json, csv, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SERVICE = ("https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services/"
           "FS_VCGI_OPENDATA_Cadastral_VTPARCELS_poly_standardized_parcels_SP_v1/"
           "FeatureServer/0/query")
WHERE = "TOWN='WARREN'"
PAGE = 2000


def get(params):
    url = SERVICE + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(3)


def main():
    feats = []
    offset = 0
    while True:
        j = get({'where': WHERE, 'outFields': '*', 'returnGeometry': 'true',
                 'outSR': '4326', 'f': 'geojson',
                 'resultOffset': offset, 'resultRecordCount': PAGE})
        batch = j.get('features', [])
        feats.extend(batch)
        print(f"  +{len(batch)} (total {len(feats)})")
        if len(batch) < PAGE:
            break
        offset += PAGE

    fc = {'type': 'FeatureCollection', 'features': feats}
    with open(os.path.join(HERE, 'warren_parcels.geojson'), 'w') as fh:
        json.dump(fc, fh)

    # attribute columns from first feature, SPAN first for easy joining
    cols = list((feats[0].get('properties') or {}).keys()) if feats else []
    for lead in ('SPAN',):
        if lead in cols:
            cols.remove(lead)
            cols.insert(0, lead)
    with open(os.path.join(HERE, 'warren_parcels_gis.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for f in feats:
            w.writerow(f.get('properties') or {})

    geom_ok = sum(1 for f in feats if f.get('geometry'))
    spans = sum(1 for f in feats if (f.get('properties') or {}).get('SPAN'))
    print("\n=== SUMMARY ===")
    print(f"parcels:        {len(feats)} (with geometry: {geom_ok})")
    print(f"with SPAN:      {spans}")
    print(f"attribute cols: {len(cols)}")


if __name__ == '__main__':
    main()
