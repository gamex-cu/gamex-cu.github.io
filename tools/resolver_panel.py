"""Completa los enlaces de PlayStation de los juegos agregados desde el panel (tools/datos/panel_juegos.json).
Si en el enlace pusiste solo el código (PPSA28002 o CUSA12345) o lo dejaste vacío, busca el producto en la
PlayStation Store y pone el id completo (EP1470-PPSA28002_00-...). Lo corre la acción de GitHub antes de armar.py.
Si no hay internet o no lo encuentra, deja el juego sin enlace (no falla)."""
import json, os, re, sys

T = os.path.dirname(os.path.abspath(__file__)) + '/'
F = T + 'datos/panel_juegos.json'
COD = re.compile(r'^(PPSA|CUSA)\d{5}$', re.I)


def main():
    pj = json.load(open(F))
    pend = [a for a in pj.get('agregar', []) if a.get('c') in ('PS4', 'PS5') and not a.get('buscado')
            and (not a.get('link') or COD.match(a['link'].strip()))]
    if not pend: print('nada que buscar'); return
    sys.path.insert(0, T)
    try:
        import buscar_playstation as bp
        cat = bp.catalogo()
    except Exception as e:
        print('no se pudo leer la PlayStation Store:', e); return
    for a in pend:
        cod = (a.get('link') or '').strip().upper()
        cands = [p for p in cat if p.get('cls') in ('FULL_GAME', 'Full Game', '', None) and a['c'] in (p.get('pl') or [])]
        hit = None
        if cod:
            hit = next((p for p in cands if cod in p['id']), None) or next((p for p in cat if cod in p['id']), None)
        else:
            for p in cands: p.setdefault('nn', bp.norm(p['n'])); p.setdefault('nums', bp.numeros(p['n']))
            try:
                hit, r = bp.elegir(a['n'], cands)
                if r < 0.85: hit = None
            except Exception: hit = None
        a['buscado'] = True
        if hit:
            a['link'] = hit['id']; print('ok', a['n'], '->', hit['id'])
        else:
            a['link'] = ''; print('sin encontrar', a['n'], cod)
    json.dump(pj, open(F, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
