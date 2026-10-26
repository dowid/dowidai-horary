"""Public-page search metadata. Private reports never enter the sitemap."""
import json
import re
from html import escape, unescape

BASE = 'https://www.askhorary.app'
PATHS = ('', '/about', '/technical', '/articles', '/articles/what-is-horary', '/articles/history', '/articles/methods', '/articles/evidence')


def enhance(html, lang, path):
    if not path:
        title = 'Ask Horary — хорарная карта онлайн и объяснение вопроса' if lang == 'ru' else 'Ask Horary — Online Horary Astrology Chart & Interpretation'
        description = ('Постройте хорарную карту по вопросу, городу и времени. Расчёт Swiss Ephemeris, объяснение ИИ и статьи о методах и ограничениях астрологии.' if lang == 'ru' else 'Create a horary astrology chart for your question, city and time. Swiss Ephemeris calculations, AI explanations, and guides to methods and limitations.')
        html = re.sub(r'<title>.*?</title>', '<title>'+escape(title)+'</title>', html, flags=re.S)
        html = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="'+escape(description, quote=True)+'">', html)
    else:
        match = re.search(r'<title>(.*?)</title>', html, re.S)
        title = unescape(match[1]) + ' | Ask Horary'
        html = re.sub(r'<title>.*?</title>', '<title>'+escape(title)+'</title>', html, flags=re.S)
        match = re.search(r'<meta name="description" content="([^"]*)">', html)
        description = unescape(match[1]) if match else title
        if not match:
            html = html.replace('</head>','<meta name="description" content="'+escape(description,quote=True)+'"></head>')
    url = BASE + '/' + lang + path
    metadata = {'og:title':title, 'og:description':description, 'og:url':url, 'og:type':'website', 'og:site_name':'Ask Horary', 'og:locale':'ru_RU' if lang=='ru' else 'en_US', 'og:image':BASE+'/static/og-card.png', 'og:image:width':'1200', 'og:image:height':'630', 'og:image:alt':'Ask Horary — horary astrology'}
    tags = ''.join('<meta property="'+key+'" content="'+escape(value,quote=True)+'">' for key,value in metadata.items())
    tags += '<meta name="twitter:card" content="summary_large_image">'
    structured = {'@context':'https://schema.org','@type':'WebSite','name':'Ask Horary','url':BASE,'inLanguage':['ru','en']}
    tags += '<script type="application/ld+json">'+json.dumps(structured,ensure_ascii=False).replace('<','\u003c')+'</script>'
    html = html.replace('</head>',tags+'</head>')
    def brand(match):
        opening = re.sub(r' aria-label="[^"]*"','',match[1])
        return opening+'<img src="/static/logo.svg" width="40" height="40" alt=""><span>Ask Horary</span></a>'
    return re.sub(r'(<a\b[^>]*class="brand"[^>]*>).*?</a>',brand,html,flags=re.S)


def sitemap(languages):
    rows=[]
    for lang in languages:
        for path in PATHS:
            links=''.join(f'<xhtml:link rel="alternate" hreflang="{code}" href="{BASE}/{code}{path}"/>' for code in languages)
            links+=f'<xhtml:link rel="alternate" hreflang="x-default" href="{BASE}/en{path}"/>'
            rows.append(f'<url><loc>{BASE}/{lang}{path}</loc>{links}</url>')
    return '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'+''.join(rows)+'</urlset>'
