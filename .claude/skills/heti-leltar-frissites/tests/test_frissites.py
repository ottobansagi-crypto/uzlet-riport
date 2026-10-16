# -*- coding: utf-8 -*-
"""A heti leltár-frissítés szkriptjeinek tesztjei, valós beküldésekkel.

Minden teszt egy korábbi élesített állapotból indul (fixtures/allapot/<commit>.json.gz:
a data.json, a TREND2026 blokk és a hónap-tömbök akkori tartalma), végigfuttatja a
szkripteket a valós beküldésen, és összeveti az eredményt azzal, ami akkor kézzel
élesbe ment. A riport HTML-kódja a mostani; csak az adatrészeket cseréljük a régire,
így a tesztekhez nem kell git-történet. Futtatás a repó gyökeréből:

    python3 -m unittest discover -s .claude/skills/heti-leltar-frissites/tests -v
"""
import gzip, json, os, re, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), 'scripts')
FIX = os.path.join(HERE, 'fixtures')
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
SABLON = os.path.join(REPO, 'uzlet-riport.html')       # a mostani riport-kód


def snapshot(commit):
    with gzip.open(os.path.join(FIX, 'allapot', commit + '.json.gz'), 'rt', encoding='utf-8') as f:
        return json.load(f)


def html_allapottal(snap):
    """A mostani riport-HTML, benne a régi állapot adatrészeivel."""
    with open(SABLON, encoding='utf-8') as f:
        h = f.read()
    t0 = h.index('const TREND2026 = ['); t1 = h.index('];', t0) + 2
    h = h[:t0] + snap['trend_block'] + h[t1:]
    for pat, uj in zip((r'const T2026_MONTHS = \[.*?\];', r'const T2026_KEYS = \[.*?\];', r'const T2026_HONAP_KEY = \{.*?\};'),
                       snap['month_arrays']):
        h = re.sub(pat, lambda m: uj, h, count=1)
    i0 = h.index('const INLINE_DATA = {'); i1 = h.index('\n};', i0) + 3
    return h[:i0] + 'const INLINE_DATA = ' + json.dumps(snap['data'], ensure_ascii=False, indent=2) + ';' + h[i1:]


def run(script, *args, check=True):
    p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args],
                       capture_output=True, text=True)
    if check and p.returncode != 0:
        raise AssertionError(f'{script} hibával állt le ({p.returncode}):\n{p.stdout}\n{p.stderr}')
    return p


def trend_rows(html):
    """A TREND2026 tömb sorai névre kulcsolva (a sorrend és a szóközök nem számítanak)."""
    block = html[html.index('const TREND2026 = ['):]
    block = block[:block.index('];')]
    return {m.group(1): m.group(0) for m in re.finditer(r'\{nev:"([^"]+)"[^}]*\}', block)}


def month_arrays(html):
    return [re.search(p, html).group(0) for p in
            (r'const T2026_MONTHS = \[.*?\];', r'const T2026_KEYS = \[.*?\];', r'const T2026_HONAP_KEY = \{.*?\};')]


def inline_data(html):
    i0 = html.index('const INLINE_DATA = {')
    i1 = html.index('\n};', i0)
    return json.loads(html[i0 + len('const INLINE_DATA = '):i1 + 2])


def norm(d):
    d = json.loads(json.dumps(d))
    d.get('sk', {}).pop('pending', None)          # a pending kulcs utólag került be, tartalma mindig []
    return json.dumps(d, sort_keys=True, ensure_ascii=False, indent=1)


class Alap(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='frissites-teszt-')
        self.addCleanup(shutil.rmtree, self.root)

    def allapot(self, commit):
        snap = snapshot(commit)
        with open(os.path.join(self.root, 'data.json'), 'w', encoding='utf-8') as fh:
            json.dump(snap['data'], fh, ensure_ascii=False, indent=2); fh.write('\n')
        with open(os.path.join(self.root, 'uzlet-riport.html'), 'w', encoding='utf-8') as fh:
            fh.write(html_allapottal(snap))
        self.kiindulo_data = self.olvas('data.json')

    def parse(self, fixture):
        out = os.path.join(self.root, 'parsed.json')
        run('parse.py', os.path.join(FIX, fixture), '-o', out)
        return out

    def olvas(self, f):
        with open(os.path.join(self.root, f), encoding='utf-8') as fh:
            return fh.read()

    def egyezik(self, vart_commit, honap_tombok=False):
        data = json.loads(self.olvas('data.json'))
        html = self.olvas('uzlet-riport.html')
        vart = snapshot(vart_commit)
        self.assertEqual(norm(data), norm(vart['data']))
        self.assertEqual(norm(inline_data(html)), norm(data), 'az INLINE_DATA eltér a data.json-tól')
        self.assertEqual(trend_rows(html), trend_rows(vart['trend_block']))
        if honap_tombok:
            self.assertEqual(month_arrays(html), vart['month_arrays'])


class TestHeti(Alap):
    def test_okt14_javitott_ugyanaz_mint_ami_elesbe_ment(self):
        self.allapot('b9df2f5')                     # október 8, javított
        p = self.parse('okt14_javitott.txt')
        run('check.py', p, '--root', self.root, check=False)
        run('apply.py', p, '--root', self.root, '--mod', 'heti', '--datum', '2026. október 14')
        self.egyezik('de758d4')


class TestHonapvaltas(Alap):
    def test_okt08_szeptember_archivalva(self):
        self.allapot('8c7ff8f')                     # szeptember lezárva, levonásokkal
        p = self.parse('okt08_javitott_nyers.txt')
        run('apply.py', p, '--root', self.root, '--mod', 'honapvaltas',
            '--honap', '2026. október', '--datum', '2026. október 8')
        self.egyezik('b9df2f5', honap_tombok=True)

    def test_lezaratlan_honapot_nem_archival(self):
        self.allapot('70a6c7a')                     # szeptember még részeredmény
        p = self.parse('okt08_javitott_nyers.txt')
        r = run('apply.py', p, '--root', self.root, '--mod', 'honapvaltas',
                '--honap', '2026. október', '--datum', '2026. október 8', check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('nincs lezárva', r.stdout + r.stderr)


class TestZaras(Alap):
    def test_szeptember_zarasa_levonasokkal(self):
        self.allapot('70a6c7a')                     # szeptember 24-i részeredmény
        p = self.parse('szept_teljes_javitott.txt')
        run('apply.py', p, '--root', self.root, '--mod', 'zaras',
            '--levonasok', os.path.join(FIX, 'szept_levonasok.tsv'))
        self.egyezik('b16a384')


class TestCheck(Alap):
    def test_okt14_nyers_hibai(self):
        self.allapot('b9df2f5')
        p = self.parse('okt14_nyers.txt')
        r = run('check.py', p, '--root', self.root, check=False)
        out = r.stdout
        self.assertNotEqual(r.returncode, 0, out)
        self.assertRegex(out, r'Bazilika.*15 785.*18 153')          # összeg nem jön ki
        self.assertRegex(out, r'BP PARK.*változatlan')               # előző beküldésből maradt
        self.assertRegex(out, r'Debrecen')                           # ismeretlen üzlet
        self.assertNotRegex(out, r'PLÁZS|Siófok')                    # bezártak: csendben kimaradnak

    def test_okt14_javitott_nincs_hiba(self):
        # A BP PARK javított sorában is 6 mező az október 8-i (Otto megerősítette) — ez jogos
        # FIGYELEM marad, de HIBA (beépítést gátló) nem lehet.
        self.allapot('b9df2f5')
        p = self.parse('okt14_javitott.txt')
        r = run('check.py', p, '--root', self.root, check=False)
        self.assertNotEqual(r.returncode, 2, r.stdout)
        self.assertNotIn('HIBA', r.stdout)
        # Az összkép tényeihez: hálózati kategória-összegek és küszöb-darabszámok
        self.assertIn('gombóc +34 933', r.stdout)
        self.assertIn('papíráru -97 550', r.stdout)
        self.assertRegex(r.stdout, r'20 ezer feletti hiány: 8 üzlet.*50 ezer feletti: 0')

    def test_javitas_ugyanarra_a_napra(self):
        # Ugyanarra a napra küldött javított tábla: a legtöbb üzlet szándékosan változatlan,
        # ezért "nem frissült" figyelmeztetés helyett a változott üzleteket kell felsorolni.
        self.allapot('de758d4')                     # október 14, javított (élesben)
        p = self.parse('okt14_nyers.txt')           # ehhez képest csak a Bazilika és a BP PARK más
        out = run('check.py', p, '--root', self.root, '--javitas', check=False).stdout
        self.assertIn('Változott 2 üzlet: Bazilika, BP PARK', out)
        self.assertNotIn('változatlan', out)
        self.assertNotIn('nem frissült a PTG', out)

    def test_apply_nem_fut_hibas_osszeggel(self):
        self.allapot('b9df2f5')
        p = self.parse('okt14_nyers.txt')
        r = run('apply.py', p, '--root', self.root, '--mod', 'heti', '--datum', '2026. október 14', check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.olvas('data.json'), self.kiindulo_data, 'hiba esetén nem írhat fájlt')


if __name__ == '__main__':
    unittest.main()
