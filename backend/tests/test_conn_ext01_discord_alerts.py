"""
Tests de Integración y Resiliencia para CONN-EXT-01:
Notificador en Tiempo Real a Discord / Slack para Alertas HSE.
"""

import unittest
from unittest.mock import patch, MagicMock
import base64

from backend.app.services.discord_alerts import (
    send_team_lead_alert,
    get_status_visuals,
    build_discord_payload,
    build_slack_payload,
    COLOR_GREEN_DECIMAL,
    COLOR_ORANGE_DECIMAL,
    COLOR_RED_DECIMAL,
)
from backend.app.services.orchestrator import orchestrator
from backend.app.schemas.email import RawEmailInput, RawAttachmentInput


class TestDiscordAlerts(unittest.TestCase):
    """Batería de pruebas unitarias y de resiliencia para el servicio de alertas Discord/Slack."""

    def test_status_color_and_visual_mapping(self):
        """Valida que los colores semánticos cumplan los lineamientos (Verde, Naranja, Rojo)."""
        # 1. Aprobado -> Verde
        c_dec, c_hex, tag, emoji = get_status_visuals("APPROVED")
        self.assertEqual(c_dec, COLOR_GREEN_DECIMAL)
        self.assertEqual(c_hex, "#2ECC71")
        self.assertIn("APROBADO", tag)
        self.assertEqual(emoji, "✅")

        # 2. Pendiente / Revisión Manual -> Naranja
        c_dec, c_hex, tag, emoji = get_status_visuals("REVISION_MANUAL")
        self.assertEqual(c_dec, COLOR_ORANGE_DECIMAL)
        self.assertEqual(c_hex, "#E67E22")
        self.assertIn("PENDIENTE", tag)
        self.assertEqual(emoji, "⚠️")

        # 3. Rechazado -> Rojo
        c_dec, c_hex, tag, emoji = get_status_visuals("DISAPPROVED")
        self.assertEqual(c_dec, COLOR_RED_DECIMAL)
        self.assertEqual(c_hex, "#E74C3C")
        self.assertIn("NO JUSTIFICADO", tag)
        self.assertEqual(emoji, "❌")

        # 4. Caso Sensible (prioridad máxima) -> Rojo urgente
        c_dec, c_hex, tag, emoji = get_status_visuals("APPROVED", is_sensitive=True)
        self.assertEqual(c_dec, COLOR_RED_DECIMAL)
        self.assertIn("CASO SENSIBLE", tag)
        self.assertEqual(emoji, "🚨")

    def test_build_discord_payload_structure(self):
        """Verifica la estructura del Embed de Discord conforme a la API de Webhooks."""
        payload = build_discord_payload(
            coder_name="Carlos Pérez",
            route="Clan Gosling",
            novelty_type="incapacidad_medica",
            radicado_id="just-12345",
            status="APPROVED",
            details="EPS Sura 2 días",
            is_sensitive=False,
        )

        self.assertIn("username", payload)
        self.assertIn("embeds", payload)
        self.assertEqual(len(payload["embeds"]), 1)

        embed = payload["embeds"][0]
        self.assertEqual(embed["color"], COLOR_GREEN_DECIMAL)
        self.assertIn("Convalidada", embed["title"])
        self.assertTrue(any(f["name"] == "👤 Coder" and f["value"] == "Carlos Pérez" for f in embed["fields"]))
        self.assertTrue(any(f["name"] == "🚀 Ruta / Clan" and f["value"] == "Clan Gosling" for f in embed["fields"]))
        self.assertTrue(any(f["name"] == "🆔 Radicado ID" and "`just-12345`" in f["value"] for f in embed["fields"]))
        self.assertTrue(any(f["name"] == "📝 Observaciones" and "EPS Sura" in f["value"] for f in embed["fields"]))
        self.assertIn("timestamp", embed)

    def test_build_slack_payload_structure(self):
        """Verifica la estructura de attachments para compatibilidad con Slack."""
        payload = build_slack_payload(
            coder_name="Laura Gómez",
            route="Clan Lovelace",
            novelty_type="calamidad_domestica",
            radicado_id="just-67890",
            status="REVISION_MANUAL",
            details="Fallecimiento de familiar directo",
            is_sensitive=True,
        )

        self.assertIn("text", payload)
        self.assertIn("attachments", payload)
        att = payload["attachments"][0]
        self.assertEqual(att["color"], "#E74C3C")
        self.assertIn("Laura Gómez", att["text"])
        self.assertIn("Clan Lovelace", att["text"])

    def test_dev_console_mode_without_webhook(self):
        """Si no hay webhook configurado, debe registrar en consola sin fallar."""
        res = send_team_lead_alert(
            coder_name="Coder Prueba",
            route="Clan Turing",
            novelty_type="incapacidad_medica",
            radicado_id="just-test-dev",
            status="APPROVED",
            webhook_url="",
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "DEV_CONSOLE")
        self.assertEqual(res["radicado_id"], "just-test-dev")

    @patch("backend.app.services.discord_alerts.httpx.Client")
    def test_webhook_dispatch_success_discord(self, mock_client_cls):
        """Simula respuesta 204 No Content de Discord Webhook."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__.return_value = mock_client

        res = send_team_lead_alert(
            coder_name="Jose Acevedo",
            route="Node.js Backend",
            novelty_type="incapacidad_medica",
            radicado_id="just-mock-204",
            status="APPROVED",
            webhook_url="https://discord.com/api/webhooks/12345/abcdef",
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "WEBHOOK_DISPATCHED")
        self.assertEqual(res["status_code"], 204)

    def test_resilience_on_network_timeout_or_error(self):
        """Verifica que ante errores de red o timeout no se levanten excepciones."""
        res = send_team_lead_alert(
            coder_name="Coder Resiliente",
            route="Clan Gosling",
            novelty_type="test",
            radicado_id="just-fail-999",
            status="APPROVED",
            webhook_url="http://127.0.0.1:59998/simulated-down-endpoint",
            timeout=0.3,
        )
        # Debe capturar la excepción y responder success=False sin romper el hilo
        self.assertFalse(res["success"])
        self.assertIn(res["mode"], ("WEBHOOK_EXCEPTION", "WEBHOOK_HTTP_ERROR"))

    def test_orchestrator_integration_triggers_alert(self):
        """Verifica que el orquestador active el notificador al procesar una justificación."""
        raw_email = RawEmailInput(
            source_provider="OUTLOOK",
            sender_email="jose.acevedo@riwi.io",
            sender_name="Jose Luis Acevedo",
            recipient_email="tl@riwi.io",
            cc_emails=["formacion.barranquilla@riwi.io"],
            subject="Incapacidad médica 28 y 29 de septiembre",
            body="Buenas tardes, adjunto incapacidad EPS Sura. CC 1000000001.",
            attachments=[
                RawAttachmentInput(
                    filename="incapacidad_eps_sura.pdf",
                    mime_type="application/pdf",
                    data_base64=base64.b64encode(b"%PDF-1.4 Dummy PDF").decode("utf-8")
                )
            ]
        )

        result = orchestrator.process_pipeline(raw_email)
        self.assertEqual(result.execution_status, "COMPLETED")
        self.assertIsNotNone(result.justification)
        # Verificar que en las notas del pipeline figure el despacho
        self.assertTrue(any("CONN-EXT-01" in note for note in result.notes))
