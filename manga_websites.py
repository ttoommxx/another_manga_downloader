"""collection of manga websites and their attributes"""
import re
import ast
from itertools import islice
import requests


class Mangalife:
    """mangalife"""

    def __init__(self):
        print("Downloading mangalife database")

        response = requests.get("https://www.manga4life.com/search/", timeout=10)

        if response.status_code != 200:
            print("Cannot reach mangalife server.")
            response.raise_for_status()

        page_text = response.text
        list_mangas = re.findall(r"vm.Directory = (.*);", page_text)[0]
        list_mangas = (
            list_mangas.replace("null", "None")
            .replace("false", "False")
            .replace("true", "True")
        )
        list_mangas = ast.literal_eval(list_mangas)
        list_mangas = [
            (entry["i"], entry["s"], entry["s"].lower()) for entry in list_mangas
        ]
        # first entry-url, second entry-display, third entry-search
        list_mangas.sort()
        self.list_mangas = list_mangas

        self.search_list_raw = []
        self.search_list = []
        self.current_word_search = ""

    def print_list(self, word_search: str, max_len: int = 100):
        """return list of mangas"""
        word_search_patter = word_search.lower().replace(" ", r".*")

        if word_search_patter != self.current_word_search:
            self.current_word_search = word_search_patter

            try:
                search_iter = (
                    entry
                    for entry in self.list_mangas
                    if re.search(word_search_patter, entry[2])
                )
                self.search_list_raw = list(islice(search_iter, max_len))
            except re.error:
                self.search_list_raw = [
                    entry for entry in self.list_mangas if word_search in entry[2]
                ]
            self.search_list = [entry[1] for entry in self.search_list_raw]

        return self.search_list

    def create_manga_obj(self, index: int) -> str:
        """fetch url to the manga page"""
        url_completion = self.search_list_raw[index][0]
        url_manga = f"https://www.manga4life.com/manga/{ url_completion }"

        name = url_manga.split("/")[-1]
        try:
            response = requests.get(url_manga, timeout=10)
        except requests.exceptions.RequestException as e:
            print(f"Failed retrieving {name} with the following error:")
            print(e)
            return None
        if response.status_code != 200:
            print(
                f"Failed retrieving {
                    name} with the following response status code:"
            )
            print(response.status_code)
            return None
        html_string = response.text
        name_display = re.findall(r"<title>(.*) \| MangaLife</title>", html_string)[0]
        chapters_string = re.findall(r"vm.Chapters = (.*);", html_string)[0].replace(
            "null", "None"
        )
        list_chapters = ast.literal_eval(chapters_string)
        list_chapters = [chapter["Chapter"] for chapter in list_chapters]

        return Manga(name, name_display, list_chapters)


class Manganato:
    """manganato"""

    def __init__(self):
        self.search_list_raw = []
        self.search_list = []
        self.current_word_search = ""

    def print_list(self, word_search: str, max_len: int = 100) -> list:
        """return list of mangas"""
        if word_search != self.current_word_search:
            self.current_word_search = word_search
            pattern = r'<a class="item-img bookmark_check" data-id="(?:.*)" href="(.*)" title="(.*)">'

            response = requests.get(
                f"https://manganato.com/search/story/{word_search}", timeout=10
            )
            if response.status_code != 200:
                print("Cannot reach the server.")
                return ""
            page_text = response.text

            list_mangas = re.findall(pattern, page_text)

            page_number = 2
            while f"page={page_number}" in response.text and len(list_mangas) < max_len:
                response = requests.get(
                    f"https://manganato.com/search/story/{word_search}?page={page_number}",
                    timeout=10,
                )
                if response.status_code != 200:
                    print("Cannot reach the server.")
                    return ""
                page_text = response.text

                new_list = re.findall(pattern, page_text)
                list_mangas.extend(new_list)
                page_number += 1

            self.search_list_raw = list_mangas[:max_len]
            self.search_list = [entry[1] for entry in self.search_list_raw]

        return self.search_list

    def create_manga_obj(self, index: int) -> str:
        """fetch url to the manga page"""

        url_manga = self.search_list_raw[index][0]


class Manga:
    """class to save information about manga"""

    def __init__(self, name, name_display, list_chapters):
        self.name = name
        self.name_display = name_display
        self.list_chapters = list_chapters


mangas = {"mangalife": Mangalife(), "manganato": Manganato()}
