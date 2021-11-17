from datetime import datetime, date
import os



def get_abs_path_from_caller(file_name, abs_path=None):
    from os import path
    from inspect import stack
    if abs_path is None:
        abs_path = path.abspath((stack()[1])[1])
        abs_path = path.join(path.dirname(abs_path), file_name)
    return abs_path


def get_relative_path_from_abs_path(abs_path):
    return '.\\' + os.path.relpath(abs_path)


def get_filename_from_path(path, include_extension=False):
    from ntpath import basename
    if include_extension:
        filename = basename(path)
    else:
        filename = basename(path)[:-4]

    return filename 


def text_insert(text_box, msg, left_newline=False, right_newline=False):
    import tkinter as tk
    output_msg = iif(left_newline, '\n', '') + msg + iif(right_newline, '\n', '')
    text_box.insert(tk.END, output_msg)


def iif(statement, true_part, false_part):
    return true_part if statement else false_part


def get_signature(lng:str, filename):
    # Create new signature or recognize the current one from pattern
    if filename[:4] == 'REV_':
        print('Revision recognized')
        return filename
    else:
        saving_date = datetime.now().strftime('%m%d%Y%H%M%S')
        print('Creating new signature')
        return 'REV_' + lng[:2] + saving_date


def make_datetime(d):
    # transforms date-like string in database to datetime format
    return datetime(int(d[6:10]), int(d[:2]), int(d[3:5]), int(d[12:14]), int(d[15:17]), int(d[18:20]))


def make_date(d):
    # transforms date-like string in database to datetime format
    return date(int(d[6:10]), int(d[:2]), int(d[3:5]))


def make_todaytime():
    return datetime(datetime.now().year, datetime.now().month, datetime.now().day, datetime.now().hour, datetime.now().minute, datetime.now().second)


def make_todayte():
    return date(datetime.now().year, datetime.now().month, datetime.now().day)