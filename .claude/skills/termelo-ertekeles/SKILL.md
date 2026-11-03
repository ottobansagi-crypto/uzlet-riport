---
name: termelo-ertekeles
description: Use when updating the termelő riport with a new month, or when Otto asks for the termelő havi szöveges értékelés (the "Sziasztok!" e-mail with gombóc, liszt and alapanyag eltérések). Covers where the V31 data lives, which columns to read, and how to generate the text.
---

# Termelő riport — havi frissítés és szöveges értékelés

A termelő riport két menüpontja (Havi gombóc gyártás, Alapanyag eltérés) a
`termelo/termelo-data.json` fájlból él. Minden hónapban ezt kell bővíteni, utána
a szöveges értékelés egy futtatás.

## A szöveges értékelés

```
python3 .claude/skills/termelo-ertekeles/scripts/ertekeles.py [--honap 2026-10] [--nullak]
```

Két blokkot ír ki. Elöl a **kiküldhető levél** Otto formájában, mögötte a **TÉNYEK**
blokk. A levél nyers számai a riport adatából jönnek, a záró bekezdés viszont
szabályból készül — ha nem illik a hónapra, azt kell átírni, nem a számokat.

A levél formája (Otto korábbi leveleiből):
nyitó mondat a gombócról és a liszt-felhasználásról, mellé a kiszállítás szerinti
fogyás; `alapanyag eltérések:` lista mértékegységgel, **százalék és forint nélkül**;
az `Édességek:` és `Italok:` külön blokkban; a végén 1–3 mondat arról, mi tűnik ki.
Az ezreseket nem tagoljuk (39342, nem 39 342). A nullára kerekedő tételek
(pl. +0,02 kg) kimaradnak, mert zajt csinálnak — `--nullak` kapcsolóval behozhatók.

## Honnan jön az adat

**FONTOS: a V31 táblázatokba SOHA nem írunk, csak olvassuk.**

| mi | hol |
|---|---|
| gombóc, dagasztás, liszt | „Alapanyag fogyások" munkafüzet → `dagasztások száma` lap |
| alapanyag eltérés | „V31 2025" munkafüzet → `2026 10` típusú havi lap |

A havi lap oszlopai (ellenőrizve 2026 szeptember/október):

| oszlop | tartalom |
|---|---|
| C | vételezés típus (Alapanyag / Édesség / Italok / Csomagolóanyag / Tisztítószerek / Irodaszerek / Egyeb anyag) |
| E, F, G | termék neve, mértékegység, bekerülési ár (100%) |
| J | nyitó leltár |
| U | elvárt záró |
| AG | tényleges záró |
| BS | bevét |

Ebből: `fogyás = J + BS − U`, `eltérés = AG − U`. Előjel: **mínusz = hiány, plusz = többlet**.
Az adat a 3. sortól indul. A `mindentudó` lap ugyanezeket a termékeket tartalmazza,
de eggyel lejjebb tolva (V31 havi lap 3. sora = mindentudó 4. sora).

## Ellenőrzés új hónap beolvasásakor

A Sheets API formázott szöveget ad vissza, és egy elcsúszott sor csendben rossz
adatot csinál. Ezért:

1. **Láncolás:** az új hónap nyitója egyezzen az előző hónap zárójával. 2026
   októberben 517-ből 487 egyezett, a többi hónapeleji korrekció a V31-ben — ez
   normális, de 10% alatt kell maradnia.
2. **Ár-próba:** ahol van mennyiség és ár, a származtatott érték jöjjön ki.
3. **Blokk-minták:** több szétszórt sortartományt kérj le újra, és vesd össze a
   beolvasottal. Kézi sorszámolásra ne hagyatkozz — 2026 októberben két oszlopnál
   is elcsúszott, és csak így derült ki.

## Tesztek

```
python3 -m unittest discover -s .claude/skills/termelo-ertekeles/tests -v
```
