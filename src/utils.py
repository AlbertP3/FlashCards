from PyQt5.QtGui import QFontMetricsF
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
        self.DICT_PATH = './src/res/config.json'
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
        res = f"{total_seconds/_int:.0f}"
    
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
    '''Works on pixels!'''

    def __init__(self, fmetrics:QFontMetricsF):
        self.fmetrics = fmetrics
        self.scw = self.fmetrics.widthChar('W') # Standard Character Width
        self.sch = self.fmetrics.height()       # Standard Character Height

    @cache
    def pixlen(self, char:str) -> float:
        return self.fmetrics.width(char)

    def strwidth(self, text:str) -> float:
        return sum(self.pixlen(c) for c in text)

    def abbreviate(self, text:str, pixlim:float) -> str:
        '''Trims text to the given pixel-length'''
        excess = self.strwidth(text) - pixlim
        if excess <= 0:
            return text
        else:
            try:
                i = 0
                while excess > 0:
                    i -= 1
                    excess -= self.strwidth(text[i])
            except IndexError:
                return text
            else:
                return text[:i]

    def make_cell(self, text:str, pixlim:float, suffix:str='…', align:str='left', 
                  filler:str='\u2009'
                ) -> str:
        if text.isascii():
            rem_text = self.abbreviate(text, pixlim)
            out = deque(rem_text)
            pixlim -= self.strwidth(rem_text)
            should_add_suffix = pixlim <= self.scw
        else:
            out = deque()
            for c in unicodedata.normalize('NFKC', text):
                len_c = self.pixlen(c)
                if pixlim >= len_c:
                    out.append(c)
                    pixlim-=len_c
                else:
                    should_add_suffix = True
                    break
            else:
                should_add_suffix = False
  
        if should_add_suffix:
            suf_len = self.strwidth(suffix)
            try:
                while pixlim < suf_len:
                    pixlim += self.pixlen(out.pop())
            except IndexError:
                pass
            out.append(suffix)
            pixlim -= suf_len

        if align == 'center':
            d, r = divmod(pixlim, 2)
            lpad = filler * int(round((d+r) /  self.strwidth(filler), 0))
            rpad = filler * int(round(d /  self.strwidth(filler), 0))
        else:
            pad = filler * int(round(pixlim /  self.strwidth(filler), 0))
            lpad = pad if align == 'right' else ''
            rpad = pad if align == 'left' else ''

        return lpad + ''.join(out) + rpad
    
    def make_table(self, 
                    data:list[list], 
                    pixlim:Union[float, list], 
                    headers:list=None, 
                    suffix='…', 
                    align:Union[str, list]='left', 
                    filler:str='\u2009', 
                    sep:str=" | ",
                    keep_last_border:bool=True):
        if isinstance(pixlim, (float, int)):
            part = pixlim / len(data[0])
            pixlim = [part for _ in range(len(data[0]))]
        sepw = (self.pixlen(sep) * (len(data[0]))-int(keep_last_border)) / len(data[0])
        for i, p in enumerate(pixlim):
            pixlim[i] = p - sepw
        if isinstance(align, str):
            align = [align for _ in range(len(data[0]))]
        if headers:
            data = [headers] + data
        out = list()
        for row in data:
            new_row = ""
            for i, text in enumerate(row):
                new_row += self.make_cell(
                    text, 
                    pixlim=pixlim[i], 
                    suffix=suffix,
                    align=align[i],
                    filler=filler
                ) + sep
            if not keep_last_border:
                new_row = new_row[:-len(sep)]
            out.append(new_row)
        return "\n".join(out)
