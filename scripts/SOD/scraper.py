from SOD.dicts import Dict_Services
from utils import Config

class dict_api:

    def __init__(self):
        # source_lng - from which language user wants to translate -->> target_lng - to which lng ...
        self.config = Config()
        self.WORDS_LIMIT = 8
        self.DEFAULT_SOURCE_LNG = self.config['sod_source_lng']
        self.DEFAULT_TARGET_LNG = self.config['sod_target_lng']
        self.dict_service = self.config['sod_dict_service']
        self.dict_services = Dict_Services()
        self.word = None
        self.mute_warning = False
        self.source_lng = self.DEFAULT_SOURCE_LNG
        self.target_lng = self.DEFAULT_TARGET_LNG
        

    def get_available_dicts(self):
        return self.dict_services.get_available_dicts()


    def set_dict_service(self, dict_service):
        if dict_service in self.dict_services.get_available_dicts():
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


    def get_dict_service(self):
        return self.dict_service


    def get_info_about_phrase(self, word:str) -> list:
        trans, orig, warn = self.dict_services[self.dict_service].get(word)
        return trans[:self.WORDS_LIMIT], orig[:self.WORDS_LIMIT], warn

