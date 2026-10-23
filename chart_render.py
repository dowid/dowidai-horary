"""Standalone chart sheet; all positions come from the stored calculation."""
import math
from html import escape
from datetime import datetime, timezone

GLYPHS = ['☉', '☽', '☿', '♀', '♂', '♃', '♄']
SIGNS = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓']
COLORS = ['#bc403d', '#398052', '#8570b8', '#367eb0'] * 3

def zodiac(longitude):
    # Round once in total arcminutes so 29°59.9′ rolls into the next sign.
    minutes = round((longitude % 360) * 60) % 21600
    sign, rest = divmod(minutes, 1800)
    degree, minute = divmod(rest, 60)
    return sign, f'{degree:02d}°', f'{minute:02d}′'

def label_angles(planets):
    """Unwrap at the largest empty arc, then separate labels (not actual positions)."""
    ordered = sorted((p['longitude'] % 360, i) for i,p in enumerate(planets))
    if not ordered: return {}
    cut = max(range(len(ordered)), key=lambda i:(ordered[(i+1)%len(ordered)][0]-ordered[i][0])%360)
    ordered = ordered[cut+1:]+ordered[:cut+1]
    result, previous = {}, None
    for angle,i in ordered:
        if previous is not None:
            while angle < previous-180: angle += 360
            angle = max(angle,previous+20)
        result[i]=angle%360
        previous=angle
    return result

def wheel(data, city=''):
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1200" viewBox="0 0 1000 1200" role="img" aria-label="Хорарная карта с домами и таблицами положений">',
         '<rect width="1000" height="1200" fill="white"/>',
         '<g font-family="Arial, DejaVu Sans, sans-serif" fill="#24282b">']
    def text(x,y,value,size=16,color='#24282b',anchor='start'):
        svg.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{escape(str(value))}</text>')
    def point(deg,r):
        a=math.radians(180+deg-data['asc'])
        return 500+r*math.cos(a),470-r*math.sin(a)
    def line(a,b,color='#a7aaac',width=1):
        svg.append(f'<path d="M{a[0]:.2f},{a[1]:.2f} L{b[0]:.2f},{b[1]:.2f}" fill="none" stroke="{color}" stroke-width="{width}"/>')
    def circle(r,fill='none',stroke='#9ca0a3'):
        svg.append(f'<circle cx="500" cy="470" r="{r}" fill="{fill}" stroke="{stroke}"/>')
    text(40,38,'ХОРАР · КАРТА МОМЕНТА',22)
    at=datetime.fromisoformat(data['time']).astimezone(timezone.utc)
    text(40,65,at.strftime('%d.%m.%Y · %H:%M:%S UTC'),16)
    text(960,38,str(city)[:65],16,anchor='end')
    if 'latitude' in data and 'longitude' in data:
        text(960,65,f"{data['latitude']:.5f}°, {data['longitude']:.5f}°",14,anchor='end')
    circle(360);circle(120,'#f1f2f2');circle(88,'#f1f2f2')
    for i,cusp in enumerate(data['houses']):
        line(point(cusp,88),point(cusp,360),width=1.8 if i%3==0 else .8)
        middle=cusp+(data['houses'][(i+1)%12]-cusp)%360/2
        x,y=point(middle,104);text(x,y+5,i+1,16,'#707477','middle')
        sign,degree,minute=zodiac(cusp)
        x,y=point(cusp,391)
        text(x,y-13,degree,16,'#555b60','middle')
        text(x,y+9,SIGNS[sign],24,COLORS[sign],'middle')
        text(x,y+28,minute,13,'#555b60','middle')
    for i,label in ((0,'ASC'),(3,'IC'),(6,'DSC'),(9,'MC')):
        x,y=point(data['houses'][i],150);text(x,y+4,label,13,'#555b60','middle')
    text(500,468,'Regiomontanus',13,'#62676a','middle')
    text(500,489,'7 планет',12,'#7c8185','middle')
    angles=label_angles(data['planets'])
    for i,p in enumerate(data['planets']):
        actual=point(p['longitude'],355)
        x,y=point(angles[i],275)
        line(actual,point(angles[i],310),'#bdc2c6',.8)
        svg.append(f'<circle cx="{actual[0]:.2f}" cy="{actual[1]:.2f}" r="2.8" fill="#343b40"/>')
        svg.append(f'<g data-planet="{escape(p["id"])}"><title>{escape(p["name"])}</title>')
        # White backing keeps degree labels readable where a house cusp passes.
        svg.append(f'<rect x="{x-29:.2f}" y="{y-39:.2f}" width="58" height="88" rx="4" fill="white"/>')
        sign,degree,minute=zodiac(p['longitude'])
        text(x,y-15,GLYPHS[i],31,anchor='middle')
        text(x,y+7,degree+' '+minute,16,anchor='middle')
        text(x,y+35,SIGNS[sign],25,COLORS[sign],'middle')
        if p['retrograde']:text(x+21,y-21,'R',13,'#bd403c')
        svg.append('</g>')
    text(40,907,'ПОЛОЖЕНИЯ ПЛАНЕТ',15)
    text(540,907,'КУСПИДЫ ДОМОВ',15)
    line((40,920),(960,920),'#b8bdbf')
    for i,p in enumerate(data['planets']):
        y=946+i*25;sign,degree,minute=zodiac(p['longitude'])
        text(40,y,GLYPHS[i],21);text(73,y,p['name'],15)
        text(190,y,degree+' '+SIGNS[sign]+' '+minute,17,COLORS[sign])
        text(320,y,f"Дом {p['house']}",14)
        text(405,y,'R' if p['retrograde'] else 'D',14,'#bd403c' if p['retrograde'] else '#555b60')
    for i,cusp in enumerate(data['houses']):
        x=540+(i//6)*220;y=946+(i%6)*25;sign,degree,minute=zodiac(cusp)
        text(x,y,f'{i+1:02d}',14,'#62676a');text(x+40,y,degree+' '+SIGNS[sign]+' '+minute,17,COLORS[sign])
    text(40,1140,'R — ретроградное движение · D — прямое. Точки у края круга — точные положения.',13,'#62676a')
    text(40,1163,'Swiss Ephemeris · '+data.get('method','Regiomontanus'),12,'#62676a')
    text(40,1186,'dowidai-horary.vercel.app · Расчётная карта; достоверность предсказаний не установлена.',12,'#62676a')
    svg.append('</g></svg>')
    return ''.join(svg)
