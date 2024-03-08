"""necessary modules"""

import os
import argparse
import multiprocessing
import queue
import threading
import signal
import time
from zipfile import ZipFile
import requests
import unicurses as uc
from manga_websites import create_manga_dict, get_manga_website

# environment variables

TIMEOUT = 100  # this variable can be changed


class Environment:
    """class that defined environment variables"""

    def __init__(self) -> None:
        self.max_processes = min(os.cpu_count(), 8)
        self.manager = multiprocessing.Manager()
        self._stop = multiprocessing.Value("i", 0)
        self.print_queue = self.manager.Queue()
        self.get_manga = create_manga_dict(TIMEOUT)

    @property
    def stop(self) -> int:
        """return stopping value"""

        return self._stop.value

    def set_child_process(self) -> None:
        """initialiser for secondary processes"""

        signal.signal(signal.SIGINT, lambda *args: None)

    def set_main_process(self) -> None:
        """set process as main"""

        def sigint_handler(*args) -> None:
            """signal INT handler"""

            print("\nQuitting..")
            self.print_queue.put(1)
            self._stop.value = 1

        signal.signal(signal.SIGINT, sigint_handler)

    def quit(self) -> None:
        """quit environment"""

        self.manager.shutdown()
        if self.stop:
            print("\nProgram terminated, re-run to resume.")


class PrintClass:
    """class contaning variables useful for the search printer"""

    def __init__(self, manga_website: str) -> None:
        self.word_display = ""
        self.url_manga = ""
        self._index = 0
        self.print_list = []
        self.queue = queue.Queue(maxsize=1)

        # enbale the curses module
        self.stdscr = uc.initscr()
        uc.cbreak()
        uc.noecho()
        uc.keypad(self.stdscr, True)
        # uc.curs_set(0)

        # start the printer thread
        self.printer_thread = threading.Thread(
            target=search_printer,
            daemon=True,
            args=(manga_website, self),
        )
        self.printer_thread.start()

    @property
    def index(self) -> int:
        """index return"""

        self._index = min(self._index, len(self.print_list))
        return self._index

    @index.setter
    def index(self, val: int) -> None:
        """index setter"""

        if 0 <= val <= min(self.rows - 3, len(self.print_list) - 1):
            self._index = val

            if self.index < len(self.print_list):
                self.url_manga = self.print_list[self.index][1]
            else:
                self.url_manga = ""

    @property
    def columns(self) -> int:
        """return number of columns"""

        return uc.getmaxyx(self.stdscr)[1]

    @property
    def rows(self) -> int:
        """return number of rows"""

        return uc.getmaxyx(self.stdscr)[0]

    def quit(self) -> None:
        """quit class"""

        self.queue.put(None)
        self.printer_thread.join()
        uc.endwin()


# functions


def printer(manga_name: str, number_chapters: int) -> None:
    """function that updates the count of the executed chapters"""

    if ENV.stop:
        return

    failed = []
    ENV.print_queue.put(None)

    for i in range(number_chapters + 1):
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


def download_and_zip(chapter: str, folder_path: str, manga: dict) -> None:
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
        if page_str is None:
            ENV.print_queue.put(chapter["name"] + " error type: " + image_link)
            return

        file_path = os.path.join(chapter_path, page_str + ".png")
        if not os.path.exists(file_path):
            try:
                response = requests.get(image_link, stream=True, timeout=10)
            except Exception as e:
                ENV.print_queue.put(chapter["name"] + " error type: " + e)
                return

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
        ENV.print_queue.put(chapter["name"])
    else:
        ENV.print_queue.put(None)


def download_manga(manga: dict) -> None:
    """main function"""

    if ENV.stop:
        return

    # create folder if does not exists
    mangas_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "Mangas")
    os.makedirs(mangas_path, exist_ok=True)
    folder_path = os.path.join(mangas_path, manga["name"])
    os.makedirs(folder_path, exist_ok=True)

    # add more to the list of chapters
    list_chapters = [
        [chapter, folder_path, manga] for chapter in manga["list_chapters"]
    ]
    number_chapters = len(list_chapters)

    # start processing pool
    pool = multiprocessing.Pool(
        processes=ENV.max_processes, initializer=ENV.set_child_process
    )

    # send all the processes to a pool
    printer_thread = threading.Thread(
        target=printer, daemon=True, args=(manga["name"], number_chapters)
    )
    printer_thread.start()
    pool.starmap(download_and_zip, list_chapters)

    pool.close()
    pool.join()
    printer_thread.join()


def search_printer(manga_website: str, print_class) -> None:
    """async search printer"""

    while print_class.queue.get():
        time.sleep(0.1)

        print_class.print_list = ENV.get_manga[manga_website].print_list(
            print_class.word_display, print_class.rows - 2
        )

        columns_len = print_class.columns

        # ----- print
        for j in range(2, print_class.rows):  # clear the remainig lines
            uc.move(j, 0)
            uc.clrtoeol()

        i = 0
        for i, entry in enumerate(print_class.print_list):
            if len(entry[0]) <= columns_len - 2:
                title = entry[0]
            else:
                title = entry[0][: columns_len - 5] + "..."
            uc.mvaddstr(2 + i, 0, f"  {title}")

        uc.move(2 + print_class.index, 0)
        uc.refresh()
        # ----- end print


def search(manga_website: str) -> dict:
    """function that search for a manga in the database"""

    ENV.get_manga[manga_website].load_database()

    print_class = PrintClass(manga_website)

    uc.mvaddstr(0, 0, "Press TAB to exit.")
    uc.mvaddstr(1, 0, "| ")

    while True:
        uc.move(2 + print_class.index, 0)
        button = str(uc.getkey(), "utf-8")

        if button == "KEY_UP":
            print_class.index -= 1
        elif button == "KEY_DOWN":
            print_class.index += 1
        elif button == "^I":
            output = None
            break
        elif button == "^J":
            output = ENV.get_manga[manga_website].create_manga(print_class.url_manga)
            break
        if button == "KEY_BACKSPACE":
            if print_class.queue.empty():
                print_class.queue.put(1)
            uc.mvaddstr(1, 2 + len(print_class.word_display), " ")
            print_class.word_display = print_class.word_display[:-1]
        elif len(button) == 1:
            if print_class.queue.empty():
                print_class.queue.put(1)
            uc.mvaddstr(1, 2 + len(print_class.word_display), button)
            print_class.word_display += button

    print_class.quit()

    return output


def main() -> None:
    """main function"""

    parser = argparse.ArgumentParser(
        prog="mangalife_downloader", description="download manga from mangalife"
    )
    parser.add_argument("-u", "--urls", nargs="+")
    args = parser.parse_args()  # args.picker contains the modality

    ENV.set_main_process()

    if args.urls:
        # FIX THIS, IT DOES NOT WORK ANYMORE WITH URL DIRECTLY, INTEGRATE IN THE OTHER FILE WITH MORE FUNCTIONS AND WRITE A TEMPLATE
        print("Press CTRL+C to quit.")
        for url in args.urls:
            manga_website = get_manga_website(url)
            if not manga_website:
                print("Manga website not identified")
                continue
            manga = ENV.get_manga[manga_website].create_manga(url)
            download_manga(manga)

    else:
        print("Select the website you want to use")
        manga_selection = list(ENV.get_manga.keys())
        for num, key in enumerate(manga_selection):
            print(num, "->", key)

        index = input()
        if index != "q" and index.isdigit() and 0 <= int(index) < len(manga_selection):
            manga_website = manga_selection[int(index)]
            manga = search(manga_website)
            if manga:
                print("Press CTRL+C to quit.")
                download_manga(manga)


if __name__ == "__main__":
    ENV = Environment()

    main()

    ENV.quit()
