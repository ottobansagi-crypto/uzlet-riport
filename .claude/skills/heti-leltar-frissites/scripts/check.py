# -*- coding: utf-8 -*-
"""A feldolgozott beküldés ellenőrzése a riport jelenlegi állapotához képest.

    python3 check.py <parsed.json> [--root <repó>]

Kimenet soronként:  HIBA (beépítés előtt Ottótól javítás kell) / FIGYELEM (rá kell kérdezni)
/ INFO (érdemes megemlíteni). Kilépési kód: 2 ha van HIBA, 1 ha csak FIGYELEM, különben 0."""
import argparse, io, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from szabalyok import BEZART, KATEGORIAK, TURES, ft

OSSZEVETETT = ['leltar_pct', 'osszes', 'gomboc', 'ital', 'desseg', 'doboz', 'ajandek', 'snack', 'selejt_ft']
NAGY_TETEL = 50000


def ures(b):
    return b.get('leltar_pct') is None and not any(b.get(k) for k in OSSZEVETETT)


def aktiv_nevek(data, honapvaltas=False):
    """Az üzletek, amelyeket a beküldésben várunk. Egy bezárt üzlet addig marad benne, amíg a folyó
    hónapban még szerepel (pl. szeptember zárásakor); hónapváltáskor az új hónapból kimarad."""
    return [u['nev'] for u in data['uzletek'] if not (honapvaltas and u['nev'] in BEZART)]


def ellenoriz(parsed, data, aktiv=None):
    hiba, figy, info = [], [], []
    aktiv = aktiv_nevek(data) if aktiv is None else aktiv
    akt = {u['nev']: u for u in data['uzletek'] if u['nev'] in aktiv}
    bekuldott = [b for b in parsed['hu'] if not (b['nev'] in BEZART and b['nev'] not in akt)]

    for b in bekuldott:
        if b['nev'] in akt:
            continue
        if ures(b):
            info.append(f"{b['nev']}: új név, minden érték üres vagy nulla — kimarad (ha már nyitott üzlet, szólj Ottónak).")
        else:
            hiba.append(f"{b['nev']}: új üzlet adattal — kell hozzá Ottótól a területvezető és hogy franchise-e.")
    nevek = {b['nev'] for b in bekuldott}
    for n in akt:
        if n not in nevek:
            hiba.append(f'{n}: hiányzik a beküldésből.')

    elozo_fc = azonos_fc = 0
    for b in bekuldott:
        if b['nev'] not in akt or ures(b):
            continue
        u = akt[b['nev']]
        if b.get('osszes') is None or b.get('leltar_pct') is None:
            hiba.append(f"{b['nev']}: hiányzik az összes eltérés vagy a százalék.")
            continue
        kat = sum(b.get(k) or 0 for k in KATEGORIAK)
        if abs(kat - b['osszes']) > TURES:
            hiba.append(f"{b['nev']}: az összes eltérés {ft(b['osszes'])}, a kategóriák összege {ft(kat)} "
                        f"(különbség {'+' if kat > b['osszes'] else ''}{ft(kat - b['osszes'])}).")
        p, o = b['leltar_pct'], b['osszes']
        if (p < 100 and o > 0) or (p > 100 and o < 0):
            figy.append(f"{b['nev']}: {p}% mellett {ft(o)} Ft — a százalék és a forint előjele ellentmond.")
        azonos = [k for k in OSSZEVETETT if (b.get(k) or 0) == (u.get(k) or 0)]
        if len(azonos) >= 6 and o != 0:
            figy.append(f"{b['nev']}: {len(azonos)} mező változatlan az előző beküldéshez képest "
                        f"({', '.join(azonos)}) — lehet, hogy nem frissült.")
        if (b.get('selejt_ft') or 0) < (u.get('selejt_ft') or 0) and data['meta'].get('reszido'):
            info.append(f"{b['nev']}: a selejt csökkent ({ft(u['selejt_ft'])} -> {ft(b['selejt_ft'])}); "
                        f"hónap közben kumulatív, csak hónapváltáskor csökkenhet.")
        t, ut = b.get('ptg') or {}, u.get('ptg') or {}
        if t.get('fiscat') is not None:
            elozo_fc += 1
            if (t.get('fiscat'), t.get('cash')) == (ut.get('fiscat'), ut.get('cash')) and (t.get('fiscat') or t.get('cash')):
                azonos_fc += 1
        for k in KATEGORIAK + ['pasta']:
            v = b.get(k)
            if v is not None and abs(v) >= NAGY_TETEL:
                megj = (b.get('megjegyzesek') or {}).get(k, '')
                info.append(f"{b['nev']}: {k} {ft(v)} Ft{' — ' + megj if megj else ''}.")
    if elozo_fc and azonos_fc >= elozo_fc / 2:
        figy.append(f'PTG: {azonos_fc} üzletnél a Fiscat és a Cash pontosan az előző beküldés értéke — '
                    f'valószínűleg nem frissült a PTG.')

    sk = parsed.get('sk')
    if sk:
        kat = sum(sk.get(k) or 0 for k in ['dough', 'drinks', 'dessert', 'boxes', 'merchandise', 'snack'])
        if sk.get('total') is None or abs(kat - sk['total']) > TURES:
            hiba.append(f"SK Kolarska: total {sk.get('total')}, a kategóriák összege {kat:g}.")
    return hiba, figy, info


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('parsed')
    ap.add_argument('--root', default='.')
    ap.add_argument('--honapvaltas', action='store_true', help='az új hónap első beküldése')
    a = ap.parse_args()
    with io.open(a.parsed, encoding='utf-8') as f:
        parsed = json.load(f)
    with io.open(os.path.join(a.root, 'data.json'), encoding='utf-8') as f:
        data = json.load(f)
    aktiv = aktiv_nevek(data, a.honapvaltas)
    hiba, figy, info = ellenoriz(parsed, data, aktiv)
    hu = [b for b in parsed['hu'] if b['nev'] in aktiv]
    print(f"Ellenőrizve: {len(hu)} üzlet, hálózati összeg {ft(sum(b.get('osszes') or 0 for b in hu))} Ft"
          f"{', SK is' if parsed.get('sk') else ''}.")
    for cimke, lista in (('HIBA', hiba), ('FIGYELEM', figy), ('INFO', info)):
        for s in lista:
            print(f'{cimke:9}{s}')
    if not (hiba or figy or info):
        print('Minden rendben.')
    sys.exit(2 if hiba else 1 if figy else 0)


if __name__ == '__main__':
    main()
