import requests
import sys
import os
import wget
from html.parser import HTMLParser

class VTMHTMLParser(HTMLParser):
    def __init__(self) -> None:
        HTMLParser.__init__(self)
        self.clips = []
        pass

    def handle_starttag(self, tag, attrs):
        self.tag   = tag
        self.props = ''
        if self.tag == 'a':
            self.href = attrs[0][1]

    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        if data == '[To Parent Directory]':
            return

        if self.tag == 'br':
            self.props = data
        elif self.tag == 'a':
            item = {
                'name': data,
                'link': 'https://www.itu.int' + self.href
            }
            self.clips.append(item)

class WebpageRunner():
    def __init__(self) -> None:
        self.dir = 'clips'
        pass

    def run(self, link):
        self.link = link
        r = requests.get(link)
        parser = VTMHTMLParser()
        parser.feed(r.content.decode('utf-8'))

        if not os.path.exists(self.dir):
            os.mkdir(self.dir)

        os.chdir(self.dir)

        for c in parser.clips:
            print("Fetching %s" % c['link'])
            wget.download(c['link'],  bar=wget.bar_thermometer)

if __name__ == "__main__":
    w = WebpageRunner()
    w.run(sys.argv[1])
