#!/usr/bin/env python3
"""
NOVA Auto-Optimize Scheduler
Ejecuta optimización automática cada 24 horas y limpia caché cuando cambian perfiles
"""

import time
import logging
import requests
from pathlib import Path
from nova.core.auto_optimizer import auto_optimize
from nova.core.memoria import init_db
from nova.core.cache_system import cache_system

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/auto_optimize_scheduler.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class AutoOptimizeScheduler:
    def __init__(self, interval_hours=24, api_url="http://localhost:8000"):
        self.interval_hours = interval_hours
        self.interval_seconds = interval_hours * 3600
        self.api_url = api_url
        self.running = False
        self.last_profile_check = None
        self.profile_hash = None

        # Asegurar que existe el directorio de logs
        Path("logs").mkdir(exist_ok=True)

    def get_profile_hash(self):
        """Obtener hash del archivo de perfiles para detectar cambios"""
        try:
            profile_file = Path("models/model_profiles.json")
            if profile_file.exists():
                content = profile_file.read_text()
                return hash(content)
            return None
        except Exception as e:
            logger.error(f"Error leyendo perfiles: {e}")
            return None

    def check_profile_changes(self):
        """Verificar si los perfiles han cambiado"""
        current_hash = self.get_profile_hash()
        if self.profile_hash is None:
            self.profile_hash = current_hash
            return False

        if current_hash != self.profile_hash:
            logger.info("🔄 Perfiles cambiaron, invalidando caché")
            self.profile_hash = current_hash
            return True

        return False

    def invalidate_cache_if_needed(self):
        """Invalidar caché si los perfiles cambiaron"""
        if self.check_profile_changes():
            try:
                cache_system.invalidate_all()
                logger.info("✅ Caché invalidado por cambio de perfiles")
            except Exception as e:
                logger.error(f"❌ Error invalidando caché: {e}")

    def run_optimization(self):
        """Ejecutar ciclo de optimización"""
        try:
            logger.info("🚀 Iniciando optimización automática...")

            # Ejecutar optimización
            result = auto_optimize(max_change=20, min_feedback=5)

            if result["status"] == "optimized":
                changes = len(result.get("changes_applied", []))
                logger.info(f"✅ Optimización completada: {changes} cambios aplicados")

                # Log de cambios específicos
                for change in result.get("changes_applied", []):
                    logger.info(
                        f"   {change['model']}: {change['old_priority']} → {change['new_priority']}"
                    )

            elif result["status"] == "insufficient_feedback":
                logger.info("📭 Optimización omitida: feedback insuficiente")

            else:
                logger.info(f"📊 Estado optimización: {result['status']}")

        except Exception as e:
            logger.error(f"❌ Error en optimización automática: {e}")

    def start_auto_tuning_service(self):
        """Iniciar servicio de auto-tuning via API"""
        try:
            response = requests.post(
                f"{self.api_url}/auto-tuning/start", json={"interval_minutes": 30}
            )
            if response.status_code == 200:
                logger.info("🎯 Servicio de auto-tuning iniciado (30 min intervals)")
            else:
                logger.warning(
                    f"⚠️ No se pudo iniciar auto-tuning service: {response.text}"
                )
        except Exception as e:
            logger.error(f"❌ Error iniciando auto-tuning service: {e}")

    def run_scheduler(self):
        """Ejecutar el scheduler principal"""
        logger.info(
            f"🔄 Iniciando scheduler de auto-optimización (cada {self.interval_hours}h)"
        )

        # Inicializar base de datos
        init_db()

        # Iniciar servicio de auto-tuning
        self.start_auto_tuning_service()

        self.running = True

        while self.running:
            try:
                # Verificar cambios en perfiles e invalidar caché si necesario
                self.invalidate_cache_if_needed()

                # Ejecutar optimización
                self.run_optimization()

                # Esperar hasta el próximo ciclo
                logger.info(f"⏰ Próxima optimización en {self.interval_hours} horas")
                time.sleep(self.interval_seconds)

            except KeyboardInterrupt:
                logger.info("🛑 Scheduler detenido por usuario")
                self.running = False
            except Exception as e:
                logger.error(f"❌ Error en scheduler: {e}")
                # Esperar un poco antes de reintentar
                time.sleep(300)  # 5 minutos

        logger.info("🏁 Scheduler finalizado")


def main():
    # Crear directorio de logs si no existe
    Path("logs").mkdir(exist_ok=True)

    # Iniciar scheduler
    scheduler = AutoOptimizeScheduler(interval_hours=24)
    scheduler.run_scheduler()


if __name__ == "__main__":
    main()
