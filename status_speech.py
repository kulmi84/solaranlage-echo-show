"""Spoken status for the isolated test skill; uses validated relay readings."""

STATUS_METRICS = (
    ('power_w', 'Leistung inklusive Balkonkraftwerk', 'power'),
    ('home_w', 'Hausverbrauch', 'power'),
    ('battery_soc', 'Akkustand', 'percent'),
    ('today_pv_kwh', 'Heutige Produktion inklusive Balkonkraftwerk', 'energy'),
    ('grid_import_w', 'Netzbezug', 'power'),
    ('grid_export_w', 'Einspeisung', 'power'),
)


def spoken_status_age(age):
    if type(age) is not int or age < 0:
        return 'Das Alter der Werte ist nicht bekannt.'
    remaining = age
    parts = []
    for seconds, singular, plural in ((86400, 'Tag', 'Tage'),
            (3600, 'Stunde', 'Stunden'), (60, 'Minute', 'Minuten'),
            (1, 'Sekunde', 'Sekunden')):
        count, remaining = divmod(remaining, seconds)
        if count:
            parts.append(str(count) + ' ' + (singular if count == 1 else plural))
    duration = ' und '.join(parts) if parts else '0 Sekunden'
    return 'Die Werte sind ' + duration + ' alt.'


def spoken_status(pv):
    metrics = pv.get('metrics', {})
    sentences = ['Achtung, die Daten sind veraltet. Zuletzt gemeldeter Status.'
                 if pv.get('stale', True) else 'Status der Solaranlage.']
    for key, label, kind in STATUS_METRICS:
        value = metrics.get(key)
        if value is None:
            sentences.append(label + ': keine Daten vorhanden.')
            continue
        if kind == 'energy':
            formatted = number(value, 'Kilowattstunden')
        elif kind == 'percent':
            formatted = number(value, 'Prozent', 0)
        elif value >= 1000:
            formatted = number(value / 1000, 'Kilowatt')
        else:
            formatted = number(value, 'Watt', 0)
        sentences.append(label + ': ' + formatted + '.')
    sentences.append(spoken_status_age(pv.get('ageSeconds')))
    return ' '.join(sentences)
