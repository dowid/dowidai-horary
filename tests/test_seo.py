import json
import re
from xml.etree import ElementTree as ET
from fastapi.testclient import TestClient
import app as web
import seo


def test_sitemap_and_all_public_metadata():
    with TestClient(web.app) as c:
        r=c.get('/sitemap.xml')
        root=ET.fromstring(r.text)
        urls=root.findall('{*}url')
        assert len(urls)==16
        for entry in urls:
            url=entry.find('{*}loc').text
            assert url.startswith(seo.BASE)
            assert len(entry.findall('{*}link'))==3
            response=c.get(url.removeprefix(seo.BASE))
            assert response.status_code==200
            text=response.text
            assert f'<link rel="canonical" href="{url}">' in text
            assert f'property="og:url" content="{url}"' in text
            assert text.count('rel="canonical"')==1
            assert '/static/logo.svg' in text
            assert 'dowidai-horary.vercel.app' not in text
            structured=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',text)[1])
            assert structured['name']=='Ask Horary'
        assert 'Sitemap: '+seo.BASE+'/sitemap.xml' in c.get('/robots.txt').text
        assert c.get('/admin').headers['x-robots-tag']=='noindex, nofollow'
        assert c.get('/static/index.html').headers['x-robots-tag']=='noindex, follow'
        assert c.get('/static/og-card.png').status_code==200
