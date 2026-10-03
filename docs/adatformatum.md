# Adatformátum a leltár-riporthoz

Ez a dokumentum azt írja le, milyen JSON-t vár a riport a külső modultól, hogy az
eredményeket ne Excelből kelljen átemelni.

## Az alapelv: egy hónap = egy fájl

A modul **egyetlen hónap pillanatképét** adja ki. A riport történeti része (korábbi
hónapok, 2026-os trend, archiválás) **nem** a modul dolga — azt a riport oldalán
állítjuk elő, mert a korábbi hónapok adatától függ.

Egy hónapból több pillanatkép is jöhet (heti részeredmények), a legutolsó felülírja
az előzőt. Hónap végén jön a `vegleges` állapotú, levonásokkal.

Magyar és szlovák üzletek **külön fájlban**, mert más a pénznem.

---

## 1. Magyar pillanatkép

```json
{
  "orszag": "HU",
  "honap": "2026-09",
  "datum": "2026-09-24",
  "allapot": "reszeredmeny",
  "penznem": "HUF",
  "uzletek": [ ... ],
  "levonasok": [ ... ]
}
```

### Fejléc mezők

| Mező | Típus | Kötelező | Leírás |
|---|---|---|---|
| `orszag` | szöveg | igen | `"HU"` vagy `"SK"` |
| `honap` | szöveg | igen | `"ÉÉÉÉ-HH"`, pl. `"2026-09"` |
| `datum` | szöveg | igen | Meddig szólnak a számok: `"ÉÉÉÉ-HH-NN"`. Ez jelenik meg a sárga sávban. |
| `allapot` | szöveg | igen | `"reszeredmeny"` (hónap közben) vagy `"vegleges"` (hónapzárás) |
| `penznem` | szöveg | igen | `"HUF"` |
| `uzletek` | lista | igen | Lásd lent |
| `levonasok` | lista | nem | Csak `vegleges` állapotnál. Hónap közben hagyható el vagy üres lista. |

### Egy üzlet

```json
{
  "nev": "Király utca",
  "leltar_pct": 99.9,
  "osszes": -15197,
  "gomboc": -2850,
  "ital": -4270,
  "desseg": 0,
  "doboz": -3650,
  "ajandek": 0,
  "snack": -4427,
  "pasta": null,
  "selejt_ft": 1617100,
  "selejt_pct": 9.1,
  "ptg": { "osszes": -17846, "fiscat": 6545, "cash": -11299 },
  "reszletek": {
    "gomboc": [ { "termek": "Szelet", "mennyiseg": 3 } ]
  },
  "megjegyzesek": {
    "ital": "Vegyesen pár termék"
  }
}
```

| Mező | Típus | Kötelező | Leírás |
|---|---|---|---|
| `nev` | szöveg | igen | **Pontosan** a kanonikus listából (lásd 3. pont) |
| `leltar_pct` | szám | igen | Százalékos mutató, pl. `99.9`. Szám, nem szöveg, **pont** a tizedesjel a JSON-ban. |
| `osszes` | egész | igen | Összes eltérés Ft-ban |
| `gomboc` | egész | igen | Gombóc eltérés |
| `ital` | egész | igen | Ital eltérés |
| `desseg` | egész | igen | Édesség eltérés |
| `doboz` | egész | igen | Dobozok / papírárú eltérés |
| `ajandek` | egész | igen | Ajándéktárgy eltérés |
| `snack` | egész | igen | Snack eltérés |
| `pasta` | egész / `null` | nem | Pasta eltérés. **Nem** része az `osszes`-nek. Ahol nincs, hagyható el vagy `null`. |
| `selejt_ft` | egész | igen | Selejt forintban |
| `selejt_pct` | szám | igen | Selejt százalék |
| `ptg` | objektum | igen | `{ "osszes", "fiscat", "cash" }` — bármelyik lehet `null`, ha nincs adat |
| `reszletek` | objektum | nem | Tételes bontás kategóriánként, lásd lent |
| `megjegyzesek` | objektum | nem | Szöveges leírás kategóriánként, lásd lent |
| `teruletvezeto` | lista | nem | Ha elhagyod, a riport a korábbi hónap beosztását használja. Csak akkor küldd, ha változott. |
| `franchise` | logikai | nem | Csak ha `true`. Jelenleg: Pécs, Miskolc. |

### `reszletek` — tételes bontás

Kulcsok: `gomboc`, `ital`, `desseg`, `doboz`, `ajandek`, `snack`.
Csak azokat a kategóriákat add meg, ahol **tényleg van** tétel-szintű adat.

```json
"reszletek": {
  "doboz": [
    { "termek": "Doboz", "mennyiseg": 100 },
    { "termek": "Papírzacskó", "mennyiseg": 100 }
  ]
}
```

A `mennyiseg` lehet tört is (`2.5`), a `termek` szabad szöveg.

### `megjegyzesek` — szöveges leírás

Ugyanazok a kulcsok, plusz `pasta`. Akkor használd, ha **nincs** tételes bontás, de
van mit mondani ("Sok termék vegyesen", "1 karton Lays chips").

Fontos: a riportban a „nincs tétel-szintű bontás" és a „sok termék vegyesen"
**két különböző dolog** — az egyik az adat hiánya, a másik maga az információ.
Ha van ilyen szöveg, küldd el, ne dobd el.

Mindkettő megadható egyszerre ugyanarra a kategóriára: a tétel-lista alatt
jelenik meg a megjegyzés.

### `levonasok` — csak hónapzáráskor

```json
"levonasok": [
  { "nev": "Király utca", "levon": 55000, "megjegyzes": "" }
]
```

Csak azok az üzletek szerepeljenek, ahol van levonás. A `megjegyzes` elhagyható.

---

## 2. Szabályok, amiket minden beküldésnél ellenőrzök

1. **A kategóriák összege egyezzen az `osszes`-szel.**
   `gomboc + ital + desseg + doboz + ajandek + snack == osszes`
   A **`pasta` nem számít bele**. Legfeljebb **±1** eltérés fogadható el (kerekítés).
   Ez a leggyakoribb hiba — ha a modul ezt maga ellenőrzi, egy kör megspórolható.

2. **Az `osszes` a mérvadó, ha eltér.** Ha a kategória-összeg és az `osszes` között
   1-nél nagyobb a különbség, visszakérdezek, nem tippelek.

3. **Előjelek:** hiány negatív, többlet pozitív. Mindenhol, a selejt kivételével
   (`selejt_ft` mindig pozitív).

4. **Nevek:** pontosan a kanonikus lista szerint. Új vagy megszűnt üzlet esetén
   külön szólj, mert az a korábbi hónapokat is érinti.

5. **Számok számként**, ne szövegként: `99.9`, nem `"99,9%"`. Ezres elválasztó,
   `%` jel, `Ft` nem szerepelhet az értékben.

6. **Hiányzó adat:** a mező elhagyása vagy `null`. Ne küldj `0`-t olyan helyre,
   ahol valójában nincs mérés — a nulla azt jelenti, hogy nincs eltérés.

---

## 3. Kanonikus üzletnevek (34)

| Név | Területvezető |
|---|---|
| Király utca | Bratkovics Ádám |
| Erzsébet krt. 30. | Ullman Zsófia |
| Fashion | Hegedűs Milán |
| Bazilika | Racsmány Ignác |
| Széll Kálmán | Hegedűs Milán |
| Corvin | Racsmány Ignác |
| Károly krt | Racsmány Ignác |
| Dob | Ullman Zsófia |
| Blaha | Anda Patrícia |
| Oktogon | Ullman Zsófia |
| Wesselényi utca | Hegedűs Milán |
| Astoria | Anda Patrícia |
| Gomba Móricz | Ullman Zsófia |
| Keleti | Hegedűs Milán |
| Fővám tér | Anda Patrícia |
| Ferenciek tere | Hegedűs Milán |
| Jászai Mari tér | Racsmány Ignác |
| Etele | Bratkovics Ádám |
| Kispest | Ullman Zsófia |
| Bosnyák tér | Bratkovics Ádám |
| Árkád | Bratkovics Ádám |
| Kazinczy | Anda Patrícia |
| Törökvész | Racsmány Ignác |
| GO Buda | Bratkovics Ádám |
| D1 Buda | Hegedűs Milán |
| D2 Baross | Racsmány Ignác |
| Újpest | Anda Patrícia |
| K1 Westend | Racsmány Ignác |
| BP PARK | Ullman Zsófia |
| PLÁZS | Bratkovics Ádám, Hegedűs Milán |
| F1 Siófok | Bratkovics Ádám, Hegedűs Milán |
| Szeged | Anda Patrícia |
| Pécs | Bratkovics Ádám *(franchise)* |
| Miskolc | Bratkovics Ádám *(franchise)* |

A forrásrendszer névváltozatait a modul oldalán érdemes leképezni. Eddig előfordult:
`13N Erzsébet krt. 40.` → `Erzsébet krt. 30.`, `Széll Kálmán Tér` → `Széll Kálmán`,
`PM PLÁZS` → `PLÁZS`. Az `Erzsébet krt 14` megszűnt, nem szerepel a riportban.

---

## 4. Szlovák pillanatkép

Ugyanaz a felépítés, de **angol mezőnevekkel és euróban**, mert az SK lap végig
angol nyelvű.

```json
{
  "orszag": "SK",
  "honap": "2026-09",
  "datum": "2026-09-24",
  "allapot": "reszeredmeny",
  "penznem": "EUR",
  "stores": [
    {
      "name": "Kolarska",
      "inventory_pct": 99.4,
      "total": -85,
      "dough": -77,
      "drinks": -1,
      "dessert": -3,
      "boxes": -2,
      "merchandise": 0,
      "snack": -3,
      "pasta": -27,
      "scrap": 2638,
      "scrap_pct": 15.8,
      "cash_register": { "total": 0, "upos": 0 },
      "details": {
        "dough": [ { "item": "45cm Bochnik", "qty": 2.5 } ]
      },
      "notes": {}
    }
  ]
}
```

Megfeleltetés a magyar mezőkhöz: `dough` = gombóc, `drinks` = ital,
`dessert` = édesség, `boxes` = papírárú, `merchandise` = ajándéktárgy,
`cash_register` = PTG (`upos` = a Fiscat megfelelője), `scrap` = selejt.

Ugyanazok a szabályok érvényesek: az összeg-ellenőrzésnél a `pasta` itt sem
számít bele, és legfeljebb ±1 € eltérés fogadható el.

**Nyitott kérdés:** a `Cash register difference` sorban a forrásban van egy
harmadik érték is a `Upos` mellett — amíg nem tudjuk, mit jelent, nem tároljuk.
Ha kiderül, felvesszük a `cash_register` objektumba.

---

## 5. Amit ne küldjön a modul

- **A teljes `data.json`-t** — a történeti részt és a trendet a riport állítja elő.
- **Újraszámolt trend-adatot** — a 2026-os trend a beküldött hónapokból épül.
- **Kitalált levonást** — levonás csak hónapzáráskor, és csak amit ti határoztok meg.
- **Formázott számot** — `"-15 197 Ft"` helyett `-15197`.
