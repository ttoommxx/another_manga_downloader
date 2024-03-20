"""
TEMPLATE
collection of manga websites and their attributes
"""

from typing import Iterator


class NameOfTheManga:
    """name of the manga"""

    def __init__(self) -> None:
        self.list_mangas = []  # total list of mangas (if available)

    def load_database(self) -> None:
        """load the database of mangas"""
        # to be executed at the beginning of the script, loads the entire database

    def print_list(self, word_search: str, max_len: int = 100) -> list[tuple[str, str]]:
        """return list of mangas"""
        # return a list of mangas that result from searching word_seach to be printed on the sceen, of length = max_len.

    def create_manga(self, url_manga: str) -> dict:
        """create manga dictionary with various attributes"""
        # this function creates two important data structures:
        # manga -> it must have 3 entries, website, name and list_chapters
        # list_chapters -> list of dictionries, each of which must contain the name of the chapter
        # both dictionaries can be added more variables for internal use

    def img_generator(self, chapter: dict, manga: dict) -> Iterator[tuple[str, str]]:
        """create a generator for pages in chapter"""
        # this function is a generator that returs 2 variables: the page number (formatted appropriately) and a response file obtained by requests.get(...)
