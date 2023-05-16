import openpyxl
from collections import OrderedDict
from utils import Config



class file_handler:

    def __init__(self, path, ws):
        self.config = Config()
        self.marked_duplicates = set()
        self.path = path
        self.wb = openpyxl.load_workbook(self.path)
        self.ws = self.wb[ws]
        self.data = OrderedDict()  # phrase: (translation, row_index)
        for r in range(1, self.ws.max_row+1):
            self.data[self.ws.cell(r, 1).value] = (self.ws.cell(r, 2).value, r)

    @property
    def is_from_native(self) -> bool:
        return self.config['sod_source_lng']==self.config['native_lng']
    

    def append_content(self, foreign_word, domestic_word) -> tuple[bool, str]:  
        if foreign_word in self.marked_duplicates:
            s, msg = self.__edit_existing(foreign_word, domestic_word)
        else:
            s, msg = self.__append_new(foreign_word, domestic_word)
        self.wb.save(self.path)
        return s, msg


    def __append_new(self, foreign_word, domestic_word) -> tuple[bool, str]:    
        target_row = self.ws.max_row + 1
        if self.ws.cell(row=target_row, column=1).value is None:
            self.ws.cell(row=target_row, column=1, value=foreign_word)
            self.ws.cell(row=target_row, column=2, value=domestic_word)
            self.data[foreign_word] = (domestic_word, target_row)
            return True, ''
        else:
            return False, '[WARNING] Target Cell is not empty!'

    
    def __edit_existing(self, foreign_word, domestic_word):
        target_row = self.data[foreign_word][1]
        self.ws.cell(row=target_row, column=1, value=foreign_word)
        self.ws.cell(row=target_row, column=2, value=domestic_word)
        self.marked_duplicates.remove(foreign_word)
        return True, ''


    def is_duplicate(self, word) -> bool:
        '''find duplicate, matching source_lng or native_lng'''
        if self.is_from_native:
            return word in {r[0] for r in self.data.values()}
        else:
            return word in self.data.keys()

    
    def get_translations(self, phrase:str) -> str:
        if self.is_from_native:
            for k, v in self.data.items():
                if v[0] == phrase:
                    return k
        else:
            return self.data[phrase][0]
        

    def close(self):
        self.wb.close()
