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

# Bezárt / megszűnt üzletek: a beküldésben még szerepelnek, de a riportba nem kerülnek,
# és a check sem jelez miattuk. (PLÁZS, F1 Siófok: 2026 októberétől bezárt, Otto kérése.)
BEZART = {'PLÁZS', 'F1 Siófok', 'Erzsébet krt 14'}

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


def ft(v):
    """Ezres tagolású forint-szám a jelentésekhez: -15197 -> '-15 197'."""
    return f'{int(round(v)):,}'.replace(',', ' ')
