""" necessary modules """
import os
import argparse
import multiprocessing
import threading
import signal
from zipfile import ZipFile
import raw_input
from manga_websites import get_manga, get_manga_website

# environment variables


class Environment:
    """class that defined environment variables"""

    def __init__(self) -> None:
        self.max_processes = min(os.cpu_count(), 8)
        self.manager = multiprocessing.Manager()
        self._stop = multiprocessing.Value("i", 0)
        self.print_queue = self.manager.Queue()

    @property
    def stop(self) -> int:
        """return stopping value"""
        return self._stop.value

    @stop.setter
    def stop(self, val) -> None:
        """setter for stop multiprocessing value"""
        self._stop = val

    def set_child_process(self) -> None:
        """initialiser for secondary processes"""
        signal.signal(signal.SIGINT, lambda *args: None)

    def set_main(self) -> None:
        """set process as main"""
        signal.signal(signal.SIGINT, self.sigint_handler)

    def sigint_handler(self, *args) -> None:
        """signal keyboard interrupt handler"""
        print("\nQuitting..")
        self.print_queue.put(1)
        self._stop.value = 1

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

    failed_number = None
    if not os.path.exists(zip_path):
        os.makedirs(chapter_path, exist_ok=True)

        # DOWNLOAD
        pages = []
        for page_str, response in get_manga[manga["website"]].img_generator(
            chapter, manga
        ):
            file_path = os.path.join(chapter_path, page_str + ".png")
            if not os.path.exists(file_path):
                get_manga[manga["website"]].img_download(file_path, response)
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
            failed_number = chapter["name"]

    ENV.print_queue.put(failed_number)


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


def search(manga_website: str) -> dict:
    """function that search for a manga in the database"""

    get_manga[manga_website].load_database()
    raw_input.clear()

    index = 0
    word_display = ""
    while True:
        raw_input.clear()
        print("Press tab to exit.")
        print("=", word_display)

        rows_len = os.get_terminal_size().lines - 3
        columns_len = os.get_terminal_size().columns

        print_list = get_manga[manga_website].print_list(word_display, rows_len)

        # adjust the index
        index = min(index, max(len(print_list) - 1, 0))

        for i, entry in enumerate(print_list):
            title = entry[0]
            if len(title) > columns_len - 2:
                title = title[: columns_len - 5] + "..."
            pre = "-" if i == index else " "
            print(pre, title)

        button = raw_input.getkey()
        if button == "enter":
            url_manga = print_list[index][1]
            return get_manga[manga_website].create_manga(url_manga)
        elif button == "backspace":
            word_display = word_display[:-1]
        elif button == "tab":
            return None
        elif button == "up":
            if index:
                index -= 1
        elif button == "down":
            if index <= rows_len - 2:
                index += 1
        elif button == "left" or button == "right":
            pass
        else:
            word_display += button


if __name__ == "__main__":
    ENV = Environment()

    parser = argparse.ArgumentParser(
        prog="mangalife_downloader", description="download manga from mangalife"
    )
    parser.add_argument("-u", "--urls", nargs="+")
    args = parser.parse_args()  # args.picker contains the modality

    ENV.set_main()

    if args.urls:
        # FIX THIS, IT DOES NOT WORK ANYMORE WITH URL DIRECTLY, INTEGRATE IN THE OTHER FILE WITH MORE FUNCTIONS AND WRITE A TEMPLATE
        print("Press CTRL+C to quit.")
        for url in args.urls:
            MANGA_WEBSITE = get_manga_website(url)
            if not MANGA_WEBSITE:
                print("Manga website not identified")
                continue
            MANGA = get_manga[MANGA_WEBSITE].create_manga(url)
            download_manga(MANGA)

    else:
        print("Select the website you want to use")
        manga_selection = list(get_manga.keys())
        for num, key in enumerate(manga_selection):
            print(num, "->", key)

        INDEX = input()
        if INDEX != "q" and INDEX.isdigit() and 0 <= int(INDEX) < len(manga_selection):
            MANGA_WEBSITE = manga_selection[int(INDEX)]

            MANGA = search(MANGA_WEBSITE)
            raw_input.clear()
            if MANGA:
                print("Press CTRL+C to quit.")
                download_manga(MANGA)

    ENV.quit()
