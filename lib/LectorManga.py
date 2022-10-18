
import ast
import requests
from typing import Dict, List
from bs4 import BeautifulSoup
from lib.Common import exit_if_fails, network_error
from lib.results.manga_class import Chapter, Manga
from lib.MangaTemplate import MangaTemplate
import re

PROVIDER_WEBSITE = "https://lectormanga.com"
IMAGE_WEBSITE = f"https://img1.fashioncomplements.com/uploads"
CHAPTERS_WEBSITE = f"{PROVIDER_WEBSITE}/library/manga"
SEARCH_URL = f"{PROVIDER_WEBSITE}/library?title="
DOMAINS = ["recipeski", "chefac", "fashioncomplements", "recipesandcooker"]

class LectorManga(MangaTemplate):
    def online_search(self, manga_name) -> List[Manga]:
        if self.search_results:
            return self.search_results
        
        data = {
            'title': manga_name,
            'order_field': 'title',
            'order_item': 'likes_count',
            'order_dir': 'desc'
        }

        headers = {
            'Origin': PROVIDER_WEBSITE,
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': '*/*',
            'Referer': SEARCH_URL + manga_name,
            'X-Requested-With': 'XMLHttpRequest'
        }

        try:
            search = self.SCRAPER.get(SEARCH_URL + manga_name, data=data, headers=headers)
            exit_if_fails(search)
        except requests.exceptions.ConnectionError:
            network_error()

        results_bea = BeautifulSoup(search.content, 'html.parser').find_all(name="a", attrs={"class" : "text-light font-weight-light"}, href=True, recursive=True)

        for result_bea in results_bea:
            result = Manga()
            result.url = result_bea.get('href')
            if result.url is None:
                self.not_found()
            result.encoded_title = result.url.split('/')[-1] # encoded title
            result.uuid = result.url.split('/')[-2]
            result.title = result_bea.get('title') # may contain special characters
            
            self.search_results.append(result)
            
        return self.search_results
    
    def get_chapters(self) -> Dict[float, Chapter]:
        if self.current_manga.chapters:
            return self.current_manga.chapters
        try:
            url = f"{CHAPTERS_WEBSITE}/{self.current_manga.uuid}/{self.current_manga.title}"
            search = self.SCRAPER.get(url)
            exit_if_fails(search)
        except requests.exceptions.ConnectionError:
            network_error()
            
        chapter_bea = BeautifulSoup(search.content, 'html.parser').find_all(name="h4", attrs={"class" : "mt-2 text-truncate"}, href=False, recursive=True)
        list_bea = BeautifulSoup(search.content, 'html.parser').find_all(name="ul", attrs={"class" : "list-group list-group-flush chapter-list"}, href=False, recursive=True)
        
        i = 0
        for chapter in chapter_bea:
            manga_chapter = Chapter()
            chapter_div = str(list_bea[i].contents[1].contents[1].contents[9])
            manga_chapter.url = BeautifulSoup(chapter_div, 'html.parser').find(name="a", attrs={"class" : "btn btn-default btn-sm"}, href=True, recursive=True).get('href')
            manga_chapter.uuid = manga_chapter.url.split('/')[-1]
            chapter_num = re.findall("[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?", chapter.next)
            self.current_manga.chapters[float(chapter_num[0])] = manga_chapter
            i = i+1

        return self.current_manga.chapters
    
    def download_pages(self, chapter_num) -> None:
        manga_chapter = self.current_manga.chapters[chapter_num]
        headers = {
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'es-419,es;q=0.8',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Referer': self.current_manga.url,
                    'sec-fetch-mode': 'navigate',
                    'Cache-Control': 'no-cache',
                    'Upgrade-Insecure-Requests': '1',
                    'Connection': 'keep-alive',
                    'Pragma': 'no-cache',
                    'sec-fetch-dest': 'document',
                    'sec-fetch-site': 'cross-site',
                    'sec-fetch-user': '?1',
                    'sec-gpc': '1'
                }
        
        self.renew_scrapper(renew=True)
        url_1_get = self.SCRAPER.get(manga_chapter.url, headers=headers)

        if self.success(url_1_get, print_ok=False):
            url_1_bea = BeautifulSoup(url_1_get.content, 'html.parser')
            
            date = re.search("var dirPath = '(.*)';", str(url_1_bea)).group(1).split("/")[-3]
            id = re.search("var dirPath = '(.*)';", str(url_1_bea)).group(1).split("/")[-2]
            pages = ast.literal_eval(re.search("var images = JSON.parse(.*);", str(url_1_bea)).group(1).replace('(\'', '').replace('\')', ''))

            chapter_dir = self.chapter_directory(self.current_manga.title, chapter_num)
            page_number = 1
            headers = {
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'es-419,es;q=0.6',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Referer': self.current_manga.url,
                'Cache-Control': 'no-cache',
                'Upgrade-Insecure-Requests': '1',
                'Connection': 'keep-alive',
                'sec-fetch-dest': 'image',
                'sec-fetch-mode': 'no-cors',
                'sec-fetch-site': 'same-site',
                'sec-fetch-user': '?1',
                'sec-gpc': '1'
            }
            
            for img in pages:
                url = f"{IMAGE_WEBSITE}/{date}/{id}/{img}"
                self.download(page_number, url, chapter_dir, text=f'Page {page_number}/{len(pages)} ({100*page_number//len(pages)}%)', headers=headers)
                page_number = page_number+1