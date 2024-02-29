"""collection of manga websites and their attributes"""
import re
import ast
import requests


class Batoto:
    """mangalife"""

    def __init__(self):
        self.list_mangas = []
        self.search_list = []
        self.search_list_raw = []
        self.current_word_search = ""

    def load_database(self) -> None:
        """load the database of mangas"""

    @classmethod
    def decode_chapter_name(cls, chapter: str) -> str:
        """decode chapter name from chapter"""

        return chapter[1]

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
        if index < -1 or index >= len(self.search_list_raw):
            return ""

        url_manga = self.search_list_raw[index][0]
        return f"https://bato.to{ url_manga }"

    def create_manga(self, url_manga: str) -> str:
        """create manga dictionary with various attributes"""

        if not url_manga:
            return None

        response = requests.get(url_manga, timeout=10)
        html_string = response.text

        list_chapters = re.findall(
            r'<a class=".*?" href="(.*?)" >\s*<b>(.*?)</b>', html_string
        )
        name = re.findall(r"<title>(.*?) Manga</title>", html_string)[0]

        manga = {
            "website": "batoto",
            "name": name,
            "list_chapters": list_chapters,
        }

        return manga

    def img_generator(self, chapter: str, manga: dict):
        """create a generator for pages in chapter"""

        chapter_url = f"https://bato.to{chapter[0]}"

        response = requests.get(chapter_url, timeout=10)

        html_string = response.text
        pages_string = re.findall(r"const imgHttps = (.*);", html_string)[0]
        images = ast.literal_eval(pages_string)

        for page_number, image_link in enumerate(images):
            response = requests.get(image_link, stream=True, timeout=10)

            yield f"{page_number:03d}", response

    def img_download(self, file_path: str, url_response) -> None:
        """image url downloader"""

        with open(file_path, "wb") as page:
            for chunk in url_response.iter_content(1024):
                page.write(chunk)
