from fastapi.testclient import TestClient
from app import app
import pytest

@pytest.mark.parametrize('model,slug', [('gpt-4.1-mini-2025-04-14','gpt-4.1-mini'), ('gpt-4.1-2025-04-14','gpt-4.1')])
def test_owner_model_setting_updates_description(monkeypatch,model,slug):
    monkeypatch.setenv('HORARY_AI_MODEL',model)
    with TestClient(app) as c:
        assert c.get('/api/status').json()['model']==model
        page=c.get('/technical')
        assert page.status_code==200
        assert model in page.text
        assert f'https://developers.openai.com/api/docs/models/{slug}"' in page.text
        simple=c.get('/about')
        assert simple.status_code==200
        assert f'https://developers.openai.com/api/docs/models/{slug}"' in simple.text
        assert '/technical' in simple.text and '/about' in page.text

def test_unknown_model_disables_requests(monkeypatch):
    monkeypatch.setenv('HORARY_AI_MODEL','unapproved-model')
    with TestClient(app) as c:
        assert c.get('/api/status').json()['ready'] is False
        c.get('/')
        r=c.post('/api/readings',json={'question':'Как посмотреть на мою работу?','city_id':'5128581','topic':'career','consent':True,'model':'gpt-4.1-mini-2025-04-14'})
        assert r.status_code==503

def test_home_cookie_security_and_demo():
    with TestClient(app) as c:
        r=c.get('/')
        assert r.status_code==200 and 'HttpOnly' in r.headers['set-cookie']
        assert 'frame-ancestors' in r.headers['content-security-policy']
        demo=c.get('/api/demo').json()
        assert demo['id']=='demo' and len(demo['data']['planets'])==7

def test_cities_russian_lookup():
    with TestClient(app) as c:
        rows=c.get('/api/cities?q=москва').json()
        assert rows[0]['name']=='Moscow'
        assert c.get('/api/cities?q=a').json()==[]

def test_cross_origin_write_blocked():
    with TestClient(app) as c:
        assert c.post('/api/readings',headers={'Origin':'https://attacker.invalid'},json={}).status_code==403

def test_no_session_cannot_submit():
    with TestClient(app) as c:
        r=c.post('/api/readings',json={'question':'Получу ли я новую работу?','city_id':'5128581','topic':'career','consent':True})
        assert r.status_code==401
