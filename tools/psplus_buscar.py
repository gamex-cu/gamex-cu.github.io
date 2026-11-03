"""Busca los juegos mensuales de PlayStation Plus Essential en el blog oficial de PlayStation y los deja como propuesta
en tools/salida/psplus_propuesta.json (la acción de GitHub la sube a la rama psplus-pendiente; el panel la muestra
y el dueño la revisa antes de guardarla). Nombres e ids de la tienda: buscar_playstation.catalogo()."""
import datetime, html, json, os, re, sys, urllib.request
import xml.etree.ElementTree as ET

T = os.path.dirname(os.path.abspath(__file__)) + '/'
FEEDS = ['https://blog.playstation.com/category/ps-plus/feed/', 'https://blog.playstation.com/feed/']
MESES_EN = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
MESES_ES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
RX = re.compile(r'PlayStation Plus (?:Monthly|Essential)? ?Games for (\w+)(?:\s+\d{4})?\s*[:\-–—]\s*(.+)$', re.I)


def bajar(u):
    r = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (GameX)'})
    return urllib.request.urlopen(r, timeout=40).read()


def primer_martes(y, m):
    d = datetime.date(y, m, 1)
    return d + datetime.timedelta(days=(1 - d.weekday()) % 7)


def juegos_de(titulo):
    t = re.sub(r'\s*\((?:PS4|PS5|PS VR2)[^)]*\)', '', titulo)
    partes = re.split(r',\s*(?:and\s+)?|\s+and\s+|\s*&\s+(?=[A-Z])', t)
    return [p.strip(' .') for p in partes if p.strip(' .')]


def main():
    post = None
    for f in FEEDS:
        try: raiz = ET.fromstring(bajar(f))
        except Exception as e: print('feed', f, e); continue
        for it in raiz.iter('item'):
            tit = html.unescape(it.findtext('title') or '').strip()
            m = RX.search(tit)
            if m and m.group(1).lower() in MESES_EN:
                post = (tit, m.group(1).lower(), m.group(2), it.findtext('link') or '', it.findtext('pubDate') or ''); break
        if post: break
    sal = {'fecha': datetime.date.today().isoformat()}
    if not post:
        sal['error'] = 'No encontré el anuncio de los juegos del mes en el blog de PlayStation.'
    else:
        tit, mes_en, lista, link, pub = post
        mi = MESES_EN.index(mes_en) + 1
        try: py = datetime.datetime.strptime(pub[5:16], '%d %b %Y'); anio = py.year + (1 if mi < py.month else 0)
        except Exception: anio = datetime.date.today().year
        sig = (anio + (mi == 12), mi % 12 + 1)
        hasta = primer_martes(*sig) - datetime.timedelta(days=1)
        sys.path.insert(0, T)
        import buscar_playstation as bp
        cat = [p for p in bp.catalogo() if p.get('cls') in ('FULL_GAME', 'Full Game')]
        for p in cat: p['nn'] = bp.norm(p['n']); p['nums'] = bp.numeros(p['n'])
        js = []
        for nombre in juegos_de(lista):
            hit, r = bp.elegir(nombre, [p for p in cat if 'PS5' in (p.get('pl') or [])])
            if not hit or r < 0.8:
                hit, r = bp.elegir(nombre, cat)
            g = {'n': nombre, 'p': 'PS5'}
            if hit and r >= 0.8:
                pl = hit.get('pl') or []
                g['p'] = 'PS4 y PS5' if 'PS4' in pl and 'PS5' in pl else ('PS5' if 'PS5' in pl else 'PS4')
                g['id'] = hit['id']; g['tienda'] = hit['n']
            js.append(g)
        sal.update({'mes': f'{MESES_ES[mi - 1]} {anio}', 'hasta': hasta.isoformat(), 'post': tit, 'link': link, 'juegos': js})
    os.makedirs(T + 'salida', exist_ok=True)
    json.dump(sal, open(T + 'salida/psplus_propuesta.json', 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(sal, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
