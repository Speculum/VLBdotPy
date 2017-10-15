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
    pass


class InvalidArgumentError (VLBdotPyError):
    """Raised when an invalid arguemtn was passed to a function"""
    pass


class CoverSizeTypes:
    """Available sizes for get_cover method"""
    LARGE = "l"
    MEDIUM = "m"
    SMALL = "s"


class MediaTypes:
    """Available media types for get_media method"""
    FRONTCOVER = "FRONTCOVER"
    BACKCOVER = "BACKCOVER"
    INLAYCOVER = "INLAYCOVER"
    INSIDE_VIEW = "INSIDE_VIEW"
    TABLE_OF_CONTENT = "TABLE_OF_CONTENT"
    ANNOTATION = "ANNOTATION"
    MAIN_DESCRIPTION = "MAIN_DESCRIPTION"
    AUTHOR_IMAGE = "AUTHOR_IMAGE"
    AUDIO_SAMPLE = "AUDIO_SAMPLE"
    PREVIEW_SAMPLE = "PREVIEW_SAMPLE"
    VIDEO_CLIP = "VIDEO_CLIP"
    REVIEW_TEXT = "REVIEW_TEXT"
    REVIEW_QUOTE = "REVIEW_QUOTE"
    FLAP_COPY = "FLAP_COPY"
    FIRST_CHAPTER = "FIRST_CHAPTER"
    INTRODUCTION = "INTRODUCTION"
    LONG_DESCRIPTION = "LONG_DESCRIPTION"
    PRODUCT_INDEX = "PRODUCT_INDEX"
    PUBLISHER_LOGO = "PUBLISHER_LOGO"
    IMPRINT_LOGO = "IMPRINT_LOGO"
    AUTHOR_DETAILS = "AUTHOR_DETAILS"
    AUTHOR_INTERVIEW = "AUTHOR_INTERVIEW"
    AUTHOR_READING = "AUTHOR_READING"


class IdTypes:
    """Avaible id types for get_book method"""
    GTIN = "gtin"
    ISBN = "isbn13"
    EAN = "ean"


class IndexSearchTypes:
    """Available search fields for index_search method"""
    AUTHOR = "author"
    PUBLISHER = "publisher"
    TITLE = "title"
    KEYWORD = "keyword"
    SET = "set"
    COLLECTION = "collection"
    IDENTIFIER = "identifier"


class SearchObject:
    """Internal structure class"""
    MAX_PAGE_SIZE = 250

    def __init__(self, session, data, long_json = False):
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

    def __init__(self, username, password, token = None, print_token = False):
        """Init Function"""

        if (token == None):
            creds = {'username': username, 'password': password}
            result = requests.post("https://api.vlb.de/api/v1/login", data=json.dumps(creds))

            if (result.status_code in Client.ERROR_CODES):
                raise InternalError(f"Response returned with error code {result.status_code}")

            token = result.text
        else:
            token = token

        if (print_token): print(token)

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


    def stack_search(self, isbns):
        query = """{
                    "content": [
        """

        for isbn in isbns:
            query += """
                        {
                            "isbn": %s
                        }
            """ % isbn

        query += """
                    ]
                }
        """


    def get_next_page(self):
        """Fetches the next result page of the last search"""
        self.last_searchObj.next()
        result = self.last_searchObj.result
        return result["content"]

    def get_book(self, id, id_type = None, long_json = False):
        """Fetches a book by its ID
            Args:
                - id: the book's ID
                - id_type (optional): type of id
                - long_json (optional): returns long json if True
        """

        url = f"https://api.vlb.de/api/v1/product/{id}"

        if (id_type != None):
            if (id_type not in [y for x, y in IdTypes.__dict__.items() if x.isupper()]):
                raise InvalidArgumentError("Argument id_type must be of type IdTypes.*")
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

    def get_cover(self, id, size = None):
        """Fetches a cover by the book's ID
            Args:
                - id: the book's ID
                - size (optional): the size of the cover
        """

        url = f"https://api.vlb.de/api/v1/cover/{id}"

        if (size != None):
            if (size not in [y for x, y in CoverSizeTypes.__dict__.items() if x.isupper()]):
                raise InvalidArgumentError("Argument size must be of type CoverSizeTypes.*")
            else:
                url += f"/{size}"

        self.session.headers["Accept"] = "application/json"
        result_raw = self.session.get(url)

        if (result_raw.status_code in Client.ERROR_CODES):
            raise InternalError(f"Response returned with error code {result_raw.status_code}\nRequest url: {url}")

        try:
            result = result_raw.json()
            if (result.get("error") is not None):
                raise InternalError(result["error_description"])
            else:
                raise InternalError("VLB.de returned a JSON string although it should not do it regarding the url!")
        except  json.decoder.JSONDecodeError:
            return result_raw.content

    def get_media(self, id, type):
        """Returns various media files for the product using the given id
            Args:
                - id: the product's id
                - type: the media type that should be returned
        """

        url = f"http://api.vlb.de/api/v1/asset/mmo/{id}"

        if (type not in [y for x, y in MediaTypes.__dict__.items() if x.isupper()]):
            raise InvalidArgumentError("Argument type must be of type MediaTypes.*")

        self.session.headers["Accept"] = "application/json"
        result_raw = self.session.get(url)

        if (result_raw.status_code in Client.ERROR_CODES):
            raise InternalError(f"Response returned with error code {result_raw.status_code}\nRequest url: {url}")

        result = result_raw.json()

        try:
            if (result.get("error") is not None):
                raise InternalError(result["error_description"])
        except AttributeError:
            pass

        fields = [x for x in result if x.get("type") == type]

        if (len(fields) == 0):
            return None

        urls = []
        types = []

        for field in fields:
            url = field["url"]

            result_raw = self.session.get(url)

            if (result_raw.status_code in Client.ERROR_CODES):
                raise InternalError(f"Response for media url returned with error code {result_raw.status_code}\nRequest url: {url}")

            urls.append(url)
            types.append(result_raw.headers["Content-Type"].split(";")[0])

        return len(fields), zip(types, urls)

    def index_search(self, field, term):
        """Returns a search index for the given term (one word)
            Args:
                - field: the field to search in
                - term: the search term
        """

        url = f"http://api.vlb.de/api/v1/index/{field}/{term}"

        if (field not in [y for x, y in IndexSearchTypes.__dict__.items() if x.isupper()]):
            raise InvalidArgumentError("Argument type must be of type IndexSearchTypes.*")

        self.session.headers["Accept"] = "application/json"
        result_raw = self.session.get(url)

        if (result_raw.status_code in Client.ERROR_CODES):
            raise InternalError(f"Response returned with error code {result_raw.status_code}\nRequest url: {url}")

        result = result_raw.json()

        try:
            if (result.get("error") is not None):
                raise InternalError(result["error_description"])
            else:
                raise InternalError("VLB.de returned a dict although it should return a list!")
        except AttributeError:
            return result_raw.json()

    def get_publisher(self, mvbid):
        """Returns data about publisher"""

        url = f"https://api.vlb.de/api/v1/publisher/{mvbid}"

        self.session.headers["Accept"] = "application/json"
        result_raw = self.session.get(url)
        if (result_raw.status_code in Client.ERROR_CODES):
            raise InternalError(f"Response returned with error code {result_raw.status_code}")
        result = result_raw.json()

        if (result.get("error") is not None):
            raise InternalError(result["error_description"])
        else:
            return result