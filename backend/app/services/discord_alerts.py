"""
Módulo Notificador en Tiempo Real a Discord / Slack para Alertas HSE (CONN-EXT-01).

Permite despachar alertas visuales tipo Embed (Discord) o Attachment (Slack)
hacia canales de Team Leaders / HSE cuando se procesa o radica una justificación,
con codificación de colores según el estado (Verde: Aprobado, Naranja: Pendiente, Rojo: Caso Sensible).

Si no hay webhook configurado en HSE_DISCORD_WEBHOOK_URL, opera en modo de consola enriquecida
(DEV_CONSOLE) sin fallar ni bloquear los flujos principales.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
import urllib.request
import urllib.error

# Intentar importar httpx si está disponible en el entorno
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

# Intentar importar settings de la aplicación de manera relativa o fallback a variables de entorno
try:
    from ..config import settings
except Exception:
    class DummySettings:
        HSE_DISCORD_WEBHOOK_URL = os.getenv("HSE_DISCORD_WEBHOOK_URL", "")
    settings = DummySettings()

logger = logging.getLogger("hse.discord_alerts")

# Constantes de Colores para Discord Embeds (Decimales) y Slack (Hex)
COLOR_GREEN_DECIMAL = 0x2ECC71   # 3066993 - Aprobado
COLOR_GREEN_HEX = "#2ECC71"

COLOR_ORANGE_DECIMAL = 0xE67E22  # 15105570 - Pendiente / Revisión Manual
COLOR_ORANGE_HEX = "#E67E22"

COLOR_RED_DECIMAL = 0xE74C3C     # 15158332 - Caso Sensible / Rechazado
COLOR_RED_HEX = "#E74C3C"


def get_status_visuals(status: str, is_sensitive: bool = False) -> Tuple[int, str, str, str]:
    """
    Retorna (color_decimal, color_hex, tag_texto, emoji) según el estado y si es caso sensible.
    
    Reglas de color:
    - Verde: Aprobado (APPROVED, POSIBLEMENTE_VALIDO, JUSTIFICADA)
    - Naranja: Pendiente / Revisión (REVISION_MANUAL, PENDING, CODER_NOT_FOUND, REQUEST_MORE_INFO)
    - Rojo: Caso Sensible (is_sensitive=True, SENSITIVE, CASO_SENSIBLE) o Rechazado (DISAPPROVED, REJECTED)
    """
    clean_status = (status or "").upper().strip()
    
    # 1. Caso Sensible tiene máxima prioridad de alerta visual (Rojo)
    if is_sensitive or clean_status in ["SENSITIVE", "CASO_SENSIBLE", "CRISIS", "EMERGENCIA"]:
        return COLOR_RED_DECIMAL, COLOR_RED_HEX, "CASO SENSIBLE / URGENTE", "🚨"
    
    # 2. Aprobado (Verde)
    if clean_status in ["APPROVED", "APROBADO", "VALIDO", "POSIBLEMENTE_VALIDO", "JUSTIFICADA"]:
        return COLOR_GREEN_DECIMAL, COLOR_GREEN_HEX, "APROBADO", "✅"
    
    # 3. Rechazado / Injustificado (Rojo)
    if clean_status in ["DISAPPROVED", "REJECTED", "RECHAZADO", "NO_JUSTIFICADA", "POSIBLEMENTE_INVALIDO"]:
        return COLOR_RED_DECIMAL, COLOR_RED_HEX, "NO JUSTIFICADO / RECHAZADO", "❌"
    
    # 4. Por defecto: Pendiente / En Revisión (Naranja)
    return COLOR_ORANGE_DECIMAL, COLOR_ORANGE_HEX, "PENDIENTE / REVISIÓN MANUAL", "⚠️"


def format_novelty_label(novelty_type: str) -> str:
    """Convierte el identificador técnico de la novedad en una etiqueta legible."""
    if not novelty_type:
        return "Novedad General"
    return novelty_type.replace("_", " ").title()


def build_discord_payload(
    coder_name: str,
    route: str,
    novelty_type: str,
    radicado_id: str,
    status: str,
    details: Optional[str] = None,
    is_sensitive: bool = False,
) -> Dict[str, Any]:
    """
    Construye la carga útil (payload) JSON con formato Embed nativo de Discord.
    """
    color_dec, _, tag_text, emoji = get_status_visuals(status, is_sensitive)
    novelty_label = format_novelty_label(novelty_type)
    
    if is_sensitive:
        title = f"{emoji} Alerta HSE: Caso Sensible Detectado"
        description = "Se ha radicado una justificación catalogada como de **alta sensibilidad o apoyo prioritario**. Requiere atención inmediata del equipo de Team Leaders / HSE."
    elif "APROBADO" in tag_text:
        title = f"{emoji} Novedad de Asistencia Convalidada"
        description = "La justificación médica / técnica cumple con todos los requisitos y ha sido aprobada."
    elif "RECHAZADO" in tag_text:
        title = f"{emoji} Novedad de Asistencia No Justificada"
        description = "La justificación no cumple con los soportes requeridos y activa umbral de seguimiento."
    else:
        title = f"{emoji} Novedad de Asistencia en Revisión"
        description = "Justificación radicada a la espera de validación de soportes o revisión manual por Team Leader."

    fields = [
        {"name": "👤 Coder", "value": coder_name or "Desconocido", "inline": True},
        {"name": "🚀 Ruta / Clan", "value": route or "No Asignada", "inline": True},
        {"name": "📋 Tipo de Novedad", "value": novelty_label, "inline": True},
        {"name": "🆔 Radicado ID", "value": f"`{radicado_id}`", "inline": True},
        {"name": "📊 Estado", "value": f"**{tag_text}**", "inline": True},
    ]

    if details:
        fields.append({"name": "📝 Observaciones", "value": str(details)[:1024], "inline": False})

    embed = {
        "title": title,
        "description": description,
        "color": color_dec,
        "fields": fields,
        "footer": {
            "text": "Riwi HSE & Team Leader Automation • Squad Conexiones (CONN-EXT-01)"
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "username": "Riwi HSE Bot de Alertas",
        "avatar_url": "https://raw.githubusercontent.com/estebanp26/Email-Automation/develop/docs/assets/riwi_logo.png",
        "embeds": [embed],
    }


def build_slack_payload(
    coder_name: str,
    route: str,
    novelty_type: str,
    radicado_id: str,
    status: str,
    details: Optional[str] = None,
    is_sensitive: bool = False,
) -> Dict[str, Any]:
    """
    Construye la carga útil (payload) JSON con formato de attachments para Slack.
    """
    _, color_hex, tag_text, emoji = get_status_visuals(status, is_sensitive)
    novelty_label = format_novelty_label(novelty_type)

    text_body = (
        f"*{emoji} Alerta de Asistencia Riwi - {tag_text}*\n"
        f"• *Coder:* {coder_name}\n"
        f"• *Ruta / Clan:* {route}\n"
        f"• *Novedad:* {novelty_label}\n"
        f"• *Radicado ID:* `{radicado_id}`\n"
        f"• *Estado:* *{status}*\n"
    )
    if details:
        text_body += f"• *Observaciones:* {details}\n"

    return {
        "text": f"{emoji} Novedad de Asistencia: *{coder_name}* ({tag_text})",
        "attachments": [
            {
                "color": color_hex,
                "title": f"Radicado: {radicado_id}",
                "text": text_body,
                "footer": "Riwi HSE & Team Leader Automation (CONN-EXT-01)",
                "ts": int(datetime.now(timezone.utc).timestamp()),
            }
        ],
    }


def print_dev_console_alert(
    coder_name: str,
    route: str,
    novelty_type: str,
    radicado_id: str,
    status: str,
    details: Optional[str] = None,
    is_sensitive: bool = False,
) -> None:
    """
    Muestra la alerta en la consola con formato enriquecido para el modo desarrollo
    cuando no hay webhook configurado en HSE_DISCORD_WEBHOOK_URL.
    """
    _, _, tag_text, emoji = get_status_visuals(status, is_sensitive)
    novelty_label = format_novelty_label(novelty_type)

    border = "═" * 70
    sub_border = "─" * 70

    print(f"\n{border}")
    print(f"🔔 [HSE NOTIFIER - MODO DESARROLLO (Sin Webhook)]")
    print(f"Canal Objetivo: Discord / Slack #alertas-team-leaders")
    print(sub_border)
    print(f"🎯 ESTADO:      {emoji} {tag_text}")
    print(f"🆔 RADICADO:    {radicado_id}")
    print(f"👤 CODER:       {coder_name}")
    print(f"🚀 RUTA / CLAN: {route}")
    print(f"📋 NOVEDAD:     {novelty_label}")
    if details:
        print(f"📝 DETALLES:    {details}")
    if is_sensitive:
        print(f"⚠️  ATENCIÓN:    Caso clasificado como SENSIBLE. Notificar a HSE de inmediato.")
    print(f"{border}\n")


def send_team_lead_alert(
    coder_name: str,
    route: str,
    novelty_type: str,
    radicado_id: str,
    status: str,
    details: Optional[str] = None,
    is_sensitive: bool = False,
    webhook_url: Optional[str] = None,
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """
    Despacha una alerta en tiempo real al canal de Team Leaders / HSE.
    
    Parámetros:
    - coder_name: Nombre completo del estudiante.
    - route: Clan o ruta formativa (e.g., 'Node.js Backend', 'Clan Gosling').
    - novelty_type: Tipo de novedad ('incapacidad_medica', 'calamidad_domestica', etc.).
    - radicado_id: Identificador único del radicado (e.g., 'just-12345').
    - status: Estado del veredicto ('APPROVED', 'REVISION_MANUAL', 'DISAPPROVED', etc.).
    - details: Observaciones adicionales o resumen del análisis de la IA.
    - is_sensitive: Flag booleano que indica si es un caso de salud mental o calamidad.
    - webhook_url: URL opcional para pruebas directas o sobreescritura de configuración.
    - timeout: Tiempo límite en segundos para la petición HTTP (por defecto 5.0 s).
    
    Comportamiento resiliente:
    - Si no hay webhook configurado, imprime en consola enriquecida (modo dev).
    - Si ocurre timeout o error de red, lo atrapa silenciosamente y retorna un diccionario
      con 'success': False sin interrumpir la ejecución del orquestador.
    """
    target_url = (webhook_url or getattr(settings, "HSE_DISCORD_WEBHOOK_URL", "") or os.getenv("HSE_DISCORD_WEBHOOK_URL", "")).strip()

    # MODO DESARROLLO: Si no hay webhook configurado, imprimir en consola enriquecida
    if not target_url:
        print_dev_console_alert(
            coder_name=coder_name,
            route=route,
            novelty_type=novelty_type,
            radicado_id=radicado_id,
            status=status,
            details=details,
            is_sensitive=is_sensitive,
        )
        return {
            "success": True,
            "mode": "DEV_CONSOLE",
            "message": "Alerta registrada en consola (modo desarrollo sin webhook)",
            "radicado_id": radicado_id,
            "status": status,
        }

    # Determinar si el webhook es de Slack o de Discord
    is_slack = "hooks.slack.com" in target_url or "slack.com" in target_url
    if is_slack:
        payload = build_slack_payload(
            coder_name=coder_name,
            route=route,
            novelty_type=novelty_type,
            radicado_id=radicado_id,
            status=status,
            details=details,
            is_sensitive=is_sensitive,
        )
    else:
        payload = build_discord_payload(
            coder_name=coder_name,
            route=route,
            novelty_type=novelty_type,
            radicado_id=radicado_id,
            status=status,
            details=details,
            is_sensitive=is_sensitive,
        )

    # Despacho HTTP resiliente
    try:
        if HAS_HTTPX:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(target_url, json=payload)
                status_code = response.status_code
        else:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                target_url,
                data=req_data,
                headers={"Content-Type": "application/json", "User-Agent": "Riwi-HSE-Bot/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status_code = response.status

        # Discord responde 204 No Content en envíos exitosos; Slack responde 200 OK
        if status_code in (200, 201, 204):
            logger.info("Alerta despachada exitosamente a webhook (status: %d)", status_code)
            return {
                "success": True,
                "mode": "WEBHOOK_DISPATCHED",
                "status_code": status_code,
                "radicado_id": radicado_id,
            }
        else:
            logger.warning("El webhook respondió con código no estándar: %d", status_code)
            return {
                "success": False,
                "mode": "WEBHOOK_HTTP_ERROR",
                "status_code": status_code,
                "radicado_id": radicado_id,
            }

    except Exception as exc:
        # Resiliencia total: No lanzar excepción para jamás tumbar el pipeline principal
        logger.error("Error no bloqueante al enviar alerta al webhook: %s", exc)
        return {
            "success": False,
            "mode": "WEBHOOK_EXCEPTION",
            "error": str(exc),
            "radicado_id": radicado_id,
        }


# =====================================================================
# Ejecución independiente para pruebas rápidas y verificación CLI
# python3 -m backend.app.services.discord_alerts
# =====================================================================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧪 EJECUTANDO TESTS INDEPENDIENTES DE DISCORD_ALERTS (CONN-EXT-01)")
    print("=" * 70)

    # Test 1: Caso Aprobado (Verde)
    print("\n--- TEST 1: Caso Aprobado (Incapacidad Médica) ---")
    r1 = send_team_lead_alert(
        coder_name="Jose Luis Acevedo Vargas",
        route="Node.js Backend - Clan Gosling",
        novelty_type="incapacidad_medica",
        radicado_id="just-demo-001",
        status="APPROVED",
        details="Incapacidad EPS Sura convalidada por 2 días. Soporte médico verificado.",
        is_sensitive=False,
    )
    assert r1["success"] is True, f"Error en Test 1: {r1}"
    print(f"Resultado Test 1: {r1}")

    # Test 2: Caso Pendiente / Revisión Manual (Naranja)
    print("\n--- TEST 2: Caso Pendiente (Falta de Soporte / Extemporáneo) ---")
    r2 = send_team_lead_alert(
        coder_name="Laura Gómez",
        route="TypeScript Fullstack - Clan Lovelace",
        novelty_type="malestar_general",
        radicado_id="just-demo-002",
        status="REVISION_MANUAL",
        details="Reportó dolor de cabeza sin soporte médico formal. Requiere validación de TL.",
        is_sensitive=False,
    )
    assert r2["success"] is True, f"Error en Test 2: {r2}"
    print(f"Resultado Test 2: {r2}")

    # Test 3: Caso Sensible / Urgente (Rojo)
    print("\n--- TEST 3: Caso Sensible (Salud Mental / Crisis) ---")
    r3 = send_team_lead_alert(
        coder_name="Andrés Mendoza",
        route="Python Data - Clan Turing",
        novelty_type="salud_mental_crisis",
        radicado_id="just-demo-003",
        status="REVISION_MANUAL",
        details="Crisis de ansiedad y colapso emocional. Solicita confidencialidad. Requiere HSE.",
        is_sensitive=True,
    )
    assert r3["success"] is True, f"Error en Test 3: {r3}"
    print(f"Resultado Test 3: {r3}")

    # Test 4: Verificación de estructura de payload Discord
    print("\n--- TEST 4: Verificación Estructura Embed Discord ---")
    payload = build_discord_payload(
        coder_name="Test Coder",
        route="Test Route",
        novelty_type="incapacidad_medica",
        radicado_id="just-test-004",
        status="APPROVED",
        is_sensitive=False,
    )
    assert "embeds" in payload
    assert payload["embeds"][0]["color"] == COLOR_GREEN_DECIMAL
    print("Payload Discord generado correctamente con color verde.")

    # Test 5: Manejo Resiliente ante URL inválida (no debe levantar excepción)
    print("\n--- TEST 5: Resiliencia ante Webhook Fallido ---")
    r5 = send_team_lead_alert(
        coder_name="Test Coder Resiliencia",
        route="Test Route",
        novelty_type="test",
        radicado_id="just-test-005",
        status="APPROVED",
        webhook_url="http://127.0.0.1:59999/webhook-no-existente",
        timeout=0.5,
    )
    assert r5["success"] is False
    assert r5["mode"] in ("WEBHOOK_EXCEPTION", "WEBHOOK_HTTP_ERROR")
    print("Manejo de excepción resiliente verificado exitosamente (no rompe el hilo).")

    print("\n" + "=" * 70)
    print("✨ Todos los tests independientes de discord_alerts completados exitosamente.")
    print("=" * 70 + "\n")
