from django.core.management.base import BaseCommand
import urllib.request
import urllib.parse
import urllib.error
import json
import re
import datetime
from blog.models import Post, Ribbon
from progress.bar import Bar
from lxml import etree
import psycopg2
from pymongo import MongoClient
import locale
locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

class AdmeParser:

    def __init__(self, url):
        self.url = url
        self.html = self.exec()

    def exec(self):
        request = urllib.request.Request(
            self.url,
            data=None,
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}
        )
        try:
            with urllib.request.urlopen(request) as f:
                content = f.read().decode('utf-8')
                content = re.sub(r'<script>[\s\S]*?</script>', '', content)
                return content
        except urllib.error.HTTPError as error:
            print(error)
            return None

    def get_html(self):
        return self.html


class AdmePostParser(AdmeParser):

    def get_title(self):
        title_gr = re.search('<h1>(.+)</h1>', self.html)
        if len(title_gr.groups()) < 1:
            return None
        return str(title_gr.groups()[0]).strip()

    def get_views_count(self):
        matches = re.search('<li class="al-stats-views"><a href="#">([\d]*)</a></li>', self.html)
        if len(matches.groups()) < 1:
            return None
        return int(str(matches.groups()[0]).strip())

    def get_posted_at(self):
        months = {'января':'1','февраля':'2','марта':'3','апреля':'4','мая':'5','июня':'6',
                  'июля':'7','августа':'8','сентября':'9','октября':'10','ноября':'11','декабря':'12',}
        matches = re.search('<li class="al-stats-date" style="display: block;">(\d+) (\w+) (\d+)</li>', self.html)
        month = int(months[matches.groups()[1]])
        return datetime.datetime(day=int(matches.groups()[0]), month=month, year=int(matches.groups()[2]))

    def get_content(self):
        article_content = re.search('<article[^>]*>([\s\S]+?)</article>', self.html)
        if article_content is None:
            return None
        return str(article_content.groups()[0]).strip()


class AdmePageParser(AdmeParser):

    def get_urls(self):
        list = re.findall(r'<a href="([^"]+)"><img class="al-pic" src="([^"]*)" width="[\d]+" height="[\d]+" alt="[^"]*"></a>', self.html)
        return list



conn = psycopg2.connect(database="microblog", user="postgres", password="123", host="localhost")
cur = conn.cursor()


class Command(BaseCommand):

    def get_page_content(self, page, term):
        url = 'https://naked-science.ru/views/ajax'
        data = {
            'view_name': 'rubric_article_block',
            'view_display_id': 'block',
            'view_args': str(term) + '/' + str(term),
            'view_path': 'taxonomy/term/' + str(term),
            'view_base_path': 'null',
            #'view_dom_id': '99600e61418512210d936c9eb07ea61c',
            #'pager_element': 0,
            'page': page,
        }
        data = urllib.parse.urlencode(data)
        data = data.encode('ascii')
        request = urllib.request.Request(url, data)
        with urllib.request.urlopen(request) as f:
            json_data = json.loads(f.read().decode('utf-8'))
            for item in json_data:
                if item['command'] == 'insert':
                    return item['data']
        return None

    def parse_page_to_csv(self, page, term):
        page_content = self.get_page_content(page, term)
        page_content = page_content.replace('&','&amp;')
        root = etree.fromstring(page_content)
        # Получаем номер последней страницы
        r = root.xpath('//li[@class="pager-last last"]/a/@href')
        reg = re.compile('([\d]+)$')
        try:
            pst = reg.search(r[0])
            last_page = int(pst.group(0))
        except IndexError:
            last_page = None
        # Получаем список статей
        posts_list = root.xpath('//div[@class="view-content"]/div')
        for post in posts_list:
            link = post.xpath('div[@class="views-field views-field-title"]/span/a/@href')[0]
            title = post.xpath('div[@class="views-field views-field-title"]/span/a/text()')[0]
            try:
                content = post.xpath('div[@class="views-field views-field-field-lead"]/div/text()')[0]
            except IndexError:
                content = ''
            post_date = \
            post.xpath('div[@class="views-field views-field-nothing"]/span/span[@class="post-date"]/text()')[0]
            comments_count = \
            post.xpath('div[@class="views-field views-field-nothing"]/span/span[@class="post-comment"]/text()')[0]
            views_count = \
            post.xpath('div[@class="views-field views-field-nothing"]/span/span[@class="post-view"]/text()')[0]
            views_count = views_count.replace(' ', '')
            if views_count[-1] == 'K':
                views_count = int(float(views_count[0:-1]) * 1000)
            elif views_count[-3:] == 'млн':
                views_count = int(float(views_count[0:-3]) * 1000000)
            cur.execute(
                "INSERT INTO parsing_pages "
                "(source, link, title, content, post_date, comments_count, views_count) "
                "VALUES (%(source)s, %(link)s, %(title)s, %(content)s, %(post_date)s, %(comments_count)s, %(views_count)s)"
                "ON CONFLICT (link) DO UPDATE SET "
                "title=%(title)s, content=%(content)s, post_date=%(post_date)s, "
                "comments_count=%(comments_count)s, views_count=%(views_count)s",
                {
                    'source': 'naked-science',
                    'link': 'https://naked-science.ru' + link.strip(),
                    'title': title,
                    'content': content,
                    'post_date': post_date,
                    'comments_count': comments_count,
                    'views_count': views_count,
                }
            )
            conn.commit()

    def parse_adme_pages(self):
        client = MongoClient()
        db = client.adme
        upst = db.posts_urls

        for page in range(1, 86):
            purl = 'https://www.adme.ru/svoboda-psihologiya/page' + str(page) + '/'
            parser = AdmePageParser(purl)
            posts_urls = parser.get_urls()
            for post_url in posts_urls:
                upst.insert_one({
                    'url': 'https://www.adme.ru' + post_url[0],
                    'img': post_url[1],
                })

    def parse_adme_posts(self):
        client = MongoClient()
        db = client.adme
        upst = db.posts_urls
        pst = db.posts
        posts_urls = upst.find()
        bar = Bar('Processing', max=posts_urls.count())
        for post_url in posts_urls:
            try:
                parser = AdmePostParser(post_url['url'])
                pst.insert_one({
                    'title': parser.get_title(),
                    'views_count': parser.get_views_count(),
                    'content': parser.get_content(),
                    'posted_at': parser.get_posted_at(),
                    'revision_at': datetime.datetime.now(),
                    'source_url': post_url['url'],
                })
            except:
                continue
            bar.next()
        bar.finish()

    def prepare_adme_posts_1(self):
        client = MongoClient()
        db = client.adme
        posts = db.posts.find()
        for post in posts:
            content = post['content']
            content = re.sub(r'(<h1>[^<]*<\/h1>)', '', content)
            content = re.sub(r'(<p>[\s]*?</p>)', '', content)
            content = re.sub(r'(<p style="text-align: right;">[\s\S]*?</p>)', '', content)
            content = re.sub(r'(<div id="js-article-share-top"[\s\S]+?<\/div>[\s]+<\/div>[\s]+<\/div>[\s]<\/div>)', '', content)
            content = re.sub(r'(<div id="js-block-[\d]+">[\s]+<p>[\s]+<strong>Смотрите также<\/strong>[\s\S]+?<\/p>[\s]+<\/div>)', '', content)
            content = re.sub(r'(<div id="js-block-">[\s\S]+?<\/div><\/div>[\s]+<\/div>)', '', content)
            content = re.sub(r'(<p>[\s]+<a name="image[\d]+" href="#image[\d]+" style="[^"]+"[\s]+class="[^"]+">[\s]+<span class="article-pic js-article-image "[\s]+data-id="[\d]+">[\s]+<img src="([^"]+?)" data-social="[^"]+?"[^\/]+\/>[\s]+<\/span>[\s]+<\/a>[\s]+<\/p>)', r'<div class="post-inner-image"><img src="\2" alt=""></div>', content)
            content = content.strip()
            post['content2'] = content
            db.posts.update_one(
                {'_id': post['_id']},
                {'$set': post}
            )

    def prepare_adme_posts_2(self):
        client = MongoClient()
        db = client.adme
        posts = db.posts.find()
        ribbon = Ribbon.objects.get(pk=11)
        for post in posts:
            Post(
                title=post['title'],
                content=post['content2'],
                status='d',
                ribbon=ribbon,
                meta_data={
                    'source_url': post['source_url'],
                }
            ).save()

    def handle(self, *args, **options):
        self.prepare_adme_posts_2()
        pass
