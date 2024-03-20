"""collection of manga websites and their attributes"""

import re
import ast
from typing import Iterator
import requests


class Batoto:
    """mangalife"""

    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    def load_database(self) -> None:
        """load the database of mangas"""

    def print_list(self, word_search: str, max_len: int = 100) -> list[tuple[str, str]]:
        """return list of mangas"""
        pattern = r'<a class="item-title" href="(.*?)" >(.*?)</a>'

        search_list: list[str] = []

        page_number = 1
        page_text = ""

        while len(search_list) < max_len:
            if page_number == 1:
                response = requests.get(
                    f"https://bato.to/search?word={word_search}",
                    timeout=self.timeout,
                )
            else:
                # at this point page_text is the previous html and page_number the next page number
                if f"page={page_number}" not in page_text:
                    break
                response = requests.get(
                    f"https://bato.to/search?word={word_search}&page={page_number}",
                    timeout=self.timeout,
                )

            page_text = response.text

            new_list = re.findall(pattern, page_text)
            if not new_list:
                break
            search_list.extend(new_list)
            page_number += 1

        return [
            (
                entry[1]
                .replace(r'<span class="highlight-text">', "")
                .replace(r"</span>", ""),
                f"https://bato.to{ entry[0] }",
            )
            for entry in search_list[:max_len]
        ]

    def create_manga(self, url_manga: str) -> dict[str, str | list[dict]]:
        """create manga dictionary with various attributes"""

        if not url_manga:
            return {}

        response = requests.get(url_manga, timeout=self.timeout)
        html_string = response.text

        list_chapters = re.findall(
            r'<a class=".*?" href="(.*?)" >\s*<b>(.*?)</b>', html_string
        )
        list_chapters = [
            {"url": f"https://bato.to{chapter[0]}", "name": chapter[1]}
            for chapter in list_chapters
        ]

        name_group = re.search(r"<title>(.*?) Manga</title>", html_string)
        assert name_group is not None
        name = name_group.group(1)

        manga = {
            "website": "batoto",
            "name": name,
            "list_chapters": list_chapters,
        }

        return manga

    def img_generator(
        self, chapter: dict, manga: dict[str, str | list[dict]]
    ) -> Iterator[tuple[str, str]]:
        """create a generator for pages in chapter"""

        chapter_url = chapter["url"]

        stop = False
        try:
            response = requests.get(chapter_url, timeout=self.timeout)
        except Exception as excp:
            yield "", str(excp)
            stop = True

        if not stop:
            html_string = response.text
            pages_group = re.search(r"const imgHttps = (.*?);", html_string)
            if not pages_group:
                yield "", "website cannot be reached"
            else:
                pages_string = pages_group.group(1)
                images = ast.literal_eval(pages_string)

                for page_number, image_link in enumerate(images):
                    yield f"{page_number:03d}", image_link
