"""Busca cada juego de tools/datos/xbox_pago.json en la tienda de Microsoft y guarda
tools/datos/etiquetas_xbox_pago.json: {ids, series, x360, online_sugeridos, sin_encontrar}.
Las correcciones a mano van en tools/datos/reglas_xbox_pago.json {"ids": {nombre: id|null}, "series": [], "no_series": [], "x360": [], "xog": [], "online": []}."""
import json, os, re, sys, urllib.parse
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from actualizar_gamepass import get_json, limpiar, ONLINE, LOCAL
T = os.path.dirname(os.path.abspath(__file__)) + '/'
ED = r"\b(game of the year|goty|definitive|ultimate|premium|gold|deluxe|complete|enhanced|anniversary|edition|the|xbox one|xbox series x\|s|xbox series x s|series x s|cross gen|cross-gen|bundle)\b"
ROM = {'ii': '2', 'iii': '3', 'iv': '4', 'vi': '6', 'vii': '7', 'viii': '8'}
def key(n):
    n = n.lower().replace('™', '').replace('®', '').replace('’', "'").replace('&', ' and ')
    n = re.sub(r'\(.*?\)', ' ', n); n = re.sub(ED, ' ', n)
    return ''.join(ROM.get(t, t) for t in re.findall(r'[a-z0-9]+', n.replace("'", '')))
def buscar(q):
    u = ('https://displaycatalog.mp.microsoft.com/v7.0/productFamilies/autosuggest?market=US&languages=en-us&productFamilyNames=Games'
         '&platformdependencyname=Windows.Xbox&query=' + urllib.parse.quote(q))
    try: d = get_json(u)
    except Exception: return []
    return [(p['ProductId'], p['Title']) for r in d.get('Results', []) for p in r.get('Products', [])]
def uno(n):
    base = re.sub(r'\s*\((Xbox One|Xbox Series X\|S|Remake|2019|Disco)\)', '', n)
    for q in [base, re.sub(r'[:\-–+].*$', '', base).strip()]:
        c = buscar(q)
        for pid, t in c:
            if key(limpiar(t)) == key(base): return n, (pid, t)
    return n, None
juegos = json.load(open(T + 'datos/xbox_pago.json'))
reg = json.load(open(T + 'datos/reglas_xbox_pago.json')) if os.path.exists(T + 'datos/reglas_xbox_pago.json') else {}
with ThreadPoolExecutor(6) as ex: hits = dict(ex.map(uno, juegos))
for n, pid in (reg.get('ids') or {}).items(): hits[n] = (pid, n) if pid else None
ids = {n: h[0] for n, h in hits.items() if h}
det = {}
L = sorted(set(ids.values()))
for i in range(0, len(L), 20):
    d = get_json('https://displaycatalog.mp.microsoft.com/v7.0/products?bigIds=' + ','.join(L[i:i + 20]) + '&market=US&languages=en-us')
    for p in d.get('Products', []):
        pr = p.get('Properties', {})
        det[p['ProductId']] = {'gen': pr.get('XboxConsoleGenCompatible') or [], 'attr': {a.get('Name') for a in (pr.get('Attributes') or [])}, 'pfn': pr.get('PackageFamilyName') or ''}
series, x360, onl = [], [], []
for n in juegos:
    if '(Xbox Series X|S)' in n: series.append(n); continue
    if '(Xbox One)' in n: continue
    e = det.get(ids.get(n))
    if not e: continue
    if 'ConsoleGen9' in e['gen'] and 'ConsoleGen8' not in e['gen']: series.append(n)
    if 'Xbox360BackwardCompat' in e['pfn']: x360.append(n)
    if e['attr'] & ONLINE and 'SinglePlayer' not in e['attr'] and not (e['attr'] & LOCAL): onl.append(n)
series = sorted((set(series) | set(reg.get('series', []))) - set(reg.get('no_series', [])))
out = {'ids': ids, 'series': series, 'x360': sorted(set(x360) | set(reg.get('x360', [])) - set(reg.get('xog', []))), 'xog': sorted(reg.get('xog', [])),
       'online': sorted(reg.get('online', [])), 'online_sugeridos': sorted(onl), 'sin_encontrar': [n for n in juegos if n not in ids],
       'titulos': {n: hits[n][1] for n in ids}}
json.dump(out, open(T + 'datos/etiquetas_xbox_pago.json', 'w'), ensure_ascii=False, indent=1)
print('encontrados', len(ids), 'de', len(juegos), '| series', len(out['series']), '| 360', len(out['x360']), '| online?', len(onl))
