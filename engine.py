"""Deterministic chart facts. Interpretive conventions are intentionally limited."""
from datetime import datetime, timezone
import math
import swisseph as swe

NAMES = ['Солнце', 'Луна', 'Меркурий', 'Венера', 'Марс', 'Юпитер', 'Сатурн']
SIGNS = ['Овен', 'Телец', 'Близнецы', 'Рак', 'Лев', 'Дева', 'Весы', 'Скорпион', 'Стрелец', 'Козерог', 'Водолей', 'Рыбы']
RULERS = [4, 3, 2, 1, 0, 2, 3, 4, 5, 6, 6, 5]
FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED

def delta(a, b):
    return (a - b + 180) % 360 - 180

def chart(at: datetime, lat: float, lon: float, topic: str):
    at = at.astimezone(timezone.utc)
    jd = swe.julday(at.year, at.month, at.day, at.hour + at.minute / 60 + at.second / 3600)
    if abs(lat) >= 66:
        raise ValueError('Для первой версии выберите город южнее полярного круга: расчёт домов на этой широте пока не поддерживается.')
    cusps, angles = swe.houses(jd, lat, lon, b'R')
    # pysweph exposes the C array with unused index 0; pyswisseph did not.
    cusps = cusps[1:] if len(cusps) == 13 else cusps
    planets = []
    for i in range(7):
        pos = swe.calc_ut(jd, i, FLAGS)[0]
        longitude = pos[0]
        house = next((h + 1 for h in range(12) if (longitude - cusps[h]) % 360 < (cusps[(h + 1) % 12] - cusps[h]) % 360), 1)
        planets.append(dict(id=f'p{i}', name=NAMES[i], longitude=round(longitude, 5), sign=SIGNS[int(longitude // 30)], degree=round(longitude % 30, 2), speed=round(pos[3], 6), retrograde=pos[3] < 0, house=house))
    aspects = []
    # Fixed 6° display orb is a documented MVP convention, not a Lilly table.
    for a in range(7):
        for b in range(a + 1, 7):
            separation = abs(delta(planets[a]['longitude'], planets[b]['longitude']))
            future_a = swe.calc_ut(jd + 1/24, a, FLAGS)[0][0]
            future_b = swe.calc_ut(jd + 1/24, b, FLAGS)[0][0]
            for angle, name in [(0, 'Соединение'), (60, 'Секстиль'), (90, 'Квадрат'), (120, 'Трин'), (180, 'Оппозиция')]:
                error = abs(separation - angle)
                if error <= 6:
                    aspects.append(dict(id=f'a{a}{b}', a=f'p{a}', b=f'p{b}', name=name, angle=angle, orb=round(error, 2), applying=abs(abs(delta(future_a, future_b))-angle) < error))
    asc_degree = angles[0] % 30
    warnings = []
    if asc_degree < 3 or asc_degree >= 27:
        warnings.append('Асцендент близок к границе знака. В выбранной традиции это повод осторожнее относиться к трактовке, а не автоматический запрет.')
    if planets[6]['house'] == 7:
        warnings.append('Сатурн в седьмом доме. Значение зависит от темы вопроса; автоматический отрицательный вывод не делается.')
    significators = {'querent': f'p{RULERS[int(cusps[0] // 30)]}', 'subject': f'p{RULERS[int(cusps[6 if topic == "relationships" else 9] // 30)]}'}
    if significators['querent'] == significators['subject']:
        warnings.append('Один управитель представляет обе стороны. Эта неоднозначность ограничивает автоматическую трактовку.')
    return dict(time=at.isoformat(), planets=planets, houses=[round(x, 5) for x in cusps], asc=round(angles[0], 5), aspects=aspects, significators=significators, warnings=warnings, method='Regiomontanus · 7 планет · Moshier · v0.1', limitations=['Орбис отображения 6° — упрощение MVP.', 'Рецепции, достоинства, передача света и Луна без курса пока не оцениваются.', 'Сходящийся аспект означает уменьшение расстояния до точного аспекта сейчас, а не доказанное достижение аспекта в будущем.'])

def wheel(data):
    def point(deg, r):
        rad = math.radians(180 - (deg - data['asc']))
        return 220 + r * math.cos(rad), 220 - r * math.sin(rad)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 440" role="img" aria-label="Карта положений планет">', '<circle cx="220" cy="220" r="209" fill="#fbf8f1" stroke="#b9b7a7"/>', '<circle cx="220" cy="220" r="171" fill="none" stroke="#b9b7a7"/>', '<circle cx="220" cy="220" r="128" fill="none" stroke="#ddd9cd"/>']
    for i in range(12):
        x,y = point(i*30,209); x2,y2=point(i*30,171)
        svg.append(f'<path d="M{x},{y} L{x2},{y2}" stroke="#b9b7a7"/>')
        x,y=point(i*30+15,190)
        svg.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" font-size="19" fill="#656d5c">{chr(9800+i)}</text>')
        x,y=point(data['houses'][i],171); x2,y2=point(data['houses'][i],128)
        svg.append(f'<path d="M{x},{y} L{x2},{y2}" stroke="#c5c4b8"/>')
    for a in data['aspects']:
        p=data['planets'][int(a['a'][1:])]; q=data['planets'][int(a['b'][1:])]
        x,y=point(p['longitude'],122); u,v=point(q['longitude'],122)
        color='#bd8570' if a['angle'] in (90,180) else '#7c9987'
        svg.append(f'<path d="M{x},{y} L{u},{v}" stroke="{color}" opacity=".5"/>')
    for i,p in enumerate(data['planets']):
        # Alternate radial lanes to reduce label collisions.
        x,y=point(p['longitude'],138+(i%3)*10)
        svg.append(f'<circle cx="{x}" cy="{y}" r="12" fill="#fbf8f1"/><text x="{x}" y="{y+5}" text-anchor="middle" font-size="16" fill="#274d45">{["☉","☽","☿","♀","♂","♃","♄"][i]}</text>')
    svg.append('</svg>')
    return ''.join(svg)
