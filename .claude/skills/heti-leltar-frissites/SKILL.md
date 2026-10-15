---
name: heti-leltar-frissites
description: Use when Otto pastes store inventory (leltár) data for the uzlet-riport — weekly partial results ("új riport adatok", "október 14-i állás"), the first data of a new month, month-end full data ("teljes havi adat", "hónap vége"), deductions (levonások, PM-kódok), or corrected rows for any of these.
---

# Heti leltár-frissítés

## Áttekintés
A riport adatát (data.json, TREND2026, INLINE_DATA, SK) **csak a `scripts/` szkriptjei írják**. Te a beküldést futtatod rajtuk, Ottónak jelented, amit a check talál, és az ő válaszai szerint haladsz. **Élesbe (`main`) csak Otto kifejezett „mehet élesre" / „mehet" válasza után kerül bármi.**

## Lépések
Munka a `claude/business-report-review-4iqn3c` ágon, a repó gyökeréből. `K=.claude/skills/heti-leltar-frissites/scripts`
1. `git fetch origin main`; ha a main előrébb jár, előbb húzd be (fast-forward vagy merge) a munkaágba.
2. Mentsd a bemásolt szöveget fájlba (scratchpad), majd: `python3 $K/parse.py <fájl> -o p.json`
3. `python3 $K/check.py p.json` (hónap első beküldésénél `--honapvaltas`).
4. **Ha van HIBA sor: állj meg, nem építesz be semmit.** Kérdezd meg Ottót (lásd a jelentés-sablont), és várj a javított sorokra. A javított sort írd át a mentett szövegben, és kezdd újra a 2. lépéstől.
5. Mód kiválasztása, majd `python3 $K/apply.py p.json --mod <mód> ...`:

| Helyzet | Mód |
|---|---|
| a folyó hónap újabb részeredménye | `heti --datum "2026. október 21"` |
| új hónap első adata (az előző lezárva) | `honapvaltas --honap "2026. november" --datum "2026. november 5"` |
| teljes havi adat | `zaras` (levonás nélkül) |
| megjöttek a levonások | `zaras --levonasok lev.tsv` (a teljes havi adattal együtt) |

   A levonás-fájl tabulátoros `nev<TAB>levon` sorokból áll, **kanonikus névvel**. A PM-kódokat a `pizzame-tudas` skill `tudas/szervezet.md` kódtáblájából oldd fel. Amit ott nem találsz, arra kérdezz rá: **soha ne tippelj**, mert a levonás munkavállalói adat.
   Hónapváltás előtt kell a zárás. Ha a teljes havi adat nem jött meg, kérdezd meg Ottót.
6. Ellenőrizd böngészőben (Playwright, Chromium: `/opt/pw-browsers`), és küldj képet Ottónak.
7. Commit és push a munkaágra. A `main`-hez ne nyúlj.
8. Írd meg a szöveges értékelést (lásd lent).
9. „Mehet élesre" után: `git fetch origin main`, ellenőrizd, hogy a main a munkaág őse, aztán `git push origin HEAD:main`. Csak fast-forward lehet.

## Jelentés Ottónak (sablon)
1. **Ami bement:** üzletszám, hálózati összeg (az előző beküldéshez képest), SK. Röviden.
2. **Kérdések** — számozva, csak a check HIBA és FIGYELEM soraiból, egy-egy mondatban, a konkrét számokkal.
3. **Szöveges értékelés** — beépített adat esetén kötelező. Ha még HIBA miatt áll a beépítés, írd oda: „a javítás után küldöm".
4. **Élesítés:** „A munkaágon van, élesbe még nem ment. Mehet?"

## Szöveges értékelés (forrás: `pizzame-tudas` → `tudas/leltar-keszlet.md`)
Kevés szám: üzletenként 1–2 mondatban az eltérés oka (kategória, termék). Minősítés és javaslat nincs. A küszöb 20 000 Ft hiány. Négy blokk: összkép (2–3 mondat) → 50 ezer feletti hiány → 20–50 ezer → 20 ezer alatt egy sorban (a többlettel zártak külön), végül „Amit érdemes kiemelni". Területvezetőt nem kell írni.

## Ismert, Otto által elfogadott tételek — ezekre NE kérdezz
- A PTG „összes" nem egyezik a Fiscat + Cash összegével (Kazinczy, BP PARK, Károly krt, Dob, Király utca stb.), a K1 Westend „hsz: 0" mezője, és az SK `Cash register` harmadik, címke nélküli értéke.
- A 100,00%-os százalék 100%-nak látszik, akkor is, ha kis hiány van mellette.
- A check INFO sorai (nagy tételek, csupa nulla új név) csak említendők, nem kérdések.
- Egy FIGYELEM-et, amit Otto ugyanerre a beküldésre már megerősített, nem kérdezel újra.

## Red flags — ha ezt gondolod, állj meg
| Gondolat | Valóság |
|---|---|
| „Beviszem a beküldött számokat, a kérdést mellé teszem" | HIBA mellett nincs beépítés. Az apply amúgy is megtagadja; ne kerüld meg kézi szerkesztéssel. |
| „Otto küldte a javított sort, tehát mehet élesre" | A javítás nem jóváhagyás. Kérdezd meg: mehet? |
| „Gyorsabb, ha megírom a saját szkriptemet" | A szkriptek tesztelve vannak a valós beküldéseken. Ha valami hiányzik belőlük, bővítsd őket, és futtasd a teszteket. |
| „Ez a PM-kód biztos X üzlet" | Csak a kódtáblából, vagy Otto megerősítésével. |

## Karbantartás
Új szabály (névváltozat, bezárt üzlet) → `scripts/szabalyok.py`. Bármilyen szkript-módosítás után futtasd a teszteket:
`python3 -m unittest discover -s .claude/skills/heti-leltar-frissites/tests -v`
