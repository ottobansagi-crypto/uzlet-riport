# -*- coding: utf-8 -*-
"""A feldolgozott beküldés beépítése a riportba (data.json + uzlet-riport.html).

    heti         a folyó hónap részeredményének cseréje
                 apply.py parsed.json --mod heti --datum "2026. október 14"
    honapvaltas  az előző (lezárt) hónap archiválása, új hónap első részeredménye
                 apply.py parsed.json --mod honapvaltas --honap "2026. november" --datum "2026. november 5"
    zaras        a folyó hónap teljes havi adata, opcionálisan a levonásokkal
                 apply.py parsed.json --mod zaras [--levonasok levonasok.tsv]

A levonások fájlja: tabulátoros 'nev<TAB>levon' sorok, kanonikus üzletnévvel (a PM-kódokat
előtte fel kell oldani). Ha bármi nem stimmel, egyetlen fájlt sem ír, és nem nulla kóddal lép ki."""
import argparse, collections, io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from szabalyok import KATEGORIAK, SK_TETELEK, TREND_EV, ft, honap_adatai
from check import aktiv_nevek, ellenoriz

OD = collections.OrderedDict
SORREND = ['nev', 'leltar_pct', 'osszes', 'gomboc', 'ital', 'desseg', 'doboz', 'snack', 'ajandek',
           'selejt_pct', 'reszletek', 'megjegyzesek', 'franchise', 'teruletvezeto', 'pasta', 'selejt_ft', 'ptg']
SK_KAT = ['dough', 'drinks', 'dessert', 'boxes', 'merchandise', 'snack']


def leall(uzenet):
    print('NEM ÍRTAM SEMMIT. ' + uzenet)
    sys.exit(2)


def egesz(v):
    return None if v is None else int(round(v))


def menny(v):
    f = float(v)
    return int(f) if f == int(f) else f


def uzlet(b, regi):
    u = {'nev': b['nev'], 'leltar_pct': round(b['leltar_pct'], 2), 'osszes': egesz(b['osszes']),
         'selejt_pct': round(b['selejt_pct'], 2), 'selejt_ft': egesz(b['selejt_ft']),
         'ptg': OD((k, egesz((b.get('ptg') or {}).get(k))) for k in ('osszes', 'fiscat', 'cash'))}
    for k in KATEGORIAK:
        u[k] = egesz(b.get(k) or 0)
    tetelek = {k: [{'termek': t['termek'], 'mennyiseg': menny(t['mennyiseg'])} for t in lista if t['mennyiseg']]
               for k, lista in (b.get('reszletek') or {}).items()}
    tetelek = {k: v for k, v in tetelek.items() if v}
    if tetelek:
        u['reszletek'] = tetelek
    if b.get('megjegyzesek'):
        u['megjegyzesek'] = dict(b['megjegyzesek'])
    if b.get('pasta') is not None:
        u['pasta'] = egesz(b['pasta'])
    if regi.get('franchise'):
        u['franchise'] = True
    if regi.get('teruletvezeto'):
        u['teruletvezeto'] = regi['teruletvezeto']
    return OD((k, u[k]) for k in SORREND if k in u)


def sk_honap(sk, honap):
    ev, _, _, szam, angol = honap_adatai(honap)
    st = OD([('name', 'Kolarska'), ('inventory_pct', sk['inventory_pct'])]
            + [(k, egesz(sk.get(k) or 0)) for k in ['total'] + SK_KAT + ['pasta']]
            + [('scrap', egesz(sk.get('scrap'))), ('scrap_pct', sk.get('scrap_pct')),
               ('cash_register', OD([('total', egesz((sk.get('cash_register') or {}).get('total'))),
                                     ('upos', egesz((sk.get('cash_register') or {}).get('upos')))]))])
    tetelek = {k: [{'item': SK_TETELEK.get(t['termek'], t['termek']), 'qty': menny(t['mennyiseg'])} for t in lista]
               for k, lista in (sk.get('reszletek') or {}).items()}
    if tetelek:
        st['details'] = tetelek
    return OD([('key', f'{ev}-{szam:02d}'), ('label', f'{angol} {ev}'), ('stores', [st])])


def levonasok_olvas(fn, nevek):
    sorok = []
    with io.open(fn, encoding='utf-8') as f:
        for ln in f:
            c = [x.strip() for x in ln.rstrip('\n').split('\t')]
            if len(c) < 2 or c[0] in ('', 'nev'):
                continue
            if c[0] not in nevek:
                leall(f'Levonás ismeretlen üzlethez: {c[0]!r}. Csak kanonikus név lehet (a kódot előbb fel kell oldani).')
            sorok.append((c[0], int(re.sub(r'\D', '', c[1])), c[2] if len(c) > 2 else ''))
    return [OD([('nev', n), ('levon', v), ('megjegyzes', m)]) for n, v, m in sorted(sorok, key=lambda s: nevek.index(s[0]))]


# ── HTML ──────────────────────────────────────────────────────────────────────
def kompakt(o):
    return json.dumps(o, ensure_ascii=False, separators=(',', ':'))


def lista(l, beh):
    if not l:
        return '[]'
    return '[\n' + ',\n'.join(' ' * (beh + 2) + kompakt(x) for x in l) + '\n' + ' ' * beh + ']'


def inline_szoveg(d):
    """Az INLINE_DATA egységes, soronként olvasható alakja (üzletenként egy sor)."""
    reszek = []
    for k, v in d.items():
        kk = json.dumps(k, ensure_ascii=False)
        if k in ('uzletek', 'levonasok'):
            reszek.append(f'  {kk}: {lista(v, 2)}')
        elif k == 'elozo_honapok':
            honapok = ['    {\n'
                       f'      "meta": {kompakt(h["meta"])},\n'
                       f'      "levonasok": {lista(h.get("levonasok", []), 6)},\n'
                       f'      "uzletek": {lista(h["uzletek"], 6)}\n'
                       '    }' for h in v]
            reszek.append(f'  {kk}: [\n' + ',\n'.join(honapok) + '\n  ]')
        elif k == 'sk':
            belso = [f'    {json.dumps(sk, ensure_ascii=False)}: ' + (lista(sv, 4) if sk == 'months' else kompakt(sv))
                     for sk, sv in v.items()]
            reszek.append(f'  {kk}: {{\n' + ',\n'.join(belso) + '\n  }')
        elif k == 'trend':
            belso = [f'    {json.dumps(n, ensure_ascii=False)}: {kompakt(t)}' for n, t in v.items()]
            reszek.append(f'  {kk}: {{\n' + ',\n'.join(belso) + '\n  }')
        else:
            reszek.append(f'  {kk}: {kompakt(v)}')
    szoveg = '{\n' + ',\n'.join(reszek) + '\n}'
    assert json.loads(szoveg) == json.loads(json.dumps(d)), 'INLINE renderelés hiba'
    return szoveg


def trend_frissit(html, kulcs, ertekek, uj_oszlop):
    t0 = html.index('const TREND2026 = ['); t1 = html.index('];', t0)
    blokk, talalt = html[t0:t1], set()

    def sor(m):
        s, nev = m.group(0), m.group(1)
        ertek = 'null' if ertekek.get(nev) is None else str(ertekek[nev])
        if nev in ertekek:
            talalt.add(nev)
        if uj_oszlop:
            if f',{kulcs}:' in s:
                leall(f'A TREND2026-ban már van {kulcs} oszlop ({nev}).')
            return s.replace(',franchise:', f',{kulcs}:{ertek},franchise:', 1)
        if nev not in ertekek:
            return s
        uj, n = re.subn(rf',{kulcs}:(-?\d+|null)', f',{kulcs}:{ertek}', s, count=1)
        if n != 1:
            leall(f'A TREND2026 {nev} sorában nincs {kulcs} oszlop.')
        return uj

    blokk = re.sub(r'\{nev:"([^"]+)"[^}]*\}', sor, blokk)
    hianyzik = set(ertekek) - talalt
    if hianyzik:
        leall('Ezek az üzletek hiányoznak a TREND2026-ból (új üzlet?): ' + ', '.join(sorted(hianyzik)))
    return html[:t0] + blokk + html[t1:]


def honap_tombok(html, kulcs, felirat, kisbetus):
    for minta, uj in ((r"(const T2026_MONTHS = \[.*?)\];", rf"\1,'{felirat}'];"),
                      (r"(const T2026_KEYS = \[.*?)\];", rf"\1,'{kulcs}'];"),
                      (r"(const T2026_HONAP_KEY = \{.*?) \};", rf"\1,'{kisbetus}':'{kulcs}' }};")):
        html, n = re.subn(minta, uj, html, count=1)
        if n != 1:
            leall('Nem találom a hónap-tömböket a HTML-ben: ' + minta)
    return html


# ── fő ────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('parsed')
    ap.add_argument('--root', default='.')
    ap.add_argument('--mod', required=True, choices=['heti', 'honapvaltas', 'zaras'])
    ap.add_argument('--datum', help='meddig szólnak a számok, pl. "2026. október 14" (heti, honapvaltas)')
    ap.add_argument('--honap', help='az új hónap, pl. "2026. november" (honapvaltas)')
    ap.add_argument('--levonasok', help='tabulátoros nev/levon fájl (zaras)')
    a = ap.parse_args()
    if a.mod in ('heti', 'honapvaltas') and not a.datum:
        leall('--datum kell.')
    if a.mod == 'honapvaltas' and not a.honap:
        leall('--honap kell.')

    dfn, hfn = os.path.join(a.root, 'data.json'), os.path.join(a.root, 'uzlet-riport.html')
    with io.open(a.parsed, encoding='utf-8') as f:
        parsed = json.load(f)
    with io.open(dfn, encoding='utf-8') as f:
        data = json.load(f, object_pairs_hook=OD)
    with io.open(hfn, encoding='utf-8') as f:
        html = f.read()

    if a.mod == 'honapvaltas':
        if data['meta'].get('reszido'):
            leall(f"A(z) {data['meta']['honap']} nincs lezárva (még részeredmény) — előbb a hónapzárás kell.")
        if a.honap == data['meta']['honap']:
            leall('Az új hónap ugyanaz, mint a folyó.')
    aktiv = aktiv_nevek(data, a.mod == 'honapvaltas')
    hiba, _, _ = ellenoriz(parsed, data, aktiv)
    if hiba:
        leall('Előbb ezeket kell rendezni:\n  ' + '\n  '.join(hiba))

    honap = a.honap if a.mod == 'honapvaltas' else data['meta']['honap']
    ev, kulcs, felirat, _, _ = honap_adatai(honap)
    if ev != TREND_EV:
        leall(f'Évváltás ({ev}): a TREND{TREND_EV} tömb csak {TREND_EV}-re szól, ezt kézzel kell megoldani.')

    regi = {u['nev']: u for u in data['uzletek']}
    uj = [uzlet(b, regi[b['nev']]) for b in parsed['hu'] if b['nev'] in aktiv]

    if a.mod == 'honapvaltas':
        data['elozo_honapok'].append(OD([('meta', OD([('honap', data['meta']['honap']), ('frissitve', data['meta']['frissitve'])])),
                                         ('levonasok', data['levonasok']), ('uzletek', data['uzletek'])]))
        data['levonasok'] = []
    if a.mod == 'zaras':
        if a.levonasok:
            data['levonasok'] = levonasok_olvas(a.levonasok, [u['nev'] for u in uj])
        meta = OD([('honap', honap), ('frissitve', f'{honap} teljes hónap' + ('' if a.levonasok else ' (levonások még nem véglegesek)'))])
    else:
        meta = OD([('honap', honap), ('frissitve', f'{a.datum}-ig (részeredmény, folyamatban)'),
                   ('reszido', True), ('reszido_datum', a.datum)])
    data['meta'] = meta
    data['uzletek'] = uj

    if parsed.get('sk'):
        skh = sk_honap(parsed['sk'], honap)
        honapok = data['sk']['months']
        i = next((i for i, m in enumerate(honapok) if m['key'] == skh['key']), None)
        if i is None:
            honapok.append(skh)
        else:
            honapok[i] = skh

    if a.mod == 'honapvaltas':
        html = honap_tombok(html, kulcs, felirat, honap.split()[-1].lower())
    html = trend_frissit(html, kulcs, {u['nev']: u['osszes'] for u in uj}, uj_oszlop=(a.mod == 'honapvaltas'))
    i0 = html.index('const INLINE_DATA = {'); i1 = html.index('\n};', i0) + 3
    html = html[:i0] + 'const INLINE_DATA = ' + inline_szoveg(data) + ';' + html[i1:]

    with io.open(dfn, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    with io.open(hfn, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Kész ({a.mod}): {meta['honap']} — {meta['frissitve']}. {len(uj)} üzlet, "
          f"hálózati összeg {ft(sum(u['osszes'] for u in uj))} Ft"
          + (f", levonás {len(data['levonasok'])} sor / {ft(sum(l['levon'] for l in data['levonasok']))} Ft" if a.mod == 'zaras' else '')
          + (f", SK {parsed['sk']['total']:g} EUR" if parsed.get('sk') else '') + '.')


if __name__ == '__main__':
    main()
