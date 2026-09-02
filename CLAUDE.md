# uzlet-riport

## Vendorolt skillek

A `.claude/skills/` alatt két külső skill-könyvtár van bemásolva, hogy minden Claude Code
sessionben – webes, desktop és CLI – install nélkül betöltődjön:

- [Superpowers](https://github.com/obra/superpowers) (MIT) – 14 skill: brainstorming, TDD,
  szisztematikus hibakeresés, terv-írás és -végrehajtás, kódreview.
- [agent-browser](https://github.com/vercel-labs/agent-browser) (Apache-2.0) – böngésző-automatizálás.
  A skill csak belépési pont, a CLI-t külön kell futtatni: `npx agent-browser <command>`
  (globális `npm i -g agent-browser` nem éli túl a felhős session konténerét).

Frissítés: `.claude/update-skills.sh`. A vendorolt verziók (upstream commitok) a
`.claude/vendor/manifest.tsv` fájlban vannak.

Az alábbi `using-superpowers` skill szabályai minden sessionre érvényesek.

@.claude/skills/using-superpowers/SKILL.md
