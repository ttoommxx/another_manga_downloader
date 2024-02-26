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

    @classmethod
    def decode_chapter_name(cls, chapter: str) -> str:
        """decode chapter name from chapter"""
        return chapter

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
        """create manga obj with various attributes"""
        url_completion = self.search_list_raw[index][0]
        url_manga = f"https://www.manga4life.com/manga/{ url_completion }"

        response = requests.get(url_manga, timeout=10)
        if response.status_code != 200:
            print(
                f"Failed retrieving {
                    url_manga} with the following response status code:"
            )
            print(response.status_code)
            return None
        html_string = response.text
        name = re.findall(r"<title>(.*) \| MangaLife</title>", html_string)[0]
        chapters_string = re.findall(r"vm.Chapters = (.*);", html_string)[0].replace(
            "null", "None"
        )
        list_chapters = ast.literal_eval(chapters_string)
        list_chapters = [chapter["Chapter"] for chapter in list_chapters]

        return Manga("mangalife", name, list_chapters)

    def img_generator(self, chapter: str, manga_obj):
        """create a generator for pages in chapter"""

        chapter_number = str(int(chapter[1:-1]))
        if chapter[-1] != "0":
            chapter_number += "." + str(chapter[-1])
        index = "-index-" + chapter[0] if chapter[0] != "1" else ""

        page_number = 0
        while True:
            page_number += 1
            url_page = f"https://www.manga4life.com/read-online/{
                manga_obj.name}-chapter-{chapter_number}{index}-page-{page_number}.html"
            response = requests.get(url_page, timeout=10)
            if (
                response.status_code != 200
                or "<title>404 Page Not Found</title>" in response.text
            ):
                break

            # web scaping
            page_text = response.text
            server_name = re.findall(r"vm.CurPathName = \"(.*)\";", page_text)[0]
            server_directory = re.findall(r"vm.CurChapter = (.*);", page_text)[
                0
            ].replace("null", "None")
            server_directory = ast.literal_eval(server_directory)
            chap_num = server_directory["Chapter"]
            chap_num = (
                chap_num[1:-1]
                if chap_num[-1] == "0"
                else chap_num[1:-1] + "." + chap_num[-1]
            )
            chap_dir = server_directory["Directory"]
            chap_dir = chap_dir + "/" if chap_dir else chap_dir
            image_link = f"https://{server_name}/manga/{manga_obj.name}/{
                chap_dir}{chap_num}-{page_number:03d}.png"
            response = requests.get(image_link, stream=True, timeout=10)
            if response.status_code != 200:
                break

            yield f"{page_number:03d}", response


class Manganato:
    """manganato"""

    def __init__(self):
        self.search_list_raw = []
        self.search_list = []
        self.current_word_search = ""

    @classmethod
    def decode_chapter_name(cls, chapter: str) -> str:
        """decode chapter name from chapter"""
        chapter_name = chapter.split("/")[-1]
        chapter_num = chapter_name.split("-")[-1]
        if "." in chapter_num:
            chapter_num, chapter_dot = chapter_num.split(".")
        else:
            chapter_dot = None
        chapter_num = int(chapter_num)
        chapter_name = f"{chapter_num:04d}{'.'+chapter_dot if chapter_dot else ''}"

        return chapter_name

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
        """create manga obj with various attributes"""
        url_manga = self.search_list_raw[index][0]
        response = requests.get(url_manga, timeout=10)
        if response.status_code != 200:
            print(
                f"Failed retrieving {
                    url_manga} with the following response status code:"
            )
            print(response.status_code)
            return None
        html_string = response.text

        list_chapters = re.findall(
            r'<a rel="nofollow" class="chapter-name text-nowrap" href="(.*?)" title="',
            html_string,
        )  # question mark makes it into lazy search
        name = re.findall(
            r"<title>(.*) Manga Online Free - Manganato</title>", html_string
        )[0]
        input(name)

        return Manga("manganato", name, list_chapters)

    def img_generator(self, chapter: str, manga_obj):
        """create a generator for pages in chapter"""

        response = requests.get(chapter, timeout=10)
        if response.status_code == 200:
            html_string = response.text
            images = re.findall(r'<img src="(.*?)(?<=\.jpg)"', html_string)

        for image_link in images:
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            response = requests.get(
                image_link, stream=True, timeout=10, headers=headers
            )
            page_number = int(image_link.split("/")[-1].split("-")[0])
            yield f"{page_number:03d}", response


class Manga:
    """class to save information about manga"""

    def __init__(self, website, name, list_chapters):
        self.website = website
        self.name = name
        self.list_chapters = list_chapters


get_manga = {"mangalife": Mangalife(), "manganato": Manganato()}
