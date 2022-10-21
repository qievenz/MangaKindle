
from abc import ABC, abstractmethod
from typing import Dict, List
from lib.Common import not_found, print_colored
from lib.results.manga_class import Chapter, Manga, Page
from colorama import Fore, Style, init as init_console_colors

class MangaTemplate(ABC):    
    def __init__(self):
        self.name = self.__class__.__name__
        self.search_results = []
        self.current_manga = Manga()
        
    def base_search(self, title) -> List[Manga]:
        if self.search_results:
            return self.search_results
        print_colored(f"Searching '{title}' in '{self.name}'...", Style.BRIGHT)
        results = self.search(title)
        if not results: not_found(title)
        print_colored(f"Found {len(results)} results.", Style.BRIGHT)
    
    @abstractmethod
    def search(self, title) -> List[Manga]:
        pass
    
    @abstractmethod
    def get_chapters(self) -> Dict[float, Chapter]:
        pass
    
    @abstractmethod
    def get_pages(self, chapter_num) -> Dict[float, Page]:
        pass