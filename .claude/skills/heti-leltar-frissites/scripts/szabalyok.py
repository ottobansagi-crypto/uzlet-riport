# -*- coding: utf-8 -*-
"""Állandó szabályok a leltár-beküldések feldolgozásához. Ha Otto új szabályt mond
(új névváltozat, bezárt üzlet), itt kell átvezetni."""

# A forrásrendszer névváltozatai -> a riport kanonikus neve.
NEVEK = {
    '13N Erzsébet krt. 40.': 'Erzsébet krt. 30.',
    'Széll Kálmán Tér': 'Széll Kálmán',
    'PM PLÁZS': 'PLÁZS',
    'Kolarska SNP': 'Kolarska',
}

# Bezárt / megszűnt üzletek -> az a hónap ('ÉÉÉÉ-HH'), amelytől már nem szerepelnek.
# A beküldésben még jöhetnek, de a check nem jelez miattuk, és hónapváltáskor kimaradnak.
#   PLÁZS, F1 Siófok: 2026 októberétől bezárt (Otto kérése).
#   BP PARK: 2026. október 4-én bezárt; az októberi hónapváltáskor még bent maradt, Otto kérésére
#            október közben kivettük (apply --kivesz), novembertől magától kimarad.
BEZART = {'Erzsébet krt 14': '2026-08', 'PLÁZS': '2026-10', 'F1 Siófok': '2026-10', 'BP PARK': '2026-11'}

# A riport hat kategóriája; ezek összege = "Összes eltérés". A pasta NEM számít bele.
KATEGORIAK = ['gomboc', 'ital', 'desseg', 'doboz', 'ajandek', 'snack']
TURES = 1   # Ft, kerekítés

# Magyar hónapnév -> (TREND2026 kulcs, oszlopfelirat, hónap száma, SK angol név)
HONAPOK = {
    'január': ('jan', 'Január', 1, 'January'),
    'február': ('feb', 'Február', 2, 'February'),
    'március': ('mar', 'Március', 3, 'March'),
    'április': ('apr', 'Április', 4, 'April'),
    'május': ('maj', 'Május', 5, 'May'),
    'június': ('jun', 'Június', 6, 'June'),
    'július': ('jul', 'Július', 7, 'July'),
    'augusztus': ('aug', 'Augusztus', 8, 'August'),
    'szeptember': ('sze', 'Szeptember', 9, 'September'),
    'október': ('okt', 'Október', 10, 'October'),
    'november': ('nov', 'November', 11, 'November'),
    'december': ('dec', 'December', 12, 'December'),
}
TREND_EV = 2026   # a TREND2026 tömb éve; évváltáskor a szkript megáll

# Az SK lap angol nyelvű: a forrás magyar tételneveit le kell fordítani.
SK_TETELEK = {
    '45-ös gombóc': '45cm Bochnik',
    '32-es gombóc': '32cm Bochnik',
    '22-es gombóc': '22cm Bochnik',
}


def honap_adatai(honap):
    """'2026. október' -> (év, kulcs, felirat, szám, angol)"""
    ev, nev = honap.replace('.', ' ').split()[0], honap.split()[-1].lower()
    if nev not in HONAPOK:
        raise SystemExit(f'Ismeretlen hónapnév: {honap!r}')
    k, felirat, szam, angol = HONAPOK[nev]
    return int(ev), k, felirat, szam, angol


def honap_kulcs(honap):
    """'2026. október' -> '2026-10'"""
    ev, _, _, szam, _ = honap_adatai(honap)
    return f'{ev}-{szam:02d}'


def kovetkezo_kulcs(kulcs):
    """'2026-10' -> '2026-11', '2026-12' -> '2027-01'"""
    ev, ho = map(int, kulcs.split('-'))
    return f'{ev + ho // 12}-{ho % 12 + 1:02d}'


def ft(v):
    """Ezres tagolású forint-szám a jelentésekhez: -15197 -> '-15 197'."""
    return f'{int(round(v)):,}'.replace(',', ' ')
