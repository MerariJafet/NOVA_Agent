#!/usr/bin/env python3
"""
Tests para el sistema de auto-optimización - Sprint 3 Día 2
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nova.core.auto_optimizer import auto_optimize, get_optimization_history, get_current_priorities, _init_optimization_log
from nova.core.memoria import init_db
from nova.core.feedback_system import record_feedback
from config.settings import settings


def setup_test_environment():
    """Configurar entorno de prueba con archivos temporales."""
    # Crear directorios temporales
    temp_dir = tempfile.mkdtemp()
    temp_config_dir = os.path.join(temp_dir, "config")
    temp_data_dir = os.path.join(temp_dir, "data")
    os.makedirs(temp_config_dir)
    os.makedirs(temp_data_dir)

    # Copiar model_profiles.json original
    original_profiles = os.path.join(os.path.dirname(__file__), "config", "model_profiles.json")
    temp_profiles = os.path.join(temp_config_dir, "model_profiles.json")
    shutil.copy2(original_profiles, temp_profiles)

    # Configurar settings temporales
    original_db_path = settings.db_path
    original_profiles_path = settings.model_profiles_path

    settings.db_path = os.path.join(temp_data_dir, "test.db")
    settings.model_profiles_path = temp_profiles

    return {
        "temp_dir": temp_dir,
        "original_db_path": original_db_path,
        "original_profiles_path": original_profiles_path
    }


def cleanup_test_environment(env):
    """Limpiar entorno de prueba."""
    settings.db_path = env["original_db_path"]
    settings.model_profiles_path = env["original_profiles_path"]
    shutil.rmtree(env["temp_dir"], ignore_errors=True)


def test_auto_optimizer_basic():
    """Test básico del auto-optimizer."""
    env = setup_test_environment()

    try:
        # Inicializar DB y tabla de optimización
        init_db()
        _init_optimization_log()

        # Verificar que no hay cambios sin feedback
        result = auto_optimize()
        assert result["status"] == "no_data"
        assert len(result["changes_applied"]) == 0
        print("✅ Test básico: Sin datos = no optimización")

        # Simular feedback para dolphin (rating alto = +priority)
        # Primero necesitamos crear mensajes para tener message_ids
        from nova.core.memoria import save_conversation

        # Crear conversaciones de prueba
        for i in range(10):  # 10 evaluaciones para dolphin
            msg_id = save_conversation(f"session_{i}", "user", f"Mensaje de prueba {i}", "dolphin-mistral:7b")
            record_feedback(msg_id, f"session_{i}", 5, "Excelente respuesta")  # Rating 5

        for i in range(10):  # 10 evaluaciones para claude
            msg_id = save_conversation(f"session_claude_{i}", "user", f"Mensaje claude {i}", "claude_code_api")
            record_feedback(msg_id, f"session_claude_{i}", 2, "Mala respuesta")  # Rating 2

        # Ejecutar optimización
        result = auto_optimize(max_change=20, min_feedback=5)

        assert result["status"] == "optimized"
        assert len(result["changes_applied"]) >= 1  # Debería haber cambios

        # Verificar cambios específicos
        changes = {change["model"]: change for change in result["changes_applied"]}

        # Dolphin debería subir priority (rating 5.0)
        if "dolphin-mistral:7b" in changes:
            assert changes["dolphin-mistral:7b"]["change"] > 0
            print(f"✅ Dolphin priority aumentó: {changes['dolphin-mistral:7b']['change']}")

        # Claude debería bajar priority (rating 2.0)
        if "claude_code_api" in changes:
            assert changes["claude_code_api"]["change"] < 0
            print(f"✅ Claude priority disminuyó: {changes['claude_code_api']['change']}")

        # Verificar que se guardaron los cambios en el archivo
        current_priorities = get_current_priorities()
        assert len(current_priorities) > 0
        print(f"✅ Priorities actuales: {current_priorities}")

        # Verificar historial de optimización
        history = get_optimization_history()
        assert len(history) >= 1
        print(f"✅ Historial de optimización: {len(history)} registros")

        print("✅ Test básico completado exitosamente")

    finally:
        cleanup_test_environment(env)


def test_limits_and_constraints():
    """Test de límites y restricciones."""
    env = setup_test_environment()

    try:
        init_db()
        _init_optimization_log()

        # Crear feedback extremo para probar límites
        from nova.core.memoria import save_conversation

        # Modelo con rating perfecto (debería intentar +40 pero limitar a +20)
        for i in range(10):
            msg_id = save_conversation(f"perfect_{i}", "user", f"Perfect {i}", "mixtral:8x7b")
            record_feedback(msg_id, f"perfect_{i}", 5, "Perfecto")

        result = auto_optimize(max_change=20, min_feedback=5)

        if "mixtral:8x7b" in [c["model"] for c in result["changes_applied"]]:
            mixtral_change = next(c["change"] for c in result["changes_applied"] if c["model"] == "mixtral:8x7b")
            assert abs(mixtral_change) <= 20  # No debe exceder el límite
            print(f"✅ Límite de cambio respetado: {mixtral_change} (máx ±20)")

        print("✅ Test de límites completado")

    finally:
        cleanup_test_environment(env)


def test_insufficient_feedback():
    """Test con feedback insuficiente."""
    env = setup_test_environment()

    try:
        init_db()
        _init_optimization_log()

        # Crear solo 3 evaluaciones (menos del mínimo de 5)
        from nova.core.memoria import save_conversation

        for i in range(3):
            msg_id = save_conversation(f"few_{i}", "user", f"Few {i}", "dolphin-mistral:7b")
            record_feedback(msg_id, f"few_{i}", 5, "Buena")

        result = auto_optimize(min_feedback=5)

        # No debería optimizar modelos con menos de 5 evaluaciones
        assert result["status"] in ["no_data", "no_changes"]
        print("✅ Test de feedback insuficiente completado")

    finally:
        cleanup_test_environment(env)


def test_backup_and_logging():
    """Test de backup y logging."""
    env = setup_test_environment()

    try:
        init_db()
        _init_optimization_log()

        # Crear feedback suficiente
        from nova.core.memoria import save_conversation

        for i in range(10):
            msg_id = save_conversation(f"backup_{i}", "user", f"Backup {i}", "dolphin-mistral:7b")
            record_feedback(msg_id, f"backup_{i}", 4, "Buena")

        result = auto_optimize()

        if result["status"] == "optimized":
            # Verificar que se creó backup
            assert "backup_created" in result
            assert os.path.exists(result["backup_created"])
            print(f"✅ Backup creado: {result['backup_created']}")

            # Verificar logging en DB
            history = get_optimization_history()
            assert len(history) >= 1
            last_log = history[0]
            assert "model_name" in last_log
            assert "change_amount" in last_log
            print(f"✅ Log registrado: {last_log['model_name']} cambió {last_log['change_amount']}")

        print("✅ Test de backup y logging completado")

    finally:
        cleanup_test_environment(env)


def run_all_tests():
    """Ejecutar todos los tests."""
    print("🚀 Ejecutando tests del Auto-Optimizer...")
    print("=" * 50)

    try:
        test_auto_optimizer_basic()
        test_limits_and_constraints()
        test_insufficient_feedback()
        test_backup_and_logging()

        print("=" * 50)
        print("🎉 Todos los tests pasaron exitosamente!")
        return True

    except Exception as e:
        print(f"❌ Error en tests: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)