"""collection of manga websites and their functions"""
from .mangalife import Mangalife

get_manga = {"mangalife": Mangalife()}


def get_manga_website(url: str) -> str:
    """identify manga website from the url"""
    if url.startswith("https://www.manga4life.com/manga/"):
        return "mangalife"
    return ""
