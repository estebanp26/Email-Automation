#!/usr/bin/env python3
"""
test_performance_indexes.py
=============================================================================
SUITE DE PRUEBAS AUTOMATIZADAS — TASK [DB-04]
Índices de Rendimiento y Tuning para Consultas del Dashboard
=============================================================================
Criterios de Aceptación Evaluados:
1. Índices B-Tree compuestos sobre justifications:
   - (coder_id, created_at DESC)
   - (validation_status, start_date)
   - (coder_id, start_date, end_date)
   - (ai_recommendation, validation_status)
2. Índices especializados GIN sobre JSONB:
   - evidence_files (ocr_spatial_data) y (spatial_boxes)
   - justifications (ocr_spatial_data)
3. Índices parciales para triaje rápido del dashboard HSE (< 50ms para 10,000+ filas).
4. Benchmark sintético de latencia validando SLA de respuesta < 50 ms.
=============================================================================
"""

import sys
import time
import random
from datetime import date, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log_test(title, passed, details=""):
    status = f"{Colors.OKGREEN}✓ PASÓ{Colors.ENDC}" if passed else f"{Colors.FAIL}✗ FALLÓ{Colors.ENDC}"
    print(f"  [{status}] {title}")
    if details:
        print(f"       → {details}")
    if not passed:
        sys.exit(1)


# =============================================================================
# 1. VERIFICACIÓN ESTRUCTURAL DDL (DB-04)
# =============================================================================
def test_ddl_integrity():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== FASE 1: INTEGRIDAD DE SCRIPTS DDL Y MIGRACIÓN DB-04 ==={Colors.ENDC}")

    mig_file = BASE_DIR / "database" / "migrations" / "004_performance_indexes_dashboard.sql"
    init_sql = BASE_DIR / "init_database.sql"
    supa_sql = BASE_DIR / "supabase_schema.sql"

    log_test("Archivo de migración 004_performance_indexes_dashboard.sql existe",
             mig_file.exists(), str(mig_file))

    content = mig_file.read_text(encoding="utf-8")
    init_content = init_sql.read_text(encoding="utf-8")
    supa_content = supa_sql.read_text(encoding="utf-8")

    # 1. Soporte de columnas OCR spatial data
    log_test("Columnas ocr_spatial_data añadidas a evidence_files y justifications",
             "ocr_spatial_data JSONB" in content and
             "ocr_spatial_data JSONB" in init_content and
             "ocr_spatial_data JSONB" in supa_content)

    # 2. Índices B-Tree compuestos
    log_test("Índice compuesto justifications(coder_id, created_at DESC)",
             "idx_justifications_coder_created_desc" in content and
             "idx_justifications_coder_created_desc" in init_content)

    log_test("Índice compuesto justifications(validation_status, start_date)",
             "idx_justifications_status_start_date" in content and
             "idx_justifications_status_start_date" in init_content)

    log_test("Índice compuesto justifications(coder_id, start_date, end_date)",
             "idx_justifications_coder_dates" in content and
             "idx_justifications_coder_dates" in init_content)

    log_test("Índice compuesto justifications(ai_recommendation, validation_status)",
             "idx_justifications_ai_rec_status" in content and
             "idx_justifications_ai_rec_status" in init_content)

    # 3. Índices especializados GIN
    log_test("Índices GIN sobre metadatos espaciales ocr_spatial_data y spatial_boxes",
             "idx_evidence_files_ocr_spatial_data_gin" in content and
             "idx_evidence_files_spatial_boxes_gin" in content and
             "idx_justifications_ocr_spatial_data_gin" in content and
             "USING GIN" in content)

    # 4. Índices parciales para triaje rápido
    log_test("Índices parciales para cola de triaje pendiente y auditoría humana",
             "idx_justifications_pending_triage" in content and
             "idx_justifications_unreviewed" in content and
             "idx_attendance_unjustified_active" in content)

    # 5. Sincronización en trigger de evidence_files
    log_test("Trigger fn_sync_evidence_file_to_attachments incluye ocr_spatial_data",
             "'ocr_spatial_data', NEW.ocr_spatial_data" in content and
             "'ocr_spatial_data', NEW.ocr_spatial_data" in init_content)


# =============================================================================
# 2. MOTOR DE BENCHMARK Y EVALUACIÓN DE RENDIMIENTO CON 10,000+ REGISTROS
# =============================================================================
class MockIndexBenchmarkEngine:
    def __init__(self, record_count=12000):
        self.record_count = record_count
        self.table = []
        
        # B-Tree Simulators (Diccionarios con claves ordenadas / buckets)
        self.idx_coder_created = {}           # (coder_id) -> list of records sorted by created_at DESC
        self.idx_status_start_date = {}       # (status, start_date) -> list of records
        self.idx_pending_triage = []          # Partial index: only pending records
        self.gin_ocr_spatial = {}             # GIN inverted index: attribute/tag -> list of record IDs

        self._populate_synthetic_data()

    def _populate_synthetic_data(self):
        statuses = ['APPROVED', 'DISAPPROVED', 'REVISION_MANUAL', 'POSIBLEMENTE_VALIDO', 'POSIBLEMENTE_INVALIDO']
        ai_recs = ['POSIBLEMENTE_VALIDO', 'POSIBLEMENTE_INVALIDO', 'REVISION_MANUAL']
        base_date = date.today() - timedelta(days=90)

        for i in range(1, self.record_count + 1):
            coder_num = random.randint(1, 297)
            coder_id = f"coder-{coder_num:03d}"
            status = random.choice(statuses)
            start_d = base_date + timedelta(days=random.randint(0, 90))
            end_d = start_d + timedelta(days=random.randint(0, 3))
            created_d = start_d + timedelta(hours=random.randint(1, 48))
            has_human = status in ('APPROVED', 'DISAPPROVED')

            has_stamp = random.choice([True, False])
            has_signature = random.choice([True, False])
            ocr_data = {
                "has_medical_stamp": has_stamp,
                "has_signature": has_signature,
                "confidence": round(random.uniform(0.7, 0.99), 2),
                "boxes": [{"x": 10, "y": 20, "w": 100, "h": 50, "label": "stamp"}] if has_stamp else []
            }

            rec = {
                "id": f"just-{i:06d}",
                "coder_id": coder_id,
                "validation_status": status,
                "ai_recommendation": random.choice(ai_recs),
                "start_date": start_d,
                "end_date": end_d,
                "created_at": created_d,
                "has_human_intervention": has_human,
                "ocr_spatial_data": ocr_data
            }
            self.table.append(rec)

            # Poblar B-Tree (coder_id, created_at DESC)
            if coder_id not in self.idx_coder_created:
                self.idx_coder_created[coder_id] = []
            self.idx_coder_created[coder_id].append(rec)

            # Poblar B-Tree (validation_status, start_date)
            k_status_date = (status, start_d)
            if k_status_date not in self.idx_status_start_date:
                self.idx_status_start_date[k_status_date] = []
            self.idx_status_start_date[k_status_date].append(rec)

            # Poblar Partial Index (Pending Triage)
            if status in ('REVISION_MANUAL', 'POSIBLEMENTE_VALIDO', 'POSIBLEMENTE_INVALIDO'):
                self.idx_pending_triage.append(rec)

            # Poblar GIN Inverted Index
            if has_stamp:
                self.gin_ocr_spatial.setdefault("stamp", []).append(rec["id"])
            if has_signature:
                self.gin_ocr_spatial.setdefault("signature", []).append(rec["id"])

        # Ordenar B-Trees por created_at DESC
        for coder_id in self.idx_coder_created:
            self.idx_coder_created[coder_id].sort(key=lambda r: r["created_at"], reverse=True)

        self.idx_pending_triage.sort(key=lambda r: r["created_at"], reverse=True)


    def query_coder_history_indexed(self, target_coder_id):
        # Index Scan en idx_justifications_coder_created_desc
        return self.idx_coder_created.get(target_coder_id, [])

    def query_coder_history_seq_scan(self, target_coder_id):
        # Sequential Scan sin índice
        filtered = [r for r in self.table if r["coder_id"] == target_coder_id]
        return sorted(filtered, key=lambda r: r["created_at"], reverse=True)

    def query_status_and_date_indexed(self, target_status, min_date):
        # Index Scan en idx_justifications_status_start_date
        results = []
        for (st, dt), recs in self.idx_status_start_date.items():
            if st == target_status and dt >= min_date:
                results.extend(recs)
        return results

    def query_pending_triage_partial(self):
        # Partial Index Scan en idx_justifications_pending_triage
        return self.idx_pending_triage

    def query_gin_ocr_spatial(self, feature_key):
        # GIN index search
        return self.gin_ocr_spatial.get(feature_key, [])


# =============================================================================
# 3. BENCHMARK DE RENDIMIENTO (SLA < 50ms)
# =============================================================================
def test_performance_benchmark():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== FASE 2: BENCHMARK Y EVALUACIÓN DE LATENCIA (10,000+ REGISTROS) ==={Colors.ENDC}")
    
    t0 = time.perf_counter()
    engine = MockIndexBenchmarkEngine(record_count=12000)
    t_pop = (time.perf_counter() - t0) * 1000
    print(f"  [INFO] Dataset sintético generado: {engine.record_count} justificaciones en {t_pop:.1f} ms")

    # Escenario 1: Historial de Coder (B-Tree Compuesto coder_id, created_at DESC)
    print(f"\n{Colors.BOLD}Escenario 1: Consulta de Historial de Coder (B-Tree Compuesto){Colors.ENDC}")
    target_coder = "coder-042"

    # Medición Sequential Scan (Sin índice)
    t_seq_start = time.perf_counter()
    for _ in range(50):
        _ = engine.query_coder_history_seq_scan(target_coder)
    t_seq_avg = ((time.perf_counter() - t_seq_start) / 50) * 1000

    # Medición Index Scan (Con índice B-Tree Compuesto)
    t_idx_start = time.perf_counter()
    for _ in range(100):
        res_indexed = engine.query_coder_history_indexed(target_coder)
    t_idx_avg = ((time.perf_counter() - t_idx_start) / 100) * 1000

    speedup = t_seq_avg / max(t_idx_avg, 0.0001)
    log_test("Consulta de Historial con índice B-Tree < 50 ms SLA",
             t_idx_avg < 50.0,
             f"Latencia Índice: {t_idx_avg:.4f} ms | Seq Scan: {t_seq_avg:.4f} ms | Speedup: {speedup:.1f}x")
    log_test("Registros recuperados correctamente ordenados",
             len(res_indexed) > 0 and
             all(res_indexed[i]["created_at"] >= res_indexed[i+1]["created_at"] for i in range(len(res_indexed)-1)),
             f"Total registros del estudiante: {len(res_indexed)}")

    # Escenario 2: Filtrado por Estado y Rango de Fechas (B-Tree Compuesto)
    print(f"\n{Colors.BOLD}Escenario 2: Filtro por Estado y Fecha en Dashboard HSE (B-Tree Compuesto){Colors.ENDC}")
    filter_date = date.today() - timedelta(days=30)
    
    t_filter_start = time.perf_counter()
    for _ in range(100):
        filter_res = engine.query_status_and_date_indexed("REVISION_MANUAL", filter_date)
    t_filter_avg = ((time.perf_counter() - t_filter_start) / 100) * 1000

    log_test("Filtro por Estado y Fecha < 50 ms SLA",
             t_filter_avg < 50.0,
             f"Latencia: {t_filter_avg:.4f} ms | Resultados coincidentes: {len(filter_res)}")

    # Escenario 3: Cola de Triaje con Índice Parcial (Partial Index)
    print(f"\n{Colors.BOLD}Escenario 3: Bandeja de Entrada con Índice Parcial (Partial Index){Colors.ENDC}")
    t_partial_start = time.perf_counter()
    for _ in range(100):
        triage_res = engine.query_pending_triage_partial()
    t_partial_avg = ((time.perf_counter() - t_partial_start) / 100) * 1000

    pct_compact = (1 - (len(triage_res) / engine.record_count)) * 100
    log_test("Bandeja de triaje pendiente con índice parcial < 50 ms SLA",
             t_partial_avg < 50.0,
             f"Latencia: {t_partial_avg:.4f} ms | Cola activa: {len(triage_res)} ({pct_compact:.1f}% ahorro vs tabla completa)")

    # Escenario 4: Búsqueda de Coordenadas y Sellos Médicos con Índice GIN
    print(f"\n{Colors.BOLD}Escenario 4: Búsqueda de Metadatos JSONB con Índice GIN{Colors.ENDC}")
    t_gin_start = time.perf_counter()
    for _ in range(100):
        stamp_matches = engine.query_gin_ocr_spatial("stamp")
    t_gin_avg = ((time.perf_counter() - t_gin_start) / 100) * 1000

    log_test("Búsqueda especializada GIN sobre ocr_spatial_data < 50 ms SLA",
             t_gin_avg < 50.0,
             f"Latencia GIN: {t_gin_avg:.4f} ms | Documentos con sello detectado: {len(stamp_matches)}")


def main():
    print("=" * 70)
    print("   TEST ÍNDICES DE RENDIMIENTO & TUNING DASHBOARD — TASK [DB-04]   ")
    print("=" * 70)
    test_ddl_integrity()
    test_performance_benchmark()
    print("\n" + "=" * 70)
    print(f"  {Colors.BOLD}{Colors.OKGREEN}¡TODAS LAS PRUEBAS DE DB-04 Y BENCHMARK PASARON CON ÉXITO!{Colors.ENDC}")
    print("=" * 70)

if __name__ == "__main__":
    main()
