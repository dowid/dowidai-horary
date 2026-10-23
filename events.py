"""Nearest astronomical events around a chart, independent of AI interpretation."""
from datetime import datetime, timezone, timedelta
from functools import lru_cache
import swisseph as swe

FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED
NAMES = ['Солнце','Луна','Меркурий','Венера','Марс','Юпитер','Сатурн']
SIGNS = ['Овен','Телец','Близнецы','Рак','Лев','Дева','Весы','Скорпион','Стрелец','Козерог','Водолей','Рыбы']
ASPECTS = {0:'Соединение',60:'Секстиль',90:'Квадрат',120:'Трин',180:'Оппозиция'}
TARGETS = (0,60,90,120,180,240,270,300)
HORIZON = 1096

def delta(a,b): return (a-b+180)%360-180
def position(jd,p): return swe.calc_ut(jd,p,FLAGS)[0]

def root(fn,a,b):
    a,b=sorted((a,b)); fa=fn(a)
    for _ in range(32):
        m=(a+b)/2;fm=fn(m)
        if b-a < 0.25/86400: return m
        if fa*fm <= 0: b=m
        else: a,fa=m,fm
    return (a+b)/2

def crossing(a,b):
    return a*b<=0 and a!=b and abs(a-b)<180

@lru_cache(maxsize=64)
def timeline(iso):
    at=datetime.fromisoformat(iso).astimezone(timezone.utc)
    jd=swe.julday(at.year,at.month,at.day,at.hour+at.minute/60+at.second/3600)
    result={'past':[],'future':[], 'horizon_days':HORIZON,'timezone':'UTC',
            'selection':'Ближайший переход знака каждой из 7 планет и ближайшие развороты R и D, ближайший основной аспект каждой пары. Поиск до 3 лет в обе стороны; это не полный календарь всех событий.',
            'missing':{}}
    pairs=[(a,b) for a in range(7) for b in range(a+1,7)]
    for direction,key in ((-1,'past'),(1,'future')):
        found={}; start=jd; before=[position(start,p) for p in range(7)]
        def add(kind,p,t,**extra):
            if abs(t-jd)<0.5/86400: return
            pos=position(t,p)
            moment=at+timedelta(days=t-jd)
            event={'kind':kind,'planet':p,'time':moment.isoformat(),'longitude':pos[0],
                   'days':round(t-jd,5), **extra}
            slot=(kind,p,extra.get('other',extra.get('motion')))
            if slot not in found:found[slot]=event
        # Six-hour brackets, refined against the ephemeris to sub-second intervals.
        for step in range(1,HORIZON*4+1):
            end=jd+direction*step/4
            after=[position(end,p) for p in range(7)]
            for p in range(7):
                if ('ingress',p,None) not in found:
                    cuts=[start,end]
                    if before[p][3]*after[p][3]<0:
                        cuts.insert(1,root(lambda x:position(x,p)[3],start,end))
                    # Split at a turn: a planet may cross a sign boundary twice
                    # inside one bracket and finish in the same sign.
                    for left,right in zip(cuts,cuts[1:]):
                        a,b=position(left,p)[0],position(right,p)[0]
                        if int(a//30)!=int(b//30):
                            forward=delta(b,a)>0
                            boundary=((int(a//30)+1)*30 if forward else int(a//30)*30)%360
                            t=root(lambda x:delta(position(x,p)[0],boundary),left,right)
                            dest=int(position(t+1/86400,p)[0]//30)
                            add('ingress',p,t,sign=dest)
                if p>=2 and any(('station',p,m) not in found for m in ('R','D')) and before[p][3]*after[p][3]<=0:
                    t=root(lambda x:position(x,p)[3],start,end)
                    motion='R' if position(t+1/1440,p)[3]<0 else 'D'
                    add('station',p,t,motion=motion)
            for a,b in pairs:
                if ('aspect',a,b) in found:continue
                candidates=[]
                cuts=[start,end]
                if (before[a][3]-before[b][3])*(after[a][3]-after[b][3])<0:
                    cuts.insert(1,root(lambda x:position(x,a)[3]-position(x,b)[3],start,end))
                for left,right in zip(cuts,cuts[1:]):
                    da=position(left,a)[0]-position(left,b)[0]
                    db=position(right,a)[0]-position(right,b)[0]
                    for target in TARGETS:
                        if crossing(delta(da,target),delta(db,target)):
                            t=root(lambda x:delta(position(x,a)[0]-position(x,b)[0],target),left,right)
                            candidates.append((abs(t-jd),t,min(target,360-target)))
                if candidates:
                    _,t,angle=min(candidates)
                    add('aspect',a,t,other=b,angle=angle)
            if len(found)==38:break
            start,before=end,after
        rows=sorted(found.values(),key=lambda x:x['time'])
        for e in rows:
            if e['kind']=='ingress':label=f"{NAMES[e['planet']]} → {SIGNS[e['sign']]}"
            elif e['kind']=='station':label=f"{NAMES[e['planet']]}: разворот {e['motion']}"
            else:label=f"{NAMES[e['planet']]} — {NAMES[e['other']]}: {ASPECTS[e['angle']].lower()}"
            e['label']=label
        result[key]=rows
        result['missing'][key]=38-len(rows)
    return result
