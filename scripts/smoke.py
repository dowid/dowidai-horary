"""One live, synthetic end-to-end reading. Deletes the test report afterwards."""
from dotenv import load_dotenv
load_dotenv('.env.vercel.local')
load_dotenv('.env.local',override=True)
from fastapi.testclient import TestClient
from app import app

with TestClient(app,base_url='https://testserver') as a, TestClient(app,base_url='https://testserver') as b:
    a.get('/');b.get('/')
    r=a.post('/api/readings',json={'question':'Как посмотреть на перспективу моей новой работы после собеседования?','topic':'career','city_id':'5128581','consent':True})
    print('Live reading:',r.status_code)
    if r.status_code!=200:
        print(r.json())
        raise SystemExit(1)
    report=r.json();rid=report['id']
    try:
        assert a.get('/api/archive').json()[0]['id']==rid
        assert b.get('/api/readings/'+rid).status_code==404
        token=a.post('/api/readings/'+rid+'/share').json()['token']
        assert b.post('/api/shared',json={'token':token}).status_code==200
        assert a.delete('/api/readings/'+rid+'/share').status_code==200
        assert b.post('/api/shared',json={'token':token}).status_code==404
        assert a.post('/api/readings/'+rid+'/feedback',json={'value':1}).status_code==200
        print('Archive, isolation, sharing, revocation, feedback: passed')
        print('AI summary:',report['data']['answer']['summary'])
        print('Token usage:',report['data']['usage'])
    finally:
        assert a.delete('/api/readings/'+rid).status_code==200
        assert a.get('/api/readings/'+rid).status_code==404
        print('Test report deleted.')
