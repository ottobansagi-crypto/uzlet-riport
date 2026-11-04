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
2. Mentsd a bemásolt szöveget fájlba **a scratchpadba, soha ne a repóba** (a repó publikus), majd: `python3 $K/parse.py <fájl> -o p.json`
3. `python3 $K/check.py p.json` (hónap első beküldésénél `--honapvaltas`; ha Otto **ugyanarra a napra** küld javított táblát vagy sorokat: `--javitas`, ez a változott üzleteket sorolja fel, és nem jelez „nem frissült"-et). Ha Otto csak néhány üzlet blokkját küldi, írd át azokat az utolsó teljes beküldésben, és azt futtasd.
4. **Ha van HIBA sor: állj meg, nem építesz be semmit.** Kérdezd meg Ottót (lásd a jelentés-sablont), és várj a javított sorokra. A javított sort írd át a mentett szövegben, és kezdd újra a 2. lépéstől.
5. Mód kiválasztása, majd `python3 $K/apply.py p.json --mod <mód> ...`:

| Helyzet | Mód |
|---|---|
| a folyó hónap újabb részeredménye | `heti --datum "2026. október 21"` |
| új hónap első adata (az előző lezárva) | `honapvaltas --honap "2026. november" --datum "2026. november 5"` |
| teljes havi adat | `zaras` (levonás nélkül) |
| megjöttek a levonások | `zaras --levonasok lev.tsv` (a teljes havi adattal együtt) |

   Ha Otto azt kéri, hogy egy (pl. bezárt) üzlet már a folyó hónapban se szerepeljen: `--kivesz "NÉV"` a check-nek és az apply-nak is; a jövőre nézve vedd fel a `szabalyok.py` BEZART listájába (attól a hónaptól, amikortól már nem kell).
   A levonás-fájl tabulátoros `nev<TAB>levon` sorokból áll, **kanonikus névvel**. A PM-kódokat a `pizzame-tudas` skill `tudas/szervezet.md` kódtáblájából oldd fel. Amit ott nem találsz, arra kérdezz rá: **soha ne tippelj**, mert a levonás munkavállalói adat.
   Hónapváltás előtt kell a zárás. Ha a teljes havi adat nem jött meg, kérdezd meg Ottót.
6. Ellenőrizd böngészőben (Playwright, Chromium: `/opt/pw-browsers`), és küldj képet Ottónak.
7. Commit és push a munkaágra. A `main`-hez ne nyúlj.
8. Írd meg a szöveges értékelést (lásd lent).
9. „Mehet élesre" után: `git fetch origin main`, ellenőrizd, hogy a main a munkaág őse, aztán `git push origin HEAD:main`. Csak fast-forward lehet.

## Jelentés Ottónak (sablon)
1. **Ami bement:** üzletszám, hálózati összeg (az előző beküldéshez képest), SK. Javításnál: mely üzletek változtak. Röviden.
2. **Kérdések** — számozva, csak a check HIBA és FIGYELEM soraiból, egy-egy mondatban, a konkrét számokkal.
3. **Szöveges értékelés** — beépített adat esetén kötelező. Ha még HIBA miatt áll a beépítés, írd oda: „a javítás után küldöm".
4. **Élesítés:** „A munkaágon van, élesbe még nem ment. Mehet?"

## Szöveges értékelés (forrás: `pizzame-tudas` → `tudas/leltar-keszlet.md`)
Előbb futtasd: `python3 $K/ertekeles.py` — ez kigyűjti a tényeket (a hónap helye az évben, a 20 ezer feletti hiányos üzletek száma havonta, a fő hiány-kategória, a javult / tartósan hiányos / előjelet váltó üzletek, a gombóc-méretek, a víz, a papíráru és a pasta mintái). A szöveg ezekből készül, nem becslésből. Ha egy kategória a hálózatban többletben van, nem lehet „fő tétel".
A szöveg **informatív, kevés számmal**, üzletenkénti felsorolás nélkül (a számok a riportban vannak). Három rész:
1. **Összkép** (2–3 mondat): a hónap az évhez és az előző hónaphoz képest, a 20 ezer feletti hiányos üzletek számának alakulása, a levonások iránya.
2. **Ami a hónapot jellemzi** (3–5 pont): több üzletben ismétlődő minták, mindegyik félkövér állítás + 1–2 mondat, a példa-üzletek zárójelben.
3. **Az üzletek trendje** (3 pont): javult / tartósan hiányos maradt / előjelet váltott.
Minősítés („legrosszabb", „romlik", „krónikus") és javaslat nincs. Egyértelmű rögzítési vagy átvételi mintánál „valószínűleg" fordulat használható. Területvezetőt nem kell írni. Heti részeredménynél ugyanez a forma, rövidebben.

## Ismert, Otto által elfogadott tételek — ezekre NE kérdezz
- A PTG „összes" nem egyezik a Fiscat + Cash összegével (Kazinczy, BP PARK, Károly krt, Dob, Király utca stb.), a K1 Westend „hsz: 0" mezője, és az SK `Cash register` harmadik, címke nélküli értéke.
- A 100,00%-os százalék 100%-nak látszik, akkor is, ha kis hiány van mellette.
- A check INFO sorai (nagy tételek, csupa nulla új név) csak említendők, nem kérdések.
- PLÁZS, F1 Siófok, BP PARK: bezártak (a `szabalyok.py` BEZART listája), a beküldésben még szerepelnek, de kimaradnak — erre ne kérdezz.
- Debrecen: Otto szerint nem része a riportnak (`NEM_RESZE`), adattal is kimarad — erre ne kérdezz.
- Egy FIGYELEM-et, amit Otto ugyanerre a beküldésre már megerősített, nem kérdezel újra.

## Red flags — ha ezt gondolod, állj meg
| Gondolat | Valóság |
|---|---|
| „Beviszem a beküldött számokat, a kérdést mellé teszem" | HIBA mellett nincs beépítés. Az apply amúgy is megtagadja; ne kerüld meg kézi szerkesztéssel. |
| „Otto küldte a javított sort, tehát mehet élesre" | A javítás nem jóváhagyás. Kérdezd meg: mehet? |
| „Gyorsabb, ha megírom a saját szkriptemet" | A szkriptek tesztelve vannak a valós beküldéseken. Ha valami hiányzik belőlük, bővítsd őket, és futtasd a teszteket. |
| „Ez a PM-kód biztos X üzlet" | Csak a kódtáblából, vagy Otto megerősítésével. |

## Karbantartás
Új szabály (névváltozat, bezárt üzlet, szövegcsere a megjegyzésekben, pl. „személyzeti víz” → „1,5l Naturaqua mentes”) → `scripts/szabalyok.py`. A szövegcserét az apply minden íráskor a teljes adatra (az archív hónapokra is) lefuttatja. Bármilyen szkript-módosítás után futtasd a teszteket:
`python3 -m unittest discover -s .claude/skills/heti-leltar-frissites/tests -v`
