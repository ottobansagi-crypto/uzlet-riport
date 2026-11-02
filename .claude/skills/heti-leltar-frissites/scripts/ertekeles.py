# -*- coding: utf-8 -*-
"""A havi szöveges értékelés tényei a riport jelenlegi állapotából (data.json + TREND2026).

    python3 ertekeles.py [--root <repó>]

Nem szöveget ír, hanem kigyűjti, amire a szöveg épül: a hónap helye az évben, a 20 ezer feletti
hiánnyal záró üzletek száma havonta, a fő hiány-kategória, a tartósan hiányos üzletek alakulása,
az előjelet váltók és a több üzletben ismétlődő minták (gombóc-méretek, víz, papíráru, pasta).
A szöveget ezekből kell megírni, nem becslésből."""
import sys
sys.dont_write_bytecode = True   # ne keletkezzen __pycache__ a repóban
import argparse, io, json, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from szabalyok import HONAPOK, KATEGORIAK, ft

KUSZOB = -20000
KAT_NEV = {'gomboc': 'gombóc', 'ital': 'ital', 'desseg': 'édesség', 'doboz': 'papíráru',
           'ajandek': 'ajándéktárgy', 'snack': 'snack'}
KULCS_NEV = {v[0]: k for k, v in HONAPOK.items()}          # 'okt' -> 'október'


def honapnev(honap):
    return honap.split()[-1].lower()                         # '2026. október' -> 'október'


def trend_sorok(html):
    b = html[html.index('const TREND2026 = ['):]
    b = b[:b.index('];')]
    sorok = {}
    for m in re.finditer(r'\{nev:"([^"]+)"([^}]*)\}', b):
        sorok[m.group(1)] = {k: (None if v == 'null' else int(v))
                            for k, v in re.findall(r'(\w+):(-?\d+|null)', m.group(2)) if k in KULCS_NEV}
    return sorok


def elojel(v):
    return ('+' if v > 0 else '') + ft(v)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', default='.')
    a = ap.parse_args()
    with io.open(os.path.join(a.root, 'data.json'), encoding='utf-8') as f:
        d = json.load(f)
    with io.open(os.path.join(a.root, 'uzlet-riport.html'), encoding='utf-8') as f:
        sorok = trend_sorok(f.read())

    akt_nev = honapnev(d['meta']['honap'])
    akt_kulcs = HONAPOK[akt_nev][0]
    reszido = bool(d['meta'].get('reszido'))
    us = d['uzletek']
    aktiv = [u['nev'] for u in us]
    kulcsok = [k for k in (v[0] for v in HONAPOK.values()) if any(k in r for r in sorok.values())]
    lezart = [k for k in kulcsok if not (reszido and k == akt_kulcs)]
    elozo_kulcs = kulcsok[kulcsok.index(akt_kulcs) - 1] if kulcsok.index(akt_kulcs) > 0 else None

    print(f"Hónap: {d['meta']['honap']}{' (részeredmény)' if reszido else ''}")

    # 1. A hónap helye az évben
    havi = {k: sum((r.get(k) or 0) for r in sorok.values()) for k in kulcsok}
    print('Hálózat havonta: ' + ', '.join(f'{KULCS_NEV[k]} {elojel(havi[k])}' for k in kulcsok))
    if lezart:
        legjobb = max(lezart, key=lambda k: havi[k])
        legrosszabb = min(lezart, key=lambda k: havi[k])
        print(f'Az év legjobb hónapja eddig: {KULCS_NEV[legjobb]}; a legrosszabb: {KULCS_NEV[legrosszabb]}.')

    # 2. 20 ezer feletti hiánnyal záró üzletek és levonások havonta
    honapok = d['elozo_honapok'] + [{'meta': d['meta'], 'uzletek': us, 'levonasok': d['levonasok']}]
    print('20 ezer feletti hiány (üzletszám): ' + ', '.join(
        f"{honapnev(h['meta']['honap'])} {sum(u['osszes'] <= KUSZOB for u in h['uzletek'])}" for h in honapok))
    print('Levonás összesen: ' + ', '.join(
        f"{honapnev(h['meta']['honap'])} {ft(sum(l['levon'] for l in h.get('levonasok', [])))}" for h in honapok))

    # 3. Kategóriák a hónapban
    kat = {k: sum(u.get(k) or 0 for u in us) for k in KATEGORIAK}
    fo = min(kat, key=kat.get)
    print('Kategóriák: ' + ', '.join(f'{KAT_NEV[k]} {elojel(v)}' for k, v in kat.items())
          + (f'; fő hiány: {KAT_NEV[fo]}' if kat[fo] < 0 else '; nincs hiányos kategória')
          + f"; pasta {elojel(sum(u.get('pasta') or 0 for u in us))} (tájékoztató).")

    # 4. Tartósan hiányos üzletek: az előző hónapok többségében (több mint felében) 20 ezer feletti hiány
    javult, maradt = [], []
    for n in aktiv:
        r = sorok.get(n, {})
        elotte = [r[k] for k in lezart if k != akt_kulcs and r.get(k) is not None]
        if len(elotte) < 4 or sum(v <= KUSZOB for v in elotte) <= 0.5 * len(elotte) or r.get(akt_kulcs) is None:
            continue
        cimke = f'{n} ({sum(v <= KUSZOB for v in elotte)}/{len(elotte)} hónap)'
        (maradt if r[akt_kulcs] <= KUSZOB else javult).append(cimke)
    print('Javult (eddig tartósan hiányos, most 20 ezer alatt): ' + (', '.join(javult) or '—'))
    print('Tartósan hiányos maradt: ' + (', '.join(maradt) or '—'))

    # 5. Előjelet váltott az előző hónaphoz képest (legalább 20 ezres mozgással)
    if elozo_kulcs:
        valto = []
        for n in aktiv:
            r = sorok.get(n, {})
            e, m = r.get(elozo_kulcs), r.get(akt_kulcs)
            if e is not None and m is not None and (e > 0) != (m > 0) and abs(m - e) >= 20000:
                valto.append((abs(m - e), f'{n} ({elojel(e)} -> {elojel(m)})'))
        print(f'Előjelet váltott ({KULCS_NEV[elozo_kulcs]} -> {akt_nev}): '
              + (', '.join(s for _, s in sorted(valto, reverse=True)) or '—'))

    # 6. Gombóc méret szerint: az összesben kioltható, ellentétes mozgások
    csop = {}
    for u in sorted(us, key=lambda u: u['gomboc']):
        for t in (u.get('reszletek') or {}).get('gomboc', []):
            if u['gomboc']:
                irany = 'hiány' if u['gomboc'] < 0 else 'többlet'
                csop.setdefault((t['termek'], irany), []).append(u['nev'])
    for (termek, irany), nevek in sorted(csop.items(), key=lambda x: -len(x[1])):
        if len(nevek) >= 2:
            sor = nevek if irany == 'hiány' else list(reversed(nevek))
            print(f'{termek} {irany}: {", ".join(sor)}')

    # 7. Megjegyzésekből kiolvasható minták
    viz_t = [u['nev'] for u in sorted(us, key=lambda u: -(u.get('ital') or 0))
             if re.search(r'víz', (u.get('megjegyzesek') or {}).get('ital', ''), re.I) and (u.get('ital') or 0) > 0]
    viz_h = [u['nev'] for u in sorted(us, key=lambda u: u.get('ital') or 0)
             if re.search(r'víz', (u.get('megjegyzesek') or {}).get('ital', ''), re.I) and (u.get('ital') or 0) < 0]
    if viz_t or viz_h:
        print(f"Személyzeti / mentes víz a megjegyzésekben — többlet: {', '.join(viz_t) or '—'}; hiány: {', '.join(viz_h) or '—'}")
    papir = [u['nev'] for u in sorted(us, key=lambda u: u.get('doboz') or 0)
             if (u.get('doboz') or 0) < 0 and re.search(r'doboz|zacsk', (u.get('megjegyzesek') or {}).get('doboz', ''), re.I)]
    if papir:
        print(f"Papíráru-hiány tételesen (doboz, zacskó): {', '.join(papir)}")
    pasta_h = [u['nev'] for u in sorted(us, key=lambda u: u.get('pasta') or 0) if (u.get('pasta') or 0) <= KUSZOB]
    pasta_t = [u['nev'] for u in sorted(us, key=lambda u: -(u.get('pasta') or 0)) if (u.get('pasta') or 0) >= -KUSZOB]
    if pasta_h or pasta_t:
        print(f"Pasta (tájékoztató, 20 ezer felett) — hiány: {', '.join(pasta_h) or '—'}; többlet: {', '.join(pasta_t) or '—'}")


if __name__ == '__main__':
    main()
