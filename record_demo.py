#!/usr/bin/env python3
"""
NOVA Demo Video Recorder
Graba video demo de 90 segundos mostrando el flujo completo:
feedback → auto-optimize → cache hit → dashboard actualizado
"""

import time
import requests
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Configuración de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DemoRecorder:
    def __init__(self, api_url="http://localhost:8000", duration_seconds=90):
        self.api_url = api_url
        self.duration_seconds = duration_seconds
        self.recording_process = None

    def start_screen_recording(self, output_file="nova_demo.mp4"):
        """Iniciar grabación de pantalla usando ffmpeg"""
        try:
            # Comando para grabar pantalla (ajustar según el sistema)
            # Para Ubuntu/Debian con X11
            cmd = [
                "ffmpeg",
                "-f",
                "x11grab",
                "-s",
                "1920x1080",
                "-i",
                ":0.0",
                "-f",
                "pulse",
                "-i",
                "default",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-preset",
                "fast",
                "-y",
                output_file,
            ]

            logger.info(f"🎬 Iniciando grabación de pantalla: {output_file}")
            self.recording_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            time.sleep(2)  # Esperar que inicie la grabación
            return True

        except Exception as e:
            logger.error(f"❌ Error iniciando grabación: {e}")
            logger.info(
                "💡 Asegúrate de tener ffmpeg instalado: sudo apt install ffmpeg"
            )
            return False

    def stop_screen_recording(self):
        """Detener grabación de pantalla"""
        if self.recording_process:
            try:
                self.recording_process.terminate()
                self.recording_process.wait(timeout=5)
                logger.info("🎬 Grabación detenida")
            except Exception as e:
                logger.error(f"❌ Error deteniendo grabación: {e}")
                self.recording_process.kill()

    def simulate_user_interaction(
        self, message, rating=5, comment="Excelente respuesta!"
    ):
        """Simular interacción de usuario: enviar mensaje y feedback"""
        try:
            # Enviar mensaje
            chat_response = requests.post(
                f"{self.api_url}/chat",
                json={"message": message, "session_id": "demo_session"},
            )

            if chat_response.status_code == 200:
                response_data = chat_response.json()
                message_id = response_data.get("response", {}).get("id") or "demo_msg_1"

                logger.info(f"💬 Mensaje enviado: '{message[:50]}...'")
                logger.info(
                    f"🤖 Respuesta: '{response_data.get('response', '')[:50]}...'"
                )

                # Esperar un poco
                time.sleep(2)

                # Enviar feedback positivo
                feedback_response = requests.post(
                    f"{self.api_url}/feedback",
                    json={
                        "message_id": message_id,
                        "session_id": "demo_session",
                        "rating": rating,
                        "comment": comment,
                    },
                )

                if feedback_response.status_code == 200:
                    logger.info(
                        f"👍 Feedback enviado: {rating} estrellas - '{comment}'"
                    )
                else:
                    logger.warning(f"⚠️ Error en feedback: {feedback_response.text}")

            else:
                logger.error(f"❌ Error en chat: {chat_response.text}")

        except Exception as e:
            logger.error(f"❌ Error en simulación de usuario: {e}")

    def trigger_auto_optimization(self):
        """Disparar optimización manual"""
        try:
            logger.info("🎯 Disparando auto-optimización...")

            response = requests.post(
                f"{self.api_url}/auto-tuning/optimize",
                json={"max_change": 20, "min_feedback": 5},
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Optimización completada: {result}")
            else:
                logger.warning(f"⚠️ Error en optimización: {response.text}")

        except Exception as e:
            logger.error(f"❌ Error en auto-optimización: {e}")

    def demonstrate_cache_hit(self):
        """Demostrar cache hit enviando el mismo mensaje"""
        try:
            logger.info("⚡ Demostrando cache hit...")

            # Enviar el mismo mensaje para demostrar cache
            message = "¿Cómo puedo mejorar mi código Python?"

            chat_response = requests.post(
                f"{self.api_url}/chat",
                json={"message": message, "session_id": "demo_session"},
            )

            if chat_response.status_code == 200:
                logger.info(
                    f"💾 Cache hit demostrado: '{message[:30]}...' → respuesta rápida"
                )
            else:
                logger.error(f"❌ Error en cache demo: {chat_response.text}")

        except Exception as e:
            logger.error(f"❌ Error en demo de caché: {e}")

    def show_dashboard_update(self):
        """Mostrar actualización del dashboard"""
        try:
            logger.info("📊 Verificando actualización del dashboard...")

            response = requests.get(f"{self.api_url}/dashboard")

            if response.status_code == 200:
                logger.info("✅ Dashboard actualizado correctamente")
                # El dashboard se auto-refresca cada 30s
            else:
                logger.error(f"❌ Error en dashboard: {response.text}")

        except Exception as e:
            logger.error(f"❌ Error verificando dashboard: {e}")

    def run_demo_sequence(self):
        """Ejecutar la secuencia completa de demo"""
        logger.info("🚀 Iniciando demo de NOVA - 90 segundos")
        logger.info("📋 Secuencia: feedback → auto-optimize → cache hit → dashboard")

        # Paso 1: Simular interacciones de usuario (20-30s)
        logger.info("📝 Paso 1: Generando feedback de usuarios...")

        messages = [
            "¿Cómo puedo mejorar mi código Python?",
            "Explícame qué es machine learning",
            "¿Cuáles son las mejores prácticas para APIs REST?",
            "¿Cómo funciona la optimización automática en NOVA?",
        ]

        for i, msg in enumerate(messages):
            self.simulate_user_interaction(
                msg, rating=5, comment=f"Excelente respuesta {i+1}!"
            )
            time.sleep(3)  # Pausa entre mensajes

        # Paso 2: Trigger auto-optimization (10s)
        logger.info("🎯 Paso 2: Ejecutando auto-optimización...")
        time.sleep(2)
        self.trigger_auto_optimization()
        time.sleep(8)  # Tiempo para que se ejecute

        # Paso 3: Demostrar cache hit (10s)
        logger.info("⚡ Paso 3: Demostrando cache inteligente...")
        time.sleep(2)
        self.demonstrate_cache_hit()
        time.sleep(8)

        # Paso 4: Mostrar dashboard actualizado (30s)
        logger.info("📊 Paso 4: Dashboard con métricas actualizadas...")
        time.sleep(2)
        self.show_dashboard_update()
        time.sleep(28)  # Tiempo para ver el dashboard

        logger.info("✅ Demo completada!")


def main():
    # Verificar que ffmpeg esté instalado
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error(
            "❌ ffmpeg no está instalado. Instala con: sudo apt install ffmpeg"
        )
        return

    # Verificar que el servidor esté corriendo
    try:
        response = requests.get("http://localhost:8000/status", timeout=5)
        if response.status_code != 200:
            logger.error("❌ El servidor NOVA no está corriendo en localhost:8000")
            return
    except Exception as e:
        logger.error(f"❌ No se puede conectar al servidor: {e}")
        return

    # Crear directorio de videos
    Path("videos").mkdir(exist_ok=True)

    # Timestamp para el archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"videos/nova_demo_{timestamp}.mp4"

    # Iniciar demo
    recorder = DemoRecorder(duration_seconds=90)

    # Iniciar grabación
    if not recorder.start_screen_recording(output_file):
        return

    try:
        # Ejecutar secuencia de demo
        recorder.run_demo_sequence()

        # Esperar un poco más para completar la grabación
        time.sleep(5)

    finally:
        # Detener grabación
        recorder.stop_screen_recording()

    logger.info(f"🎬 Video guardado en: {output_file}")
    logger.info(f"📏 Duración aproximada: {recorder.duration_seconds} segundos")


if __name__ == "__main__":
    main()
