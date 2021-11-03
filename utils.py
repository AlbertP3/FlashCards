

def get_abs_path_from_caller(file_name, abs_path=None):
    from os import path
    from inspect import stack
    if abs_path is None:
        abs_path = path.abspath((stack()[1])[1])
        abs_path = path.join(path.dirname(abs_path), file_name)
    return abs_path


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
