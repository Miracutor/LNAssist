import shutil
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from readability import Document
from tqdm import tqdm
from lnassist.epub import Epub


def is_valid(url):
    """Check if the url is valid
    """
    parsed = requests.utils.urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)


def is_image(url):
    """Check if the image url is in known file format
    """
    url: str
    if url.endswith(".png") == url.endswith(".jpg") == url.endswith(".gif") == url.endswith(".jpeg"):
        return False
    else:
        return True


def is_absolute(url):
    """Check if the url is absolute path
    """
    return bool(requests.utils.urlparse(url).netloc)


def request_url(url):
    """Request url.
    """
    try:
        response = requests.get(url)
    except requests.exceptions.RequestException as e:
        print('For some reason, the content cannot be fetched from Internet.')
        print('- Check your internet connection.')
        print('- Check if your url provided is valid.')
        print('Error: ' + str(e))
        print('')
        return

    return response


def if_only_true(*args):
    """Check if only one flags is True.
    """
    found = False
    already_found = False
    for it in args:
        if it is True:
            found = True
            if already_found is True:
                found = False
                break
            else:
                already_found = True

    return found


def print_title(text):
    print(text)
    x = 0
    while x < len(text):
        print('-', end='')
        x = x + 1
    print('')


def print_row(num: int, text: str):
    print('[' + str(num) + '] [' + text + ']')


class LNAssist:
    def __init__(self):
        self.series: str = 'None'  # Current series's short name. Example: Otomege
        # Example: The World of Otome Games is Tough For Mobs
        self.vol: int = 0  # Current volume
        self.chp_tasks_list = []  # List of chapter tasks
        self.img_tasks_list = []  # List of img tasks
        self.path: Path = Path('files')  # Current working path; use only if none series specified
        self.epub = None

    def set_series(self, short_name: str, volume: int):
        """Set the current series and the current volume numbering.

        Arguments:
        short_name -- short name of the series
        volume -- the current vol count
        """
        self.series: str = short_name.lower()  # convert to lower case
        self.vol: int = volume
        self.path: Path = Path('files')  # Reset to root folder first
        self.path: Path = self.path / self.series / ('vol' + str(self.vol))
        text = str(short_name) + ' Volume ' + str(volume)
        print_title(text)

    def out_epub(self):
        """"Export chapters and illustrations into an EPUB file.
        """
        self.epub = Epub(self.series + str(self.vol), self.path)
        self.epub.load()
        self.epub.output()

    def add(self, url: str, chapter: float = 0, prologue: bool = False, epilogue: bool = False, afterword: bool = False,
            illustrations: bool = False, extra: bool = False, sidestory: bool = False, interlude: bool = False):
        """Add a task into the queue.

        Arguments:
        url -- Current task url
        chapter -- Current task chapter count. Optional.

        Flags:
        prologue -- if current task chapter is prologue
        epilogue -- if current task chapter is epilogue
        afterword -- if current task chapter is afterword
        extra -- if current task chapter is extra
        sidestory -- if current task chapter is side story
        interlude -- if current task chapter is interlude
        illustrations -- if current task is for illustrations
        """
        if illustrations is False:
            if prologue or epilogue or afterword or extra or sidestory or interlude:
                if if_only_true(prologue, epilogue, afterword, extra, sidestory, interlude) is False:
                    print('Only one of these flags (prologue, epilogue, afterword, extra, sidestory, interlude) can be '
                          'enabled at one time.')
                    return
            self.chp_tasks_list.append(Task(url, chapter, prologue=prologue, epilogue=epilogue, afterword=afterword,
                                            extra=extra, sidestory=sidestory, interlude=interlude))
        else:
            self.img_tasks_list.append(Task(url, illustrations=illustrations))

    def run(self):
        """Run all the added tasks.
        """
        if len(self.chp_tasks_list) is 0 and len(self.img_tasks_list) is 0:
            print("No task available. Please add task first.")
            return

        if len(self.chp_tasks_list) is not 0:
            for x in tqdm(self.chp_tasks_list, "Executing chapter tasks  ", unit="tsk", ascii=True):
                x: Task
                self.extract_chapter(x.url, x.chapter, x.prologue, x.epilogue, x.afterword, x.extra, x.sidestory,
                                     x.interlude)  # chapter
            self.chp_tasks_list.clear()

        if len(self.img_tasks_list) is not 0:
            for x in self.img_tasks_list:
                x: Task
                self.extract_img(x.url)  # image task
            self.img_tasks_list.clear()

    def list(self):
        if len(self.chp_tasks_list) is 0 and len(self.img_tasks_list) is 0:
            print("No task available. Please add task first.")
            return

        print('Series: ' + self.series)
        print('Volume: ' + str(self.vol))
        print('')

        if len(self.chp_tasks_list) is not 0:
            print_title('Chapter Task List')
            i: int = 1
            for x in self.chp_tasks_list:
                x: Task
                if x.check_any() is True:
                    if x.extra:
                        print_row(i, 'extra (' + str(x.chapter) + ')')
                    elif x.sidestory:
                        print_row(i, 'ss (' + str(x.chapter) + ')')
                    elif x.interlude:
                        print_row(i, 'interlude (' + str(x.chapter) + ')')
                    elif x.prologue:
                        print_row(i, 'prologue')
                    elif x.epilogue:
                        print_row(i, 'epilogue')
                    elif x.afterword:
                        print_row(i, 'afterword')
                else:
                    print_row(i, 'chp (' + str(x.chapter) + ')')
                i += 1
            print('')

        if len(self.img_tasks_list) is not 0:
            print_title('Illustrations Task List')
            i: int = 1
            for x in self.img_tasks_list:
                x: Task
                print_row(i, 'illustrations (' + str(x.url) + ')')
                i += 1

    def clear(self, entire: bool = False):
        """Clear the current path according the current series.

        Optional:
        entire -- True if you want to delete entire files directory instead of current path. Default is False.
        """
        if entire is True:
            current = Path('files')
        else:
            current = self.path

        if current.is_dir():
            shutil.rmtree(current)
            print('Current folder cleared!')
        else:
            print('Current path not exist or already cleared!')

    def extract_chapter(self, url: str, chapter: float = 0, prologue: bool = False, epilogue: bool = False,
                        afterword: bool = False, extra: bool = False, sidestory: bool = False, interlude: bool = False):
        """Extract chapter text from the url and repackages into an xhtml for EPUB.

        Arguments:
        url -- Current url
        chapter -- Current chapter count. Optional.

        Flags:
        prologue -- if current chapter is prologue
        epilogue -- if current chapter is epilogue
        afterword -- if current chapter is afterword
        extra -- if current chapter is extra
        sidestory -- if current chapter is side story
        interlude -- if current chapter is interlude
        """
        if prologue or epilogue or afterword or extra or sidestory or interlude:
            if if_only_true(prologue, epilogue, afterword, extra, sidestory, interlude) is False:
                print('Only one of these flags (prologue, epilogue, afterword, extra, sidestory, interlude) can be '
                      'enabled at one time.')
                return

        if prologue is True:
            file_name = 'prologue.xhtml'
        elif epilogue is True:
            file_name = 'epilogue.xhtml'
        elif afterword is True:
            file_name = 'afterword.xhtml'
        elif extra is True and chapter is 0:
            file_name = 'extra.xhtml'
        elif extra is True:
            file_name = 'extra' + str(chapter) + '.xhtml'
        elif sidestory is True and chapter is 0:
            file_name = 'ss.xhtml'
        elif sidestory is True:
            file_name = 'ss' + str(chapter) + '.xhtml'
        elif interlude is True and chapter is 0:
            file_name = 'interlude.xhtml'
        elif interlude is True:
            file_name = 'interlude' + str(chapter) + '.xhtml'
        else:
            file_name = 'chp' + str(chapter) + '.xhtml'

        response = request_url(url)
        if response is None:
            return

        doc = Document(response.text)
        soup = BeautifulSoup(doc.summary(), "xml")
        soup.html['xmlns'] = 'http://www.w3.org/1999/xhtml'
        soup.html['xmlns:epub'] = 'http://www.idpf.org/2007/ops'
        # The tags that necessary for EPUB xhtml files

        chapter_path = self.path / 'chapters'
        if not chapter_path.is_dir():
            chapter_path.mkdir(parents=True)

        chapter_path = chapter_path / file_name
        chapter_path.write_text(soup.prettify(), encoding='UTF-8')

    def extract_img(self, url):
        """Fetch image links from the given url and download the links.

        Arguments:
        url -- Current url
        """
        response = request_url(url)
        if response is None:
            return

        soup = BeautifulSoup(response.content, "lxml")
        urls = []
        for img in tqdm(soup.find_all("img"), "Extracting images links  ", unit="img", ascii=True):
            img_url = img.attrs.get("src")
            if not img_url:
                continue

            if not is_absolute(img_url):
                img_url = requests.sessions.urljoin(url, img_url)

            try:
                pos = img_url.index("?")
                img_url = img_url[:pos]
            except ValueError:
                pass

            if not is_image(img_url):
                continue

            if is_valid(img_url):
                urls.append(img_url)

        for img in tqdm(urls, "Downloading images       ", unit="img", ascii=True):
            self.download_img(img)

    def download_img(self, url):
        """Downloads a image given an URL and puts it in the current path.

        Arguments:
        url -- Current url
        """
        pathname = self.path / "illustrations"
        buffer_size = 1024
        if not pathname.is_dir():
            pathname.mkdir(parents=True)

        response = requests.get(url, stream=True)
        filename = pathname / url.split("/")[-1]
        with filename.open("wb") as f:
            for chunk in response.iter_content(buffer_size):
                if chunk:
                    f.write(chunk)

            f.close()


class Task:
    def __init__(self, url: str, chapter: float = 0, prologue: bool = False, epilogue: bool = False,
                 afterword: bool = False, illustrations: bool = False, extra: bool = False, sidestory: bool = False,
                 interlude: bool = False):
        self.chapter = chapter
        self.url = url
        self.prologue = prologue
        self.epilogue = epilogue
        self.afterword = afterword
        self.extra = extra
        self.sidestory = sidestory
        self.interlude = interlude
        self.illustrations = illustrations

    def check_any(self):
        if self.interlude or self.sidestory or self.extra or self.afterword or self.prologue or self.epilogue is True:
            return True
        else:
            return False
