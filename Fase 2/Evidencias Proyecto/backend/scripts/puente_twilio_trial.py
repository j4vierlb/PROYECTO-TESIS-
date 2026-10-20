# =============================================================================
# scripts/puente_twilio_trial.py — Puente para probar WhatsApp con cuenta Trial
# -----------------------------------------------------------------------------
# Las cuentas Trial nuevas de Twilio usan un número compartido (+1 737 ...) al
# que no se le puede configurar el webhook. Este script hace de Twilio:
#   1. Cada 2 s consulta por la API los mensajes que llegaron a ese número.
#   2. Los envía al webhook del backend con la misma firma X-Twilio-Signature
#      que pondría Twilio (así se prueba también la validación).
#   3. Toma el texto de la respuesta TwiML y se lo manda al cliente por la API.
#
# SOLO para pruebas locales (HU-18). En producción Twilio llama al webhook
# directamente y este script no se usa.
#
# Uso, desde la carpeta backend y con el sistema levantado:
#   .venv\Scripts\python scripts\puente_twilio_trial.py
# Lee las claves del .env de la raíz del repo. Ctrl+C para detenerlo.
# =============================================================================

import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import httpx
from twilio.request_validator import RequestValidator

ROOT_ENV = Path(__file__).resolve().parents[4] / ".env"
BACKEND_URL = "http://localhost:8000/webhooks/whatsapp"
TRIAL_NUMBER = "whatsapp:+17372508034"
POLL_SECONDS = 2


def read_env(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def main() -> None:
    env = read_env(ROOT_ENV)
    sid, token = env.get("TWILIO_ACCOUNT_SID"), env.get("TWILIO_AUTH_TOKEN")
    webhook_url = env.get("TWILIO_WEBHOOK_URL")
    if not (sid and token and webhook_url):
        sys.exit(f"Faltan TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN o TWILIO_WEBHOOK_URL en {ROOT_ENV}")

    api = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    validator = RequestValidator(token)
    twilio = httpx.Client(auth=(sid, token), timeout=15)
    backend = httpx.Client(timeout=90)  # OpenAI puede tardar
    started = datetime.now(timezone.utc)
    seen: set[str] = set()

    print(f"Puente activo: {TRIAL_NUMBER} -> {BACKEND_URL}. Escribe por WhatsApp. Ctrl+C para salir.")
    while True:
        try:
            page = twilio.get(api, params={"To": TRIAL_NUMBER, "PageSize": 20}).json()
            # La API los entrega del más nuevo al más antiguo: se procesan en orden.
            for msg in reversed(page.get("messages", [])):
                sent = datetime.strptime(msg["date_created"], "%a, %d %b %Y %H:%M:%S %z")
                if msg["sid"] in seen or msg["direction"] != "inbound" or sent < started:
                    continue
                seen.add(msg["sid"])
                form = {
                    "AccountSid": sid,
                    "MessageSid": msg["sid"],
                    "From": msg["from"],
                    "To": msg["to"],
                    "Body": msg["body"] or "",
                    "NumMedia": msg.get("num_media") or "0",
                }
                print(f"\n<- {msg['from']}: {form['Body']}")
                signature = validator.compute_signature(webhook_url, form)
                response = backend.post(BACKEND_URL, data=form, headers={"X-Twilio-Signature": signature})
                print(f"   backend respondió {response.status_code}")
                if response.status_code != 200:
                    print(f"   {response.text[:300]}")
                    continue
                for node in ET.fromstring(response.text).iter("Message"):
                    text = "".join(node.itertext()).strip()
                    if not text:
                        continue
                    print(f"-> {text}")
                    sent_reply = twilio.post(api, data={"From": TRIAL_NUMBER, "To": msg["from"], "Body": text})
                    if sent_reply.status_code >= 400:
                        # La Trial solo permite enviar plantillas (error 21654): la
                        # respuesta queda en este log y en mensajes_whatsapp.
                        print(f"   Twilio no la envió al teléfono: {sent_reply.json().get('message')}")
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # sin red, Twilio caído, etc.: se reintenta
            print(f"   error: {exc!r}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nPuente detenido.")
