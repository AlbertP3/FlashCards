import os
from unittest import TestCase, mock
import re
import unittest
import requests
from functools import partial
import SOD.dicts as sod_dicts
from tools import LocalFileAdapter, dict_mock
from data import PONS_EXAMPLES, EXAMPLE_PHRASES

CWD = os.path.dirname(os.path.abspath(__file__))



class Test_dicts(TestCase):
    
    def setUp(self):
        self.d_api = sod_dicts.Dict_Services()
        self.d_api.dicts['mock'] = dict_mock()
        

    def mock_connection_html(self, file_name):
        requests_session = requests.session()
        requests_session.mount(f'file://', LocalFileAdapter())
        html = requests_session.get(f"file://{CWD}/res/dicts/{file_name}")
        return html


    def test_pons_regex(self):
        re_patterns = sod_dicts.dict_pons().re_patterns
        for raw, expected in PONS_EXAMPLES.items():
            s = raw
            for p, r in re_patterns.items():
                s = re.sub(p, r, s)
            self.assertEqual(s, expected)


    @unittest.skip('TODO: Replace online connection with a mock')
    def test_get_from_pons(self):
        d = self.d_api['pons']
        translations, originals, warnings = d.get_info_about_phrase('machine learning')
        self.assertNotIn('COMPUT ', originals[0])
        self.assertEqual('uczenie maszynowe', translations[0])

        translations, originals, warnings = d.get_info_about_phrase('ravenous')
        self.assertNotIn('person ', originals[0])
        self.assertEqual('wygłodniały', translations[0])
        


    @unittest.skip('TODO: Replace online connection with a mock')
    def test_get_from_merriam(self):
        d = self.d_api['merriam']
        translations, originals, warnings = d.get_info_about_phrase('iconoclast')
        self.assertIn('a person who attacks settled beliefs or institutions', translations)

    
    def test_get_from_mock(self):
        d = self.d_api['mock']
        translations, originals, warnings = d.get('whatever')
        self.assertNotEqual(translations, [])
        self.assertIn('witaj świEcie', translations)


    def test_dict_diki_query_success_1(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_decorous.txt')
        t, o, w = d.get('decorous')
        self.assertEqual(w, [])
        self.assertEqual(['odpowiedni (o wyglądzie), stosowny (o zachowaniu), w dobrym guście'], t)
        self.assertEqual('decorous', o[0])

    def test_dict_diki_query_success_2(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_gasket.txt')
        t, o, w = d.get('gasket')
        self.assertEqual(w, [])
        self.assertEqual(['uszczelka', 'krawat'], t)
        self.assertEqual(['gasket', 'gasket'], o)

    def test_dict_diki_query_success_3(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_abbreviation.txt')
        t, o, w = d.get('abbreviation')
        self.assertEqual(w, [])
        self.assertEqual(['skrót (skrócona nazwa)', 'skrócenie'], t[:2])

    def test_dict_diki_query_success_4(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_affliction.txt')
        t, o, w = d.get('affliction')
        self.assertEqual(w, [])
        self.assertEqual(["zmartwienie, przygnębienie, nieszczęście", "dolegliwość, przypadłość, schorzenie"], t)
        self.assertEqual('affliction', o[0])

    def test_dict_diki_query_success_5(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_environment.txt')
        t, o, w = d.get('environment')
        self.assertEqual(w, [])
        self.assertEqual(['otoczenie, środowisko, anturaż (tworzone przez otaczających ludzi oraz rzeczy)', 'otoczenie, środowisko (rodzaj lub charakterystyczne cechy danego obszaru)', 'środowisko, środowisko naturalne'], t)
        self.assertEqual(['environment', 'the environment', 'environment'], o)

    def test_dict_diki_query_success_6(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_transmogrify.txt')
        t, o, w = d.get('transmogrify')
        self.assertEqual(['przemienić (za pomocą czarów)'], t)
        self.assertEqual(['transmogrify'], o)
        self.assertEqual([], w)

    def test_dict_diki_query_success_7(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_przemieniac.txt')
        t, o, w = d.get('przemieniac')
        self.assertEqual(['transform', 'metamorphose', 'przemienić, zmienić', 'przemienić (za pomocą czarów)'], t)
        self.assertEqual(['przekształcać, transformować, przekształcić się', 'przeobrażać się', 'przemienić', 'przekształcać, transformować, przekształcić się'], o)
        self.assertEqual([], w)

    def test_dict_diki_query_success_8(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_discern.txt')
        t, o, w = d.get('discern')
        self.assertEqual(len(t), len(o))
        self.assertEqual(['discern']*3, o)
        self.assertEqual(['rozeznawać się, dostrzegać', 'dostrzegać, spostrzegać', 'rozeznać'], t)

    def test_dict_diki_query_success_9(self):
        d = self.d_api['diki']
        self.d_api.switch_languages('pl', 'en')
        d.get_page_content = partial(self.mock_connection_html, 'diki_torebka.txt')
        t, o, w = d.get('torebka')
        self.assertEqual(len(t), len(o))
        self.assertEqual(['torebka, torba (damska)', 'torebka, torba, worek, torebka (ilość)', 'woreczek, torebka (jako wewnętrzna część rośliny lub zwierzęcia)', 'torebka (np. z wonnymi ziołami)', 'Słownik terminów anatomicznych', 'torba, torebka', 'pochewka, torebka'], o)
        self.assertEqual(['bag , handbag , purse', 'bag', 'sac', 'sachet', 'capsula', 'bagful', 'involucre'], t)

    def test_dict_diki_query_error_1(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_affilication.txt')
        t, o, w = d.get('affilication')
        self.assertEqual('Czy chodziło ci o: affiliation, affliction, affrication', w[0])

    @unittest.skip("TODO")
    def test_get_from_cambridge(self):
        d = self.d_api['cambridge']
        d.get_page_content = partial(self.mock_connection_html, '')
