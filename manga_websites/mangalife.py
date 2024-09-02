"""collection of manga websites and their attributes"""

import re
import ast
from typing import Iterator
from itertools import islice
import requests


class Mangalife:
    """mangalife"""

    name = "mangalife"
    page = "https://www.manga4life.com"

    def __init__(self, timeout: int) -> None:
        self.list_mangas: list[str] = []
        self.timeout = timeout

    def load_database(self) -> None:
        """load the database of mangas"""

        print("Downloading mangalife database")
        response = requests.get(self.page + "/search/", timeout=self.timeout)

        if response.status_code != 200:
            print("Cannot reach mangalife server.")
            response.raise_for_status()

        page_text = response.text
        list_mangas_group = re.search(r"vm.Directory = (.*);", page_text)
        assert list_mangas_group is not None
        list_mangas = (
            list_mangas_group.group(1)
            .replace("null", "None")
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

    def print_list(self, word_search: str, max_len: int = 100) -> list[tuple[str, str]]:
        """return list of mangas"""

        word_search_patter = word_search.lower().replace(" ", r".*?")
        try:
            re.compile(word_search_patter)
        except re.error:
            search_iter = (
                entry for entry in self.list_mangas if word_search in entry[2]
            )
        else:
            search_iter = (
                entry
                for entry in self.list_mangas
                if re.search(word_search_patter, entry[2])
            )

        search_list = list(islice(search_iter, max_len))
        return [(entry[1], self.page + "/manga/" + entry[0]) for entry in search_list]

    def create_manga(self, url_manga: str) -> dict[str, str | list[dict]]:
        """create manga dictionary with various attributes"""

        if not url_manga:
            return {}

        response = requests.get(url_manga, timeout=self.timeout)

        html_string = response.text
        name_group = re.search(r"<title>(.*?) \| MangaLife</title>", html_string)
        assert name_group is not None
        name = name_group.group(1)

        chapters_group = re.search(r"vm.Chapters = (.*?);", html_string)
        assert chapters_group is not None
        chapters_string = chapters_group.group(1).replace("null", "None")

        list_chapters = ast.literal_eval(chapters_string)
        for chapter in list_chapters:
            chapter["name"] = chapter["Chapter"]

        manga = {
            "website": "mangalife",
            "name": name,
            "list_chapters": list_chapters,
            "true name": url_manga.split("/")[-1],
        }

        return manga

    def img_generator(
        self, chapter: dict, manga: dict[str, str | list[dict]]
    ) -> Iterator[tuple[str, str]]:
        """create a generator for pages numbers and their url in chapter"""

        chapter_name = chapter["name"]
        chapter_number = str(int(chapter_name[1:-1]))
        if chapter_name[-1] != "0":
            chapter_number += "." + chapter_name[-1]
        index = ("-index-" + chapter_name[0]) if chapter_name[0] != "1" else ""

        page_number = 0
        while True:
            page_number += 1
            url_page = (
                self.page
                + f"/read-online/{
                manga["true name"]}-chapter-{chapter_number}{index}-page-{page_number}.html"
            )
            try:
                response = requests.get(url_page, timeout=self.timeout)
            except Exception as excp:
                yield "", str(excp)
                break

            if response.status_code != 200:
                break
            page_text = response.text
            if r"<title>404 Page Not Found</title>" in page_text:
                break

            server_name_group = re.search(r"vm.CurPathName = \"(.*?)\";", page_text)
            server_directory_group = re.search(r"vm.CurChapter = (.*?);", page_text)
            if not server_name_group or not server_directory_group:
                yield "", "website cannot be reached"
                break

            server_name = server_name_group.group(1)
            server_directory = server_directory_group.group(1).replace("null", "None")
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

            yield f"{page_number:03d}", image_link
