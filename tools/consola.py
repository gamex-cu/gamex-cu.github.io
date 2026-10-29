"""Genera app/consola.txt: el catálogo en texto simple para las apps de PS4/PS5/Switch.
La app lo descarga al abrirse (si hay internet) y lo guarda; sin internet usa el que tenga.
Formato (UTF-8, campos separados por tabulador, una línea por registro):
  GAMEX1
  V <versión>          número que sube en cada cambio
  F <fecha>            texto para mostrar ("28 oct 2026")
  M <mes de PS Plus>
  C <nombre> <slug> <color> <color texto>   (hex sin #)
  J <etiquetas> <nombre del juego>          (pertenece al último C)
  FIN
Uso: python3 consola.py [ruta/a/index.html] (lo llama armar.py)."""
import datetime, json, os, re, sys

T = os.path.dirname(os.path.abspath(__file__)) + '/'
R = os.path.dirname(T.rstrip('/')) + '/'
NOM = {'Switch': 'Nintendo Switch', 'PS4': 'PlayStation 4', 'PS5': 'PlayStation 5'}
FLAGS = [('ONLINE', 1), ('SERIES', 2), ('X360', 4), ('VR', 8), ('VRO', 16), ('PORT', 32), ('EMU', 64), ('EXCL', 128)]
MESES = 'ene feb mar abr may jun jul ago sep oct nov dic'.split()


def leer(web):
    s = open(web, encoding='utf-8').read()
    dec = json.JSONDecoder()

    def tomar(nombre, conjunto=True):
        m = re.search(r'\b' + nombre + (r'=new Set\(' if conjunto else r'='), s)
        if not m: return [] if conjunto else {}
        return dec.raw_decode(s, m.end())[0]

    raw = tomar('RAW', False)
    i = s.index('const CONS=') + len('const CONS=')
    cons = json.loads(s[i:s.index('];', i) + 1].replace("'", '"'))
    flags = {}
    for nombre, bit in FLAGS:
        for k in tomar(nombre): flags[k] = flags.get(k, 0) | bit
    mes = dec.raw_decode(s, s.index('const PSPMES=') + len('const PSPMES='))[0]
    try:  # catálogos nuevos creados desde el panel (van antes de PlayStation Plus)
        ce = [x for x in json.load(open(T + 'datos/catalogos_extra.json')) if x.get('n')]
        for x in ce: cons.insert(len(cons) - 1, [x['n'], x['n'], x.get('color', '#3d7bff'), '', x.get('texto', '#fff')])
    except FileNotFoundError: pass
    try:  # orden escogido en el panel
        orden = (json.load(open(T + 'datos/tienda.json')).get('orden') or {}).get('catalogos') or []
        if orden: cons.sort(key=lambda x: orden.index(x[0]) if x[0] in orden else 999)
    except FileNotFoundError: pass
    return raw, cons, flags, mes


def hx(h):
    h = h.lstrip('#')
    return (h * 2 if len(h) == 3 else h)[:6].lower()


def limpio(t):
    return ' '.join(str(t).replace('\t', ' ').split())


def generar(web=R + 'index.html', ver=None, salida=R + 'app/consola.txt'):
    raw, cons, flags, mes = leer(web)
    if ver is None: ver = json.load(open(R + 'app/version.json'))['catalogo']
    hoy = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-4)))
    out = ['GAMEX1', f'V\t{ver}', f'F\t{hoy.day} {MESES[hoy.month - 1]} {hoy.year}', f'M\t{limpio(mes)}']
    n = 0
    for c in cons:
        nombre, slug, col, _, txt = c[:5]
        juegos = raw.get(nombre, [])
        if not juegos: continue
        out.append('\t'.join(['C', NOM.get(nombre, nombre), nombre, hx(col), hx(txt)]))
        for j in sorted(juegos, key=lambda x: x.lower()):
            out.append(f'J\t{flags.get(nombre + "|" + j, 0)}\t{limpio(j)}'); n += 1
    out.append('FIN')
    open(salida, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
    return n


if __name__ == '__main__':
    print('consola.txt:', generar(*(sys.argv[1:2] or [])), 'juegos')
