"""necessary modules"""

import os
import argparse
import multiprocessing
import threading
import signal
import time
from zipfile import ZipFile
import requests
import raw_input
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

    @property
    def rows_len(self) -> int:
        """rows length"""

        return os.get_terminal_size().lines - 3

    @property
    def columns_len(self) -> int:
        """columns length"""

        return os.get_terminal_size().columns

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

    def generate_search_print(outer_self):
        """generate the class search print"""

        class SearchPrint:
            """class contaning variables useful for the search printer"""

            def __init__(self) -> None:
                self.word_display = ""
                self.url_manga = ""
                self.index = 0
                self.queue = outer_self.manager.Queue()

            def quit(self) -> None:
                """quit class"""

                self.queue.put(None)

        return SearchPrint()

    def quit(self) -> None:
        """quit environment"""

        self.manager.shutdown()
        if self.stop:
            print("\nProgram terminated, re-run to resume.")


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


def search_print_function(manga_website: str, search_print) -> None:
    """async search printer"""

    while search_print.queue.get():
        time.sleep(0.05)

        print_list = ENV.get_manga[manga_website].print_list(
            search_print.word_display, ENV.rows_len
        )

        # adjust the index
        search_print.index = min(search_print.index, max(len(print_list) - 1, 0))

        columns_len = ENV.columns_len

        # ----- print
        to_print = ["Press tab to exit.\n= ", search_print.word_display]
        for i, entry in enumerate(print_list):
            if len(entry[0]) <= columns_len - 2:
                title = entry[0]
            else:
                title = entry[0][: columns_len - 5] + "..."
            if i == search_print.index:
                pre = "-"
            else:
                pre = " "
            to_print.append("\n")
            to_print.append(pre)
            to_print.append(" ")
            to_print.append(title)

        raw_input.keyboard_detach()
        raw_input.clear()
        print(*to_print, sep="")
        raw_input.keyboard_attach()
        # ----- end print

        if search_print.index < len(print_list):
            search_print.url_manga = print_list[search_print.index][1]
        else:
            search_print.url_manga = ""

    raw_input.keyboard_detach()


def search(manga_website: str) -> dict:
    """function that search for a manga in the database"""

    ENV.get_manga[manga_website].load_database()

    search_print = ENV.generate_search_print()

    printer_thread = threading.Thread(
        target=search_print_function, daemon=True, args=(manga_website, search_print)
    )
    printer_thread.start()

    while True:
        raw_input.clear()
        print("Press tab to exit.")
        print("=", search_print.word_display)

        button = raw_input.getkey()
        search_print.queue.put(1)

        if button == "enter":
            search_print.quit()
            printer_thread.join()
            return ENV.get_manga[manga_website].create_manga(search_print.url_manga)

        elif button == "backspace":
            search_print.word_display = search_print.word_display[:-1]

        elif button == "tab":
            search_print.quit()
            printer_thread.join()
            return None

        elif button == "up":
            if search_print.index:
                search_print.index -= 1

        elif button == "down":
            if search_print.index <= ENV.rows_len - 2:
                search_print.index += 1

        elif button == "left" or button == "right":
            pass

        else:
            search_print.word_display += button


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
            raw_input.clear()
            if manga:
                print("Press CTRL+C to quit.")
                download_manga(manga)


if __name__ == "__main__":
    ENV = Environment()

    main()

    ENV.quit()
