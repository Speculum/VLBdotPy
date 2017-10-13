import requests
import json
import re

class VLBdotPyError (Exception):
    """Base class for VLBdotPy error"""
    pass


class BadCredentialsError (VLBdotPyError):
    """Raised when credentials given to Client are incorrect"""
    pass


class InternalError (VLBdotPyError):
    """Raised when an internal error occurs"""
    pass


class MaximumExceededError (VLBdotPyError):
    """Raised when some number exceeded a maximum"""


class InvalidArgumentError (VLBdotPyError):
    pass


class SearchObject:
    """Internal structure class"""
    MAX_PAGE_SIZE = 250

    def __init__(self, session, data, long_json = False): # session, search, size = MAX_PAGE_SIZE, status = "active", direction = "desc", page = None, sort = None, source = None):
        if ("next_page" not in vars()): self.page = 1
        # if (data.get("page") != None): self.next_page = data.get("page")
        # else: data["page"] = self.next_page

        self.session = session
        self.data = data
        self.long_json = long_json

        if (long_json): self.session.headers["Accept"] = "application/json"
        else: self.session.headers["Accept"] = "application/json-short"

        result_raw = self.session.get("https://api.vlb.de/api/v1/products", params=self.data)
        if (result_raw.status_code in Client.ERROR_CODES):
            raise InternalError (f"Response returned with error code {result_raw.status_code}")
        self.result = result_raw.json()

        if (self.result.get("error") is not None):
            raise InternalError(self.result["error_description"])
        else:
            self.total_pages = self.result["totalPages"]

    def next(self):
        self.page += 1

        if (self.page > self.total_pages):
            raise MaximumExceededError ("Maximum page number of the current search is " + str(self.total_pages))

        self.data["page"] = self.page

        result_raw = self.session.get("https://api.vlb.de/api/v1/products", params=self.data)
        if (result_raw.status_code in Client.ERROR_CODES):
            raise InternalError(f"Response returned with error code {result_raw.status_code}")
        self.result = result_raw.json()

        if (self.result.get("error") is not None):
            raise InternalError(self.result["error_description"])
        else:
            self.total_pages = self.result["totalPages"]


class SearchBuilder:
    """Class to safely build a VLB search string. Should be used with Client.search()"""

    def __init__(self, format_str, *args):
        if (not isinstance(format_str, str)):
            raise InvalidArgumentError("Argument format_str must be of type string!")

        query = ""
        args = [Client.sanitize_search(x) for x in args]

        points = [m.start() for m in re.finditer('\{}', format_str)]
        points = [x for x in points if x != 0 and format_str[x-1] != "\\"]

        if (len(points) != len(args)):
            raise InvalidArgumentError("You need to provide exactly as many argumnents as '{}'!")

        try:
            # query = format_str.replace("{}", "%s")
            query = format_str.format(*args)
        except Exception as e:
            raise InternalError(f"An error occurred while formatting string! Error:\n{e}")

        self.query_string = query


class Client:
    """VLBdotPy's Client Class"""
    ERROR_CODES = [400, 401, 403, 404, 500]
    ID_TYPES = ["gtin", "isbn13", "ean"]

    def __init__(self, username, password):
        """Init Function"""
        creds = {'username': username, 'password': password}
        result = requests.post("https://api.vlb.de/api/v1/login", data=json.dumps(creds))

        if (result.status_code in Client.ERROR_CODES):
            raise InternalError(f"Response returned with error code {result.status_code}")

        token = result.text
        self.session = requests.session()
        self.session.headers["Authorization"] = "Bearer " + token
        self.session.headers["Content-Type"] = "application/json"
        # self.session.headers["Accept"] = "application/json-short"
        self.session.headers["User-Agent"] = "VLBdotPy"


    @staticmethod
    def sanitize_search(string):
        string = re.sub(" und ", " \"und\" ", string, flags=re.IGNORECASE)
        string = re.sub(" and ", " \"and\" ", string, flags=re.IGNORECASE)
        string = re.sub(" oder ", " \"oder\" ", string, flags=re.IGNORECASE)
        string = re.sub(" or ", " \"or\" ", string, flags=re.IGNORECASE)
        string = re.sub(" nicht ", " \"nicht\" ", string, flags=re.IGNORECASE)
        string = re.sub(" not ", " \"not\" ", string, flags=re.IGNORECASE)

        string = re.sub("und ", "\"und\" ", string, flags=re.IGNORECASE)
        string = re.sub("and ", "\"and\" ", string, flags=re.IGNORECASE)
        string = re.sub("oder ", "\"oder\" ", string, flags=re.IGNORECASE)
        string = re.sub("or ", "\"or\" ", string, flags=re.IGNORECASE)
        string = re.sub("nicht ", "\"nicht\" ", string, flags=re.IGNORECASE)
        string = re.sub("not ", "\"not\" ", string, flags=re.IGNORECASE)

        string = re.sub(" und", " \"und\"", string, flags=re.IGNORECASE)
        string = re.sub(" and", " \"and\"", string, flags=re.IGNORECASE)
        string = re.sub(" oder", " \"oder\"", string, flags=re.IGNORECASE)
        string = re.sub(" or", " \"or\"", string, flags=re.IGNORECASE)
        string = re.sub(" nicht", " \"nicht\"", string, flags=re.IGNORECASE)
        string = re.sub(" not", " \"not\"", string, flags=re.IGNORECASE)
        return string


    def search(self, search, size = SearchObject.MAX_PAGE_SIZE, status = "active", direction = "desc", page = 1, sort = None, source = None, long_json = False):
        """Searches using the search string.
            Args:
                - search: a VLB-formatted string
                - books_per_page: maximal number of books per page
                _ long_json: returns long json result if True
        """

        data = {
                "page": page,
                "size": size,
                "search": search,
                "status": status,
                "direction": direction
                }

        if (sort != None): data["sort"] = sort
        if (source != None): data["source"] = source

        self.last_searchObj = SearchObject(self.session, data, long_json)

        result = self.last_searchObj.result
        return result["content"]
        #if (int(result["numberOfElements"]) == 0):
        #    return {}
        #else:


    def stack_search(self, isbns):
        pass

    def get_next_page(self):
        """Fetches the next result page of the last search"""
        self.last_searchObj.next()
        result = self.last_searchObj.result
        return result["content"]

    def get_by_id(self, id, id_type=None, long_json=False):
        """Fetches a book by its ID
            Args:
                - id: the book's ID
                - id_type (optional): type of id
                - long_json (optional): returns long json if True
        """

        url = f"https://api.vlb.de/api/v1/product/{id}"

        if (id_type != None):
            if (id_type not in Client.ID_TYPES):
                raise InvalidArgumentError("Argument id_type must be either 'gtin', 'isbn13' or 'ean'")
            else:
                url += f"/{id_type}"

        if (long_json): self.session.headers["Accept"] = "application/json"
        else: self.session.headers["Accept"] = "application/json-short"

        result_raw = self.session.get(url)
        if (result_raw.status_code in Client.ERROR_CODES):
            raise InternalError(f"Response returned with error code {result_raw.status_code}\nRequest url: {url}")
        result = result_raw.json()

        if (result.get("error") is not None):
            raise InternalError(result["error_description"])

        return result

    # def for cover and media stuff

    # def index, publisher,     