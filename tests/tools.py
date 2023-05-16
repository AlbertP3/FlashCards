import requests
import os, sys
from urllib.request import url2pathname
 


class LocalFileAdapter(requests.adapters.BaseAdapter):
    """Protocol Adapter to allow Requests to GET file:// URLs"""

    @staticmethod
    def _chkpath(method, path):
        """Return an HTTP status for the given filesystem path."""
        if method.lower() in ('put', 'delete'):
            return 501, "Not Implemented"  # TODO
        elif method.lower() not in ('get', 'head'):
            return 405, "Method Not Allowed"
        elif os.path.isdir(path):
            return 400, "Path Not A File"
        elif not os.path.isfile(path):
            return 404, "File Not Found"
        elif not os.access(path, os.R_OK):
            return 403, "Access Denied"
        else:
            return 200, "OK"


    def send(self, req, **kwargs):  # pylint: disable=unused-argument
        """Return the file specified by the given request
        @type req: C{PreparedRequest}
        """
        path = os.path.normcase(os.path.normpath(url2pathname(req.path_url)))
        response = requests.Response()

        response.status_code, response.reason = self._chkpath(req.method, path)
        if response.status_code == 200 and req.method.lower() != 'head':
            try:
                response.raw = open(path, 'rb')
            except (OSError, IOError) as err:
                response.status_code = 500
                response.reason = str(err)

        if isinstance(req.url, bytes):
            response.url = req.url.decode('utf-8')
        else:
            response.url = req.url

        response.request = req
        response.connection = self

        return response


    def close(self):
        pass



class dict_mock():
    def get(self, word):
        translations = ['witaj świEcie', 'domyślny serwis', 'czerwony', 'traktować kogoś z honorami', 'lorem ipsum']
        originals = ['hello world', 'default dict service for tests', 'red', 'to roll out the red carpet for sb [or to give sb the red carpet treatment]', 'dolor sit amet']
        warnings = []
        if word == 'none': 
            translations.clear()
            originals.clear()
        elif word == 'mauve':
            translations = ['mauve']
            originals = ['jasno fioletowy']
        elif word == 'error':
            warnings = ['TEST ERROR INDUCED']
        return translations, originals, warnings



class cell_mock:
    def __init__(self, value) -> None:
        self.value = value

class xlsx_mock:
    def __init__(self, data:list, rows=10) -> None:
        self.data = [[None]*3 for _ in range(rows)]
        self.init_len = len(data)
        for i, r in enumerate(data):
            self.data[i+1] = ['', *r]

    def cell(self, row, column, value=None):
        if value: 
            self.data[row][column] = value
        return cell_mock(self.data[row][column])
    
    @property
    def max_row(self):
        i = 0
        for k in self.data[1:]:
            if not k[1]:
                break
            i+=1
        return i

class workbook_mock:
    def __init__(self, ws:dict) -> None:
        self.ws = ws  # worksheets = {name: data}

    def __getitem__(self, ws):
        return xlsx_mock(self.ws[ws])

    def save(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass