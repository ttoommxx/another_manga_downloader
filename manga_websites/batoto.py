"""collection of manga websites and their attributes"""
import re
import ast
from itertools import islice
import requests


class Batoto:
    """mangalife"""

    def __init__(self):
        self.list_mangas = []
        self.search_list = []
        self.search_list_raw = []
        self.current_word_search = ""

    def load_database(self):
        """load the database of mangas"""

    @classmethod
    def decode_chapter_name(cls, chapter: str) -> str:
        """decode chapter name from chapter"""

    def print_list(self, word_search: str, max_len: int = 100) -> list:
        """return list of mangas"""
        if word_search != self.current_word_search:
            self.current_word_search = word_search
            pattern = r'<a class="item-title" href="(.*?)" >(.*?)<span class="highlight-text">(.*?)</span>(.*?)</a>'

            list_mangas = []

            page_number = 1
            page_text = ""

            while len(list_mangas) < max_len:
                if page_number == 1:
                    response = requests.get(
                        f"https://bato.to/search?word={word_search}", timeout=10
                    )
                else:
                    # at this point page_text is the previous html and page_number the next page number
                    if f"page={page_number}" not in page_text:
                        break
                    response = requests.get(
                        f"https://bato.to/search?word={word_search}&page={page_number}",
                        timeout=10,
                    )

                if response.status_code != 200:
                    print("Cannot reach the server.")
                    break

                page_text = response.text

                new_list = re.findall(pattern, page_text)
                if not new_list:
                    break
                list_mangas.extend(new_list)
                page_number += 1

            self.search_list_raw = list_mangas[:max_len]
            self.search_list = ["".join(entry[1:]) for entry in self.search_list_raw]

        return self.search_list

    def index_to_url(self, index: int) -> str:
        """convert index to url"""
        url_manga = self.search_list_raw[index][0]
        return f"https://bato.to{ url_manga }"

    def create_manga(self, url_manga: str) -> str:
        """create manga dictionary with various attributes"""

    def img_generator(self, chapter: str, manga: dict):
        """create a generator for pages in chapter"""

    def img_download(self, file_path: str, url_response) -> None:
        """image url downloader"""


# class Manganato:
#     """manganato"""

#     def __init__(self):
#         self.search_list_raw = []
#         self.search_list = []
#         self.current_word_search = ""

#     @classmethod
#     def decode_chapter_name(cls, chapter: str) -> str:
#         """decode chapter name from chapter"""
#         chapter_name = chapter.split("/")[-1]
#         chapter_num = chapter_name.split("-")[-1]
#         if "." in chapter_num:
#             chapter_num, chapter_dot = chapter_num.split(".")
#         else:
#             chapter_dot = None
#         chapter_num = int(chapter_num)
#         chapter_name = f"{chapter_num:04d}{'.'+chapter_dot if chapter_dot else ''}"

#         return chapter_name

#     def create_manga_obj(self, index: int) -> str:
#         """create manga obj with various attributes"""
#         url_manga = self.search_list_raw[index][0]
#         response = requests.get(url_manga, timeout=10)
#         if response.status_code != 200:
#             print(
#                 f"Failed retrieving {
#                     url_manga} with the following response status code:"
#             )
#             print(response.status_code)
#             return None
#         html_string = response.text

#         list_chapters = re.findall(
#             r'<a rel="nofollow" class="chapter-name text-nowrap" href="(.*?)" title="',
#             html_string,
#         )  # question mark makes it into lazy search
#         name = re.findall(
#             r"<title>(.*) Manga Online Free - Manganato</title>", html_string
#         )[0]
#         input(name)

#         return Manga("manganato", name, list_chapters)

#     def img_generator(self, chapter: str, manga_obj):
#         """create a generator for pages in chapter"""

#         response = requests.get(chapter, timeout=10)
#         if response.status_code == 200:
#             html_string = response.text
#             images = re.findall(r'<img src="(.*?)(?<=\.jpg)"', html_string)

#         for image_link in images:
#             headers = {
#                 "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0",
#                 "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#                 "Accept-Language": "en-US,en;q=0.9",
#             }
#             response = requests.get(
#                 image_link, stream=True, timeout=10, headers=headers
#             )
#             page_number = int(image_link.split("/")[-1].split("-")[0])
#             yield f"{page_number:03d}", response
