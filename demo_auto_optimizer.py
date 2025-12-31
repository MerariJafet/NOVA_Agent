#!/usr/bin/env python3
"""
Demostración del Sistema de Auto-Optimización - Sprint 3 Día 2
Muestra cómo NOVA se auto-optimiza basado en feedback humano
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nova.core.auto_optimizer import (
    auto_optimize,
    get_optimization_history,
    get_current_priorities,
)
from nova.core.memoria import init_db, save_conversation
from nova.core.feedback_system import record_feedback
from nova.core.auto_optimizer import _init_optimization_log


def demo_auto_optimization():
    """Demostración completa del sistema de auto-optimización."""
    print("🚀 Demostración del Sistema de Auto-Optimización NOVA")
    print("=" * 60)

    # Inicializar sistema
    print("📋 Inicializando sistema...")
    init_db()
    _init_optimization_log()

    print("📊 Priorities iniciales:")
    initial_priorities = get_current_priorities()
    for model, priority in initial_priorities.items():
        print(f"   {model}: {priority}")
    print()

    # Simular feedback humano
    print("👥 Simulando feedback humano...")

    # Dolphin recibe feedback excelente (rating 5)
    print("   🐬 Dolphin recibe 15 evaluaciones excelentes...")
    for i in range(15):
        msg_id = save_conversation(
            f"demo_dolphin_{i}", "user", f"¿Qué es la IA? {i}", "dolphin-mistral:7b"
        )
        record_feedback(
            msg_id, f"demo_dolphin_{i}", 5, "Respuesta excepcional, muy útil"
        )

    # Claude recibe feedback malo (rating 2)
    print("   🤖 Claude recibe 12 evaluaciones negativas...")
    for i in range(12):
        msg_id = save_conversation(
            f"demo_claude_{i}", "user", f"¿Cómo funciona Python? {i}", "claude_code_api"
        )
        record_feedback(msg_id, f"demo_claude_{i}", 2, "Respuesta confusa y poco útil")

    # Mixtral recibe feedback neutral (rating 3)
    print("   🔄 Mixtral recibe 8 evaluaciones neutrales...")
    for i in range(8):
        msg_id = save_conversation(
            f"demo_mixtral_{i}",
            "user",
            f"¿Qué es machine learning? {i}",
            "mixtral:8x7b",
        )
        record_feedback(msg_id, f"demo_mixtral_{i}", 3, "Respuesta aceptable")

    print()

    # Ejecutar auto-optimización
    print("⚡ Ejecutando auto-optimización...")
    result = auto_optimize(max_change=20, min_feedback=5)

    print(f"📈 Estado: {result['status']}")
    print(f"🔄 Cambios aplicados: {len(result['changes_applied'])}")
    print()

    # Mostrar cambios detallados
    print("📋 Cambios aplicados:")
    for change in result["changes_applied"]:
        direction = "⬆️" if change["change"] > 0 else "⬇️"
        print(
            f"   {direction} {change['model']}: {change['old_priority']} → {change['new_priority']} (cambio: {change['change']})"
        )
    print()

    # Mostrar priorities finales
    print("📊 Priorities finales:")
    final_priorities = get_current_priorities()
    for model, priority in final_priorities.items():
        initial = initial_priorities.get(model, 0)
        change = priority - initial
        direction = "⬆️" if change > 0 else "⬇️" if change < 0 else "➡️"
        print(f"   {direction} {model}: {priority} (cambio: {change:+d})")
    print()

    # Mostrar historial de optimización
    print("📜 Historial de optimización:")
    history = get_optimization_history(limit=10)
    for entry in history:
        print(
            f"   {entry['created_at'][:19]} | {entry['model_name']} | cambio: {entry['change_amount']:+d} | rating: {entry['avg_rating']:.1f}"
        )
    print()

    # Mostrar backup creado
    if "backup_created" in result:
        print(f"💾 Backup creado: {result['backup_created']}")
        print()

    print("🎯 Sistema de auto-optimización funcionando correctamente!")
    print("   NOVA ahora puede aprender automáticamente de sus interacciones")
    print("   y ajustar sus prioridades para mejorar el rendimiento futuro.")


if __name__ == "__main__":
    demo_auto_optimization()
