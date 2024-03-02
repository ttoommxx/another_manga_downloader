"""
TEMPLATE
collection of manga websites and their attributes
"""

import requests


class NameOfTheManga:
    """name of the manga"""

    def __init__(self):
        self.list_mangas = []  # total list of mangas (if available)
        self.search_list = []  # list with entries name_manga, url_manga
        self.current_word_search = ""  # current word used for searching

    def load_database(self) -> None:
        """load the database of mangas"""
        # to be executed at the beginning of the script, loads the entire database

    def print_list(self, word_search: str, max_len: int = 100) -> list:
        """return list of mangas"""
        # return a list of mangas that result from searching word_seach to be printed on the sceen, of length = max_len.

    def create_manga(self, url_manga: str) -> str:
        """create manga dictionary with various attributes"""
        # this function creates two important data structures:
        # manga -> it must have 3 entries, website, name and list_chapters
        # list_chapters -> list of dictionries, each of which must contain the name of the chapter
        # both dictionaries can be added more variables for internal use

    def img_generator(self, chapter: str, manga: dict):
        """create a generator for pages in chapter"""
        # this function is a generator that returs 2 variables: the page number (formatted appropriately) and a response file obtained by requests.get(...)
