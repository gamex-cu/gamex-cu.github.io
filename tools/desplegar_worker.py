"""Sube (o actualiza) el Worker de avisos a Cloudflare y guarda su dirección en tools/datos/push.json.
Necesita ~/secretos/cloudflare.json (o /home/claude/secretos/cloudflare.json) con {"cuenta": "...", "token": "..."}
y acceso a api.cloudflare.com. La clave del Worker se crea sola la primera vez."""
import json, os, secrets, ssl, urllib.request, uuid
T = os.path.dirname(os.path.abspath(__file__)) + '/'
SEC = next((p for p in [os.path.expanduser('~/secretos'), '/home/claude/secretos'] if os.path.exists(p + '/cloudflare.json')), '/home/claude/secretos')
CF = json.load(open(SEC + '/cloudflare.json'))
if 'clave_worker' not in CF:
    CF['clave_worker'] = secrets.token_urlsafe(32); json.dump(CF, open(SEC + '/cloudflare.json', 'w'), indent=1)
pr = os.environ.get('HTTPS_PROXY'); ca = '/root/.ccr/ca-bundle.crt'
OP = urllib.request.build_opener(*([urllib.request.ProxyHandler({'https': pr})] if pr else []),
                                 urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca) if os.path.exists(ca) else ssl.create_default_context()))
API = f"https://api.cloudflare.com/client/v4/accounts/{CF['cuenta']}"
def cf(path, method='GET', data=None, ctype='application/json', base=API):
    h = {'Authorization': 'Bearer ' + CF['token']}
    if data is not None and ctype: h['Content-Type'] = ctype
    req = urllib.request.Request(base + path, data=data, method=method, headers=h)
    try: return json.load(OP.open(req, timeout=60))
    except urllib.error.HTTPError as e: raise SystemExit(f'Cloudflare {e.code}: {e.read().decode()[:500]}')
NOMBRE = 'gamex-avisos'
ns = [n for n in cf('/storage/kv/namespaces?per_page=100')['result'] if n['title'] == NOMBRE]
ns_id = ns[0]['id'] if ns else cf('/storage/kv/namespaces', 'POST', json.dumps({'title': NOMBRE}).encode())['result']['id']
meta = {'main_module': 'worker.js', 'compatibility_date': '2025-01-01',
        'bindings': [{'type': 'kv_namespace', 'name': 'SUBS', 'namespace_id': ns_id}, {'type': 'secret_text', 'name': 'CLAVE', 'text': CF['clave_worker']}]}
b = uuid.uuid4().hex
body = (f'--{b}\r\nContent-Disposition: form-data; name="metadata"\r\nContent-Type: application/json\r\n\r\n{json.dumps(meta)}\r\n'
        f'--{b}\r\nContent-Disposition: form-data; name="worker.js"; filename="worker.js"\r\nContent-Type: application/javascript+module\r\n\r\n'
        + open(T + 'push-worker.js').read() + f'\r\n--{b}--\r\n').encode()
cf(f'/workers/scripts/{NOMBRE}', 'PUT', body, f'multipart/form-data; boundary={b}')
cf(f'/workers/scripts/{NOMBRE}/subdomain', 'POST', json.dumps({'enabled': True}).encode())
sub = cf('/workers/subdomain')['result']['subdomain']
url = f'https://{NOMBRE}.{sub}.workers.dev'
p = json.load(open(T + 'datos/push.json')); p['url'] = url; json.dump(p, open(T + 'datos/push.json', 'w'), indent=1)
print('Worker listo:', url)
