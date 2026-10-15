# -*- coding: utf-8 -*-
"""Otto bemásolt leltár-táblájából (tabulátorral tagolt szöveg) JSON-t készít.

    python3 parse.py <beküldés.txt> -o <parsed.json>

Egy üzlet-blokk: a név sora, utána a mezősorok ("Százalékos mutató", "Összes eltérés",
"Gombóc eltérés" ...). A cellák: [mező, érték, üres, mennyiség, termék, ..., megjegyzés].
A blokkon kívüli sorokat (pl. Otto kísérőszövege) figyelmen kívül hagyja.
Az SK blokk ("Kolarska SNP") angol mezőnevű, külön kerül ki."""
import sys
sys.dont_write_bytecode = True   # ne keletkezzen __pycache__ a repóban
import argparse, io, json, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from szabalyok import NEVEK

MEZOK = {'Százalékos mutató': 'leltar_pct', 'Összes eltérés': 'osszes', 'Gombóc eltérés': 'gomboc',
         'Ital eltérés': 'ital', 'Édesség eltérés': 'desseg', 'Dobozok eltérés': 'doboz',
         'Ajándéktárgy': 'ajandek', 'Snack': 'snack', 'Pasta': 'pasta',
         'Selejt': 'selejt_ft', 'Selejt %': 'selejt_pct'}
SK_MEZOK = {'Percentage': 'inventory_pct', 'Total difference': 'total', 'Pizza dough ball': 'dough',
            'Drinks difference': 'drinks', 'Dessert difference': 'dessert', 'Boxes difference': 'boxes',
            'Merchandise': 'merchandise', 'Pasta': 'pasta', 'Snack': 'snack', 'Scrap': 'scrap',
            'Scrap percentage': 'scrap_pct'}
TETELES = {'gomboc', 'ital', 'desseg', 'doboz', 'ajandek', 'snack', 'pasta'}
SK_TETELES = {'dough', 'drinks', 'dessert', 'boxes', 'merchandise', 'snack', 'pasta'}


def szam(s):
    """'-15 197' / '99,41%' / '1,5' -> float; üres -> None."""
    s = re.sub(r'[\s  %]', '', s or '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


def karton(t):
    """A forrásban a '#' a karton jele: '3# 1,5L víz' -> '3 karton 1,5L víz'."""
    return re.sub(r'(\d+(?:[.,]\d+)?)\s*#\s*', r'\1 karton ', t).strip()


def mezo(sor):
    """Az első cella mezőnévként (a kis-nagybetű a 'snack' sornál ingadozik)."""
    fej = sor[0].strip()
    for m in (MEZOK, SK_MEZOK):
        for k in m:
            if fej.lower() == k.lower():
                return k
    if fej.startswith('PTG/rendszer') or fej.startswith('Cash register'):
        return fej
    return None


def ptg(sor):
    resz = ' '.join(c.strip() for c in sor[1:])
    f = re.search(r'Fiscat[:\s]+(-?[\d ]+)', resz)
    c = re.search(r'Cash[:\s]+(-?[\d ]+)', resz)
    return {'osszes': szam(sor[1]) if len(sor) > 1 else None,
            'fiscat': szam(f.group(1)) if f else None, 'cash': szam(c.group(1)) if c else None}


def feldolgoz(szoveg):
    blokkok, akt = [], None
    for nyers in szoveg.split('\n'):
        sor = nyers.split('\t')
        fej = sor[0].strip()
        if not fej:
            continue
        m = mezo(sor)
        if m is None:                                  # új blokk (üzletnév) vagy kísérőszöveg
            akt = {'nev': NEVEK.get(fej, fej), '_mezok': 0}
            blokkok.append(akt)
            continue
        if akt is None:
            continue
        akt['_mezok'] += 1
        ertek = szam(sor[1]) if len(sor) > 1 else None
        if m.startswith('PTG/rendszer'):
            akt['ptg'] = ptg(sor)
        elif m.startswith('Cash register'):
            akt['cash_register'] = {'total': ertek, 'upos': szam(sor[3]) if len(sor) > 3 else None}
        else:
            kulcs = MEZOK.get(m) or SK_MEZOK.get(m)
            if m in SK_MEZOK and m not in MEZOK:
                akt['_sk'] = True
            akt[kulcs] = ertek
            menny = szam(sor[3]) if len(sor) > 3 else None
            termek = sor[4].strip() if len(sor) > 4 else ''
            if kulcs in TETELES | SK_TETELES and menny and termek:
                akt.setdefault('reszletek', {}).setdefault(kulcs, []).append({'termek': termek, 'mennyiseg': menny})
            vege = [c.strip() for c in sor[5:] if c.strip()]
            if kulcs in TETELES and vege:
                akt.setdefault('megjegyzesek', {})[kulcs] = karton(vege[-1])
    hu, sk = [], None
    for b in blokkok:
        if not b.pop('_mezok'):
            continue                                   # kísérőszöveg, nem üzlet
        if b.pop('_sk', False):
            sk = b
        else:
            hu.append(b)
    return {'hu': hu, 'sk': sk}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('bekuldes')
    ap.add_argument('-o', '--out', required=True)
    a = ap.parse_args()
    with io.open(a.bekuldes, encoding='utf-8') as f:
        eredmeny = feldolgoz(f.read())
    with io.open(a.out, 'w', encoding='utf-8') as f:
        json.dump(eredmeny, f, ensure_ascii=False, indent=1)
    print(f"{len(eredmeny['hu'])} magyar blokk, SK: {'van' if eredmeny['sk'] else 'nincs'} -> {a.out}")


if __name__ == '__main__':
    main()
