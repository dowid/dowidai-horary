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
