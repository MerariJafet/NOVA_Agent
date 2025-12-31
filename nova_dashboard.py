#!/usr/bin/env python3
"""
NOVA Dashboard - Monitor visual en tiempo real
Muestra lo que NOVA está pensando, diciendo y haciendo
"""

import sys
import os
import time
import requests
from datetime import datetime

from nova.core.cache_system import cache_system

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# Colores ANSI para terminal
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def clear_screen():
    """Limpiar pantalla"""
    os.system("clear" if os.name == "posix" else "cls")


def print_logo():
    """Mostrar logo ASCII de NOVA"""
    logo = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗            ║
║                ████╗  ██║██╔═══██╗██║   ██║██╔══██╗           ║
║                ██╔██╗ ██║██║   ██║██║   ██║███████║           ║
║                ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║           ║
║                ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║           ║
║                ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝           ║
║                                                              ║
║              🤖 SISTEMA DE AUTO-OPTIMIZACIÓN 🤖              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}"""
    print(logo)


def get_status():
    """Obtener estado del sistema"""
    try:
        response = requests.get("http://localhost:8010/auto-tuning/status", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def format_priority_bar(priority, max_priority=100):
    """Crear barra visual de priority"""
    filled = int((priority / max_priority) * 20)
    empty = 20 - filled

    if priority >= 90:
        color = Colors.GREEN
        emoji = "⭐⭐⭐⭐⭐"
    elif priority >= 70:
        color = Colors.CYAN
        emoji = "⭐⭐⭐⭐"
    elif priority >= 50:
        color = Colors.YELLOW
        emoji = "⭐⭐⭐"
    elif priority >= 30:
        color = Colors.MAGENTA
        emoji = "⭐⭐"
    else:
        color = Colors.RED
        emoji = "⭐"

    bar = f"{color}{'█' * filled}{Colors.END}{'░' * empty}"
    return f"{bar} {priority:3d} {emoji}"


def show_brain_activity():
    """Mostrar actividad cerebral de NOVA"""
    status = get_status()
    if not status:
        print(f"{Colors.RED}❌ No se puede conectar al cerebro de NOVA{Colors.END}")
        print(
            f"{Colors.YELLOW}💡 Asegúrate de que el servidor esté corriendo:{Colors.END}"
        )
        print("   uvicorn nova.api.routes:app --host 0.0.0.0 --port 8010")
        return

    print(
        f"{Colors.BOLD}{Colors.BLUE}🧠 CEREBRO DE NOVA - ACTIVIDAD EN TIEMPO REAL{Colors.END}"
    )
    print("=" * 60)

    # Estado del auto-tuning
    active = status["active"]
    cycles = status["stats"]["cycles"]
    status_emoji = "🟢" if active else "🔴"
    status_text = "ACTIVO" if active else "INACTIVO"

    print(f"{Colors.BOLD}Estado del Cerebro:{Colors.END} {status_emoji} {status_text}")
    print(f"{Colors.BOLD}Ciclos de Pensamiento:{Colors.END} {cycles}")

    if status["stats"]["last_run"]:
        last_run_time = datetime.fromtimestamp(status["stats"]["last_run"]).strftime(
            "%H:%M:%S"
        )
        print(f"{Colors.BOLD}Última Reflexión:{Colors.END} {last_run_time}")
    else:
        print(f"{Colors.BOLD}Última Reflexión:{Colors.END} Nunca")

    print(f"\n{Colors.BOLD}{Colors.GREEN}💭 LO QUE NOVA ESTÁ PENSANDO:{Colors.END}")
    print("-" * 40)

    # Mostrar prioridades como pensamientos
    priorities = status["current_priorities"]
    thoughts = []

    for model, priority in priorities.items():
        if model == "dolphin-mistral:7b":
            if priority >= 90:
                thoughts.append(
                    f"🐬 Dolphin es EXCELENTE ({priority}) - ¡Lo prefiero mucho!"
                )
            else:
                thoughts.append(f"🐬 Dolphin necesita mejorar ({priority})")
        elif model == "claude_code_api":
            if priority <= 10:
                thoughts.append(f"🤖 Claude es MALO ({priority}) - ¡Lo evito!")
            else:
                thoughts.append(f"🤖 Claude está mejorando ({priority})")
        elif model == "mixtral:8x7b":
            thoughts.append(f"🔄 Mixtral es confiable ({priority}) - ¡Buena opción!")
        elif model == "moondream:1.8b":
            thoughts.append(f"🎨 Moondream es perfecto ({priority}) - ¡Para imágenes!")

    for thought in thoughts:
        print(f"  💭 {thought}")

    print(f"\n{Colors.BOLD}{Colors.YELLOW}🎯 LO QUE NOVA ESTÁ HACIENDO:{Colors.END}")
    print("-" * 40)

    # Mostrar barras de prioridad
    print(f"{Colors.BOLD}Priorities de Modelos:{Colors.END}")
    for model, priority in priorities.items():
        model_name = model.replace("_", " ").replace(":", " ").title()
        bar = format_priority_bar(priority)
        print(f"  {model_name:<20} {bar}")

    print(f"\n{Colors.BOLD}{Colors.MAGENTA}💬 LO QUE NOVA ESTÁ DICIENDO:{Colors.END}")
    print("-" * 40)

    # Mostrar últimas decisiones
    if status["recent_history"]:
        latest = status["recent_history"][0]
        model = latest["model_name"]
        change = latest["change_amount"]
        rating = latest["avg_rating"]
        feedback_count = latest["total_feedback"]

        if change > 0:
            decision = (
                f"¡Subí la priority de {model} porque tiene buen rating ({rating:.1f})!"
            )
        elif change < 0:
            decision = (
                f"Bajé la priority de {model} porque tiene mal rating ({rating:.1f})"
            )
        else:
            decision = f"Mantengo {model} estable con rating {rating:.1f}"

        print(f"  🗣️  {decision}")
        print(f"      📊 {feedback_count} evaluaciones analizadas")
        print(f"      ⏰ Decisión tomada: {latest['created_at'][11:19]}")

    print(f"\n{Colors.BOLD}{Colors.CYAN}📊 ESTADÍSTICAS DEL CEREBRO:{Colors.END}")
    print("-" * 40)
    total_feedback = sum(
        entry["total_feedback"] for entry in status["recent_history"][:5]
    )
    avg_rating = (
        sum(entry["avg_rating"] for entry in status["recent_history"][:5])
        / len(status["recent_history"][:5])
        if status["recent_history"]
        else 0
    )

    print(f"  📈 Feedback procesado: {total_feedback}")
    print(f"  ⭐ Rating promedio: {avg_rating:.2f}")
    print(f"  🔄 Optimizaciones: {len(status['recent_history'])}")

    # Estadísticas del caché
    cache_stats = cache_system.get_cache_stats()
    print(f"\n{Colors.BOLD}{Colors.GREEN}🚀 ESTADÍSTICAS DEL CACHÉ:{Colors.END}")
    print("-" * 40)
    print(f"  📦 Entradas totales: {cache_stats['total_entries']}")
    print(f"  ✅ Entradas válidas: {cache_stats['valid_entries']}")
    print(f"  ⏰ Entradas expiradas: {cache_stats['expired_entries']}")
    print(f"  🎯 Hit rate: {cache_stats['hit_rate_percent']:.1f}%")
    print(f"  💾 Tamaño: {cache_stats['size_mb']:.2f} MB")
    print(f"  🤖 Modelo top: {cache_stats['top_model']}")
    print(f"  📅 TTL: {cache_stats['ttl_days']:.0f} días")


def show_footer():
    """Mostrar footer con instrucciones"""
    print(
        f"\n{Colors.BOLD}{Colors.WHITE}💡 PRESIONA CTRL+C PARA SALIR | ACTUALIZA CADA 5 SEGUNDOS{Colors.END}"
    )
    print(f"{Colors.CYAN}🔄 NOVA se está auto-optimizando continuamente...{Colors.END}")


def main():
    """Función principal"""
    try:
        while True:
            clear_screen()
            print_logo()
            show_brain_activity()
            show_footer()

            # Esperar 5 segundos antes de actualizar
            time.sleep(5)

    except KeyboardInterrupt:
        clear_screen()
        print_logo()
        print(
            f"\n{Colors.GREEN}👋 ¡Hasta luego! NOVA sigue pensando y mejorándose sola...{Colors.END}"
        )
        print(
            f"{Colors.CYAN}💡 El auto-tuning continúa corriendo en background{Colors.END}\n"
        )


if __name__ == "__main__":
    main()
