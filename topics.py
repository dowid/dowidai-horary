"""Supported question scopes; house assignments are explicit, never an AI guess."""
TOPICS = {
    'relationships': (7, 'H002', 'партнёр в собственных отношениях'),
    'career': (10, 'H005', 'собственная работа и карьера'),
    'home': (4, 'H007', 'собственное жильё и обустройство дома; переезд только как тема жилья, без сравнения мест'),
    'study': (9, 'H008', 'собственное высшее или специализированное обучение'),
    'travel': (9, 'H009', 'собственная дальняя поездка или путешествие за границу'),
    'friendship': (11, 'H010', 'собственная дружба и поддержка друзей'),
}

def topic_rules(topic):
    house, rule, scope = TOPICS[topic]
    return f'{rule}: {scope} — управитель {house}-го дома. Это ограниченная символическая схема, не полный анализ темы.'

def allowed_rules(topic):
    return {'H001', TOPICS[topic][1], 'P003', 'P006'}
