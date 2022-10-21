
import ast
import requests
from typing import Dict, List
from bs4 import BeautifulSoup
from lib.Common import chapter_directory, encode_url_format, exit_if_fails, network_error, not_found, success
from lib.OnlineMangaTemplate import OnlineMangaTemplate
from lib.results.manga_class import Chapter, Manga
import re

PROVIDER_WEBSITE = "https://lectormanga.com"
IMAGE_WEBSITE = f"https://img1.fashioncomplements.com/uploads"
CHAPTERS_WEBSITE = f"{PROVIDER_WEBSITE}/library/manga"
SEARCH_URL = f"{PROVIDER_WEBSITE}/library?title="
DOMAINS = ["recipeski", "chefac", "fashioncomplements", "recipesandcooker"]

class LectorManga(OnlineMangaTemplate):
    def search(self, title) -> List[Manga]:
        data = {
            'title': title,
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
            'Referer': SEARCH_URL + title,
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        manga_name_encode = encode_url_format(title)
        search = self.scraper_get(SEARCH_URL + manga_name_encode, data=data, headers=headers)
        results_bea = BeautifulSoup(search.content, 'html.parser').find_all(name="a", attrs={"class" : "text-light font-weight-light"}, href=True, recursive=True)

        for result_bea in results_bea:
            result = Manga()
            result.path = result_bea.get('href')
            if result.path is None:
                not_found()
            result.encoded_title = result.path.split('/')[-1] # encoded title
            result.uuid = result.path.split('/')[-2]
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
            manga_chapter.path = BeautifulSoup(chapter_div, 'html.parser').find(name="a", attrs={"class" : "btn btn-default btn-sm"}, href=True, recursive=True).get('href')
            manga_chapter.uuid = manga_chapter.path.split('/')[-1]
            chapter_num = re.findall("[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?", chapter.next)
            self.current_manga.chapters[float(chapter_num[0])] = manga_chapter
            i = i+1

        return self.current_manga.chapters
    
    def get_pages(self, chapter_num) -> None:
        manga_chapter = self.current_manga.chapters[chapter_num]
        headers = {
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'es-419,es;q=0.8',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Referer': self.current_manga.path,
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
        
        self.renew_scrapper()
        url_1_get = self.scraper_get(manga_chapter.url, headers=headers)
        url_1_bea = BeautifulSoup(url_1_get.content, 'html.parser')
        
        date = re.search("var dirPath = '(.*)';", str(url_1_bea)).group(1).split("/")[-3]
        id = re.search("var dirPath = '(.*)';", str(url_1_bea)).group(1).split("/")[-2]
        pages = ast.literal_eval(re.search("var images = JSON.parse(.*);", str(url_1_bea)).group(1).replace('(\'', '').replace('\')', ''))

        chapter_dir = chapter_directory(self.current_manga.title, chapter_num)
        page_number = 1
        headers = {
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'es-419,es;q=0.6',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Referer': self.current_manga.path,
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