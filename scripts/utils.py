import random
from collections import UserDict
from functools import lru_cache
from datetime import datetime, timedelta
import os
import pandas as pd
import re
import configparser
import csv
import inspect
from time import perf_counter
import inspect
import logging
from ntpath import basename

UTILS_STATUS_DICT = dict()
log = logging.getLogger(__name__)


def timer(func):
    def timed(*args, **kwargs):
        caller = inspect.stack()[1][3]
        t1 = perf_counter() 
        result = func(*args, **kwargs)
        t2 = perf_counter()
        log.info(f'{func.__name__} called by {caller} took {(t2-t1)*1000:0.4f}ms', stacklevel=2)
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
        self.PATH_TO_DICT = './scripts/resources/config.ini'
        self.iterable_fields:set= {'languages', 'optional'}
        self.iter_sep = ','
        self.parser = configparser.RawConfigParser(inline_comment_prefixes=None)
        self.__refresh()
    
    def __refresh(self):
        self.parser.read(self.PATH_TO_DICT)
        self.default_section = self.parser.sections()[0]
        self.sections = self.parser.sections()[1:]
        self.data = dict(self.parser.items(self.default_section))
        for s in self.sections:
            self.data[s] = dict(self.parser.items(s))
        self.parse_items()

    def save(self):
        for field in self.iterable_fields:
            self.data[field] = self.iter_sep.join(self.data[field])
        for k, v in self.data.items():
            if k in self.sections: [self.parser.set(k, k_, v_) for k_, v_ in v.items()]
            else: self.parser.set(self.default_section, k, v)
        with open(self.PATH_TO_DICT, 'w') as configfile:
            self.parser.write(configfile)

    def parse_items(self):
        for field in self.iterable_fields:
            if not isinstance(self.data[field], list):
                self.data[field] = self.data[field].split(self.iter_sep)
        for window, geometry in self.data['GEOMETRY'].items():
            if not isinstance(geometry, tuple):
                self.data['GEOMETRY'][window] = tuple(eval(geometry))

config = Config()

def post_utils(text):
    caller_function = inspect.stack()[1].function
    UTILS_STATUS_DICT[caller_function] = text


def get_abs_path_from_caller(file_name, abs_path=None):
    from os import path
    from inspect import stack
    if abs_path is None:
        abs_path = path.abspath((stack()[1])[1])
        abs_path = path.join(path.dirname(abs_path), file_name)
    return abs_path


def get_filename_from_path(path, include_extension=False):
    if include_extension:
        filename = basename(path)
    else:
        filename = (basename(path)).split('.')[0]
    return filename 


def get_sign(num, plus_sign='+', neg_sign='-'):
    if num > 0:
        return plus_sign
    elif num < 0:
        return neg_sign
    else:
        return ''


def make_datetime(d):
    return datetime.strptime(d, '%m/%d/%Y, %H:%M:%S')


def save_revision(dataset:pd.DataFrame(), signature):
    try:
        dataset.to_csv(os.path.join(config['revs_path'], f"{signature}.csv"), index=False)
        save_success = True
        post_utils(f'{signature} successfully saved')
    except PermissionError:
        post_utils('Permission Denied. Please close the file before modifications')
        save_success = False
    return save_success
     

def get_most_similar_file_regex(path, lookup_file, if_nothing_found='load_any'):
    files = get_files_in_dir(path)
    for file in files:
        if re.match(lookup_file.lower(), file.lower()) is not None:
            return file
            
    if if_nothing_found == 'load_any':
        return files[0] 
    

def get_most_similar_file_startswith(path, lookup_file, if_nothing_found='load_any'):
    files = sorted(get_files_in_dir(path, include_extension=True), reverse=True)
    for file in files:
        if file.lower().startswith(lookup_file.lower()):
            return file
            
    if if_nothing_found == 'load_any':
        return files[0] 



def remove_layout(layout):
    # https://stackoverflow.com/questions/37564728/pyqt-how-to-remove-a-layout-from-a-layout
     if layout is not None:
         while layout.count():
             item = layout.takeAt(0)
             widget = item.widget()
             if widget is not None:
                 widget.setParent(None)
             else:
                 remove_layout(item.layout())


def get_children_layouts(layout):
    layouts = list()
    for l in layout.children():
        layouts.append(l)
        for w in range(l.count()):
            wdg = l.itemAt(w).widget()
            if wdg is None:
                layouts.append(l.itemAt(w))
    return layouts


def get_children_widgets(layout):
    widgets = list()
    for i in range(layout.count()):
            w = layout.itemAt(i)
            if w is not None:
                widgets.append(w.widget())
    return widgets


def get_files_in_dir(path, include_extension = True, exclude_open=True):
    files_list = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    if not include_extension:
        files_list = [f.split('.')[0] for f in files_list if f not in ['desktop.ini']]
    if exclude_open:
        # exclude locks for open files for OS: Linux, Windows
        files_list[:] = [f for f in files_list if not f.startswith('.~') or f.startswith('~$')]
    return files_list


def format_timedelta(tmd:timedelta): 
    if tmd.days > 365:
        interval, time_value = 'year',  round(tmd.days/365.25, 1)
    elif tmd.days > 31:
        interval, time_value = 'month', round(tmd.days/30.437, 1)
    elif tmd.days > 1 :
        interval, time_value = 'day', round(tmd.days, 1)
    elif tmd.total_seconds() > 3600:
        interval, time_value = 'hour', round(tmd.total_seconds()/3600, 0)
    elif tmd.total_seconds() > 60:
        interval, time_value = 'minute', round(tmd.total_seconds()/60, 0)
    else:
        interval, time_value = 'second', round(tmd.total_seconds(), 0)

    suffix = '' if int(time_value) == 1 else 's'
    prec = 0 if int(time_value) == time_value else '1'    
    return f'{time_value:.{prec}f} {interval}{suffix}'


def format_seconds(total_seconds):
    hours = total_seconds // 3600
    minutes = round((total_seconds % 3600)/60,0)
    leading_zero = '0' if minutes <= 9 else ''
    if hours == 0:
        s = '' if int(minutes) == 1 else 's'
        res = f'{minutes:.0f} minute{s}'
    else:
        s = '' if int(hours) == 1 else 's'
        res = f'{hours:.0f}:{leading_zero}{minutes:.0f} hour{s}'
    return res


def get_signature(file_name, lng_gist, is_revision):
        # create unique signature for currently loaded rev
        # or return filename for lng
        # Special Case - mistakes list -> return file name
        
        if is_revision or '_mistakes' in file_name:
            signature = file_name
        else:
            # update_signature_timestamp() is directly dependent on this format
            saving_date = datetime.now().strftime('%m%d%Y%H%M%S')
            signature = 'REV_' + lng_gist + saving_date
        return signature


def update_signature_timestamp(signature):
    # Tighly coupled with get_signature
    updated_signature = signature[:6] + datetime.now().strftime('%m%d%Y%H%M%S')
    return updated_signature


def get_lng_from_signature(signature):
    for lng in config['languages']:
        if lng in signature:
            matched_lng = lng
            break
    else:
        matched_lng = 'UNKNOWN'
    return matched_lng


def load_dataset(file_path, do_shuffle=True, seed=None):
    _, extension = os.path.splitext(file_path)
    operation_status = ''
    
    # Choose File Extension Handler
    try:
        if extension in ['.csv', '.txt']:
            dataset = read_csv(file_path)
        elif extension in ['.xlsx', '.xlsm']:  
            dataset = read_excel(file_path)
        elif extension in ['.odf']:
            dataset = pd.read_excel(file_path, engine='odf')
        else:
            dataset = pd.DataFrame()
            operation_status = f'Chosen extension is not (yet) supported: {extension}'
    except FileNotFoundError as e:
        operation_status = 'File Not Found'
        dataset = pd.DataFrame()
    except Exception as e:
        operation_status = f'Exception occurred: {e}'
        dataset = pd.DataFrame()

    if do_shuffle:
        dataset = shuffle_dataset(dataset, seed)

    post_utils(operation_status)
    return dataset


def shuffle_dataset(dataset:pd.DataFrame, seed=None):
    if not seed: pd_random_seed = random.randrange(10000)
    else: pd_random_seed = config['pd_random_seed']
    config.update({'pd_random_seed':pd_random_seed})
    return dataset.sample(frac=1, random_state=pd_random_seed).reset_index(drop=True)


CSV_SNIFFER = None
def set_csv_sniffer():
    global CSV_SNIFFER
    CSV_SNIFFER = None if config['csv_sniffer'] == 'off' else config['csv_sniffer']
set_csv_sniffer()


def read_csv(file_path):
    delim = get_dialect(file_path) if CSV_SNIFFER else ','
    dataset = pd.read_csv(file_path, encoding='utf-8',sep=delim)   
    return dataset


def get_dialect(dataset_path, investigate_rows=10):
    data = list()
    with open(dataset_path, 'r', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        for r in csvreader:
            data.append(r)
            if len(data)>=investigate_rows:
                break
    return csv.Sniffer().sniff(str(data[1]) + '\n' + str(data[2]), delimiters=CSV_SNIFFER).delimiter


def read_excel(file_path):
    sht_id = 0
    return pd.read_excel(file_path, sheet_name=sht_id)


def dataset_is_valid(dataset:pd.DataFrame):
    rows_count = dataset.shape[0]
    cols_count = dataset.shape[1]
    if rows_count < 1:
        operation_status = 'Not enough rows'
        is_valid = False
    elif cols_count == 2:
        operation_status = 'OK'
        is_valid = True
    elif cols_count > 2:
        operation_status = f'Selected file has {cols_count} columns. Only first 2 will be loaded'
        is_valid = True  # as dataset is still viable
    elif cols_count < 2:
        operation_status = 'Selected file is invalid - not enough columns. Min is 2.'
        is_valid = False
    
    post_utils(operation_status)
    return is_valid


def validate_setup():
    operation_status = ""

    # Database
    if config['db_path'].split('/')[-1] not in [f for f in os.listdir(config['resources_path'])]:
        operation_status += 'Initializing new Database\n'
        pd.DataFrame(columns=['TIMESTAMP','SIGNATURE','TOTAL','POSITIVES', 'SEC_SPENT']).to_csv(config['db_path'], sep=';')

    # Lngs folder
    lngs_dir_name = os.path.normpath(config['lngs_path'])
    if lngs_dir_name not in [f for f in os.listdir('.')]:
        operation_status += 'Creating Lngs dir\n'
        os.mkdir('./' + lngs_dir_name)

    # Revs folder
    revs_dir_name = os.path.normpath(config['revs_path'])
    if revs_dir_name not in [f for f in os.listdir('.')]:
        operation_status += 'Creating revs dir\n'
        os.mkdir('./' + revs_dir_name)

    post_utils(operation_status)


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


def format_seconds_to(total_seconds:int, interval:str, include_remainder=True, null_format:str=None, max_len=0, fmt:str=None) -> str:
    if interval == 'hour':
        prev_interval = 60
        interval = 3600
        sep = ':'
    elif interval == 'minute':
        prev_interval = 1
        interval = 60
        sep = ':'
    elif interval == 'day':
        prev_interval = 3600
        interval = 86400
        sep = '.'
    elif interval == 'week':
        prev_interval = 86400
        interval = 604800
        sep = '.'
    elif interval == 'month':
        prev_interval = 604800
        interval = 18408297.6
        sep = '.'
    elif interval == 'year':
        prev_interval = 18408297.6
        interval = 220899571.2
        sep = '.'
    
    total_intervals = total_seconds // interval
    remaining_intervals = (abs(total_seconds) % interval)/prev_interval
    
    if null_format is not None and total_intervals + remaining_intervals == 0:
        res = null_format
    elif include_remainder:
        res = f'{round(total_intervals, 0):0>2.0f}{sep}{round(remaining_intervals,0):0>2.0f}'
    else:
        res = f"{round(total_intervals, 0):.0f}"
    
    if max_len != 0 and len(res) > max_len and include_remainder:
        # remove remainder and the colon
        res = res.split(':')[0].rjust(max_len, ' ')

    return res


def filter_with_list(filter_, list_, case_sensitive=True):
    res = list()
    for i in list_:
        for k in filter_:
            if in_str(k, i, case_sensitive):
                res.append(i)
    return res


def in_str(sub_string, string, case_sensitive=True):
    if case_sensitive:
        return sub_string in string
    else:
        return sub_string.casefold() in string.casefold()

true_values = {'yes', '1', 'true', 'on', True}
def boolinize(s:str):
    return s.lower() in true_values

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


@singleton
class Caliper:
    def __init__(self):
        self.re_ewc = re.compile(r"[\u04FF-\uFFFF]", re.IGNORECASE)

    @lru_cache(maxsize=1024)
    def exlen(self, text:str) -> int:
        '''Returns printable extra width'''
        return len(self.re_ewc.findall(text))

    def strlen(self, text:str) -> int:
        '''Get <text> length while accounting for non-standard width chars'''
        return len(text) + self.exlen(text)
    
    def make_cell(self, text:str, rlim:int, ioff:int=0, suffix:str='… ') -> str:
            lsw = False
            if self.strlen(text) + ioff > rlim:
                free = rlim - ioff - len(suffix)
                c, ewcs = '', self.re_ewc.findall(text)
                for t in text:
                    free -= 2 if t in ewcs else 1
                    if free >= 0:
                        c += t
                    else:
                        lsw = t in ewcs
                        break
                text = c + suffix
            plim = rlim - ioff - self.exlen(text)
            return text.ljust(plim+lsw, ' ')


caliper = Caliper()
