""" necessary modules """
import os
import argparse
import multiprocessing
import threading
import re
import ast
import signal
from zipfile import ZipFile
from itertools import islice
import requests
import raw_input


class Environment:
    """ class that defined environment variables """

    def __init__(self):
        self.max_processes = min(os.cpu_count(), 8)
        self.manager = multiprocessing.Manager()
        self._stop = multiprocessing.Value("i", 0)
        self.print_queue = self.manager.Queue()

    @property
    def stop(self) -> int:
        """ return stopping value """
        return self._stop.value

    @stop.setter
    def stop(self, val) -> None:
        """ setter for stop multiprocessing value """
        self._stop = val

    def set_child_process(self) -> None:
        """ initialiser for secondary processes """
        signal.signal(signal.SIGINT, lambda *args:None)

    def sigint_handler(self, sig, frame) -> None:
        """ signal keyboard interrupt handler """
        print("\nQuitting..")
        self.print_queue.put(1)
        self._stop.value = 1

    def quit(self) -> None:
        """ quit environment """
        self.manager.shutdown()
        if self.stop:
            print("\nProgram terminated, re-run to resume.")


def printer(manga_name: str, number_chapters: int) -> None:
    """ function that updates the count of the executed chapters """
    if ENV.stop:
        return
    failed = []
    ENV.print_queue.put(None)
    for i in range(number_chapters+1):
        token = ENV.print_queue.get()
        if token == 1:
            return
        if token:
            failed.append(token)
        print(f"- {manga_name}: {i} / {number_chapters} completed.", end="\r")

    print()
    if failed:
        print("The following chapters have failed.")
        for chapter in failed:
            print(chapter)
    else:
        print("No chapter has failed.")


def download_and_zip(chapter: dict, folder_path: str, manga_name: str) -> None:
    """ given path and chapter_path, create the zip file
    add a token to the queue when the process is done """
    if ENV.stop:
        return

    chapter_name_number = chapter["Chapter"]
    chapter_number = str(int(chapter_name_number[1:-1]))
    if chapter_name_number[-1] != "0":
        chapter_number += "." + str(chapter_name_number[-1])
    index = "-index-"+chapter_name_number[0] if chapter_name_number[0] != "1" else ""

    chapter_path = os.path.join(folder_path, chapter_name_number)
    zip_path = chapter_path + ".cbz"

    failed_number = None
    if not os.path.exists(zip_path):
        os.makedirs(chapter_path, exist_ok=True)

        # DOWNLOAD
        pages = []
        page_number = 0
        while True:
            page_number += 1
            url_page = f"https://www.manga4life.com/read-online/{manga_name}-chapter-{chapter_number}{index}-page-{page_number}.html"
            response = requests.get(url_page, timeout=10)
            if response.status_code != 200 or "<title>404 Page Not Found</title>" in response.text:
                break

            # web scaping
            page_text = response.text
            server_name = re.findall(r"vm.CurPathName = \"(.*)\";", page_text)[0]
            server_directory = re.findall(r'vm.CurChapter = (.*);', page_text)[0].replace("null","None")
            server_directory = ast.literal_eval(server_directory)
            chap_num = server_directory["Chapter"]
            chap_num = chap_num[1:-1] if chap_num[-1] == "0" else chap_num[1:-1]+"."+chap_num[-1]
            chap_dir = server_directory["Directory"]
            chap_dir = chap_dir+"/" if chap_dir else chap_dir
            image_link = f"https://{server_name}/manga/{manga_name}/{chap_dir}{chap_num}-{page_number:03d}.png"
            response = requests.get(image_link, stream=True, timeout=10)
            if response.status_code != 200:
                break

            file_path = os.path.join(chapter_path, f"{page_number:03d}.png")
            if not os.path.exists(file_path):
                # open the file in binary write mode
                with open(file_path, "wb") as page:
                    for chunk in response.iter_content(1024):
                        page.write(chunk)
            if ENV.stop:
                return

            pages.append(file_path)

        # ZIP
        with ZipFile(zip_path, "a") as zip_file:
            for page in pages:
                if ENV.stop:
                    break
                page_path = os.path.join(chapter_path, page)
                zip_file.write(page_path, page)
        if ENV.stop:
            if os.path.exists(zip_path):
                os.remove(zip_path)
            return

        # remove folder
        for page in pages:
            os.remove(page)
        if not os.listdir(chapter_path):
            os.rmdir(chapter_path)

        # save chapter name is fail
        if not os.path.exists(zip_path):
            failed_number = chapter_name_number

    ENV.print_queue.put(failed_number)


def download_manga(url_manga: str) -> None:
    """ main function """
    if ENV.stop:
        return
    if not url_manga.startswith("https://www.manga4life.com/"):
        print(url_manga)
        print("is not manga4life website.")
        return

    # fetch url and chapters data
    manga_name = url_manga.split("/")[-1]
    try:
        response = requests.get(url_manga, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"Failed retrieving {manga_name} with the following error:")
        print(e)
        return
    if response.status_code != 200:
        print(f"Failed retrieving {manga_name} with the following response status code:")
        print(response.status_code)
        return
    html_string = response.text
    manga_name_display = re.findall(r"<title>(.*) \| MangaLife</title>", html_string)[0]
    chapters_string = re.findall(r"vm.Chapters = (.*);", html_string)[0].replace("null", "None")
    list_chapters = ast.literal_eval(chapters_string)

    # create folder if does not exists
    mangas_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "Mangas")
    os.makedirs(mangas_path, exist_ok=True)
    folder_path = os.path.join(mangas_path, manga_name_display)
    os.makedirs(folder_path, exist_ok=True)

    # add more to the list of chapters
    list_chapters = [[chapter, folder_path, manga_name] for chapter in list_chapters]
    number_chapters = len(list_chapters)

    # start processing pool
    pool = multiprocessing.Pool(processes=ENV.max_processes, initializer=ENV.set_child_process)

    # send all the processes to a pool
    printer_thread = threading.Thread(target=printer,
                                        daemon=True,
                                      args=(manga_name_display, number_chapters))
    printer_thread.start()
    pool.starmap(download_and_zip, list_chapters)

    pool.close()
    pool.join()
    printer_thread.join()


def search() -> str:
    """ function that search for a manga in the database """
    raw_input.clear()
    print("Downloading list of manga chapters..")
    response = requests.get("https://www.manga4life.com/search/", timeout=10)
    if response.status_code != 200:
        print("Cannot reach the server.")
        return ""
    page_text = response.text
    list_mangas = re.findall(r'vm.Directory = (.*);', page_text)[0]
    list_mangas = list_mangas.replace("null", "None").replace("false", "False").replace("true", "True")
    list_mangas = ast.literal_eval(list_mangas)
    list_mangas = [(entry["i"], entry["s"], entry["s"].lower())
                  for entry in list_mangas]
    # first entry-url, second entry-display, third entry-search
    list_mangas.sort()

    index = 0
    word_display = ""
    while True:
        raw_input.clear()
        print("Press tab to exit.")
        print("=", word_display)
        rows_len = os.get_terminal_size().lines-3
        columns_len = os.get_terminal_size().columns
        word_search = word_display.lower()
        search_list = (entry for entry in list_mangas if word_search in entry[2])
        search_list = list(islice(search_list, rows_len))

        index = min(index, max(len(search_list)-1, 0))

        for i, entry in enumerate(search_list):
            title = entry[1]
            if len(title) > columns_len-2:
                title = title[:columns_len-5] + "..."
            pre = "-" if i == index else " "
            print(pre, title)

        button = raw_input.get_key()
        if button == "enter":
            return f"https://www.manga4life.com/manga/{search_list[index][0]}"
        elif button == "backspace":
            word_display = word_display[:-1]
        elif button == "tab":
            return ""
        elif button == "up":
            if index:
                index -= 1
        elif button == "down":
            if index <= rows_len-2:
                index += 1
        elif button == "left" or button == "right":
            pass
        else:
            word_display += button


if __name__ == "__main__":
    ENV = Environment()

    parser = argparse.ArgumentParser(prog="mangalife_downloader",
                                    description="download manga from mangalife")
    parser.add_argument("-u", "--urls", nargs="+")
    args = parser.parse_args()  # args.picker contains the modality

    signal.signal(signal.SIGINT, ENV.sigint_handler)

    if args.urls:
        print("Press CTRL+C to quit.")
        for url in args.urls:
            download_manga(url)
    else:
        url = search()
        raw_input.clear()
        if url:
            print("Press CTRL+C to quit.")
            download_manga(url)

    ENV.quit()
