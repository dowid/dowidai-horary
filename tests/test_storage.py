"""Run with HORARY_DB_TESTS=1 and DATABASE_URL. Uses an isolated temporary schema."""
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
import pytest
import psycopg
from psycopg.rows import dict_row
import storage

pytestmark=pytest.mark.skipif(os.getenv('HORARY_DB_TESTS')!='1',reason='Requires dedicated database integration-test opt-in')

@pytest.fixture
def db_schema(monkeypatch):
    schema='test_'+secrets.token_hex(8)
    url=os.environ.get('HORARY_DATABASE_URL') or os.environ['DATABASE_URL']
    with psycopg.connect(url) as db:db.execute(f'CREATE SCHEMA {schema}')
    def connect():
        conn=psycopg.connect(url,row_factory=dict_row,connect_timeout=10)
        conn.execute(f'SET LOCAL search_path TO {schema}')
        return conn
    monkeypatch.setattr(storage,'connect',connect)
    storage.migrate()
    yield connect
    with psycopg.connect(url) as db:db.execute(f'DROP SCHEMA {schema} CASCADE')

def test_parallel_limit_and_monthly_ceiling(db_schema):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:storage.reserve('owner','ip','question'),range(4)))
    assert results.count(None)==1 and results.count('rate')==3
    with db_schema() as db:
        assert db.execute('SELECT reservations FROM quota').fetchone()['reservations']==1
        db.execute('UPDATE quota SET reservations=380')
    assert storage.reserve('new-owner','new-ip','new-question')=='budget'
    with db_schema() as db:
        assert db.execute('SELECT reservations FROM quota').fetchone()['reservations']==380

def test_parallel_daily_limit_counts_repeated_questions(db_schema):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda i:storage.reserve('owner',f'ip-{i}','same-question'),range(12)))
    assert results.count(None)==10 and results.count('daily')==2
    with db_schema() as db:
        assert db.execute('SELECT reservations FROM quota').fetchone()['reservations']==10
        db.execute("UPDATE throttle SET touched=now()-interval '25 hours' WHERE key='o:owner'")
    assert storage.reserve('owner','new-ip','same-question') is None
    assert storage.reserve('owner','another-ip','same-question')=='daily'

def test_legacy_attempt_counts_and_minute_limit_preserved(db_schema):
    with db_schema() as db:
        db.execute("INSERT INTO throttle(key) VALUES ('o:owner')")
    assert storage.reserve('owner','ip','question') is None
    assert storage.reserve('owner','ip','different-question')=='rate'
    for i in range(8):
        assert storage.reserve('owner',f'other-{i}','question') is None
    assert storage.reserve('owner','last-ip','question')=='daily'
    with db_schema() as db:
        assert db.execute('SELECT reservations FROM quota').fetchone()['reservations']==9

@pytest.mark.parametrize('model', ['gpt-4.1-mini-2025-04-14', 'gpt-4.1-2025-04-14'])
def test_archive_privacy_sharing_deletion_with_stubbed_ai(db_schema,monkeypatch,model):
    import app as web
    from fastapi.testclient import TestClient
    monkeypatch.setenv('AI_PAUSED','0')
    monkeypatch.setenv('OPENAI_API_KEY','test-only-not-a-real-key')
    monkeypatch.setenv('SESSION_SECRET','test-only-secret')
    monkeypatch.setenv('HORARY_AI_MODEL',model)
    class Reply:
        def raise_for_status(self):pass
        def json(self):
            import json
            answer={'status':'ok','summary':'Тестовый текст, не реальный ответ ИИ.','factors':[{'text':'Тестовая ссылка на факт.','fact_id':'p0','rule_id':'H005'}],'reflection':'Какие факты вам известны?'}
            return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(answer)}}],'usage':{}}
    class FakeClient:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,*args,**kwargs):
            assert kwargs['json']['model']==model
            return Reply()
    with TestClient(web.app,base_url='https://testserver') as a, TestClient(web.app,base_url='https://testserver') as b:
        monkeypatch.setattr(web.httpx,'Client',FakeClient)
        a.get('/'); b.get('/')
        r=a.post('/api/readings',json={'question':'Как посмотреть на перспективу моей новой работы?','topic':'career','city_id':'5128581','consent':True})
        assert r.status_code==200
        assert r.json()['data']['model']==model
        rid=r.json()['id']
        assert len(a.get('/api/archive').json())==1
        assert b.get('/api/readings/'+rid).status_code==404
        token=a.post('/api/readings/'+rid+'/share').json()['token']
        assert b.post('/api/shared',json={'token':token}).status_code==200
        a.delete('/api/readings/'+rid+'/share')
        assert b.post('/api/shared',json={'token':token}).status_code==404
        a.delete('/api/readings/'+rid)
        assert a.get('/api/readings/'+rid).status_code==404


def test_voice_separate_limits_shared_budget(db_schema):
    assert storage.reserve('owner','ip','',purpose='voice') is None
    assert storage.reserve('owner','ip','question') is None
    assert storage.reserve('owner','ip','',purpose='voice')=='rate'
    for i in range(9):
        assert storage.reserve('owner',f'voice-{i}','',purpose='voice') is None
    assert storage.reserve('owner','last','',purpose='voice')=='daily'
    with db_schema() as db:
        assert db.execute('SELECT reservations FROM quota').fetchone()['reservations']==11
        db.execute('UPDATE quota SET reservations=380')
    assert storage.reserve('other','other','',purpose='voice')=='budget'
