from utils import Config
from abc import ABC, abstractmethod
from collections import OrderedDict
import bs4
import re
import requests



class dict_template(ABC):

    @abstractmethod
    def get(self, word:str):
        return list, list, list

    @abstractmethod
    def get_page_content(self):
        pass

    @abstractmethod
    def fetch_data(self, bs:bs4.BeautifulSoup, class_name:str, lng:str=None):
        pass

    @abstractmethod
    def check_for_warning(self, bs:bs4.BeautifulSoup):
        pass



class dict_pons(dict_template):

    def __init__(self):
        self.config = Config.get_instance()
        self.dict_url = 'https://en.pons.com/translate/|ORIGINAL|-|TRANSLATION|/|PHRASE|'
        self.pons_mapping = dict(
            en = 'english',
            pl = 'polish',
            ru = 'russian',
            de = 'german',
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
        translations = self.fetch_data(bs, 'target', self.pons_mapping[self.target_lng].capitalize())
        originals = self.fetch_data(bs, 'source', self.pons_mapping[self.source_lng].capitalize())
        re_patterns[r'\[(((or )?AM)|lub|perf|inf).*\]'] = ' '
        re_patterns[r'( |\()+(f?pl|fig|m|\(?f\)?|nt|mpl|imperf)([^a-zA-Z0-9\(/]+|$)'] = ' '
        re_patterns[r' ( |$)'] = ''
        re_patterns[r' /'] = '/'
        for r, s in re_patterns.items():
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
            if text_ != lng: res.append(text_)
        return res

    
    def check_for_warning(self, bs: bs4.BeautifulSoup):
        output = list()
        alerts = bs.find_all('div', attrs={'class':'alert'})
        if alerts:
            sim_res = alerts[1].find_all('a', href=re.compile(r'/translate/english-polish/'))
            if sim_res:
                output.append('You are viewing results spelled similarly:')
                output.append(' | '.join([word.get_text().strip() for word in sim_res]))
        return output



class dict_merriam(dict_template):

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



class dict_mock(dict_template):

    def __init__(self):
        pass

    def get(self, word):
        originals = ['witaj świecie', 'domyślny serwis', 'czerwony', 'traktować kogoś z honorami', 'lorem ipsum']
        translations = ['hello world', 'default dict service for tests', 'red', 'to roll out the red carpet for sb [or to give sb the red carpet treatment]', 'dolor sit amet']
        warnings = []
        if word == 'none': 
            translations.clear()
            originals.clear()
        elif word == 'mauve':
            originals = ['mauve']
            translations = ['jasno fioletowy']
        return translations, originals, warnings
    
    def get_page_content(self):
        pass
    def check_for_warning(self, bs: bs4.BeautifulSoup):
        pass
    def fetch_data(self, bs: bs4.BeautifulSoup, class_name: str, lng: str = None):
        pass



class Dict_Services:
    def __init__(self):
        self.dicts = dict(
            pons = dict_pons(),
            merriam = dict_merriam(),
            mock = dict_mock(),
        )
    

    def __getitem__(self, key):
        return self.dicts[key]


    def get_available_dicts(self):
        return self.dicts.keys()
    



    

