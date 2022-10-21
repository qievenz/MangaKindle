from multiprocessing.pool import INIT
import os
from pathlib import Path
from typing import Dict, List

from lib.Common import decode, encode, folders, titles_match
from lib.Constants import MANGA_DIR
from lib.results.manga_class import Chapter, Manga, Page


class LocalManga():
    def __init__(self):
        self.current_manga = Manga()
    
    def local_search(self, title, directory = MANGA_DIR) -> List[Manga]:
        for subdir, path in folders(directory):
            if titles_match(title, subdir):
                self.current_manga.title = decode(subdir)
                self.current_manga.url = path
                self.current_manga.chapters = self.get_chapters(path)
                return
    
    def get_chapters(self, manga_dir) -> Dict[float, Chapter]:
        chapters = {}
        chapters_dir = os.listdir(manga_dir)
        for chapter_dir in chapters_dir:
            chapter = Chapter()
            chapter.uuid = chapter_dir
            chapter.url = manga_dir + "/" + chapter_dir
            chapter.pages = self.get_pages(chapter.url)
            chapters[float(chapter.uuid)] = chapter
        return chapters
            
    def get_pages(self, chapter_dir) -> Dict[float, Page]:
        pages = {}
        page_files = os.listdir(chapter_dir)
        for page_file in page_files:
            page = Page()
            page.uuid = page_file.split('.')[0]
            page.url = chapter_dir + "/" + page_file
            pages[float(page.uuid)] = page
        return pages