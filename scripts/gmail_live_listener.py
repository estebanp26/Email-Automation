#!/usr/bin/env python3
"""
gmail_live_listener.py
=============================================================================
Escuchador en tiempo real de correos reales de Gmail para RIWI HSE.
Incluye filtros de seguridad y relevancia:
1. Filtro temporal: Ignora correos históricos previos al arranque del script.
2. Filtro de lista negra: Bloquea dominios de redes, juegos, spam y no-reply.
3. Filtro semántico HSE: Solo despacha correos con palabras clave de justificación
   (incapacidad, cita médica, calamidad, permiso, inasistencia, coder, riwi, etc.).
=============================================================================
"""

import os
import sys
import time
import json
import base64
import imaplib
import email
from email.header import decode_header
import email.utils
import urllib.request
import urllib.error
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Cargar automáticamente variables desde .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

# Respaldo de lectura directa si no están en os.environ
if not os.getenv("GMAIL_USER") or not os.getenv("GMAIL_APP_PASSWORD"):
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GMAIL_USER="):
                    os.environ["GMAIL_USER"] = line.split("=", 1)[1].strip()
                elif line.startswith("GMAIL_APP_PASSWORD="):
                    os.environ["GMAIL_APP_PASSWORD"] = line.split("=", 1)[1].strip()

# Colores para la terminal
GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Dominios y remitentes que nunca corresponden a justificaciones de coders
SPAM_DOMAINS = [
    "kick.com", "duolingo.com", "spotify.com", "twitter.com", "x.com", 
    "redditmail.com", "reddit.com", "instagram.com", "facebookmail.com",
    "twitch.tv", "chess.com", "riotgames.com", "battle.net", "ccpgames.com",
    "linkedin.com", "github.com", "store.steampowered.com", "youtube.com",
    "google.com", "accounts.google.com"
]

SPAM_PREFIXES = [
    "noreply", "no-reply", "donotreply", "notifications", "alert", "alerts", 
    "security", "marketing", "news", "newsletter", "billing", "promociones"
]

# Palabras clave indispensables para considerar un correo como justificación HSE
HSE_KEYWORDS = [
    "justificacion", "justificación", "excusa", "incapacidad", "cita", "medica", 
    "médica", "odontol", "salud", "sura", "sanitas", "nueva eps", "compensar", 
    "famisanar", "eps", "calamidad", "urgencia", "hospital", "clinica", "clínica", 
    "reposo", "formula medica", "fórmula médica", "inasistencia", "ausencia", 
    "falta", "retirarme", "salir antes", "salida temprana", "permiso", "preaviso", 
    "coder", "riwi", "novedad", "soporte", "enfermo", "diagnostico", "diagnóstico"
]


def clean_header_text(header_val: str) -> str:
    """Decodifica encabezados MIME que puedan venir codificados en UTF-8 / Base64 / Quoted-Printable."""
    if not header_val:
        return ""
    decoded_fragments = decode_header(header_val)
    parts = []
    for frag, enc in decoded_fragments:
        if isinstance(frag, bytes):
            try:
                parts.append(frag.decode(enc or "utf-8", errors="replace"))
            except Exception:
                parts.append(frag.decode("latin-1", errors="replace"))
        else:
            parts.append(str(frag))
    return "".join(parts).strip()


def parse_sender(from_header: str):
    """Extrae (nombre, email) de la cabecera From."""
    decoded = clean_header_text(from_header)
    name = "Coder"
    email_addr = decoded
    if "<" in decoded and ">" in decoded:
        parts = decoded.split("<", 1)
        name_cand = parts[0].strip().strip('"').strip("'")
        email_cand = parts[1].split(">", 1)[0].strip()
        if name_cand:
            name = name_cand
        if email_cand:
            email_addr = email_cand
    return name, email_addr.lower()


def is_spam_or_non_hse(sender_email: str, subject: str, body: str) -> tuple[bool, str]:
    """
    Determina si un correo debe ser descartado porque es spam, de plataforma o no relacionado a HSE.
    Retorna (is_discarded, reason).
    """
    sender_lower = sender_email.lower()
    subject_lower = subject.lower()
    body_lower = body.lower()
    full_text = f"{subject_lower} {body_lower}"

    # 1. Comprobación de dominio en lista negra
    for domain in SPAM_DOMAINS:
        if domain in sender_lower:
            return True, f"Dominio comercial/social ignorado ({domain})"

    # 2. Comprobación de prefijo común de noreply
    user_part = sender_lower.split("@")[0] if "@" in sender_lower else sender_lower
    for pfx in SPAM_PREFIXES:
        if pfx in user_part:
            return True, f"Remitente automático/no-reply ignorado ({pfx})"

    # 3. Comprobación obligatoria de palabras clave de justificación HSE
    has_hse_keyword = any(kw in full_text for kw in HSE_KEYWORDS)
    if not has_hse_keyword:
        return True, "No contiene términos de asistencia, cita, salud o justificación HSE"

    return False, "Válido"


def is_received_after(msg: email.message.Message, cutoff_time: datetime) -> bool:
    """Verifica si la fecha del correo es posterior a la hora de corte de inicio del listener."""
    date_header = msg.get("Date")
    if not date_header:
        return True
    try:
        msg_date = email.utils.parsedate_to_datetime(date_header)
        if msg_date.tzinfo is None:
            msg_date = msg_date.replace(tzinfo=timezone.utc)
        return msg_date >= cutoff_time
    except Exception:
        return True


def process_message(msg_raw: bytes, webhook_url: str, cutoff_time: datetime):
    """Parsea el mensaje RFC 822, aplica filtros y lo despacha al webhook de n8n."""
    msg = email.message_from_bytes(msg_raw)

    subject = clean_header_text(msg.get("Subject", "Sin asunto"))
    from_raw = msg.get("From", "")
    sender_name, sender_email = parse_sender(from_raw)
    message_id = msg.get("Message-ID", f"msg_{int(time.time())}_{sender_email}")
    received_date_str = msg.get("Date", datetime.now().isoformat())

    # 1. Filtro Temporal: Descartar si el correo es anterior a la hora de corte
    if not is_received_after(msg, cutoff_time):
        print(f"{YELLOW}[Ignorado - Correo Antiguo]: {subject} (Recibido: {received_date_str}){RESET}")
        return False

    body_text = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            # Adjuntos
            filename = part.get_filename()
            if filename:
                filename = clean_header_text(filename)
                payload_bytes = part.get_payload(decode=True)
                if payload_bytes:
                    b64_data = base64.b64encode(payload_bytes).decode("ascii")
                    attachments.append({
                        "filename": filename,
                        "mime_type": content_type or "application/octet-stream",
                        "size_bytes": len(payload_bytes),
                        "data_base64": b64_data
                    })
                continue

            # Cuerpo de texto
            if "attachment" not in content_disposition.lower():
                if content_type == "text/plain" and not body_text:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                elif content_type == "text/html" and not body_text:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if payload:
            body_text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")

    body_text = body_text.strip()

    # 2. Filtro de Relevancia e Intención HSE
    is_discarded, reason = is_spam_or_non_hse(sender_email, subject, body_text)
    if is_discarded:
        print(f"{YELLOW}[Ignorado - Filtro HSE]: {reason} | De: {sender_email} | Asunto: {subject}{RESET}")
        return False

    # 3. Payload validado para n8n
    payload = {
        "source_provider": "GMAIL",
        "sender_email": sender_email,
        "sender_name": sender_name,
        "email_subject": subject,
        "email_body": body_text,
        "received_at": datetime.now().isoformat(),
        "message_id": message_id,
        "attachments": attachments,
        "has_attachments": len(attachments) > 0
    }

    # Despacho HTTP a n8n
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            elapsed = time.time() - t0
            print(f"{GREEN}[✓] ¡Justificación HSE enviada con éxito a n8n! ({elapsed:.2f}s, HTTP {resp.status}){RESET}")
            print(f"    {BOLD}Remitente:{RESET} {sender_name} <{sender_email}>")
            print(f"    {BOLD}Asunto:{RESET} {subject}")
            print(f"    {BOLD}Adjuntos:{RESET} {len(attachments)} archivo(s) -> {[a['filename'] for a in attachments]}")
            print(f"    {CYAN}Visualizar en el panel: http://localhost:5173/requests{RESET}\n")
            return True
    except Exception as e:
        print(f"{RED}[✗] Error enviando correo a n8n ({webhook_url}): {e}{RESET}\n")
        return False


def listen_inbox(user: str, password: str, webhook_url: str, poll_interval: int = 4):
    clean_pwd = password.replace(" ", "").strip()
    clean_user = user.strip()

    # Hora de inicio: solo se procesarán correos que lleguen a partir de este momento
    # Con un margen de tolerancia de 2 minutos para sincronización de reloj
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=2)

    print(f"\n{BLUE}{BOLD}======================================================================{RESET}")
    print(f"{BLUE}{BOLD}   RIWI HSE — ESCUCHADOR EN VIVO DE CORREOS GMAIL (IMAP)             {RESET}")
    print(f"{BLUE}{BOLD}======================================================================{RESET}")
    print(f"[*] Conectando a {CYAN}imap.gmail.com:993{RESET}...")
    print(f"[*] Buzón de escucha: {GREEN}{clean_user}{RESET}")
    print(f"[*] Webhook destino: {CYAN}{webhook_url}{RESET}")
    print(f"[*] Filtro de inicio: {CYAN}Solo correos nuevos (desde {cutoff_time.strftime('%H:%M:%S UTC')}){RESET}")
    print(f"[*] Filtro de contenido: {GREEN}Solo justificaciones HSE (incapacidad, citas, salud, etc.){RESET}")
    print(f"[*] Intervalo de sondeo: {poll_interval} segundos")
    print(f"{YELLOW}[*] Esperando correos de justificación... (Ctrl+C para salir){RESET}\n")

    while True:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(clean_user, clean_pwd)
            mail.select("INBOX")
            
            # Obtener el UID más alto actual para ignorar todos los 2900+ correos antiguos al instante
            status, data = mail.uid("search", None, "ALL")
            all_uids = [int(x) for x in data[0].split()] if (status == "OK" and data and data[0]) else []
            last_uid = all_uids[-1] if all_uids else 0
            
            print(f"{GREEN}[✓] Conexión IMAP autenticada con éxito.{RESET}")
            print(f"{GREEN}[✓] Marcador fijado en el correo más reciente (UID={last_uid}).{RESET}")
            print(f"{CYAN}[✓] Se omiten al 100% los {len(all_uids)} correos existentes en el buzón.{RESET}")
            print(f"{BOLD}[⚡] Escuchando EXCLUSIVAMENTE correos que lleguen a partir de este instante...{RESET}\n")

            while True:
                # Búsqueda ultra-rápida únicamente de UIDs mayores que last_uid
                status, response = mail.uid("search", None, f"UID {last_uid + 1}:*")
                if status == "OK" and response and response[0]:
                    new_uids = [int(x) for x in response[0].split() if int(x) > last_uid]
                    for uid_int in sorted(new_uids):
                        uid_str = str(uid_int)
                        st, fetch_data = mail.uid("fetch", uid_str, "(RFC822)")
                        if st == "OK" and fetch_data and fetch_data[0]:
                            raw_email = fetch_data[0][1]
                            process_message(raw_email, webhook_url, cutoff_time)
                            # Marcar como visto
                            mail.uid("store", uid_str, "+FLAGS", "(\\Seen)")
                        last_uid = max(last_uid, uid_int)

                time.sleep(poll_interval)
                mail.noop()

        except KeyboardInterrupt:
            print(f"\n{YELLOW}[*] Deteniendo escuchador de Gmail por solicitud del usuario...{RESET}")
            try:
                mail.logout()
            except Exception:
                pass
            sys.exit(0)
        except Exception as e:
            print(f"{YELLOW}[!] Aviso de conexión: {e}. Reconectando en 5 segundos...{RESET}")
            time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="Escuchador IMAP en vivo de Gmail para RIWI HSE")
    parser.add_argument("--email", "-e", default=os.getenv("GMAIL_USER"), help="Dirección de correo Gmail")
    parser.add_argument("--password", "-p", default=os.getenv("GMAIL_APP_PASSWORD"), help="Contraseña de aplicación de 16 caracteres")
    parser.add_argument("--webhook", "-w", default="http://localhost:5678/webhook/riwi-email-incoming", help="URL del webhook en n8n")
    parser.add_argument("--interval", "-i", type=int, default=4, help="Segundos entre cada chequeo de bandeja")

    args = parser.parse_args()

    if not args.email or not args.password:
        print(f"{RED}[✗] Error: Se requiere especificar --email y --password (o definir GMAIL_USER y GMAIL_APP_PASSWORD en .env){RESET}")
        sys.exit(1)

    listen_inbox(args.email, args.password, args.webhook, args.interval)


if __name__ == "__main__":
    main()
