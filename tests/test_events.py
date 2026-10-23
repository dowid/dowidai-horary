from datetime import datetime,timezone,timedelta
import xml.etree.ElementTree as ET
import pytest
from events import timeline,position,delta,crossing
import swisseph as swe

@pytest.fixture(scope='module')
def result():return timeline('2026-10-23T17:44:50+00:00')

def jd(iso):
    t=datetime.fromisoformat(iso)
    return swe.julday(t.year,t.month,t.day,t.hour+t.minute/60+(t.second+t.microsecond/1e6)/3600)

def test_all_events_are_actual_ephemeris_crossings(result):
    at=jd('2026-10-23T17:44:50+00:00')
    for key in ('past','future'):
        rows=result[key]
        assert len(rows)==38
        assert rows==sorted(rows,key=lambda e:e['time'])
        slots=set()
        for e in rows:
            t=jd(e['time']);p=e['planet'];pos=position(t,p)
            assert (t<at) == (key=='past')
            assert abs(e['days']-(t-at))<.00001
            slot=(e['kind'],p,e.get('other',e.get('motion')))
            assert slot not in slots;slots.add(slot)
            if e['kind']=='aspect':
                assert abs(abs(delta(pos[0],position(t,e['other'])[0]))-e['angle'])<.0001
            elif e['kind']=='station':
                before,after=position(t-1/1440,p)[3],position(t+1/1440,p)[3]
                assert before*after<0
                assert (after<0)==(e['motion']=='R')
            else:
                before=int(position(t-1/1440,p)[0]//30)
                after=int(position(t+1/1440,p)[0]//30)
                assert before!=after and after==e['sign']


def test_reference_events_and_time_zone(result):
    # Reference screenshot: Moon ingress Oct 23 22:53 GMT+3; Mercury R Oct 24 10:12 GMT+3.
    moon=next(e for e in result['future'] if e['kind']=='ingress' and e['planet']==1)
    mercury=next(e for e in result['future'] if e['kind']=='station' and e['planet']==2 and e['motion']=='R')
    for e,expected in ((moon,'2026-10-23T19:53:00+00:00'),(mercury,'2026-10-24T07:12:00+00:00')):
        assert abs((datetime.fromisoformat(e['time'])-datetime.fromisoformat(expected)).total_seconds())<90
    assert any(e['motion']=='D' for e in result['future'] if e['kind']=='station' and e['planet']==2)


def test_circular_discontinuities_do_not_create_false_roots():
    assert not crossing(179,-179)
    assert crossing(-.1,.1)


def test_event_export_contains_all_rows_and_fits(result):
    from engine import chart,wheel
    from chart_render import event_sheet,full_sheet
    data=chart(datetime(2026,10,23,17,44,50,tzinfo=timezone.utc),59.9386,30.3142,'career')
    data['events']=result
    svg,height,scale=event_sheet(data)
    root=ET.fromstring(svg)
    for node in root.iter():
        if node.tag.endswith('text'):assert float(node.attrib['y'])<height
    texts=list(root.itertext())
    for key in ('past','future'):
        for e in result[key]:assert e['label'] in texts
    full=ET.fromstring(full_sheet(wheel(data),svg,height))
    assert int(full.attrib['height'])==1200+height
    ET.fromstring(scale)
