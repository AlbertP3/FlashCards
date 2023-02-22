from utils import Config, register_log
from abc import ABC, abstractmethod
from collections import OrderedDict
import bs4
import re
import requests



dict_services = dict()
def register_dict(name:str):
    def add_dict(d):
        dict_services[name] = d()
        return d
    return add_dict


class template_dict(ABC):
    @abstractmethod
    def get(self, word:str) -> tuple[list[str], list[str], list[str]]:
        # returns (translations, originals, warnings)
        return



@register_dict('pons')
class dict_pons(template_dict):

    def __init__(self):
        self.config = Config()
        self.dict_url = 'https://en.pons.com/translate/|ORIGINAL|-|TRANSLATION|/|PHRASE|'
        self.pons_mapping = dict(
            en = 'english',
            pl = 'polish',
            ru = 'russian',
            de = 'german',
        )
        self.re_patterns = OrderedDict([
            (r'\[(((or )?AM)|lub|perf|inf).*\]' , ' '),
            (r'( |\()+(f?pl|fig|m|\(?f\)?|nt|mpl|imperf)([^a-zA-Z0-9\(/]+|$)' , ' '),
            (r'(ELEC|Brit|HISTORY)', ''),
            (r' ( |$)', ''),
            (r' /', '/'),
        ])


    def get(self, word:str):
        self.word = word
        self.target_lng = self.config['sod_target_lng']
        self.source_lng = self.config['sod_source_lng']
        warnings = list()
        content = self.get_page_content()
        bs = bs4.BeautifulSoup(content.content, 'html5lib')
        warnings = self.check_for_warning(bs)
        translations = self.fetch_data(bs, 'target', self.pons_mapping[self.target_lng].capitalize())
        originals = self.fetch_data(bs, 'source', self.pons_mapping[self.source_lng].capitalize())
        for r, s in self.re_patterns.items():
            translations = [re.sub(r, s, text_) for text_ in translations]
            originals = [re.sub(r, s, text_) for text_ in originals]

        return translations, originals, warnings
    

    def get_page_content(self):
        url = self.dict_url.replace('|PHRASE|', self.word)
        url = url.replace('|ORIGINAL|', self.pons_mapping[self.source_lng])
        url = url.replace('|TRANSLATION|', self.pons_mapping[self.target_lng])
        html = requests.get(url)
        return html
    

    def fetch_data(self, bs:bs4.BeautifulSoup, class_name:str, lng:str):
        res = list()
        for row in bs.find_all('div', attrs={'class':class_name}):
            if row.find('acronym'): row.find('acronym').extract()
            if isinstance(row, bs4.element.Tag) and row.get('class')=='topic': 
                continue
            text_ = ''.join([word.get_text() for word in row]).strip()
            # Remove language tag, dicts list
            if text_ != lng and '\n' not in text_: res.append(text_)
        return res

    
    def check_for_warning(self, bs: bs4.BeautifulSoup):
        output = list()
        alerts = bs.find_all('div', attrs={'class':'alert'})
        if alerts:
            sim_res = alerts[1].find_all('a', href=re.compile(f'/translate/{self.pons_mapping[self.source_lng]}-{self.pons_mapping[self.target_lng]}/'))
            if sim_res:
                output.append('You are viewing results spelled similarly:')
                output.append(' | '.join([word.get_text().strip() for word in sim_res]))
        return output


@register_dict('merriam')
class dict_merriam(template_dict):

    def __init__(self):
        self.dict_url = 'https://www.merriam-webster.com/dictionary/|PHRASE|'

    
    def get(self, word:str):
        self.word = word
        warnings = list()
        content = self.get_page_content()
        bs = bs4.BeautifulSoup(content.content, 'html5lib')
        translations = self.fetch_data(bs, 'dtText')
        [warnings.append(msg) for msg in self.check_for_warning(bs)]
        return translations, ['']*len(translations), warnings


    def get_page_content(self):
        url = self.dict_url.replace('|PHRASE|', self.word)
        html = requests.get(url)
        return html

    
    def fetch_data(self, bs: bs4.BeautifulSoup, class_name: str):
        translations = list()
        for row in bs.find_all('span', attrs={'class':class_name}):
            text_ = ''.join([word.get_text() for word in row]).strip()
            # text_ = re.sub('xxx', '', text_)
            translations.append(text_[2:])
        return translations


    def check_for_warning(self, bs: bs4.BeautifulSoup):
        output = list()
        alerts = bs.find_all('p', attrs={'class': 'spelling-suggestions'})
        if alerts:
            output.append("The word you've entered isn't in the dictionary")
            output.append(' | '.join([word.get_text().strip() for word in alerts]))
        return output



@register_dict('babla')
class dict_babla(template_dict):

    def __init__(self):
        self.config = Config()
        self.dict_url = 'https://en.bab.la/dictionary/|ORIGINAL|-|TRANSLATION|/|PHRASE|'
        self.babla_mapping = dict(
            en = 'english',
            pl = 'polish',
        )

    def get(self, word:str):
        self.word = word
        self.target_lng = self.config['sod_target_lng']
        self.source_lng = self.config['sod_source_lng']
        warnings = list()
        re_patterns = OrderedDict()
        content = self.get_page_content()
        bs = bs4.BeautifulSoup(content.content, 'html5lib')
        warnings = self.check_for_warning(bs)
        originals = self.fetch_data_source(bs) if not warnings else list()
        translations = self.fetch_data_target(bs) if not warnings else list()
        for r, s in re_patterns.items():
            translations = [re.sub(r, s, text_) for text_ in translations]
            originals = [re.sub(r, s, text_) for text_ in originals]

        return translations[:len(originals)], originals, warnings


    def get_page_content(self):
        url = self.dict_url.replace('|PHRASE|', self.word)
        url = url.replace('|ORIGINAL|', self.babla_mapping[self.source_lng])
        url = url.replace('|TRANSLATION|', self.babla_mapping[self.target_lng])
        agent = {"User-Agent":"Mozilla/5.0"}
        html = requests.get(url, headers=agent)
        return html


    def fetch_data_source(self, bs:bs4.BeautifulSoup):
        res = list()
        bs_res = bs.find_all('a', attrs={'class':'babQuickResult'})
        for word in bs_res:
            text_ = ', '.join([w.strip().replace('\n','') for w in word if len(w)>1 and \
                        not any({i in w for i in {'volume_up','Translations', 'Monolingual examples', 'Collocations', 'Synonyms', 'Context sentences'}})])
            if text_: res.append(text_)
        return res


    def fetch_data_target(self, bs:bs4.BeautifulSoup):
        res = list()
        uls = bs.find_all(lambda tag: tag.name == 'ul' and tag.get('class') == ['sense-group-results']) 
        for li in uls:
            li = ', '.join([i.get_text().replace('volume_up\n','').strip() for i in li if len(i.get_text().replace('volume_up\n','').strip())>1])
            res.append(li)
        return res


    def check_for_warning(self, bs:bs4.BeautifulSoup):
        if not bs.find('ul', attrs={'class': 'did-you-mean'}): return list()

        output = list()
        alerts = bs.find(attrs={'class': 'did-you-mean'})
        if alerts:
            sim_res = alerts.find_all('li')
            if sim_res:
                output.append('Did you mean:')
                output.append(' | '.join([word.get_text().replace('volume_up\n','').strip() for word in sim_res]))
        return output



@register_dict('diki')
class dict_diki(template_dict):
    def __init__(self):
        self.config = Config()
        self.dict_url = 'https://www.diki.pl/slownik-|TRANSLATION|?q=|PHRASE|'
        self.diki_mapping = dict(
            en = 'angielskiego',
            de = 'niemieckiego',
        )

    def get(self, word:str):
        self.word = word
        self.target_lng = self.config['sod_target_lng']
        self.source_lng = self.config['sod_source_lng']
        warnings = list()
        content = self.get_page_content()
        bs = bs4.BeautifulSoup(content.content, 'html5lib')
        warnings = self.check_for_warning(bs)
        originals = self.fetch_data_source(bs) if not warnings else list()
        translations = self.fetch_data_target(bs) if not warnings else list()
        if len(originals) < len(translations):
            originals+=[originals[0]]*(len(translations)-len(originals))
        elif len(originals) > len(translations):
            translations+=[translations[0]]*(len(originals)-len(translations))
        return translations, originals, warnings


    def get_page_content(self):
        url = self.dict_url.replace('|PHRASE|', self.word)
        url = url.replace('|TRANSLATION|', self.diki_mapping.get(self.target_lng, self.diki_mapping['en']))
        agent = {"User-Agent":"Mozilla/5.0"}
        html = requests.get(url, headers=agent)
        return html


    def fetch_data_source(self, bs:bs4.BeautifulSoup):
        # diki returns different results when translating
        # from language that is not in the service e.g. PL
        if self.source_lng in self.diki_mapping.keys():
            res = self._fetch_data_source_incl(bs)
        else:
            res = self._fetch_data_source_excl(bs)
        return res


    def _fetch_data_source_incl(self, bs:bs4.BeautifulSoup):
        tags = {r'\*':'', r' [a-zA-Z]* dawne użycie':''}
        res = list()
        bs_res = bs.find_all('div', class_='hws')
        for word in bs_res:
            text_ = ' '.join(word.text.split())
            for t, r in tags.items():
                text_ = re.sub(t, r, text_)
            res.append(text_.strip())
        return res


    def _fetch_data_source_excl(self, bs:bs4.BeautifulSoup):
        res = list()
        ul = bs.find_all('ul', class_='nativeToForeignMeanings')
        for i, v in enumerate(ul):
            transl = ', '.join([a.text for a in ul[i].find_all('span', 'hw')])
            transl = ' '.join([w.strip() for w in transl.split()])
            res.append(transl or 'N/A')

            context_transl = ', '.join([a.text for a in ul[i].find_all('div', 'cat')]) 
            context_transl = ' '.join([w.strip() for w in context_transl.split()])
            try:
                if context_transl: res.insert(-2, context_transl)
            except IndexError:
                pass
        return res



    def fetch_data_target(self, bs:bs4.BeautifulSoup):
        if self.source_lng in self.diki_mapping.keys():
            res = self._fetch_data_target_incl(bs)
        else:
            res = self._fetch_data_target_excl(bs)
        return res


    def _fetch_data_target_incl(self, bs:bs4.BeautifulSoup):
        tags = ['oficjalnie', 'policzalny', 'Słownik żeglarski', '[]']
        res = list()
        li = bs.find_all('li', class_=re.compile(r'meaning\d+'))
        for i, v in enumerate(li):
            transl = ', '.join([w.text for w in li[i].find_all('span', class_='hw')])
            for t in tags:
                transl = transl.replace(t, '')
            transl = ' '.join([w.strip() for w in transl.split()])
            if transl: res.append(transl)
        return res


    def _fetch_data_target_excl(self, bs:bs4.BeautifulSoup):
        res = list()
        ol = bs.find('ol', class_='nativeToForeignEntrySlices')
        for li in ol.find_all('li', recursive=False):
            transl = ', '.join([a.text for a in li.find_all('span', 'hw', recursive=False)])
            transl = ' '.join([w.strip() for w in transl.split()])
            res.append(transl or 'N/A')
        return res


    def check_for_warning(self, bs:bs4.BeautifulSoup):
        warn = bs.find('div', class_='dictionarySuggestions')
        if warn: return [warn.text.replace('\n','').strip()]
        else: return list()
        


class Dict_Services:
    # source_lng - from which language user wants to translate -->> target_lng - to which lng ...
    # dict_service - which dict is currently selected

    def __init__(self):
        self.config = Config()
        self.dicts:dict = dict_services
        self.dict_service:str = self.config['sod_dict_service']
        self.DEFAULT_SOURCE_LNG = self.config['sod_source_lng']
        self.DEFAULT_TARGET_LNG = self.config['sod_target_lng']
        self.WORDS_LIMIT = 8
        self.word = None
        self.mute_warning = False
        self.source_lng = self.DEFAULT_SOURCE_LNG
        self.target_lng = self.DEFAULT_TARGET_LNG


    def __getitem__(self, key):
        return self.dicts[key]


    def get_available_dicts(self):
        return self.dicts.keys()
    

    def set_dict_service(self, dict_service):
        if dict_service in self.get_available_dicts():
            self.dict_service = dict_service
            self.config.update({'sod_dict_service':dict_service})
            

    def switch_languages(self, src_lng:str=None, tgt_lng:str=None):
        if src_lng == self.target_lng:
            self.set_target_language(self.source_lng)
            self.set_source_language(src_lng)
        elif src_lng != self.source_lng:
            self.set_source_language(src_lng)
            self.set_target_language(tgt_lng)


    def set_source_language(self, src_lng=None):
        self.source_lng = src_lng or self.DEFAULT_SOURCE_LNG
        self.config.update({'sod_source_lng': self.source_lng})


    def set_target_language(self, tgt_lng=None):
        self.target_lng = tgt_lng or self.DEFAULT_TARGET_LNG
        self.config.update({'sod_target_lng': self.target_lng})


    def get_info_about_phrase(self, word:str) -> tuple[list, list, list]:
        try:
            trans, orig, warn = self.dicts[self.dict_service].get(word)
        except requests.exceptions.ConnectionError:
            trans, orig, warn = [], [], ['No Internet Connection!']
        return trans[:self.WORDS_LIMIT], orig[:self.WORDS_LIMIT], warn



    

