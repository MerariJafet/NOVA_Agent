#!/usr/bin/env python3
"""
Test manual para verificar el routing del mensaje problemático.
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nova.core.intelligent_router import route

def test_problematic_message():
    """Test del mensaje que fallaba en el test suite."""
    message = "Dame una estrategia detallada y ejemplos de código para la integración"
    result = route(message)
    
    print("Mensaje:", message)
    print("Modelo seleccionado:", result["model"])
    print("Confianza:", result["confidence"])
    print("Razonamiento:", result["reasoning"])
    print("Alternativas:", result["alternatives"])
    
    # Verificar que sea mixtral
    expected = "mixtral:8x7b"
    if result["model"] == expected:
        print("✅ CORRECTO: Seleccionó mixtral como esperado")
        return True
    else:
        print(f"❌ ERROR: Esperaba {expected}, pero obtuvo {result['model']}")
        return False

if __name__ == "__main__":
    success = test_problematic_message()
    sys.exit(0 if success else 1)