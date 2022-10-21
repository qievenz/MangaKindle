class Manga:
    def __init__(self):
        self.path = ""
        self.encoded_title = ""
        self.uuid = ""
        self.title = ""
        self.chapters = {}
        
class Chapter:    
    def __init__(self):
        self.uuid = ""
        self.path = ""
        self.pages = {}
    
class Page:
    def __init__(self):
        self.uuid = ""
        self.path = ""