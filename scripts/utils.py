from collections import UserDict, deque
from functools import cache
from datetime import timedelta
import unicodedata
import os
import pandas as pd
import json
import inspect
from time import perf_counter
import logging
from typing import Union

log = logging.getLogger(__name__)



class FccQueue:
    '''Collects messages to be displayed in the console'''

    def __init__(self):
        self.queue = deque()
    
    def put(self, record:str):
        if record:
            self.queue.append(record)
        
    def pull(self):
        return self.queue.popleft()
    
    def dump(self):
        res = list(self.queue)
        self.queue.clear()
        return res

fcc_queue = FccQueue() 


def perftm(func):
    def timed(*args, **kwargs):
        caller = inspect.stack()[1][3]
        t1 = perf_counter() 
        result = func(*args, **kwargs)
        t2 = perf_counter()
        log.debug(f'{func.__name__} called by {caller} took {(t2-t1)*1000:0.4f}ms', stacklevel=2)
        return result
    return timed
        

def singleton(cls):
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance


@singleton
class Config(UserDict):
    def __init__(self):
        self.DICT_PATH = './scripts/resources/config.json'
        self.default_off_values = {'off', 'no', 'none', ''}
        self.data = json.load(open(self.DICT_PATH, 'r'))

    def save(self):
        json.dump(
            self.data, 
            open(self.DICT_PATH, 'w'), 
            indent=4, 
            ensure_ascii=False
        )
        log.debug("Config saved")

    def translate(self, key, val_on=None, val_off=None, off_values:set=None):
        if self.data[key] in (off_values or self.default_off_values):
            return val_off
        else:
            return val_on or self.data[key]

config = Config()


def get_filename_from_path(path, include_extension=False):
    filename = os.path.basename(path)
    if not include_extension:
        filename = filename.split('.')[0]
    return filename 


def get_sign(num, plus_sign='+', neg_sign='-'):
    if num > 0:
        return plus_sign
    elif num < 0:
        return neg_sign
    else:
        return ''


def get_files_in_dir(path, include_extension = True, exclude_open=True):
    files_list = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f not in {'desktop.ini'}]
    if not include_extension:
        files_list = [f.split('.')[0] for f in files_list]
    if exclude_open:
        # exclude locks for open files for OS: Linux, Windows
        files_list[:] = [f for f in files_list if not any(f.startswith(tmp) for tmp in {'~$','.~'})]
    return files_list


def format_timedelta(tmd:timedelta): 
    if tmd.days >= 365:
        interval, time_value = 'year',  round(tmd.days/365.25, 1)
    elif tmd.days >= 31:
        interval, time_value = 'month', round(tmd.days/30.437, 1)
    elif tmd.days >= 1 :
        interval, time_value = 'day', round(tmd.total_seconds()/86_400, 0)
    elif tmd.total_seconds() >= 3600:
        interval, time_value = 'hour', round(tmd.total_seconds()/3600, 0)
    elif tmd.total_seconds() >= 60:
        interval, time_value = 'minute', round(tmd.total_seconds()/60, 0)
    else:
        interval, time_value = 'second', round(tmd.total_seconds(), 0)

    suffix = '' if int(time_value) == 1 else 's'
    prec = 0 if int(time_value) == time_value else '1'    
    return f'{time_value:.{prec}f} {interval}{suffix}'


def validate_setup():
    operation_status = ""

    if config['db_path'].split('/')[-1] not in [f for f in os.listdir(config['resources_path'])]:
        operation_status += 'Initializing new Database\n'
        pd.DataFrame(columns=['TIMESTAMP','SIGNATURE', 'LNG', 'TOTAL','POSITIVES', 'SEC_SPENT']).to_csv(config['db_path'], sep=';')

    lngs_dir_name = os.path.normpath(config['lngs_path'])
    if lngs_dir_name not in [f for f in os.listdir('.')]:
        operation_status += 'Creating Lngs dir\n'
        os.mkdir(lngs_dir_name)

    revs_dir_name = os.path.normpath(config['revs_path'])
    if revs_dir_name not in [f for f in os.listdir('.')]:
        operation_status += 'Creating revs dir\n'
        os.mkdir(revs_dir_name)

    mstk_dir_name = os.path.normpath(config['mistakes_path'])
    if mstk_dir_name not in [f for f in os.listdir('.')]:
        operation_status += 'Creating revs dir\n'
        os.mkdir(mstk_dir_name)

    fcc_queue.put(operation_status)


# TODO replace with Caliper.make_table
def get_pretty_print(list_, extra_indent=1, separator='', keep_last_border=False, alingment:list=list(), headers:list=None) -> str:
    printout = '' 
    longest_elements = list()

    # convert to list
    if isinstance(list_, dict):
        list_ = [[k, v] for k, v in list_.items()]

    if headers:
        list_.insert(0, headers)
        
    # find longest element for each sub-list
    for k in range(len(list_[0])):
        longest_elements.append(max([len(str(item[k])) for item in list_]))

    alingment += ['^'] * (len(list_) - len(alingment))
    for item in list_:
        line = ''
        for sub_index, sub_item in enumerate(item):
            i = longest_elements[sub_index]+extra_indent
            a = alingment[sub_index]
            rpad = ' ' if a=='>' else ''
            lpad = ' ' if a=='<' else ''
            line+=f'{lpad}{sub_item:{a}{i}}{rpad}{separator}'
        if not keep_last_border and separator: line=line[:-len(separator)] 
        printout += line + '\n'
    
    return printout[:-1]


SECONDS_CONVERTERS = {
    'minute': (60, 1),
    'hour':  (3600, 60),
    'day': (86400, 3600),
    'week': (604800, 86400),
    'month': (18408297.6, 604800),
    'year': (220899571.2, 18408297.6)
}
def format_seconds_to(
        total_seconds:int, interval:str, rem:int=1, int_name:str=None, 
        null_format:str=None, pref_len=0, sep='.'
    ) -> str:
    _int, _prev_int = SECONDS_CONVERTERS[interval]
    tot_int, _rem = divmod(total_seconds, _int)
    rem_int = int(_rem // _prev_int)
    
    if null_format is not None and tot_int + rem_int == 0:
        res = null_format
    elif rem:
        res = f'{tot_int:.0f}{sep}{rem_int:0{rem}d}'
    else:
        res = f"{tot_int:.0f}"
    
    if int_name:
        postfix = ('', 's')[tot_int>=2]
        res = f"{res} {int_name}{postfix}"

    if pref_len != 0:
        res = res[:pref_len].rjust(pref_len, ' ')
        if res.endswith(sep):
            res = res[:-1] + ' '

    return res


class Placeholder:
    pass


def flatten_dict(d:dict, root:str='BASE', lim_chars:int=None) -> list:
    res = list([root, k, str(v)] for k, v in d.items() if not isinstance(v, dict))
    for k, v in d.items():
        if isinstance(v, dict):
            res.extend(flatten_dict(v, root=k))
    if lim_chars:
        res = [[str(x)[:lim_chars] for x in i] for i in res]
    return res


class Caliper:
    def __init__(self, fmetrics):
        self.fmetrics = fmetrics
        self.WIDTHS = {
            'F': 2, 'H': 1, 'W': 2,
            'N': 2, 'A': 1, 'Na': 1
        }
    
    @cache
    def charlen(self, char:str) -> int:
        return self.WIDTHS[unicodedata.east_asian_width(char)]

    def strlen(self, text:str) -> int:
        return sum(self.charlen(c) for c in text)

    def chrlim(self, width:int, char='W') -> int:
        return int(width / self.fmetrics.widthChar(char))

    def make_cell(self, text:str, lim:int, suffix:str='… ', align:str='left', filler:str=' ') -> str:
        if text.isascii():
            out = list(text[:lim])
            lim -= len(text[:lim])
            should_add_suffix = lim == 0
        else:
            out = list()
            for c in unicodedata.normalize('NFKC', text):
                len_c = self.charlen(c)
                if lim >= len_c:
                    out.append(c)
                    lim-=len_c
                else:
                    should_add_suffix = True
                    break
            else:
                should_add_suffix = False
        
        if should_add_suffix:
            suf_len = self.strlen(suffix)
            while lim < suf_len:
                lim+=self.charlen(out.pop())
            out += suffix
            lim -= suf_len
        
        if align == 'center':
            d, r = int(lim//2), lim%2
            llim, rlim = d + r, d
            rpad, lpad = filler, filler
        else:
            llim, rlim = lim, lim
            rpad, lpad = filler*bool(align=='left'), filler*bool(align=='right')

        return lpad*llim + ''.join(out) + rpad*rlim

    
    def make_table(self, data:list, lim:Union[float, list], headers:list=None, suffix='... ', align:Union[str, list]='left', filler:str=' '):
        ...
