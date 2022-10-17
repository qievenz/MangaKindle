class Manga:
    def __init__(self):
        self.url = ""
        self.encoded_title = ""
        self.uuid = ""
        self.title = ""
        self.chapters = {}
        
class Chapter:    
    def __init__(self):
        self.uuid = ""
        self.url = ""
        self.pages = {}
    
class Page:
    def __init__(self):
        self.uuid = ""
        self.url = ""