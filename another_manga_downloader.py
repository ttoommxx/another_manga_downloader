"""manga downloader written in Python"""

import os
import sys
import argparse
from multiprocessing.pool import ThreadPool
import queue
import threading
import signal
import ctypes
from zipfile import ZipFile
import requests
import unicurses as uc
from manga_websites import create_manga_dict, get_manga_website


if sys.version_info.major == 3 and sys.version_info.minor >= 13 and sys._is_gil_enabled():
    print("Python GIL is enabled, might experience performance")

# environment variables


class Environment:
    """class that defined environment variables"""

    def __init__(self, timeout) -> None:
        self.timeout = timeout
        self.stop = 0
        self.print_queue = queue.Queue()
        self.get_manga = create_manga_dict(timeout)

    def set_main_process(self) -> None:
        """set process as main"""

        def sigint_main(*args) -> None:
            """signal INT handler"""

            print("\nQuitting..")
            self.print_queue.put(1)
            self.stop = 1

        signal.signal(signal.SIGINT, sigint_main)

    def quit(self) -> None:
        """quit environment"""

        if self.stop:
            print("\nProgram terminated, re-run to resume.")


ENV = Environment(timeout=10)


class SearchClass:
    """class contaning variables useful for the search printer"""

    def __init__(self, manga_website: str) -> None:
        self.word = ""
        self.url_manga = ""
        self._index = 0
        self._print_list: list[tuple[str, str]] = []
        self.queue: queue.Queue[int] = queue.Queue(maxsize=1)

        # enable the curses module
        uc.cbreak()
        uc.noecho()
        uc.keypad(uc.stdscr, True)
        uc.curs_set(0)
        uc.leaveok(uc.stdscr, True)

        # start the printer thread
        self.printer_thread = threading.Thread(
            target=search_printer,
            daemon=True,
            args=(manga_website, self),
        )
        self.printer_thread.start()

    @property
    def print_list(self) -> list[tuple[str, str]]:
        """print_list return"""

        return self._print_list

    @print_list.setter
    def print_list(self, new_list: list[tuple[str, str]]) -> None:
        """print_list setter"""

        self._print_list = new_list
        self.index = min(self.index, max(len(new_list) - 1, 0))

    @property
    def index(self) -> int:
        """index return"""

        return self._index

    @index.setter
    def index(self, val: int) -> None:
        """index setter"""

        if 0 <= val < min(self.rows - 2, len(self.print_list)):
            self._index = val

        if self.index < len(self.print_list):
            self.url_manga = self.print_list[self.index][1]
        else:
            self.url_manga = ""

    @property
    def columns(self) -> int:
        """return number of columns"""

        return uc.getmaxx(uc.stdscr)

    @property
    def rows(self) -> int:
        """return number of rows"""

        return uc.getmaxy(uc.stdscr)

    def queue_put(self) -> None:
        """put 1 in queue if it is empty"""

        if self.queue.empty():
            self.queue.put(1)

    def quit(self) -> None:
        """quit class"""

        self.queue.put(0)
        self.printer_thread.join()
        uc.clear()
        uc.endwin()


# functions


def printer(manga_name: str, number_chapters: int) -> None:
    """function that updates the count of the executed chapters"""

    if ENV.stop:
        return

    failed = []
    ENV.print_queue.put(None)

    print(f"- {manga_name}:")

    for i in range(number_chapters + 1):
        token = ENV.print_queue.get()
        if token == 1:
            return
        if token:
            failed.append(token)
        print(f"  {i} / {number_chapters}", end="\r")

    print()
    if failed:
        print("The following chapters have failed.")
        for chapter in failed:
            print(chapter)
    else:
        print("No chapter has failed.")


def download_and_zip(
    chapter: dict, folder_path: str, manga: dict[str, str | list[dict]]
) -> None:
    """given a chapter and a path, create the zip file
    add a token to the queue when the process is done"""

    if ENV.stop:
        return

    chapter_path = os.path.join(folder_path, chapter["name"])
    zip_path = chapter_path + ".cbz"

    if os.path.exists(zip_path):
        ENV.print_queue.put(None)
        return

    os.makedirs(chapter_path, exist_ok=True)

    # DOWNLOAD
    pages = []
    for page_str, image_link in ENV.get_manga[manga["website"]].img_generator(
        chapter, manga
    ):
        if not page_str:
            ENV.print_queue.put(f"{chapter['name']} error type '{image_link}'")
            return

        file_path = os.path.join(chapter_path, page_str + ".png")
        if not os.path.exists(file_path):
            try:
                response = requests.get(image_link, stream=True, timeout=ENV.timeout)
            except Exception as excp:
                ENV.print_queue.put(f"{chapter['name']} error type: {excp}")
                return

            with open(file_path, "wb") as page_file:
                for chunk in response.iter_content(1024):
                    page_file.write(chunk)

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
        ENV.print_queue.put(chapter["name"])
    else:
        ENV.print_queue.put(None)


def download_manga(manga: dict[str, str | list[dict]]) -> None:
    """main function"""

    if ENV.stop:
        return

    # create folder if does not exists
    home = os.path.expanduser("~")
    mangas_path = os.path.join(home, "Mangas")
    os.makedirs(mangas_path, exist_ok=True)
    assert isinstance(manga["name"], str)
    folder_path = os.path.join(mangas_path, manga["name"])
    os.makedirs(folder_path, exist_ok=True)

    # add more to the list of chapters
    list_chapters = [
        (chapter, folder_path, manga) for chapter in manga["list_chapters"]
    ]
    number_chapters = len(list_chapters)

    # send all the processes to a pool
    printer_thread = threading.Thread(
        target=printer, daemon=True, args=(manga["name"], number_chapters)
    )
    printer_thread.start()

    # start processing pool
    with ThreadPool(processes=8) as pool:
        pool.starmap(download_and_zip, list_chapters)

    printer_thread.join()


def search_printer(manga_website: str, search_class: SearchClass) -> None:
    """async search printer"""

    print_win = uc.newwin(search_class.rows - 2, search_class.columns, 2, 0)
    uc.leaveok(print_win, True)

    while search_class.queue.get():
        search_class.print_list = ENV.get_manga[manga_website].print_list(
            search_class.word, search_class.rows - 2
        )

        columns_len = search_class.columns

        # ----- print
        uc.wresize(print_win, search_class.rows - 2, search_class.columns)
        uc.wclear(print_win)

        for i, entry in enumerate(search_class.print_list):
            if len(entry[0]) <= columns_len - 2:
                title = entry[0]
            else:
                title = entry[0][: columns_len - 5] + "..."
            if i == search_class.index:
                pre = "-"
            else:
                pre = " "
            uc.mvwaddwstr(print_win, i, 0, f"{pre} {title}")

        uc.wrefresh(print_win)
        # ----- end print


def search(stdscr: ctypes.c_void_p, manga_website: str) -> dict[str, str | list[dict]]:
    """function that search for a manga in the database"""

    ENV.get_manga[manga_website].load_database()

    search_class = SearchClass(manga_website)

    uc.mvaddstr(0, 0, "Press TAB to exit.")
    uc.mvaddch(1, 0, "|")

    while True:
        button = uc.getkey()

        if button == "KEY_UP":
            if len(search_class.print_list) > 1:
                uc.mvaddch(2 + search_class.index, 0, " ")
                search_class.index -= 1
                uc.mvaddch(2 + search_class.index, 0, "-")
        elif button == "KEY_DOWN":
            if len(search_class.print_list) > 1:
                uc.mvaddch(2 + search_class.index, 0, " ")
                search_class.index += 1
                uc.mvaddch(2 + search_class.index, 0, "-")
        elif button == "^I":
            output = {}
            break
        elif button == "^J":
            output = ENV.get_manga[manga_website].create_manga(search_class.url_manga)
            break
        if button == "KEY_BACKSPACE":
            if search_class.word:
                uc.mvaddch(1, 1 + len(search_class.word), " ")
                search_class.word = search_class.word[:-1]
                if search_class.queue.empty():
                    search_class.queue_put()
        elif len(button) == 1:
            uc.mvadd_wch(1, 2 + len(search_class.word), button)
            search_class.word += button
            if search_class.queue.empty():
                search_class.queue_put()

    search_class.quit()

    return output


def main(urls: list[str]) -> None:
    """main function"""

    ENV.set_main_process()

    if urls:
        print("Press CTRL+C to quit.")
        for url in urls:
            manga_website = get_manga_website(url)
            if not manga_website:
                print("Manga website not identified")
                continue
            manga = ENV.get_manga[manga_website].create_manga(url)
            download_manga(manga)

    else:
        search_again = True
        while search_again:
            print("Select the website you want to use")
            manga_selection = list(ENV.get_manga.keys())
            for num, key in enumerate(manga_selection):
                print(num, "->", key)

            index = input("Selection: ")
            if index.isdigit() and 0 <= int(index) < len(manga_selection):
                manga_website = manga_selection[int(index)]
                manga = uc.wrapper(search, manga_website)
                if manga:
                    print("Press CTRL+C to quit.")
                    download_manga(manga)

            search_again = input(
                "Do you want to search again? [y/n] "
            ).strip().lower() in ("y", "yes")

    ENV.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="another_manga_downloader",
        description="yes, yikes, here's another manga downloader..",
    )
    parser.add_argument("-u", "--urls", nargs="+", help="insert links to download")
    args = parser.parse_args()  # args.picker contains the modality

    main(args.urls)
