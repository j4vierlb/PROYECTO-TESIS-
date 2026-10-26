"""HTTP de escritura exclusivamente contra el QA Android en 127.0.0.1:18787.

Requiere schema.sql, seed.sql, migracion_croquis_terreno.sql y fixture.sql.
No imprime tokens, no llama OpenAI/Twilio y no admite la URL del backend real.
"""
from pathlib import Path
import json
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:18787'
VISIT = '99999999-9999-4999-8999-999999999999'
results = []

def call(method, path, body=None, token=None, data=None, content_type='application/json'):
    headers = {'Content-Type': content_type}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    payload = data if data is not None else (json.dumps(body).encode() if body is not None else None)
    request = urllib.request.Request(BASE + path, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
            return response.status, json.loads(raw) if response.headers.get_content_type() == 'application/json' else raw
    except urllib.error.HTTPError as response:
        return response.code, None

def check(name, code, expected, valid=True):
    results.append({'id': name, 'expected':expected, 'actual':code, 'passed':code == expected and bool(valid)})
    if code != expected or not valid:
        print(json.dumps({'checks':results}))
        raise SystemExit('Unexpected QA result: ' + name)

code, auth = call('POST','/auth/login',{'usuario':'tecnico1@killbichos.cl','clave':'demo1234'})
check('FIELD-API-01-login',code,200)
token = auth['access_token']
code, visit = call('PATCH','/visitas/'+VISIT,{'estado':'en_curso','notas':'QA Android: persistencia de notas'},token)
check('FIELD-API-02-start-notes',code,200,visit and visit['notas'] == 'QA Android: persistencia de notas')
code, croquis = call('POST','/croquis/'+VISIT,token=token)
check('FIELD-API-03-create-croquis',code,201)
code, same = call('POST','/croquis/'+VISIT,token=token)
check('FIELD-API-04-idempotent-croquis',code,200,same and same['id'] == croquis['id'])
code, device = call('POST','/croquis/'+VISIT+'/dispositivos',{'tipo':'cebadero','lat':-33.4869,'lng':-70.5989},token)
check('FIELD-API-05-add-coordinates',code,201,device and abs(device['lat']+33.4869)<0.000001)
device_id = device['id']
path = '/dispositivos-trampa/'+device_id
code, moved = call('PATCH',path,{'accion':'mover','lat':-33.4870,'lng':-70.5990},token)
check('FIELD-API-06-move',code,200,moved and abs(moved['lat']+33.4870)<0.000001)
code, confirmed = call('PATCH',path,{'accion':'confirmar'},token)
check('FIELD-API-07-confirm',code,200,confirmed and confirmed['confirmado'])
logo = Path(__file__).resolve().parents[2] / 'app-movil/assets/images/logo.png'
boundary = 'AndroidFieldQaBoundary'
form = (f'--{boundary}\r\nContent-Disposition: form-data; name="foto"; filename="qa.png"\r\nContent-Type: image/png\r\n\r\n').encode()+logo.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
code, photo = call('POST',path+'/foto',token=token,data=form,content_type='multipart/form-data; boundary='+boundary)
check('FIELD-API-08-upload-png',code,200,photo and bool(photo['foto_url']))
code, data = call('GET',path+'/foto',token=token)
check('FIELD-API-09-private-photo',code,200,data == logo.read_bytes())
code, _ = call('GET',path+'/foto')
check('FIELD-API-10-no-token',code,401)
code, outsider = call('POST','/auth/login',{'usuario':'externo@android.test','clave':'demo1234'})
check('FIELD-API-11-other-company-login',code,200)
code, _ = call('GET',path+'/foto',token=outsider['access_token'])
check('FIELD-API-12-other-company-photo',code,403)
code, _ = call('GET','/visitas/'+VISIT,token=outsider['access_token'])
check('FIELD-API-13-other-company-visit',code,403)
code, retired = call('PATCH',path,{'accion':'eliminar'},token)
check('FIELD-API-14-retire',code,200,retired and retired['estado']=='retirado')
code, _ = call('PATCH','/visitas/'+VISIT,{'estado':'completada'},token)
check('FIELD-API-15-complete',code,200)
code, _ = call('PATCH',path,{'accion':'confirmar'},token)
check('FIELD-API-16-closed-visit-write',code,409)
print(json.dumps({'qa_base':BASE,'work_database_modified':False,'calls_to_openai_twilio':False,
                  'passed':sum(r['passed'] for r in results),'total':len(results),'checks':results},indent=2))
