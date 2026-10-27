"""Busca la página oficial de cada juego de PS4/PS5 en la PlayStation Store.

Uso:  python3 tools/buscar_playstation.py            -> PS4 y PS5
      python3 tools/buscar_playstation.py PS5        -> solo una consola
      añade --probar para ver los resultados sin guardar

Baja el catálogo completo de la tienda (todas las páginas de "Juegos de PS4" y "Juegos de PS5")
y compara cada juego de tu lista con esos nombres.
Guarda tools/datos/enlaces_<consola>.json {nombre: id_producto} y
tools/salida/sin_enlace_<consola>.txt (dudosos y no encontrados, para revisar).
Las correcciones a mano van en tools/datos/enlaces_manuales.json {"PS4|Nombre": "id_producto"}.
Necesita acceso a web.np.playstation.com.
"""
import json, os, re, ssl, sys, unicodedata, urllib.parse, urllib.request, difflib

T = os.path.dirname(os.path.abspath(__file__)) + '/'
CATS = {'PS5': '4cbf39e2-5749-4970-ba81-93a489e4570c', 'PS4': '44d8bb20-653e-431e-8ad0-c0a365f68d2f'}
HASH = '4ce7d410a4db2c8b635a48c1dcec375906ff63b19dadd87e073f8fd0c0481d35'

def abrir():
    hs = []
    pr = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if pr: hs.append(urllib.request.ProxyHandler({'https': pr}))
    ca = '/root/.ccr/ca-bundle.crt'
    hs.append(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca) if os.path.exists(ca) else ssl.create_default_context()))
    return urllib.request.build_opener(*hs)
OP = abrir()

def pagina(cid, off, size=500):
    var = {"id": cid, "pageArgs": {"size": size, "offset": off}, "sortBy": {"name": "productReleaseDate", "isAscending": False}, "filterBy": [], "facetOptions": []}
    u = ('https://web.np.playstation.com/api/graphql/v1/op?operationName=categoryGridRetrieve&variables=' + urllib.parse.quote(json.dumps(var)) +
         '&extensions=' + urllib.parse.quote(json.dumps({"persistedQuery": {"version": 1, "sha256Hash": HASH}})))
    req = urllib.request.Request(u, headers={'x-psn-store-locale-override': 'en-US', 'content-type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    return json.load(OP.open(req, timeout=90))['data']['categoryGridRetrieve']

def catalogo():
    todo = []
    for c, cid in CATS.items():
        off = 0
        while True:
            g = pagina(cid, off)
            todo += [{'id': p['id'], 'n': p['name'], 'pl': p.get('platforms') or [c], 'cls': p.get('storeDisplayClassification') or ''} for p in g['products']]
            off += len(g['products'])
            if g['pageInfo']['isLast'] or not g['products']: break
    return todo

ROM = {'ii': '2', 'iii': '3', 'iv': '4', 'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9', 'xi': '11', 'xii': '12', 'xiii': '13', 'xiv': '14', 'xv': '15', 'xvi': '16'}
QUITAR = (r"\(?\bps4\W*(&|and|y)\W*ps5\b\)?|\bcross[- ]gen( bundle| edition)?\b|\bps[45]\b|[™®©]|\b(standard|digital|deluxe|complete|ultimate|definitive|gold|premium|"
          r"collector'?s?|launch|vault|cross-?buy|game of the year|goty|director'?s cut|enhanced|bundle|edition|version|the|a|an|of|and)\b")
def norm(s):
    s = re.sub(r'[™®©]', '', s)
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower().replace('&', ' and ')
    s = re.sub(QUITAR, ' ', s)
    return ' '.join(ROM.get(t, t) for t in re.findall(r'[a-z0-9]+', s))
def numeros(s): return {t for t in norm(s).split() if t.isdigit()}

def elegir(nombre, cands):
    nn, nums = norm(nombre), numeros(nombre)
    exactos = [x for x in cands if x['nn'] == nn]
    if exactos:
        exactos.sort(key=lambda x: (x['cls'] != 'Full Game', len(x['n'])))
        return exactos[0], 1.0
    mejor, mr = None, 0
    for x in cands:
        if x['nums'] != nums: continue
        r = difflib.SequenceMatcher(None, nn, x['nn']).ratio()
        if r > mr or (r == mr and mejor and x['cls'] == 'Full Game' and mejor['cls'] != 'Full Game'): mejor, mr = x, r
    return mejor, mr

def buscar_viejo(nombre, consola):
    q = ' '.join(re.sub(r"[:–\-!?,.'’()]", ' ', nombre).split())[:80]
    u = f'https://store.playstation.com/store/api/chihiro/00_09_000/tumbler/US/en/999/{urllib.parse.quote(q)}?suggested_size=15&mode=game'
    try: d = json.load(OP.open(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30))
    except Exception: return None, 0
    cands = []
    for l in d.get('links', []):
        if l.get('top_category') not in ('downloadable_game', 'disc_based_game'): continue
        pl = list(l.get('playable_platform') or []) + (['PS4'] if 'PS4' in l.get('name', '') else [])
        if not any(consola in p for p in pl): continue
        cands.append({'id': l.get('id'), 'n': l.get('name', ''), 'cls': 'Full Game', 'nn': norm(l.get('name', '')), 'nums': numeros(l.get('name', ''))})
    return elegir(nombre, cands) if cands else (None, 0)

class _SinRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
def _opener_sin_redir():
    hs = [_SinRedir()]
    pr = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if pr: hs.append(urllib.request.ProxyHandler({'https': pr}))
    ca = '/root/.ccr/ca-bundle.crt'
    hs.append(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca) if os.path.exists(ca) else ssl.create_default_context()))
    return urllib.request.build_opener(*hs)
OP2 = _opener_sin_redir()
def abre(pid):
    try: return OP2.open(urllib.request.Request('https://store.playstation.com/es-mx/product/' + pid, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).status == 200
    except Exception: return False

def main():
    consolas = [a for a in sys.argv[1:] if a in CATS] or ['PS4', 'PS5']
    tienda = catalogo()
    for x in tienda: x['nn'], x['nums'] = norm(x['n']), numeros(x['n'])
    manual = {}
    if os.path.exists(T + 'datos/enlaces_manuales.json'): manual = json.load(open(T + 'datos/enlaces_manuales.json'))
    for c in consolas:
        juegos = json.load(open(T + f'datos/{c.lower()}.json'))
        cands = [x for x in tienda if c in x['pl']]
        ok, dudas, no = {}, [], []
        for n in juegos:
            if c + '|' + n in manual: ok[n] = manual[c + '|' + n]; continue
            x, r = elegir(n, cands)
            if not x or r < 0.9:
                x2, r2 = buscar_viejo(n, c)
                if x2 and r2 > r: x, r = x2, r2
            if x and r >= 0.9: ok[n] = x['id']
            elif x and r >= 0.7: dudas.append((n, x['n'], round(r, 2), x['id']))
            else: no.append(n)
        vivos = {x['id'] for x in tienda}
        from concurrent.futures import ThreadPoolExecutor
        dudar = [n for n, pid in ok.items() if pid not in vivos]
        with ThreadPoolExecutor(8) as ex: muertos = [n for n, v in zip(dudar, ex.map(lambda n: abre(ok[n]), dudar)) if not v]
        for n in muertos: del ok[n]; no.append(n + '   (la página ya no existe en la tienda)')
        print(c, 'tienda:', len(cands), '| con enlace:', len(ok), '| dudosos:', len(dudas), '| no encontrados:', len(no))
        if '--probar' in sys.argv: continue
        json.dump(dict(sorted(ok.items())), open(T + f'datos/enlaces_{c.lower()}.json', 'w'), ensure_ascii=False, indent=0)
        os.makedirs(T + 'salida', exist_ok=True)
        with open(T + f'salida/sin_enlace_{c.lower()}.txt', 'w') as f:
            f.write(f'== DUDOSOS ({len(dudas)}): nombre en tu lista  ->  lo más parecido en la tienda ==\n')
            f.writelines(f'{n}  ->  {nom}  ({r})\n' for n, nom, r, _ in dudas)
            f.write(f'\n== NO ENCONTRADOS EN LA TIENDA ({len(no)}) ==\n'); f.writelines(n + '\n' for n in no)
        json.dump({n: pid for n, _, _, pid in dudas}, open(T + f'salida/dudosos_{c.lower()}.json', 'w'), ensure_ascii=False, indent=0)

if __name__ == '__main__':
    main()
