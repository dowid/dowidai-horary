import hashlib
import time
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
import app as web
import admin


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setenv('SESSION_SECRET','test-admin-signing-secret')
    monkeypatch.setenv('HORARY_ADMIN_PASSWORD_HASH',hashlib.sha256(b'correct-password').hexdigest())


def test_auth_required_before_any_database_read(credentials,monkeypatch):
    def forbidden():raise AssertionError('Anonymous user reached the database')
    monkeypatch.setattr(admin.storage,'connect',forbidden)
    with TestClient(web.app) as c:
        for token in ('','forged','123.nonce.fake'):
            c.cookies.set('horary_admin',token)
            assert c.get('/api/admin/stats').status_code==401
        page=c.get('/admin')
        assert page.headers['cache-control']=='no-store'
        assert page.headers['x-robots-tag']=='noindex, nofollow'


def test_login_cookie_forgery_expiry_rotation_logout(credentials,monkeypatch):
    monkeypatch.setattr(admin,'login_allowed',lambda r:None)
    monkeypatch.setenv('VERCEL','1')
    with TestClient(web.app,base_url='https://testserver') as c:
        assert c.post('/api/admin/login',json={'password':'wrong'}).status_code==401
        r=c.post('/api/admin/login',json={'password':'correct-password'})
        assert r.status_code==200
        cookie=r.headers['set-cookie']
        assert all(s in cookie for s in ('HttpOnly','Secure','SameSite=strict','Max-Age=28800'))
        token=c.cookies.get('horary_admin')
        request=Request({'type':'http','headers':[(b'cookie',('horary_admin='+token).encode())]})
        admin.require_admin(request)
        now=time.time()
        with monkeypatch.context() as m:
            m.setattr(admin.time,'time',lambda:now+admin.TTL+1)
            with pytest.raises(web.HTTPException):admin.require_admin(request)
        with monkeypatch.context() as m:
            m.setenv('HORARY_ADMIN_PASSWORD_HASH',hashlib.sha256(b'changed').hexdigest())
            with pytest.raises(web.HTTPException):admin.require_admin(request)
        r=c.post('/api/admin/logout')
        assert 'Max-Age=0' in r.headers['set-cookie']
        assert c.get('/api/admin/stats').status_code==401
        assert c.post('/api/admin/login',json={'password':'correct-password'},headers={'Origin':'https://attacker.example'}).status_code==403


def test_admin_fail_closed_when_unconfigured(monkeypatch):
    monkeypatch.delenv('HORARY_ADMIN_PASSWORD_HASH',raising=False)
    with TestClient(web.app) as c:
        assert c.get('/api/admin/stats').status_code==503
