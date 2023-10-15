
from abc import ABC, abstractmethod
import os
from re import search
from typing import Dict, List
from colorama import Fore
from lib.Common import encode_path, exit_if_fails, network_error, print_colored, success, write_file
from lib.AbstractMangas.MangaTemplate import MangaTemplate
from lib.results.manga_class import Chapter, Manga, Page
import cloudscraper
import requests

class OnlineMangaTemplate(MangaTemplate, ABC):
    def __init__(self):
        super().__init__()
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
        except requests.exceptions.ConnectionError:
            network_error()
        return response
    
    @abstractmethod
    def search(self, title) -> List[Manga]:
        pass
    
    @abstractmethod
    def get_chapters(self) -> Dict[float, Chapter]:
        pass
    
    @abstractmethod
    def get_pages(self, chapter_num) -> Dict[float, Page]:
        pass