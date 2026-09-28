#!/usr/bin/env python3
"""
test_live_n8n_database.py
=============================================================================
VALIDACIÓN EN VIVO DE BASE DE DATOS Y CONEXIONES N8N — POSTGRESQL 16 DOCKER
=============================================================================
Prueba las operaciones reales de base de datos contra el esquema DDL v2.1
implementado para n8n y el frontend HSE:
1. Conexión a PostgreSQL en contenedor Docker 'hse-postgres'.
2. Inserción de catálogo de coders y usuarios HSE con password_hash.
3. Ejecución de consultas parametrizadas de cada nodo de n8n.
4. Validación de restricciones de integridad (CHECK constraints).
5. Consulta de la vista analítica v_justifications_dashboard.
=============================================================================
"""

import os
import sys
import json
import uuid
import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "user": os.getenv("POSTGRES_USER", "hse_admin"),
    "password": os.getenv("POSTGRES_PASSWORD", "hse_segura_123"),
    "dbname": os.getenv("POSTGRES_DB", "hse_email_automation"),
}

def log(msg, status="OK"):
    icon = "[✓]" if status == "OK" else "[✗]"
    print(f"  {icon} {msg}")

def main():
    print("=" * 70)
    print("   TEST EN VIVO: BASE DE DATOS N8N V2.1 (POSTGRESQL 16 DOCKER)      ")
    print("=" * 70)

    print("\n[1/5] Conectando a PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    log("Conexión establecida con éxito")

    print("\n[2/5] Sembrando catálogo de Coders y Usuarios HSE...")
    # Insertar Coder de prueba
    coder_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO coders (id, cedula, full_name, email, route, is_active)
        VALUES (%s, '1002345678', 'Santiago Morales', 'santiago.morales@riwi.io', 'Node.js Cloud Native', TRUE)
        ON CONFLICT (email) DO UPDATE SET full_name = EXCLUDED.full_name
        RETURNING id;
    """, (coder_id,))
    coder_row = cur.fetchone()
    real_coder_id = coder_row["id"]
    log(f"Coder 'Santiago Morales' disponible (ID: {str(real_coder_id)[:8]}...)")

    # Insertar Usuario HSE (Paola)
    hse_user_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO hse_users (id, email, password_hash, full_name, role, is_active)
        VALUES (%s, 'paola.tl@riwi.io', '$2b$12$e8Y3yqGczf5RShBrwBpx1234567890abcdef', 'Paola Andrea Martínez', 'TEAM_LEADER', TRUE)
        ON CONFLICT (email) DO UPDATE SET full_name = EXCLUDED.full_name
        RETURNING id;
    """, (hse_user_id,))
    hse_row = cur.fetchone()
    real_hse_id = hse_row["id"]
    log(f"Usuario HSE 'Paola Andrea Martínez' registrada (ID: {str(real_hse_id)[:8]}...)")
    conn.commit()

    print("\n[3/5] Probando consultas de nodos n8n...")

    # Simular Nodo 03: Buscar Coder en DB
    cur.execute("""
        SELECT id AS coder_id, cedula AS coder_cedula, full_name AS coder_full_name, email AS coder_email, route AS coder_route, is_active AS coder_is_active 
        FROM coders 
        WHERE email = %s OR (cedula = %s AND %s <> '') OR (LOWER(full_name) = LOWER(%s) AND %s <> '') 
        LIMIT 1;
    """, ('santiago.morales@riwi.io', '1002345678', '1002345678', 'Santiago Morales', 'Santiago Morales'))
    found_coder = cur.fetchone()
    assert found_coder is not None, "El nodo 03 de n8n debe encontrar al coder"
    log("Nodo 03 (Buscar Coder en DB) resolvió correctamente al coder")

    # Simular Nodo 11A: Insertar Justificación APPROVED
    msg_id_1 = f"msg_{uuid.uuid4().hex[:8]}"
    cur.execute("""
        INSERT INTO justifications (
            coder_id, sender_email, sender_name, email_subject, email_body, email_url,
            message_id, conversation_id, received_at, intent, excuse_type, start_date, end_date,
            ai_confidence, ai_reason, ai_response, coder_identification_status, validation_status,
            resolution_mode, has_human_intervention, validation_notes, attachments
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, NOW(), 'EXCUSA', 'inasistencia_medica', '2026-09-25', '2026-09-26',
            0.96, 'Incapacidad médica EPS Sanitas válida con sello', '{"valido": true}'::jsonb,
            'IDENTIFIED', 'APPROVED', 'AUTOMATIC_AI', FALSE, 'Aprobada automáticamente por IA',
            '[{"filename": "incapacidad.pdf", "mime_type": "application/pdf"}]'::jsonb
        ) RETURNING id;
    """, (
        real_coder_id, 'santiago.morales@riwi.io', 'Santiago Morales',
        'Incapacidad médica 25 y 26 Septiembre', 'Adjunto certificado médico de EPS Sanitas.',
        'https://outlook.office.com/mail/deeplink/read/' + msg_id_1,
        msg_id_1, 'conv_123'
    ))
    approved_id = cur.fetchone()["id"]
    log(f"Nodo 11A (Insertar APPROVED) insertó justificación {str(approved_id)[:8]}...")

    # Simular Nodo 11C: Insertar Justificación MANUAL_INTERACTION
    msg_id_2 = f"msg_{uuid.uuid4().hex[:8]}"
    cur.execute("""
        INSERT INTO justifications (
            coder_id, sender_email, sender_name, email_subject, email_body, email_url,
            message_id, conversation_id, received_at, intent, excuse_type, start_date, end_date,
            ai_confidence, ai_reason, ai_response, coder_identification_status, validation_status,
            resolution_mode, has_human_intervention, validation_notes, attachments
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, NOW(), 'EXCUSA', 'calamidad_domestica', '2026-09-28', '2026-09-28',
            0.80, 'Calamidad familiar reportada sin certificado adjunto', '{"valido": false, "manual": true}'::jsonb,
            'IDENTIFIED', 'MANUAL_INTERACTION', 'AUTOMATIC_AI', FALSE, 'Derivado a revisión manual por falta de soporte',
            '[]'::jsonb
        ) RETURNING id;
    """, (
        real_coder_id, 'santiago.morales@riwi.io', 'Santiago Morales',
        'Inasistencia por calamidad familiar', 'Fallecimiento de familiar cercano, sin adjunto.',
        'https://outlook.office.com/mail/deeplink/read/' + msg_id_2,
        msg_id_2, 'conv_456'
    ))
    manual_id = cur.fetchone()["id"]
    log(f"Nodo 11C (Insertar MANUAL_INTERACTION) insertó justificación {str(manual_id)[:8]}...")

    # Simular Escenario 6: Resolución Manual de Paola desde el Frontend
    cur.execute("""
        UPDATE justifications
        SET validation_status = 'APPROVED',
            resolution_mode = 'MANUAL_HSE',
            has_human_intervention = TRUE,
            hse_user_id = %s,
            hse_decision = 'APPROVED',
            hse_notes = 'Validado telefónicamente con el coder por Paola. Se acepta calamidad.',
            hse_reviewed_at = NOW(),
            start_date = '2026-09-28',
            end_date = '2026-09-29'
        WHERE id = %s
        RETURNING id, validation_status, resolution_mode, has_human_intervention;
    """, (real_hse_id, manual_id))
    updated_row = cur.fetchone()
    assert updated_row["resolution_mode"] == "MANUAL_HSE"
    assert updated_row["has_human_intervention"] is True
    log("Escenario 6: Resolución manual por Team Leader Paola ejecutada exitosamente")

    conn.commit()

    print("\n[4/5] Probando Restricciones de Seguridad (CHECK Constraints)...")
    # Probar que rechaza un resolution_mode inválido
    try:
        cur.execute("UPDATE justifications SET resolution_mode = 'INVALID_MODE' WHERE id = %s;", (manual_id,))
        conn.commit()
        assert False, "Debió fallar por constraint chk_resolution_mode"
    except psycopg2.Error:
        conn.rollback()
        log("Constraint 'chk_resolution_mode' interceptó y bloqueó valor inválido")

    # Probar que rechaza fechas inconsistentes (end_date < start_date)
    try:
        cur.execute("UPDATE justifications SET start_date = '2026-09-30', end_date = '2026-09-20' WHERE id = %s;", (manual_id,))
        conn.commit()
        assert False, "Debió fallar por constraint chk_dates_validity"
    except psycopg2.Error:
        conn.rollback()
        log("Constraint 'chk_dates_validity' (end_date >= start_date) interceptó error de fecha")

    print("\n[5/5] Consultando vista analítica v_justifications_dashboard...")
    cur.execute("""
        SELECT id, validation_status, resolution_mode, has_human_intervention,
               coder_display_name, coder_cedula, coder_route, email_subject,
               total_days, hse_reviewer_name, hse_reviewer_email, has_attachments
        FROM v_justifications_dashboard
        ORDER BY created_at DESC
        LIMIT 5;
    """)
    rows = cur.fetchall()
    log(f"Vista v_justifications_dashboard retornó {len(rows)} filas con éxito")
    for r in rows:
        print(f"    • [{r['validation_status']}] {r['coder_display_name']} ({r['coder_route']}) | Modo: {r['resolution_mode']} | Intervención humana: {r['has_human_intervention']} | Revisó: {r['hse_reviewer_name'] or 'N/A'}")

    conn.close()
    print("\n" + "=" * 70)
    print("  ¡PRUEBA EN VIVO DE BASE DE DATOS Y FLUJO N8N 100% EXITOSA!      ")
    print("=" * 70)
    return 0

if __name__ == "__main__":
    sys.exit(main())
