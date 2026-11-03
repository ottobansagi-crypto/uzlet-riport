# -*- coding: utf-8 -*-
"""Az értékelő szkript a repó valódi adatán fut; a számokat a riport adja."""
import sys
sys.dont_write_bytecode = True
import io, json, os, subprocess, unittest

GYOKER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
SZKRIPT = os.path.join(GYOKER, '.claude', 'skills', 'termelo-ertekeles', 'scripts', 'ertekeles.py')


def futtat(*args):
    k = subprocess.run([sys.executable, '-I', SZKRIPT, '--root', GYOKER] + list(args),
                       capture_output=True, text=True)
    if k.returncode:
        raise AssertionError(k.stderr)
    return k.stdout


class Ertekeles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(GYOKER, 'termelo', 'termelo-data.json'), encoding='utf-8') as f:
            cls.d = json.load(f)
        cls.ki = futtat()

    def test_levelformaja(self):
        self.assertTrue(self.ki.startswith('Sziasztok!\n'))
        self.assertIn('alapanyag eltérések:', self.ki)
        self.assertIn('TÉNYEK', self.ki)

    def test_gomboc_es_liszt_a_nyito_mondatban(self):
        h = self.d['honapok'][-1]
        fej = self.ki.split('alapanyag eltérések:')[0]
        for v in (h['gomboc'], h['liszt'], h['tk_liszt']):
            self.assertIn('%.0f' % v, fej, '%r hiányzik a nyitó mondatból' % v)
        self.assertNotIn(' ', fej)      # Otto nem tagolja az ezreseket

    def test_a_level_nem_tartalmaz_szazalekot_vagy_forintot(self):
        level = self.ki.split('=' * 70)[0]
        self.assertNotIn('%', level)
        self.assertNotIn(' Ft', level)

    def test_nullara_kerekedo_tetel_kimarad_de_nullakkal_bejon(self):
        t = {x['nev']: x for x in self.d['alapanyag']['idoszakok'][-1]['termekek']}
        def nullara(x):
            v = x['elteres']
            if v is None or v == 0:
                return False
            if x['egyseg'] in ('gramm', 'ml'):
                v /= 1000.0
            return round(abs(v), 0 if x['egyseg'] == 'db' else 1) == 0
        apro = [n for n, x in t.items() if x.get('kategoria') and nullara(x)]
        if not apro:
            self.skipTest('ebben a hónapban nincs nullára kerekedő tétel')
        level = self.ki.split('=' * 70)[0]
        for n in apro:
            self.assertNotIn(n + ':', level)
        self.assertIn('Napolitana: 0', futtat('--nullak').split('=' * 70)[0])

    def test_korabbi_honap_is_lefut(self):
        ids = [i['id'] for i in self.d['alapanyag']['idoszakok']]
        if len(ids) < 2:
            self.skipTest('csak egy időszak van')
        self.assertIn('Sziasztok!', futtat('--honap', ids[0]))

    def test_ismeretlen_honapra_hibaval_all_le(self):
        k = subprocess.run([sys.executable, '-I', SZKRIPT, '--root', GYOKER, '--honap', '1999-01'],
                           capture_output=True, text=True)
        self.assertNotEqual(k.returncode, 0)


if __name__ == '__main__':
    unittest.main()
