import json
from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
import app as web
from engine import chart, RULERS
from topics import TOPICS
from topic_detection import detect_topic, combined_usage

@pytest.mark.parametrize('topic,house', [('relationships',7),('career',10),('home',4),('study',9),('travel',9),('friendship',11)])
def test_topic_uses_correct_house_and_preserves_astronomy(topic, house):
    at = datetime(2026,10,23,12,tzinfo=timezone.utc)
    data = chart(at,40.71,-74.01,topic)
    baseline = chart(at,40.71,-74.01,'career')
    assert data['planets'] == baseline['planets']
    assert data['houses'] == baseline['houses']
    assert data['significators']['subject'] == f"p{RULERS[int(data['houses'][house-1]//30)]}"

def test_unknown_topic_cannot_silently_become_career():
    with pytest.raises(ValueError):
        chart(datetime.now(timezone.utc),40.71,-74.01,'unknown')

@pytest.mark.parametrize('topic', list(TOPICS))
def test_topic_rules_reach_model_and_answer_can_be_saved(monkeypatch, topic):
    monkeypatch.setattr(web,'owner',lambda request:'test-owner')
    monkeypatch.setattr(web,'status',lambda:{'paused':False,'ready':True})
    monkeypatch.setattr(web,'cities',lambda:{'test':{'name':'Test','latitude':40.71,'longitude':-74.01}})
    monkeypatch.setattr(web.storage,'reserve',lambda *args:None)
    monkeypatch.setenv('SESSION_SECRET','test')
    monkeypatch.setenv('OPENAI_API_KEY','test-not-real')
    monkeypatch.setattr(web,'public_report',lambda row,lang:row)
    saved=[]
    monkeypatch.setattr(web.storage,'connect',lambda:nullcontext(SimpleNamespace(execute=lambda *args:saved.append(args))))
    def post(url,headers,json):
        if json['max_tokens']==300:
            return SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'choices':[{'finish_reason':'stop','message':{'content':__import__('json').dumps({'status':'ok','topic':topic})}}], 'usage':{'prompt_tokens':100,'completion_tokens':10,'total_tokens':110}})
        payload=__import__('json').loads(json['messages'][1]['content'])
        assert TOPICS[topic][1]+':' in payload['rules']
        for other,(_,rule,_) in TOPICS.items():
            if other!=topic: assert rule+':' not in payload['rules']
        answer={'status':'ok','summary':'Symbolic observation','reflection':'What matters to you?', 'factors':[{'fact_id':'p1','rule_id':TOPICS[topic][1],'text':'A symbolic factor'}]}
        return SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'choices':[{'finish_reason':'stop','message':{'content':__import__('json').dumps(answer)}}]})
    monkeypatch.setattr(web.httpx,'Client',lambda **kwargs:nullcontext(SimpleNamespace(post=post)))
    request=SimpleNamespace(headers={},client=SimpleNamespace(host='test'))
    result=web.reading(web.Question(question='A personal question for this topic',city_id='test',consent=True),request)
    assert saved and result['data']['topic_house']==TOPICS[topic][0]
    assert result['data']['rules_version']=='0.2'
    assert result['data']['usage']['total_tokens']==110

def test_all_topics_in_both_languages():
    with TestClient(web.app) as client:
        for lang in ('ru','en'):
            page=client.get('/'+lang).text
            for topic in TOPICS: assert f'data-topic="{topic}"' in page
            assert 'name="topic"' not in page

@pytest.mark.parametrize('decision', [
    {'status':'clarify','message':'What situation do you mean?'},
    {'status':'unsupported','message':'This subject is not supported yet.'},
])
def test_clarification_never_builds_chart_or_saves_report(monkeypatch, decision):
    monkeypatch.setattr(web,'owner',lambda request:'test-owner')
    monkeypatch.setattr(web,'status',lambda:{'paused':False,'ready':True})
    monkeypatch.setattr(web,'cities',lambda:{'test':{'name':'Test','latitude':40.71,'longitude':-74.01}})
    monkeypatch.setenv('SESSION_SECRET','test')
    monkeypatch.setenv('OPENAI_API_KEY','test-not-real')
    reservations=[]
    monkeypatch.setattr(web.storage,'reserve',lambda *args:reservations.append(args))
    monkeypatch.setattr(web,'detect_topic',lambda *args:(decision,{}))
    monkeypatch.setattr(web.httpx,'Client',lambda **kwargs:nullcontext(None))
    def forbidden(*args): raise AssertionError('No chart or database write expected')
    monkeypatch.setattr(web,'chart',forbidden)
    monkeypatch.setattr(web.storage,'connect',forbidden)
    result=web.reading(web.Question(question='Will everything work out?',city_id='test',consent=True),SimpleNamespace(headers={},client=SimpleNamespace(host='test')))
    assert result==decision and len(reservations)==1

@pytest.mark.parametrize('result', [{'status':'ok','topic':'invented'}, {'status':'clarify','message':''}, {'status':'other'}])
def test_classifier_rejects_invalid_output(result):
    response=SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'choices':[{'finish_reason':'stop','message':{'content':json.dumps(result)}}]})
    client=SimpleNamespace(post=lambda *args,**kwargs:response)
    with pytest.raises(ValueError): detect_topic(client,'test','test','Question text','en')

def test_usage_includes_both_calls_and_cached_tokens():
    assert combined_usage({'prompt_tokens':100,'completion_tokens':10,'total_tokens':110,'prompt_tokens_details':{'cached_tokens':20}}, {'prompt_tokens':200,'completion_tokens':50,'total_tokens':250}) == {'prompt_tokens':300,'completion_tokens':60,'total_tokens':360,'prompt_tokens_details':{'cached_tokens':20}}
