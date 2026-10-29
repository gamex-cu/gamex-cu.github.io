"""Marca como "solo online" los juegos nuevos de Game Pass que el dueño escogió en el panel y pasa los pendientes a revisados.
Uso: python3 tools/gamepass_marcar.py '["Juego 1","Juego 2"]'   (lo corre la acción de GitHub al publicar)"""
import json, os, sys
D = os.path.dirname(os.path.abspath(__file__)) + '/datos/'
marcar = set(json.loads(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].strip() else '[]'))
r = json.load(open(D + 'reglas_gamepass.json')); g = json.load(open(D + 'gamepass.json'))
clave = {v: k for k, v in r['nombres'].items()}
actuales = {n for n, _ in g['games']}
r['online'] = sorted(set(r['online']) | (marcar & actuales))
g['online'] = sorted(set(g['online']) | (marcar & actuales))
rev = set(r.get('revisados', []))
for n in r.get('pendientes', []):
    if n in clave: rev.add(clave[n])
r['revisados'] = sorted(rev); r['pendientes'] = []
json.dump(r, open(D + 'reglas_gamepass.json', 'w'), ensure_ascii=False, indent=1)
json.dump(g, open(D + 'gamepass.json', 'w'), ensure_ascii=False)
print('marcados solo online:', sorted(marcar & actuales))
