"""collection of manga websites and their attributes"""
import re
import ast
from itertools import islice
import requests


class Mangalife:
    """mangalife"""

    def __init__(self):
        self.list_mangas = []
        self.search_list_raw = []
        self.search_list = []
        self.current_word_search = ""

    def load_database(self) -> None:
        """load the database of mangas"""
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

    def index_to_url(self, index: int) -> str:
        """convert index to url"""
        if index < -1 or index >= len(self.search_list_raw):
            return ""

        url_completion = self.search_list_raw[index][0]
        return f"https://www.manga4life.com/manga/{ url_completion }"

    def create_manga(self, url_manga: str) -> str:
        """create manga dictionary with various attributes"""

        if not url_manga:
            return None

        response = requests.get(url_manga, timeout=10)

        html_string = response.text
        name = re.findall(r"<title>(.*) \| MangaLife</title>", html_string)[0]
        chapters_string = re.findall(r"vm.Chapters = (.*);", html_string)[0].replace(
            "null", "None"
        )
        list_chapters = ast.literal_eval(chapters_string)

        manga = {
            "website": "mangalife",
            "name": name,
            "list_chapters": list_chapters,
            "true name": url_manga.split("/")[-1],
        }

        for chapter in list_chapters:
            chapter["manga"] = manga
            chapter["name"] = chapter["Chapter"]

        return manga

    def img_generator(self, chapter: str, manga: dict):
        """create a generator for pages in chapter"""

        chapter_name = chapter["name"]
        chapter_number = str(int(chapter_name[1:-1]))
        if chapter_name[-1] != "0":
            chapter_number += "." + chapter_name[-1]
        index = "-index-" + chapter_name[0] if chapter_name[0] != "1" else ""

        page_number = 0
        while True:
            page_number += 1
            url_page = f"https://www.manga4life.com/read-online/{
                manga["true name"]}-chapter-{chapter_number}{index}-page-{page_number}.html"
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
            image_link = f"https://{server_name}/manga/{manga["true name"]}/{
                chap_dir}{chap_num}-{page_number:03d}.png"
            response = requests.get(image_link, stream=True, timeout=10)
            if response.status_code != 200:
                break

            yield f"{page_number:03d}", response

    def img_download(self, file_path: str, url_response) -> None:
        """image url downloader"""

        with open(file_path, "wb") as page:
            for chunk in url_response.iter_content(1024):
                page.write(chunk)
