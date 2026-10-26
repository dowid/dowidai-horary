"""Locale registry and server-rendered pages. Add a catalog and content folder per locale."""
import copy
import os
import seo
import json
from functools import lru_cache
from html import escape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parent
LANGUAGES = {'ru': {'name': 'Русский', 'locale': 'ru-RU', 'prompt_language':'русском'}, 'en': {'name': 'English', 'locale': 'en-US', 'prompt_language':'английском'}}


def language(request):
    value = request.headers.get('x-horary-language', 'ru')
    return value if value in LANGUAGES else 'ru'


@lru_cache(maxsize=16)
def catalog(lang):
    if lang == 'ru':
        return {}
    return json.loads((ROOT / 'static' / 'locales' / (lang + '.json')).read_text(encoding='utf-8'))


def translate(value, lang):
    return catalog(lang).get(value, value)


class Page(HTMLParser):
    def __init__(self, lang):
        super().__init__(convert_charrefs=True)
        self.lang, self.parts = lang, []

    def handle_decl(self, decl):
        self.parts.append('<!' + decl + '>')

    def handle_starttag(self, tag, attrs):
        if tag == 'link' and dict(attrs).get('rel') in ('canonical','alternate'):
            return
        out = []
        for key, value in attrs:
            if value is None:
                out.append(key)
                continue
            if key in ('aria-label', 'placeholder', 'title', 'content'):
                value = translate(value, self.lang)
            if tag == 'html' and key == 'lang':
                value = self.lang
            if key == 'href' and (value == '/' or value.split('#')[0] in ('/about', '/technical', '/articles') or value.startswith('/articles/')):
                value = '/' + self.lang + ('' if value == '/' else value)
            out.append(f'{key}="{escape(value, quote=True)}"')
        self.parts.append('<' + tag + (' ' + ' '.join(out) if out else '') + '>')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.parts.append('</' + tag + '>')

    def handle_data(self, data):
        stripped = data.strip()
        translated = translate(stripped, self.lang)
        self.parts.append(escape(data.replace(stripped, translated, 1) if stripped else data, quote=False))


def page(filename, lang, path=''):
    source = ROOT / 'static' / filename
    localized = ROOT / 'static' / lang / filename
    if lang != 'ru' and localized.exists():
        source = localized
    parser = Page(lang)
    parser.feed(source.read_text(encoding='utf-8'))
    html = ''.join(parser.parts)
    options = ''.join(f'<option value="{code}"'+(' selected' if code == lang else '')+f'>{info["name"]}</option>' for code, info in LANGUAGES.items())
    switch = '<label class="language-picker"><span class="sr-only">Language / Язык</span><select id="languageSelect" aria-label="Language / Язык">'+options+'</select></label>'
    html = html.replace('</nav>', switch+'</nav>', 1)
    scripts = f'<script src="/i18n/{lang}.js?v=1" defer></script><script src="/static/i18n.js?v=1" defer></script>'
    environment = escape(os.getenv('VERCEL_ENV', 'development'), quote=True)
    version = escape(os.getenv('VERCEL_GIT_COMMIT_SHA', 'local')[:12], quote=True)
    scripts += f'<script src="/static/analytics.js?v=1" data-environment="{environment}" data-version="{version}" defer></script>'
    # i18n must execute before app and voice scripts.
    html = html.replace('<head>', '<head>'+scripts, 1)
    base = seo.BASE
    links = ''.join(f'<link rel="alternate" hreflang="{code}" href="{base}/{code}{path}">' for code in LANGUAGES)
    links += f'<link rel="alternate" hreflang="x-default" href="{base}/en{path}">'
    html = html.replace('</head>', f'<link rel="canonical" href="{base}/{lang}{path}">'+links+'</head>')
    return seo.enhance(html, lang, path)


@lru_cache(maxsize=16)
def technical_catalog(lang):
    if lang == 'ru':
        return {}
    return json.loads((ROOT / 'locales' / (lang + '.json')).read_text(encoding='utf-8'))


def technical_text(value, lang):
    translations = technical_catalog(lang)
    if value in translations:
        return translations[value]
    # Composed chart labels use a small controlled vocabulary.
    for a, b in translations.items():
        if a.startswith('@'):
            value = value.replace(a[1:], b)
    return value


def localize_chart(data, lang):
    data = copy.deepcopy(data)
    for p in data['planets']:
        for key in ('name', 'sign'):
            p[key] = technical_text(p[key], lang)
    for a in data['aspects']:
        a['name'] = technical_text(a['name'], lang)
    for key in ('warnings', 'limitations'):
        data[key] = [technical_text(s, lang) for s in data[key]]
    data['method'] = technical_text(data['method'], lang)
    if 'events' in data:
        data['events']['selection'] = technical_text(data['events']['selection'], lang)
        for key in ('past', 'future'):
            for e in data['events'][key]:
                e['label'] = technical_text(e['label'], lang)
    return data


def localize_svg(svg, lang):
    # Translate only text and accessibility labels, never coordinates or SVG syntax.
    import re
    from html import unescape
    svg = re.sub(r'>([^<>]+)<', lambda m: '>'+escape(technical_text(unescape(m[1]), lang), quote=False)+'<', svg)
    return re.sub(r'aria-label="([^"]*)"', lambda m: 'aria-label="'+escape(technical_text(unescape(m[1]), lang), quote=True)+'"', svg)
