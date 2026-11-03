# -*- coding: utf-8 -*-
"""A termelő havi szöveges értékelése a riport adatfájljából (termelo/termelo-data.json).

    python3 ertekeles.py [--honap 2026-10] [--root <repó>] [--nullak]

Két dolgot ír ki. Elöl a kiküldhető levelet Otto formájában: nyitó mondat a gombócról és a
liszt-felhasználásról, utána az eltérések listája mértékegységgel (százalék és forint nélkül),
a végén a záró bekezdés. Mögötte a TÉNYEK blokkot, amiből a záró bekezdés készült — ha a
generált mondatok nem illenek a hónapra, azokat kell átírni, nem a számokat.

Csak a kiemelt (kategóriával ellátott) termékeket listázza, és alapból csak a nem nulla
eltéréseket. A --nullak kapcsolóval a pontosan nullára kijött tételek is bekerülnek.
"""
import sys
sys.dont_write_bytecode = True
import argparse, io, json, math, os

# Otto rövid nevei a levélben
ROVID = {
    'Liszt "piros"': 'Liszt',
    'TK liszt': 'Tk Liszt',
    'Sonka Cotto': 'Sonka',
    'Spinata Calabra': 'Calabra',
    'Pepperoni szalámi': 'Pepperoni',
    'P Szalámi Napolitana': 'Napolitana',
    'Gyulai kolbász': 'Gyulai',
    'Parmezánsajt': 'Parmezán',
    'Gelato Pistachio-Mascarpone': 'Gelato Pisztácia',
    'Gelato Nutella krémmel': 'Gelato Nutella',
    'Tartufata szósz 1,85 kg': 'Tartufata szósz',
    'Funghi mix zacskó 1,7 kg': 'Funghi mix',
}
# külön blokkot kapnak a levélben, a többi kategória egy listába megy
KULON_BLOKK = ['Édességek', 'Italok']
FO_ALAPANYAG = ['Liszt "piros"', 'TK liszt', 'Olívaolaj']
FO_KUSZOB = 0.5     # %, ezen belül "nincs érdemi eltérés"
TOBBI_KUSZOB = 3.0  # %, ezen belül "nagy eltérés nincs"
NULLARA_KUSZOB = 2.0  # %, ennél kisebb múlt havi hiányt nem emlegetünk


def szam(v, tizedes):
    s = ('%.*f' % (tizedes, v)).replace('.', ',')
    if ',' in s:
        s = s.rstrip('0').rstrip(',')
    return s


def ezres(v):
    """Otto a leveleiben nem tagolja az ezreseket: 39342, 11522."""
    return '%.0f' % v


def valtozo(t):
    """Az eltérés a levélben használt mértékegységben, kerekítve. (érték, mértékegység)."""
    v, me = t['elteres'], t['egyseg']
    if me == 'gramm':
        v, me = v / 1000.0, 'kg'
    elif me == 'ml':
        v, me = v / 1000.0, 'L'
    tizedes = 0 if me == 'db' else 1
    # fél felfelé, hogy a -1,45 ne -1,4 legyen a float ábrázolás miatt
    l = 10 ** tizedes
    v = math.floor(abs(v) * l + 0.5) / l * (1 if v >= 0 else -1)
    return v, me, tizedes


def mennyiseg(t):
    v, me, tizedes = valtozo(t)
    return ('+' if v > 0 else '') + szam(v, tizedes) + ' ' + me


def nullara_kerekedik(t):
    """A +0,02 kg típusú tétel a levélben zaj, nem adat."""
    return t['elteres'] is None or valtozo(t)[0] == 0


def szazalek(t):
    return t['elteres'] / t['fogyas'] * 100 if t['fogyas'] else None


def idoszak(d, hid):
    for i in d['alapanyag']['idoszakok']:
        if i['id'] == hid:
            return i
    raise SystemExit('nincs ilyen időszak: %s (van: %s)'
                     % (hid, ', '.join(i['id'] for i in d['alapanyag']['idoszakok'])))


def elozo(d, hid):
    ids = [i['id'] for i in d['alapanyag']['idoszakok']]
    k = ids.index(hid)
    return idoszak(d, ids[k - 1]) if k > 0 else None


def kiemelt(i):
    return {t['nev']: t for t in i['termekek'] if t.get('kategoria')}


def lista(nevek, mind, nullak):
    """A már sorba rakott tételek; a nullára kerekedők kimaradnak."""
    ki = []
    for n in nevek:
        t = mind[n]
        if nullara_kerekedik(t) and not nullak:
            continue
        ki.append('%s: %s' % (ROVID.get(n, n), mennyiseg(t)))
    return ki


def zaro(O, E):
    """A záró bekezdés mondatai a tényekből. Ha nem illik a hónapra, ez írandó át."""
    m = []
    tul = [n for n in FO_ALAPANYAG
           if n in O and szazalek(O[n]) is not None and abs(szazalek(O[n])) >= FO_KUSZOB]
    if not tul:
        m.append('A fő alapanyagoknál - liszt, TK liszt, olívaolaj - nincs érdemi eltérés, '
                 'a hónap ebből a szempontból rendben volt.')
    else:
        m.append('A fő alapanyagok közül %s tér el a szokásosnál jobban.'
                 % ', '.join(ROVID.get(n, n).lower() for n in tul))

    if E:
        romlott = []
        for n, t in O.items():
            if t['kategoria'] != 'Édességek' or t['elteres'] is None or t['elteres'] >= 0:
                continue
            r = E.get(n)
            if r and r['elteres'] is not None and t['elteres'] < r['elteres'] - 1e-9:
                romlott.append((n, r['elteres'], t['elteres']))
        romlott.sort(key=lambda x: x[2] - x[1])
        if romlott:
            reszlet = ', '.join('a %s %s-ról %s-ra'
                                % (ROVID.get(n, n), szam(abs(a), 0), szam(abs(b), 0))
                                for n, a, b in romlott[:2])
            m.append('Az édességeknél nőtt a hiány: %s.' % reszlet)
        nullara = [n for n, t in O.items()
                   if nullara_kerekedik(t) and n in E
                   and (szazalek(E[n]) or 0) <= -NULLARA_KUSZOB]
        if nullara:
            nevek = [ROVID.get(n, n) for n in nullara[:3]]
            m.append('A %s viszont a múlt havi hiány után most pontosan kijött.'
                     % (' és a '.join([', '.join(nevek[:-1]), nevek[-1]]).strip(' ,')
                        if len(nevek) > 1 else nevek[0]))

    tobbi = [abs(szazalek(t)) for n, t in O.items()
             if n not in FO_ALAPANYAG and t['kategoria'] not in KULON_BLOKK
             and szazalek(t) is not None]
    if tobbi and max(tobbi) < TOBBI_KUSZOB:
        m.append('A többi fontos terméknél nagy eltérés nincs.')
    return ' '.join(m)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.')
    ap.add_argument('--honap', help='pl. 2026-10; alapból a legutolsó időszak')
    ap.add_argument('--nullak', action='store_true', help='a nulla eltérésű tételek is')
    a = ap.parse_args()

    with io.open(os.path.join(a.root, 'termelo', 'termelo-data.json'), encoding='utf-8') as f:
        d = json.load(f)

    hid = a.honap or d['alapanyag']['idoszakok'][-1]['id']
    i = idoszak(d, hid)
    e = elozo(d, hid)
    O = kiemelt(i)
    E = kiemelt(e) if e else {}
    h = next((x for x in d['honapok'] if x['id'] == hid), None)
    if h is None:
        raise SystemExit('nincs gombóc adat erre a hónapra: %s' % hid)

    v31_liszt = O.get('Liszt "piros"')
    v31_tk = O.get('TK liszt')
    sorrend = [k for k in d['alapanyag']['kategoria_sorrend'] if k not in KULON_BLOKK]
    def rendez(k):
        nevek = [x for x in O if O[x]['kategoria'] == k]
        if k == 'Fő termékek':   # Otto mindig a liszttel kezdi, nem a legnagyobb eltéréssel
            elol = [n for n in FO_ALAPANYAG if n in nevek]
            return elol + [n for n in nevek if n not in elol]
        return sorted(nevek, key=lambda x: abs(szazalek(O[x]) or 0), reverse=True)
    fo_nevek = [n for k in sorrend for n in rendez(k)]

    print('Sziasztok!')
    print()
    print('A hónapban összesen %s db gombóc gyártása során %s kg lisztet és' % (
        ezres(h['gomboc']), ezres(h['liszt'])))
    print('%s kg TK lisztet használtunk el. A kiszállítások alapján %s kg liszt' % (
        ezres(h['tk_liszt']), ezres(v31_liszt['fogyas']) if v31_liszt else '?'))
    print('és %s kg tk liszt fogyott el.' % (ezres(v31_tk['fogyas']) if v31_tk else '?'))
    print()
    print()
    print('alapanyag eltérések:')
    print()
    for s in lista(fo_nevek, O, a.nullak):
        print(s)
        print()
    for blokk in KULON_BLOKK:
        nevek = sorted([n for n in O if O[n]['kategoria'] == blokk],
                       key=lambda x: abs(szazalek(O[x]) or 0), reverse=True)
        sorok = lista(nevek, O, a.nullak)
        if not sorok:
            continue
        print()
        print('%s:' % blokk)
        print()
        for s in sorok:
            print(s)
            print()
    print()
    print(zaro(O, E))

    print()
    print('=' * 70)
    print('TÉNYEK  (nem a levél része — ebből készült a záró bekezdés)')
    print('=' * 70)
    print('Időszak: %s (%s)   előző: %s' % (i['cimke'], i['id'], e['id'] if e else '-'))
    print('Gombóc %s | dagasztás %s | gombóc/dagasztás %.0f | TK arány %s%%' % (
        ezres(h['gomboc']), szam(h['dagasztas']['ossz'], 3),
        h['gomboc'] / h['dagasztas']['ossz'], szam(h['tk_arany'], 2)))
    ft = lambda M: sum(t['elteres'] * t['ar'] for t in M.values()
                       if t['ar'] is not None and t['elteres'] is not None)
    print('Ft hatás: %s | előző hónap: %s' % (
        ezres(ft(O)), ezres(ft(E)) if E else '-'))
    kat = {}
    for t in O.values():
        kat[t['kategoria']] = kat.get(t['kategoria'], 0) + (
            t['elteres'] * t['ar'] if t['ar'] is not None and t['elteres'] is not None else 0)
    print('Kategóriák: ' + ', '.join('%s %s Ft' % (k, ezres(v))
                                     for k, v in sorted(kat.items(), key=lambda x: x[1])))
    print()
    print('%-30s %10s %10s %10s' % ('termék', 'eltérés', '%', 'előző %'))
    for n in sorted(O, key=lambda n: abs(szazalek(O[n]) or 0), reverse=True):
        p, r = szazalek(O[n]), (szazalek(E[n]) if n in E else None)
        print('%-30s %10s %10s %10s' % (
            n, mennyiseg(O[n]),
            '-' if p is None else szam(p, 2) + '%',
            '-' if r is None else szam(r, 2) + '%'))
    nulla = [n for n in O if O[n]['elteres'] == 0]
    if nulla:
        print()
        print('Pontosan nullára jött ki (%d): %s' % (len(nulla), ', '.join(sorted(nulla))))


if __name__ == '__main__':
    main()
