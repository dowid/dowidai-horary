from datetime import datetime,timezone,timedelta
import xml.etree.ElementTree as ET
import pytest
from engine import chart,delta,wheel

def test_same_instant_same_chart():
    utc=datetime(2026,10,23,12,tzinfo=timezone.utc)
    assert chart(utc,40.71,-74.01,'career')==chart(utc.astimezone(timezone(timedelta(hours=-4))),40.71,-74.01,'career')

def test_chart_geometry_and_house_membership():
    c=chart(datetime(2000,1,1,12,tzinfo=timezone.utc),51.5,0,'relationships')
    assert len(c['planets'])==7 and len(c['houses'])==12
    # J2000 Sun near 280° ecliptic longitude; independent broad astronomical sanity check.
    assert 279<c['planets'][0]['longitude']<281
    for p in c['planets']:
        h=p['house']-1
        assert (p['longitude']-c['houses'][h])%360 < (c['houses'][(h+1)%12]-c['houses'][h])%360
    assert ET.fromstring(wheel(c)).tag.endswith('svg')

def test_polar_latitude_is_explicitly_unsupported():
    with pytest.raises(ValueError):chart(datetime.now(timezone.utc),78,15,'career')

def test_wraparound():
    assert delta(359,1)==-2
    assert abs(delta(0,180))==180


def test_chart_sheet_metadata_and_escaping():
    c=chart(datetime(2026,10,23,17,44,50,tzinfo=timezone.utc),59.9386,30.3142,'relationships')
    root=ET.fromstring(wheel(c,'<script>test</script>'))
    assert root.attrib['viewBox']=='0 0 1000 1200'
    assert root.attrib['width']=='1000' and root.attrib['height']=='1200'
    assert not any(e.tag.endswith('script') for e in root.iter())
    content=' '.join(root.itertext())
    assert '17:44:50 UTC' in content and '59.93860' in content
    assert all(p['name'] in content for p in c['planets'])
    assert all(axis in content for axis in ('ASC','MC','DSC','IC'))
    assert len([e for e in root.iter() if 'data-planet' in e.attrib])==7
    # Archived reports predate coordinate persistence and still render.
    del c['latitude'];del c['longitude']
    ET.fromstring(wheel(c,'Archive'))


def test_chart_label_wraparound_and_rounding():
    from chart_render import zodiac,label_angles
    assert zodiac(359.999)==(0,'00°','00′')
    planets=[{'longitude':v} for v in (358,359,0,1,2,3,4)]
    angles=list(label_angles(planets).values())
    assert len(set(angles))==7
    assert all(abs(delta(a,b))>=19.99 for i,a in enumerate(angles) for b in angles[i+1:])
