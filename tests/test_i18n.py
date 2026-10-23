import json
import re
from html.parser import HTMLParser
from pathlib import Path
from fastapi.testclient import TestClient
import app as web
import i18n


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text=[]
        self.links=[]
    def handle_data(self, data):
        self.text.append(data)
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='link': self.links.append(attrs)


def test_all_english_pages_and_language_links():
    with TestClient(web.app) as c:
        for path in ('','/about','/technical','/articles','/articles/what-is-horary','/articles/history','/articles/methods','/articles/evidence'):
            r=c.get('/en'+path)
            assert r.status_code==200
            parsed=Text();parsed.feed(r.text)
            leftovers=re.findall(r'[А-Яа-яЁё]+',' '.join(parsed.text))
            assert set(leftovers) <= {'Русский','Язык'}, (path,leftovers)
            assert 'id="languageSelect"' in r.text
            assert len([l for l in parsed.links if l.get('rel')=='canonical'])==1
            assert '<html lang="en">' in r.text
            assert '/en/about' in r.text
        assert c.get('/xx/about').status_code==404
        assert c.get('/i18n/xx.js').status_code==404
        assert c.get('/en').text.index('/static/i18n.js') < c.get('/en').text.index('/static/app.js')
        assert c.get('/en').cookies.get('horary_owner') is None  # existing browser is preserved
        assert c.get('/ru').status_code==200


def test_demo_calculations_are_identical_and_cached_timeline_not_mutated():
    with TestClient(web.app) as c:
        english=c.get('/api/demo',headers={'X-Horary-Language':'en'}).json()
        russian=c.get('/api/demo').json()
        assert english['data']['planets'][0]['name']=='Sun'
        assert russian['data']['planets'][0]['name']=='Солнце'
        assert english['data']['language']=='en'
        assert english['data']['houses']==russian['data']['houses']
        assert [p['longitude'] for p in english['data']['planets']]==[p['longitude'] for p in russian['data']['planets']]
        assert not re.search('[А-Яа-яЁё]',english['export_svg'])
        assert not re.search('[А-Яа-яЁё]',json.dumps(english['data'],ensure_ascii=False))
        assert 'Солнце' in russian['export_svg']
        assert c.get('/api/readings/nope',headers={'X-Horary-Language':'en'}).status_code==401


def test_catalog_covers_client_messages():
    messages=i18n.catalog('en')
    for name in ('app.js','voice.js'):
        js=(Path('static')/name).read_text(encoding='utf-8')
        for key in re.findall(r"t\('([^']*[А-Яа-яЁё][^']*)'",js):
            assert key in messages,(name,key)
        # No Russian copy left in dynamic template literals.
        for template in re.findall(r'`([^`]+)`',js):
            cleaned=re.sub(r"t\('[^']+'\)",'',template)
            assert not re.search('[А-Яа-яЁё]',cleaned),(name,template)


def test_unknown_language_and_validation_do_not_echo_input():
    with TestClient(web.app) as c:
        c.get('/en')
        r=c.post('/api/readings',json={'question':'A question about my job','topic':'career','city_id':'5128581','consent':True,'language':'xx'},headers={'X-Horary-Language':'en'})
        assert r.status_code==422
        secret='test-password-do-not-echo'
        r=c.post('/api/admin/login',json={'password':[secret]})
        assert r.status_code==422 and secret not in r.text
