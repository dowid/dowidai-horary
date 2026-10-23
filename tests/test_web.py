from fastapi.testclient import TestClient
from app import app

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
