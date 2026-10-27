"""Busca la página oficial de cada juego de PS4/PS5 en la PlayStation Store.
Uso: python3 tools/buscar_playstation.py PS4|PS5 [--solo-nuevos]
Guarda tools/datos/enlaces_<consola>.json  {nombre: id_producto}  y  tools/salida/sin_enlace_<consola>.txt
Necesita acceso a store.playstation.com."""
import json, os, re, ssl, sys, unicodedata, urllib.parse, urllib.request, difflib
from concurrent.futures import ThreadPoolExecutor
T = os.path.dirname(os.path.abspath(__file__)) + '/'
def abrir():
    hs = []
    pr = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if pr: hs.append(urllib.request.ProxyHandler({'https': pr}))
    ca = '/root/.ccr/ca-bundle.crt'
    hs.append(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca) if os.path.exists(ca) else ssl.create_default_context()))
    return urllib.request.build_opener(*hs)
OP = abrir()
STOP = r"\b(ps4 and ps5|the|a|of|edition|deluxe|complete|ultimate|definitive|remastered|remake|gold|premium|digital|game|the video ?game|ps4|ps5|director'?s cut|goty|game of the year|standard|bundle|collection|enhanced|anniversary)\b"
def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower().replace('&', ' and ')
    s = re.sub(r'[™®©]', '', s); s = re.sub(STOP, ' ', s)
    return ' '.join(re.findall(r'[a-z0-9]+', s))
ROM = {'i':'1','ii':'2','iii':'3','iv':'4','v':'5','vi':'6','vii':'7','viii':'8','ix':'9','x':'10','xi':'11','xii':'12','xiii':'13','xiv':'14','xv':'15','xvi':'16'}
def numeros(s):
    s = re.sub(r'\(?ps4\s*(&|and|y)\s*ps5\)?|\bps[45]\b|4k|\d{4}', ' ', s.lower())
    return {ROM.get(t, t) for t in re.findall(r'[a-z0-9]+', s) if t.isdigit() or (t in ROM and t not in ('i', 'v', 'x'))}
def buscar(nombre, consola, q=None):
    q0 = q
    q = q or re.sub(r'[:–\-!?,.\'’]', ' ', nombre); q = ' '.join(q.split())[:80]
    u = f'https://store.playstation.com/store/api/chihiro/00_09_000/tumbler/US/en/999/{urllib.parse.quote(q)}?suggested_size=10&mode=game'
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        d = json.load(OP.open(req, timeout=30))
    except Exception:
        return None, 0, ''
    mejor = (None, 0, '')
    for l in d.get('links', []):
        nm = l.get('name', '')
        pp = ' '.join(l.get('playable_platform') or []) + ' ' + nm
        if consola not in pp: continue
        if l.get('top_category') not in ('downloadable_game', 'disc_based_game'): continue
        if numeros(nombre) != numeros(nm): continue
        r = difflib.SequenceMatcher(None, norm(nombre), norm(nm)).ratio()
        if r > mejor[1]: mejor = (l.get('id'), r, l.get('name', ''))
    if mejor[0] is None and q0 is None:
        corto = norm(nombre)
        if corto and corto != norm(q): return buscar(nombre, consola, corto)
    return mejor
def main():
    consola = sys.argv[1]
    juegos = json.load(open(T + f'datos/{consola.lower()}.json'))
    ruta = T + f'datos/enlaces_{consola.lower()}.json'
    previos = json.load(open(ruta)) if os.path.exists(ruta) else {}
    if '--solo-nuevos' in sys.argv: juegos = [j for j in juegos if j not in previos]
    lim = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else None
    if lim: juegos = juegos[:lim]
    with ThreadPoolExecutor(8) as ex: res = list(ex.map(lambda n: (n, buscar(n, consola)), juegos))
    ok, dudas, no = {}, [], []
    for n, (pid, r, nom) in res:
        if pid and r >= 0.85: ok[n] = pid
        elif pid and r >= 0.6: dudas.append((n, nom, round(r, 2), pid))
        else: no.append(n)
    if '--probar' in sys.argv:
        for n, (pid, r, nom) in res: print(f'{r:.2f}  {n}  ->  {nom}  {pid}')
        return
    previos.update(ok)
    json.dump(dict(sorted(previos.items())), open(ruta, 'w'), ensure_ascii=False, indent=0)
    os.makedirs(T + 'salida', exist_ok=True)
    with open(T + f'salida/sin_enlace_{consola.lower()}.txt', 'w') as f:
        f.write(f'== DUDOSOS ({len(dudas)}): nombre en tu lista -> lo que encontró la tienda ==\n')
        f.writelines(f'{n}  ->  {nom}  ({r})\n' for n, nom, r, _ in dudas)
        f.write(f'\n== NO ENCONTRADOS ({len(no)}) ==\n'); f.writelines(n + '\n' for n in no)
    json.dump({n: pid for n, _, _, pid in dudas}, open(T + f'salida/dudosos_{consola.lower()}.json', 'w'), ensure_ascii=False, indent=0)
    print(consola, 'con enlace:', len(ok), 'dudosos:', len(dudas), 'no encontrados:', len(no))
if __name__ == '__main__': main()
