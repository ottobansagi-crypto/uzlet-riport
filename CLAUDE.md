# uzlet-riport

## Skillek

A Superpowers és az agent-browser skillek a claude.ai fiókból szinkronizálódnak
(`anthropic-skills:` előtaggal), nem ebből a repóból. Minden sessionben elérhetők.

Munka előtt olvasd el az `anthropic-skills:using-superpowers` skillt, és tartsd
magad hozzá: ha egy skill illik a feladatra, használd, ne improvizálj helyette.

Két projekt-skill van ebben a repóban:

- `.claude/skills/heti-leltar-frissites/` — az **üzlet** riport. Ezt kell használni,
  valahányszor Otto leltáradatot küld (heti részeredmény, hónap eleje, teljes havi
  adat, levonások, javított sorok).
- `.claude/skills/termelo-ertekeles/` — a **termelő** riport: új hónap beolvasása a
  V31-ből és a havi szöveges értékelés.
