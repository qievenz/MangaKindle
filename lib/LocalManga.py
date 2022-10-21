from multiprocessing.pool import INIT
import os
from pathlib import Path
from typing import Dict, List

from lib.Common import chapter_directory, decode, encode, folders, manga_directory, titles_match
from lib.Constants import MANGA_DIR
from lib.MangaTemplate import MangaTemplate
from lib.results.manga_class import Chapter, Manga, Page


class LocalManga(MangaTemplate):
    def __init__(self):
        super().__init__()
        self.name = "Local"
    
    def search(self, title, directory = MANGA_DIR) -> List[Manga]:
        for subdir, path in folders(directory):
            if titles_match(title, subdir):
                result = Manga()
                result.title = decode(subdir)
                result.path = path
                self.search_results.append(result)
        
        return self.search_results
    
    def get_chapters(self) -> Dict[float, Chapter]:
        if self.current_manga.chapters:
            return self.current_manga.chapters
        
        chapters = {}
        manga_dir_chapters = os.listdir(self.current_manga.path)
        for manga_chapter in manga_dir_chapters:
            chapter = Chapter()
            chapter.uuid = manga_chapter
            chapter.path = manga_chapter
            chapter.pages = self.get_pages(float(chapter.uuid))
            chapters[float(chapter.uuid)] = chapter
        return chapters
            
    def get_pages(self, chapter_num) -> Dict[float, Page]:
        if self.current_manga.chapters and self.current_manga.chapters[chapter_num] and self.current_manga.chapters[chapter_num].pages:
            return self.current_manga.chapters[chapter_num].pages
        
        pages = {}
        chapter_dir = chapter_directory(self.current_manga.title, chapter_num)
        page_files = os.listdir(chapter_dir)
        for page_file in page_files:
            page = Page()
            page.uuid = page_file.split('.')[0]
            page.path = chapter_dir + "/" + page_file
            pages[float(page.uuid)] = page
        return pages