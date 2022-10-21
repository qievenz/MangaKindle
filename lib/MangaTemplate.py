
from abc import ABC, abstractmethod
import os
from typing import Dict, List
from urllib import request
from colorama import Fore
from lib.Common import encode_path, exit_if_fails, network_error, print_colored, success, write_file
from lib.results.manga_class import Chapter, Manga
import cloudscraper

class MangaTemplate(ABC):
    search_results: List[Manga]
    current_manga: Manga
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.search_results = []
        self.current_manga = Manga()
        self.SCRAPER = cloudscraper.create_scraper(browser = 'chrome', allow_brotli = False, debug = False)
        
    def renew_scrapper(self):
        self.SCRAPER = cloudscraper.create_scraper(delay=10,
                                    browser={
                                            'browser': 'chrome',
                                            'platform': 'android',
                                            'desktop': False
                                            },
                                    captcha={'provider': '2captcha'})

    def download(self, filename, url, directory='.', extension='png', text='', ok=200, headers=None):
        path = encode_path(filename, extension, directory)
        if os.path.isfile(path):
            text = text if text else path
            separation = ' ' * (20 - len(text))
            print_colored(f'{text}{separation}- Already exists', Fore.YELLOW)
            return False
        req = self.scraper_get(url, headers=headers)
        if success(req, text, ok, print_ok=bool(text)):
            data = req.content
            write_file(path, data)
            return True
        return False
    
    def scraper_get(self, url, headers=None, data=None):
        try:
            response = self.SCRAPER.get(url, headers=headers, data=data)
            exit_if_fails(url)
        except request.exceptions.ConnectionError:
            network_error()
        return response
    
    @abstractmethod
    def online_search(self, manga_name) -> List[Manga]:
        pass
    
    @abstractmethod
    def get_chapters(self) -> Dict[float, Chapter]:
        pass
    
    @abstractmethod
    def download_pages(self, chapter_num) -> None:
        pass
    