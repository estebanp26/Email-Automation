import time
from typing import Dict, Any

class SpeedProfiler:
    """High-resolution profiler for measuring engine execution times."""
    def __init__(self):
        self.start_time = time.perf_counter()
        self.timings: Dict[str, float] = {}
        self._current_lap = None

    def start_lap(self, name: str):
        self.timings[f"_start_{name}"] = time.perf_counter()

    def end_lap(self, name: str) -> float:
        start_key = f"_start_{name}"
        if start_key in self.timings:
            elapsed = time.perf_counter() - self.timings.pop(start_key)
            self.timings[name] = round(elapsed, 4)
            return elapsed
        return 0.0

    def total_elapsed(self) -> float:
        return round(time.perf_counter() - self.start_time, 4)

    def summary(self, total_pages: int = 0) -> Dict[str, Any]:
        total = self.total_elapsed()
        pages_per_sec = round(total_pages / total, 2) if total > 0 and total_pages > 0 else 0.0
        return {
            "total_seconds": total,
            "total_ms": round(total * 1000, 1),
            "pages_processed": total_pages,
            "pages_per_second": pages_per_sec,
            "breakdown": {k: v for k, v in self.timings.items() if not k.startswith("_")}
        }


class LiveMetricsTracker:
    """Thread-safe live telemetry tracker for Strata Core."""
    def __init__(self):
        self._boot_time = time.time()
        self._total_requests = 0
        self._approved_auto = 0
        self._rejected_auto = 0
        self._manual_reviews = 0
        self._latencies = []
        self._by_type = {}
        self._last_evaluated_at = None

    def record_evaluation(self, valido: bool, manual: bool, tipo: str, latency: float):
        self._total_requests += 1
        self._latencies.append(latency)
        if len(self._latencies) > 200:
            self._latencies.pop(0)

        if manual:
            self._manual_reviews += 1
        elif valido:
            self._approved_auto += 1
        else:
            self._rejected_auto += 1

        self._by_type[tipo] = self._by_type.get(tipo, 0) + 1
        self._last_evaluated_at = time.strftime("%Y-%m-%d %H:%M:%S")

    def get_stats(self) -> Dict[str, Any]:
        uptime_sec = round(time.time() - self._boot_time, 1)
        avg_lat = round(sum(self._latencies) / len(self._latencies), 2) if self._latencies else 0.0
        sorted_lat = sorted(self._latencies) if self._latencies else []
        p50 = round(sorted_lat[len(sorted_lat) // 2], 2) if sorted_lat else 0.0
        p95 = round(sorted_lat[int(len(sorted_lat) * 0.95)], 2) if sorted_lat else 0.0

        return {
            "service": "Strata Core HSE Engine",
            "status": "online",
            "uptime_seconds": uptime_sec,
            "total_evaluaciones": self._total_requests,
            "distribucion_veredictos": {
                "aprobadas_auto": self._approved_auto,
                "rechazadas_auto": self._rejected_auto,
                "revision_manual": self._manual_reviews,
                "tasa_aprobacion_pct": round((self._approved_auto / self._total_requests) * 100, 1) if self._total_requests > 0 else 0.0
            },
            "distribucion_tipos": self._by_type,
            "latencia_metricas": {
                "media_segundos": avg_lat,
                "p50_segundos": p50,
                "p95_segundos": p95,
                "muestras_recientes": len(self._latencies)
            },
            "ultima_evaluacion_timestamp": self._last_evaluated_at
        }


metrics_tracker = LiveMetricsTracker()
