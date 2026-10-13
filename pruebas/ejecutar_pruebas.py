#!/usr/bin/env python3
# =============================================================================
# ejecutar_pruebas.py — Pruebas de integración, seguridad y rendimiento
# Kill Bichos IA (plan de pruebas, documento 07)
# -----------------------------------------------------------------------------
# QUÉ HACE
#   Llama a la API real (la que levanta `docker compose up --build`) y comprueba
#   cada caso del plan: login, permisos 401/403, validaciones 422, conflictos 409,
#   cancelación sin borrar y tiempos de respuesta con usuarios simultáneos.
#   Al final imprime una tabla y guarda el resultado en la carpeta `pruebas/`
#   (un .md y un .json con la fecha) para adjuntarlo como evidencia.
#
# CÓMO SE USA (desde la raíz del repositorio, con el sistema ya levantado)
#   python3 "Fase 2/Evidencias Proyecto/pruebas/ejecutar_pruebas.py"
#   python3 ".../ejecutar_pruebas.py" --url http://localhost:8000
#
# REQUISITOS
#   Solo Python 3.9+ (no instala nada). Para PS-06 y PS-07 usa `docker compose
#   exec` si está disponible; si no, esos casos quedan como OMITIDO.
#
# AVISO
#   Crea datos de prueba (clientes y visitas llamados "PRUEBA-AUTO ..."). Las
#   visitas se cancelan al final; los clientes no se pueden borrar porque tienen
#   visitas. Para volver a los datos de demo originales: database/reset_demo.sql
#   Los resultados reales dependen de TU ejecución: este script no inventa nada.
# =============================================================================

import argparse
import json
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

ADMIN = ("admin@killbichos.cl", "demo1234")
TECNICO = ("tecnico1@killbichos.cl", "demo1234")
UMBRAL_RNF02_SEG = 2.0       # meta propuesta del RNF-02
USUARIOS_SIMULTANEOS = 10    # PR-01..03: 10 usuarios a la vez
RONDAS = 5                   # cada usuario repite 5 veces

resultados = []              # (id, caso, esperado, obtenido, estado)
BASE = "http://localhost:8000"


# ------------------------------------------------------------------ utilidades
def llamar(metodo, ruta, token=None, cuerpo=None, form=None, timeout=15):
    """Devuelve (codigo_http, json_o_texto, segundos)."""
    headers = {}
    data = None
    if token:
        headers["Authorization"] = "Bearer " + token
    if cuerpo is not None:
        data = json.dumps(cuerpo).encode()
        headers["Content-Type"] = "application/json"
    if form is not None:
        from urllib.parse import urlencode
        data = urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(BASE + ruta, data=data, method=metodo, headers=headers)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw, code = r.read().decode(), r.status
    except urllib.error.HTTPError as e:
        raw, code = e.read().decode(), e.code
    except Exception as e:  # sin conexión, timeout, etc.
        return 0, str(e), time.perf_counter() - t0
    dt = time.perf_counter() - t0
    try:
        return code, json.loads(raw) if raw else None, dt
    except ValueError:
        return code, raw, dt


def registrar(id_, caso, esperado, obtenido, ok):
    estado = "APROBADO" if ok else "FALLIDO"
    resultados.append((id_, caso, esperado, str(obtenido), estado))
    print(f"[{estado:9}] {id_:6} {caso} -> esperado {esperado}, obtenido {obtenido}")


def omitir(id_, caso, motivo):
    resultados.append((id_, caso, "-", motivo, "OMITIDO"))
    print(f"[OMITIDO  ] {id_:6} {caso} -> {motivo}")


def login(usuario):
    code, body, _ = llamar("POST", "/auth/login", cuerpo={"usuario": usuario[0], "clave": usuario[1]})
    return code, body


def compose_psql(sql):
    """Ejecuta SQL en el contenedor de la base. Devuelve texto o None si no se puede."""
    try:
        out = subprocess.run(
            ["docker", "compose", "exec", "-T", "db", "sh", "-c",
             'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "$0"', sql],
            capture_output=True, text=True, timeout=30)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


# --------------------------------------------------------------------- pruebas
def main():
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=BASE)
    BASE = ap.parse_args().url.rstrip("/")
    inicio = datetime.now()
    print(f"Probando {BASE} — {inicio:%Y-%m-%d %H:%M:%S}\n")

    code, body, _ = llamar("GET", "/health")
    registrar("PI-01", "GET /health (sistema vivo)", "200 {status: ok}", code,
              code == 200 and isinstance(body, dict) and body.get("status") == "ok")
    if code == 0:
        print("\nNo se pudo conectar con la API. ¿Corriste `docker compose up --build`?")
        sys.exit(1)

    # ---- Login
    c_adm, b_adm = login(ADMIN)
    tok_adm = b_adm.get("access_token") if isinstance(b_adm, dict) else None
    registrar("PI-02", "Login administrador válido", "200 + access_token y refresh_token", c_adm,
              c_adm == 200 and bool(tok_adm) and bool(b_adm.get("refresh_token")))
    c_tec, b_tec = login(TECNICO)
    tok_tec = b_tec.get("access_token") if isinstance(b_tec, dict) else None
    registrar("PI-03", "Login técnico válido", "200 + access_token", c_tec, c_tec == 200 and bool(tok_tec))
    if not (tok_adm and tok_tec):
        print("\nSin tokens no se puede seguir (¿cambiaron los usuarios de demo?).")
        guardar(inicio)
        sys.exit(1)

    # ---- Operadores y estadísticas (panel)
    code, ops, _ = llamar("GET", "/panel/operadores", tok_adm)
    op_id = ops[0]["id"] if code == 200 and ops else None
    registrar("PI-04", "Panel: lista de técnicos", "200 y al menos 1 técnico", code, code == 200 and bool(ops))
    code, st, _ = llamar("GET", "/panel/stats", tok_adm)
    registrar("PI-05", "Panel: estadísticas", "200 con clientes, visitas_hoy y pendientes", code,
              code == 200 and isinstance(st, dict) and {"clientes", "visitas_hoy", "pendientes"} <= set(st))

    # ---- Clientes
    sufijo = datetime.now().strftime("%H%M%S")
    nuevo = {"nombre": f"PRUEBA-AUTO {sufijo}", "telefono_whatsapp": f"+5690000{sufijo}",
             "direccion": "Av. Prueba 123, Macul", "lat": -33.49, "lng": -70.60}
    code, cli, _ = llamar("POST", "/clientes", tok_adm, nuevo)
    cli_id = cli.get("id") if code == 201 and isinstance(cli, dict) else None
    registrar("PI-06", "Crear cliente válido", "201 con id", code, code == 201 and bool(cli_id))

    # ---- Visitas
    manana = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0).isoformat()
    vis_id = None
    if cli_id and op_id:
        code, vis, _ = llamar("POST", "/panel/visitas", tok_adm,
                              {"cliente_id": cli_id, "operador_id": op_id, "fecha_hora": manana, "notas": "PRUEBA-AUTO"})
        vis_id = vis.get("id") if code == 201 and isinstance(vis, dict) else None
        registrar("PI-07", "Crear visita manual asignada a un técnico", "201 con origen manual y estado agendada", code,
                  code == 201 and vis.get("origen_agendamiento") == "manual" and vis.get("estado") == "agendada")
        code, lista, _ = llamar("GET", f"/panel/visitas?operador_id={op_id}", tok_adm)
        registrar("PI-08", "Panel: filtrar visitas por técnico", "200 y la visita creada aparece", code,
                  code == 200 and any(v["id"] == vis_id for v in lista))
    else:
        omitir("PI-07", "Crear visita manual", "falta cliente o técnico")
        omitir("PI-08", "Filtrar visitas por técnico", "falta cliente o técnico")

    # ---- Técnico: agenda, detalle y cambio de estado sobre SU visita
    if vis_id:
        code, det, _ = llamar("GET", f"/visitas/{vis_id}", tok_tec)
        registrar("PI-09", "Técnico: detalle de su visita", "200 con cliente y estado", code,
                  code == 200 and det.get("id") == vis_id)
        code, upd, _ = llamar("PATCH", f"/visitas/{vis_id}", tok_tec, {"estado": "en_curso"})
        registrar("PI-10", "Técnico: iniciar visita (PATCH estado en_curso)", "200 y estado en_curso", code,
                  code == 200 and upd.get("estado") == "en_curso")
    else:
        omitir("PI-09", "Técnico: detalle de su visita", "no se creó la visita")
        omitir("PI-10", "Técnico: iniciar visita", "no se creó la visita")
    code, hoy, _ = llamar("GET", "/operadores/me/visitas-hoy", tok_tec)
    registrar("PI-11", "Técnico: agenda de hoy", "200 y una lista", code, code == 200 and isinstance(hoy, list))
    code, hist, _ = llamar("GET", "/operadores/me/visitas-historial?limit=5&offset=0", tok_tec)
    registrar("PI-12", "Técnico: historial paginado", "200 y una lista", code, code == 200 and isinstance(hist, list))

    # ---- Croquis y trampas (datos de demo)
    visita_con_croquis, croquis = None, None
    candidatas = (hoy if isinstance(hoy, list) else []) + (hist if isinstance(hist, list) else [])
    for v in candidatas:
        c, cr, _ = llamar("GET", f"/croquis/{v['id']}", tok_tec)
        if c == 200 and cr.get("dispositivos"):
            visita_con_croquis, croquis = v["id"], cr
            break
    if croquis:
        registrar("PI-13", "Técnico: ver croquis con trampas", "200 con dispositivos", 200, True)
        disp = croquis["dispositivos"][0]
        code, d2, _ = llamar("PATCH", f"/dispositivos-trampa/{disp['id']}", tok_tec, {"accion": "confirmar"})
        registrar("PI-14", "Técnico: confirmar trampa", "200 y confirmado=true", code,
                  code == 200 and d2.get("confirmado") is True)
        code, _, _ = llamar("PATCH", f"/dispositivos-trampa/{disp['id']}", tok_adm, {"accion": "confirmar"})
        registrar("PS-11", "Administrador no puede tocar trampas", "403", code, code == 403)
        code, _, _ = llamar("PATCH", f"/dispositivos-trampa/{disp['id']}", tok_tec, {"accion": "mover"})
        registrar("PS-10", "Validación: mover trampa sin lat/lng", "422", code, code == 422)
    else:
        for i, c in [("PI-13", "ver croquis"), ("PI-14", "confirmar trampa"),
                     ("PS-11", "admin no toca trampas"), ("PS-10", "mover sin lat/lng")]:
            omitir(i, c, "ninguna visita de demo con croquis (¿corriste seed/demo_historial?)")

    # ---- Reglas de negocio: conflicto y cancelación sin borrar
    if cli_id and vis_id:
        code, _, _ = llamar("DELETE", f"/clientes/{cli_id}", tok_adm)
        registrar("PI-15", "Eliminar cliente con visitas", "409 y no se borra", code, code == 409)
        code, _, _ = llamar("DELETE", f"/panel/visitas/{vis_id}", tok_adm)
        code2, lista, _ = llamar("GET", f"/panel/visitas?operador_id={op_id}", tok_adm)
        sigue = [v for v in lista if v["id"] == vis_id] if code2 == 200 else []
        registrar("PI-16", "Cancelar visita sin borrarla", "204 y la visita sigue con estado cancelada", code,
                  code == 204 and bool(sigue) and sigue[0]["estado"] == "cancelada")
    # Exploratoria: visita sin técnico (el esquema de respuesta exige operador_id)
    if cli_id:
        code, vis2, _ = llamar("POST", "/panel/visitas", tok_adm, {"cliente_id": cli_id, "fecha_hora": manana})
        registrar("PI-17", "(exploratoria) Crear visita sin técnico asignado", "201 (o rechazo controlado 4xx, nunca 500)",
                  code, code in (201, 400, 422))
        if code == 201 and isinstance(vis2, dict) and vis2.get("id"):
            llamar("DELETE", f"/panel/visitas/{vis2['id']}", tok_adm)

    # ---- Seguridad
    code, b, _ = llamar("POST", "/auth/login", cuerpo={"usuario": ADMIN[0], "clave": "clave-incorrecta"})
    code_b, b_b, _ = llamar("POST", "/auth/login", cuerpo={"usuario": "noexiste@killbichos.cl", "clave": "x"})
    registrar("PS-01", "Login con clave incorrecta / usuario inexistente",
              "401 en ambos y el mismo mensaje (no revela si el usuario existe)", f"{code}/{code_b}",
              code == 401 and code_b == 401 and b == b_b)
    c1, _, _ = llamar("GET", "/operadores/me/visitas-hoy")
    c2, _, _ = llamar("GET", "/panel/stats")
    registrar("PS-02", "Endpoints protegidos sin token", "401 en ambos", f"{c1}/{c2}", c1 == 401 and c2 == 401)
    c1, _, _ = llamar("GET", "/panel/stats", "token.falso.invalido")
    registrar("PS-03", "Token inválido", "401", c1, c1 == 401)
    c1, _, _ = llamar("GET", "/panel/stats", tok_tec)
    registrar("PS-04", "Técnico intenta usar el panel", "403", c1, c1 == 403)
    c1, _, _ = llamar("GET", "/operadores/me/visitas-hoy", tok_adm)
    registrar("PS-05", "Administrador en la agenda del técnico", "403", c1, c1 == 403)

    # PS-06: visita de OTRO técnico (se crea un segundo técnico con SQL)
    ajeno = None
    if cli_id and compose_psql("SELECT 1") is not None:
        compose_psql(
            "INSERT INTO operadores (id, empresa_id, nombre, telefono, email, password_hash) "
            "SELECT '44444444-4444-4444-4444-444444444444'::uuid, empresa_id, 'Técnico Prueba', '+56911111111', "
            "'tecnico2@killbichos.cl', password_hash FROM operadores WHERE email='tecnico1@killbichos.cl' "
            "ON CONFLICT DO NOTHING")
        code, v3, _ = llamar("POST", "/panel/visitas", tok_adm,
                             {"cliente_id": cli_id, "operador_id": "44444444-4444-4444-4444-444444444444",
                              "fecha_hora": manana, "notas": "PRUEBA-AUTO ajena"})
        if code == 201:
            ajeno = v3["id"]
    if ajeno:
        code, _, _ = llamar("GET", f"/visitas/{ajeno}", tok_tec)
        registrar("PS-06", "Técnico consulta la visita de otro técnico", "403", code, code == 403)
        llamar("DELETE", f"/panel/visitas/{ajeno}", tok_adm)
    else:
        omitir("PS-06", "Técnico consulta visita ajena", "no se pudo crear un segundo técnico (requiere docker compose exec)")

    hashes = compose_psql("SELECT count(*) FILTER (WHERE password_hash LIKE '$2%'), count(*) FROM usuarios")
    if hashes:
        ok_h, total = hashes.split("|")
        registrar("PS-07", "Contraseñas guardadas como hash bcrypt (tabla usuarios)", "todas empiezan con $2",
                  f"{ok_h} de {total}", ok_h == total and int(total) > 0)
    else:
        omitir("PS-07", "Contraseñas como hash", "requiere docker compose exec")

    c1, _, _ = llamar("POST", "/clientes", tok_adm, {**nuevo, "lat": 500})
    registrar("PS-08", "Validación: latitud fuera de rango", "422", c1, c1 == 422)
    c1, _, _ = llamar("POST", "/clientes", tok_adm, {"nombre": "x"})
    registrar("PS-09", "Validación: campos obligatorios faltantes", "422", c1, c1 == 422)
    c1, _, _ = llamar("POST", "/webhooks/whatsapp", form={"From": "whatsapp:+56900000000", "Body": "hola", "MessageSid": "SMPRUEBA"})
    registrar("PS-12", "Webhook de WhatsApp sin firma de Twilio", "403 (TWILIO_VALIDATE_SIGNATURE=true)", c1, c1 == 403)

    # ---- Rendimiento (RNF-02: < 2 s con 10 usuarios simultáneos)
    def medir(nombre, id_, metodo, ruta, token=None, cuerpo=None):
        total = USUARIOS_SIMULTANEOS * RONDAS
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=USUARIOS_SIMULTANEOS) as ex:
            res = list(ex.map(lambda _: llamar(metodo, ruta, token, cuerpo), range(total)))
        dur = time.perf_counter() - t0
        tiempos = sorted(r[2] for r in res)
        errores = sum(1 for r in res if r[0] not in (200, 201))
        p95 = tiempos[int(len(tiempos) * 0.95) - 1]
        obtenido = (f"{total} peticiones, {USUARIOS_SIMULTANEOS} simultáneas: media {statistics.mean(tiempos):.3f} s, "
                    f"p95 {p95:.3f} s, máx {tiempos[-1]:.3f} s, errores {errores}, total {dur:.1f} s")
        registrar(id_, nombre, f"p95 < {UMBRAL_RNF02_SEG:.0f} s y 0 errores", obtenido,
                  p95 < UMBRAL_RNF02_SEG and errores == 0)

    medir("Rendimiento: login", "PR-01", "POST", "/auth/login", None, {"usuario": TECNICO[0], "clave": TECNICO[1]})
    medir("Rendimiento: agenda del técnico", "PR-02", "GET", "/operadores/me/visitas-hoy", tok_tec)
    medir("Rendimiento: agenda del panel", "PR-03", "GET", "/panel/visitas", tok_adm)

    guardar(inicio)


def guardar(inicio):
    carpeta = Path(__file__).resolve().parent
    fecha = inicio.strftime("%Y-%m-%d_%H%M")
    ap = sum(1 for r in resultados if r[4] == "APROBADO")
    fa = sum(1 for r in resultados if r[4] == "FALLIDO")
    om = sum(1 for r in resultados if r[4] == "OMITIDO")
    lineas = [f"# Resultados de pruebas automáticas — {inicio:%d-%m-%Y %H:%M}", "",
              f"API probada: {BASE}", f"Aprobadas: {ap} · Fallidas: {fa} · Omitidas: {om}", "",
              "| ID | Caso | Esperado | Obtenido | Estado |", "|---|---|---|---|---|"]
    for r in resultados:
        lineas.append("| " + " | ".join(x.replace("|", "/") for x in r) + " |")
    (carpeta / f"resultados_{fecha}.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    (carpeta / f"resultados_{fecha}.json").write_text(
        json.dumps([dict(zip(("id", "caso", "esperado", "obtenido", "estado"), r)) for r in resultados],
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResumen: {ap} aprobadas, {fa} fallidas, {om} omitidas.")
    print(f"Guardado en {carpeta}/resultados_{fecha}.md")
    print("Adjunta ese archivo (y una captura de esta pantalla) como evidencia del plan de pruebas.")
    sys.exit(1 if fa else 0)


if __name__ == "__main__":
    main()
