from cfg import config
from abc import abstractmethod
from collections import OrderedDict
import bs4
import re
import requests
import itertools
import string
import logging
import SOD.file_handler
from cfg import config

log = logging.getLogger("SOD")

ReqExcMsg = {
    403: "⨷ Access Forbidden!",
    404: "⨷ Page not Found!",
    400: "⨷ Bad Request!",
    500: "⨷ Internal Server Error!",
}

dict_services = dict()


def get_unique_shortname(name: str):
    fallbacks = itertools.chain([name.capitalize(), *string.ascii_letters])
    while name in {v["shortname"] for v in dict_services.values()}:
        name = fallbacks.__next__()
    return name


def register_dict(name: str, shortname: str = None):
    def add_dict(d):
        dict_services[name] = {
            "service": d(),
            "shortname": get_unique_shortname(shortname or name[0]),
        }
        return d

    return add_dict


class TemplateDict:

    def __init__(self):
        self.timeout = config["SOD"]["request_timeout"]
        self.make_headers()
        self.req_status = 200

    @abstractmethod
    def get(self, word: str) -> tuple[list[str], list[str], list[str]]:
        """returns (translations, originals, warnings)"""
        return

    def set_languages(self, src: str, tgt: str):
        self.source_lng = src
        self.target_lng = tgt

    def make_headers(self):
        self.headers = dict()
        if ua := config.get("user_agent"):
            self.headers["User-Agent"] = ua

    def check_status_code(self, resp: requests.Response):
        self.req_status = resp.status_code
        if self.req_status != 200:
            raise requests.exceptions.RequestException


@register_dict("pons")
class DictPons(TemplateDict):

    def __init__(self):
        super().__init__()
        self.dict_url = (
            "https://en.pons.com/translate/|ORIGINAL|-|TRANSLATION|/|PHRASE|"
        )
        self.pons_mapping = dict(
            en="english",
            pl="polish",
            ru="russian",
            de="german",
            jp="japanese",
        )
        self.re_patterns = OrderedDict(
            [
                (r"\[(((or )?AM)|lub|perf|inf).*\]", " "),
                (r"( |\()+(f?pl|fig|m|\(?f\)?|nt|mpl|imperf)([^a-zA-Z0-9\(/]+|$)", " "),
                (r"(ELEC|Brit|HISTORY)", ""),
                (r" ( |$)", ""),
                (r" /", "/"),
            ]
        )

    def get(self, word: str):
        self.word = word
        warnings = list()
        content = self.get_page_content()
        self.check_status_code(content)
        bs = bs4.BeautifulSoup(content.content, "html5lib")
        warnings = self.check_for_warning(bs)
        translations = self.fetch_data(
            bs, "target", self.pons_mapping[self.target_lng].capitalize()
        )
        originals = self.fetch_data(
            bs, "source", self.pons_mapping[self.source_lng].capitalize()
        )
        for r, s in self.re_patterns.items():
            translations = [re.sub(r, s, text_) for text_ in translations]
            originals = [re.sub(r, s, text_) for text_ in originals]
        translations, originals = self.ensure_order(translations, originals)
        return translations, originals, warnings

    def get_page_content(self):
        url = self.dict_url.replace("|PHRASE|", self.word)
        url = url.replace("|ORIGINAL|", self.pons_mapping[self.source_lng])
        url = url.replace("|TRANSLATION|", self.pons_mapping[self.target_lng])
        html = requests.get(url, timeout=self.timeout)
        return html

    def fetch_data(self, bs: bs4.BeautifulSoup, class_name: str, lng: str):
        res = list()
        for row in bs.find_all("div", attrs={"class": class_name}):
            if row.find("acronym"):
                row.find("acronym").extract()
            if isinstance(row, bs4.element.Tag) and row.get("class") == "topic":
                continue
            text_ = "".join([word.get_text() for word in row]).strip()
            # Remove language tag, dicts list
            if text_ != lng and "\n" not in text_:
                res.append(text_)
        return res

    def check_for_warning(self, bs: bs4.BeautifulSoup):
        output = list()
        alerts = bs.find_all("div", attrs={"class": "alert"})
        if alerts:
            sim_res = alerts[1].find_all(
                "a",
                href=re.compile(
                    f"/translate/{self.pons_mapping[self.source_lng]}-{self.pons_mapping[self.target_lng]}/"
                ),
            )
            if sim_res:
                output.append("You are viewing results spelled similarly:")
                output.append(" | ".join([word.get_text().strip() for word in sim_res]))
        return output

    def ensure_order(self, translations, originals):
        """Checks if translations were shown as source. If so, changes translations with originals."""
        w = self.word.lower()
        if any([w in t.lower() for t in translations]):
            translations, originals = originals, translations
        return translations, originals


@register_dict("merriam")
class DictMerriam(TemplateDict):

    def __init__(self):
        super().__init__()
        self.dict_url = "https://www.merriam-webster.com/dictionary/|PHRASE|"

    def get(self, word: str):
        self.word = word
        warnings = list()
        content = self.get_page_content()
        self.check_status_code(content)
        bs = bs4.BeautifulSoup(content.content, "html5lib")
        translations = self.fetch_data(bs, "dtText")
        [warnings.append(msg) for msg in self.check_for_warning(bs)]
        return translations, [""] * len(translations), warnings

    def get_page_content(self):
        url = self.dict_url.replace("|PHRASE|", self.word)
        html = requests.get(url, timeout=self.timeout)
        return html

    def fetch_data(self, bs: bs4.BeautifulSoup, class_name: str):
        translations = list()
        for row in bs.find_all("span", attrs={"class": class_name}):
            text_ = "".join([word.get_text() for word in row]).strip()
            # text_ = re.sub('xxx', '', text_)
            translations.append(text_[2:])
        return translations

    def check_for_warning(self, bs: bs4.BeautifulSoup):
        output = list()
        alerts = bs.find_all("p", attrs={"class": "spelling-suggestions"})
        if alerts:
            output.append("The word you've entered isn't in the dictionary")
            output.append(" | ".join([word.get_text().strip() for word in alerts]))
        return output


@register_dict("babla")
class DictBabla(TemplateDict):

    def __init__(self):
        super().__init__()
        self.dict_url = "https://en.bab.la/dictionary/|ORIGINAL|-|TRANSLATION|/|PHRASE|"
        self.babla_mapping = dict(
            en="english",
            pl="polish",
            jp="japanese",
            de="german",
            ru="russian",
        )

    def get(self, word: str):
        self.word = word
        warnings = list()
        re_patterns = OrderedDict()
        content = self.get_page_content()
        self.check_status_code(content)
        bs = bs4.BeautifulSoup(content.content, "html5lib")
        warnings = self.check_for_warning(bs)
        originals = self.fetch_data_source(bs) if not warnings else list()
        translations = self.fetch_data_target(bs) if not warnings else list()
        for r, s in re_patterns.items():
            translations = [re.sub(r, s, text_) for text_ in translations]
            originals = [re.sub(r, s, text_) for text_ in originals]

        return translations[: len(originals)], originals, warnings

    def get_page_content(self):
        url = self.dict_url.replace("|PHRASE|", self.word)
        url = url.replace("|ORIGINAL|", self.babla_mapping[self.source_lng])
        url = url.replace("|TRANSLATION|", self.babla_mapping[self.target_lng])
        html = requests.get(url, headers=self.headers, timeout=self.timeout)
        return html

    def fetch_data_source(self, bs: bs4.BeautifulSoup):
        res = list()
        bs_res = bs.find_all("a", attrs={"class": "babQuickResult"})
        for word in bs_res:
            text_ = ", ".join(
                [
                    w.strip().replace("\n", "")
                    for w in word
                    if len(w) > 1
                    and not any(
                        {
                            i in w
                            for i in {
                                "volume_up",
                                "Translations",
                                "Monolingual examples",
                                "Collocations",
                                "Synonyms",
                                "Context sentences",
                            }
                        }
                    )
                ]
            )
            if text_:
                res.append(text_)
        return res

    def fetch_data_target(self, bs: bs4.BeautifulSoup):
        res = list()
        uls = bs.find_all(
            lambda tag: tag.name == "ul" and tag.get("class") == ["sense-group-results"]
        )
        for li in uls:
            li = ", ".join(
                [
                    i.get_text().replace("volume_up\n", "").strip()
                    for i in li
                    if len(i.get_text().replace("volume_up\n", "").strip()) > 1
                ]
            )
            res.append(li)
        return res

    def check_for_warning(self, bs: bs4.BeautifulSoup):
        if not bs.find("ul", attrs={"class": "did-you-mean"}):
            return list()

        output = list()
        alerts = bs.find(attrs={"class": "did-you-mean"})
        if alerts:
            sim_res = alerts.find_all("li")
            if sim_res:
                output.append("Did you mean:")
                output.append(
                    " | ".join(
                        [
                            word.get_text().replace("volume_up\n", "").strip()
                            for word in sim_res
                        ]
                    )
                )
        return output


@register_dict("diki")
class DictDiki(TemplateDict):

    def __init__(self):
        super().__init__()
        self.dict_url = "https://www.diki.pl/slownik-|TRANSLATION|?q=|PHRASE|"
        self.diki_mapping = dict(
            en="angielskiego",
            de="niemieckiego",
        )

    def get(self, word: str):
        self.word = word
        warnings = list()
        content = self.get_page_content()
        self.check_status_code(content)
        bs = bs4.BeautifulSoup(content.content, "html5lib")
        warnings = self.check_for_warning(bs)
        originals = self.fetch_data_source(bs) if not warnings else list()
        translations = self.fetch_data_target(bs) if not warnings else list()
        if len(originals) < len(translations):
            originals += [originals[0]] * (len(translations) - len(originals))
        elif len(originals) > len(translations):
            translations += [translations[0]] * (len(originals) - len(translations))
        return translations, originals, warnings

    def get_page_content(self):
        url = self.dict_url.replace("|PHRASE|", self.word)
        url = url.replace(
            "|TRANSLATION|",
            self.diki_mapping.get(self.target_lng, self.diki_mapping["en"]),
        )
        html = requests.get(url, headers=self.headers, timeout=self.timeout)
        return html

    def fetch_data_source(self, bs: bs4.BeautifulSoup):
        # diki returns different results when translating
        # from language that is not in the service e.g. PL
        if self.source_lng in self.diki_mapping.keys():
            res = self._fetch_data_source_incl(bs)
        else:
            res = self._fetch_data_source_excl(bs)
        return res

    def _fetch_data_source_incl(self, bs: bs4.BeautifulSoup):
        tags = {r"\*": "", r" [a-zA-Z]* dawne użycie": ""}
        res = list()
        bs_res = bs.find_all("div", class_="hws")
        for word in bs_res:
            text_ = " ".join(word.text.split())
            for t, r in tags.items():
                text_ = re.sub(t, r, text_)
            res.append(text_.strip())
        return res

    def _fetch_data_source_excl(self, bs: bs4.BeautifulSoup):
        res = list()
        ul = bs.find_all("ul", class_="nativeToForeignMeanings")
        for i, v in enumerate(ul):
            transl = ", ".join([a.text for a in ul[i].find_all("span", "hw")])
            transl = " ".join([w.strip() for w in transl.split()])
            res.append(transl or "N/A")

            context_transl = ", ".join([a.text for a in ul[i].find_all("div", "cat")])
            context_transl = " ".join([w.strip() for w in context_transl.split()])
            try:
                if context_transl:
                    res.insert(-2, context_transl)
            except IndexError:
                pass
        return res

    def fetch_data_target(self, bs: bs4.BeautifulSoup):
        if self.source_lng in self.diki_mapping.keys():
            res = self._fetch_data_target_incl(bs)
        else:
            res = self._fetch_data_target_excl(bs)
        return res

    def _fetch_data_target_incl(self, bs: bs4.BeautifulSoup):
        tags = ["oficjalnie", "policzalny", "Słownik żeglarski", "[]"]
        res = list()
        li = bs.find_all("li", class_=re.compile(r"meaning\d+"))
        for i, v in enumerate(li):
            transl = ", ".join([w.text for w in li[i].find_all("span", class_="hw")])
            for t in tags:
                transl = transl.replace(t, "")
            transl = " ".join([w.strip() for w in transl.split()])
            if transl:
                res.append(transl)
        return res

    def _fetch_data_target_excl(self, bs: bs4.BeautifulSoup):
        res = list()
        ol = bs.find("ol", class_="nativeToForeignEntrySlices")
        for li in ol.find_all("li", recursive=False):
            transl = ", ".join(
                [a.text for a in li.find_all("span", "hw", recursive=False)]
            )
            transl = " ".join([w.strip() for w in transl.split()])
            res.append(transl or "N/A")
        return res

    def check_for_warning(self, bs: bs4.BeautifulSoup):
        warn = bs.find("div", class_="dictionarySuggestions")
        if warn:
            return [warn.text.replace("\n", "").strip()]
        else:
            return list()


@register_dict("local")
class DictLocal(TemplateDict):

    def __init__(self):
        super().__init__()

    def get(self, word: str):
        try:
            from_native = self.source_lng == SOD.file_handler.ACTIVE_FH.native_lng
            if config["SOD"]["use_regex"]:
                transl, orig = SOD.file_handler.ACTIVE_FH.get_translations_with_regex(
                    word, from_native
                )
            else:
                transl, orig = SOD.file_handler.ACTIVE_FH.get_translations(
                    word, from_native
                )
            if transl:
                err = []
            else:
                raise KeyError
        except KeyError:
            transl, orig, err = [], [], []
        except re.error as e:
            transl, orig, err = [], [], [f"⚠ Regex Error: {str(e)}"]
        return transl, orig, err


class Dict_Services:
    # source_lng - from which language user wants to translate -->> target_lng - to which lng ...
    # dict_service - which dict is currently selected

    def __init__(self):
        self.dicts: dict = dict_services
        self.available_dicts = set(self.dicts.keys())
        self.available_dicts_short = set(v["shortname"] for v in self.dicts.values())
        self.dict_service: str = config["SOD"]["dict_service"]
        self.word = None
        self.mute_warning = False
        self.source_lng = None
        self.target_lng = None

    def __getitem__(self, key):
        return self.dicts[key]["service"]

    @property
    def available_lngs(self) -> tuple:
        return (self.source_lng, self.target_lng)

    def set_dict_service(self, dict_service):
        if dict_service in self.available_dicts:
            self.dict_service = dict_service
            config["SOD"].update({"dict_service": dict_service})

    def switch_languages(self, src_lng: str = None, tgt_lng: str = None):
            if src_lng and tgt_lng:
                if src_lng != tgt_lng:
                    self.source_lng = src_lng
                    self.target_lng = tgt_lng
            elif not src_lng and not tgt_lng:
                src, tgt = self.source_lng, self.target_lng
                self.source_lng = tgt
                self.target_lng = src
            elif src_lng == self.target_lng:
                self.set_target_language(self.source_lng)
                self.set_source_language(src_lng)
            elif src_lng != self.source_lng:
                self.set_source_language(src_lng)
                self.set_target_language(tgt_lng)

    def set_source_language(self, src_lng=None):
        if src_lng:
            self.source_lng = src_lng

    def set_target_language(self, tgt_lng=None):
        if tgt_lng:
            self.target_lng = tgt_lng

    def get_info_about_phrase(self, word: str) -> tuple[list, list, list]:
        try:
            self.dicts[self.dict_service]["service"].set_languages(
                self.source_lng, self.target_lng
            )
            trans, orig, warn = self.dicts[self.dict_service]["service"].get(word)
        except requests.exceptions.ConnectionError:
            trans, orig, warn = [], [], ["🌐 No Internet Connection"]
        except requests.exceptions.Timeout:
            trans, orig, warn = [], [], ["⏲ Request Timed Out"]
        except requests.exceptions.RequestException:
            rs = self.dicts[self.dict_service]["service"].req_status
            trans, orig, warn = [], [], [ReqExcMsg.get(rs, f"⨷ Unknown Error: {rs}!")]
        except AttributeError as e:
            trans, orig, warn = [], [], ["⎙ Scraping Error"]
            log.error(e, exc_info=True)
        except Exception as e:
            trans, orig, warn = [], [], ["⨷ Unknown Error"]
            log.error(e, exc_info=True)
        return trans, orig, warn
