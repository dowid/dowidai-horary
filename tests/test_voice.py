import io
import wave
import pytest
from fastapi.testclient import TestClient
import app as web


def audio(seconds=1):
    out=io.BytesIO()
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"\0\0" * int(seconds*16000))
    return out.getvalue()

@pytest.mark.parametrize('data',[b'bad',audio(31),audio()[:100],audio().replace(b'WAVE',b'FAKE')],ids=['bad','too-long','truncated','wrong-header'])
def test_invalid_audio(data):
    with pytest.raises(web.HTTPException):web.validate_audio(data)

@pytest.mark.parametrize('seconds',[.1,1,30])
def test_valid_audio(seconds):web.validate_audio(audio(seconds))

def test_transcribe_validation_budget_and_provider(monkeypatch):
    monkeypatch.setattr(web,'status',lambda:{'ready':True})
    monkeypatch.setenv('SESSION_SECRET','test-secret')
    monkeypatch.setenv('OPENAI_API_KEY','test-secret')
    reservations=[]; calls=[]
    def reserve(*args,**kwargs):
        reservations.append(kwargs);return None
    monkeypatch.setattr(web.storage,'reserve',reserve)
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,*args,**kwargs):
            calls.append(kwargs)
            class Reply:
                def raise_for_status(self):pass
                def json(self):return {'text':'Как посмотреть на мою работу?'}
            return Reply()
    monkeypatch.setattr(web.httpx,'AsyncClient',Client)
    headers={'Content-Type':'audio/wav','x-voice-consent':'true'}
    with TestClient(web.app) as c:
        assert c.post('/api/transcribe',content=audio(),headers=headers).status_code==401
        c.get('/')
        assert c.post('/api/transcribe',content=audio()).status_code==422
        assert c.post('/api/transcribe',content=b'bad',headers=headers).status_code==422
        assert c.post('/api/transcribe',content=audio(31),headers=headers).status_code==413
        assert c.post('/api/transcribe',content=audio(),headers={**headers,'Origin':'https://other.invalid'}).status_code==403
        assert not calls and not reservations
        r=c.post('/api/transcribe',content=audio(),headers=headers)
        assert r.status_code==200 and r.json()['text'].startswith('Как')
        assert reservations==[{'purpose':'voice'}]
        assert calls[0]['files']['file'][1]==audio()
        for reason in ('daily','rate','budget'):
            monkeypatch.setattr(web.storage,'reserve',lambda *a,**kw:reason)
            assert c.post('/api/transcribe',content=audio(),headers=headers).status_code==429
        assert len(calls)==1
