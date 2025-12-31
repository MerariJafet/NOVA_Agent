import argparse
import sys
from nova.core.launcher import start, stop


def main():
    parser = argparse.ArgumentParser(
        description="Control del sistema NOVA", usage="python nova.py {start|stop}"
    )
    parser.add_argument(
        "command",
        choices=["start", "stop"],
        help="Comando a ejecutar: start para iniciar, stop para detener",
    )

    args = parser.parse_args()

    if args.command == "start":
        try:
            result = start()
            print("✅ NOVA iniciado exitosamente!")
            print(f"🌐 Interfaz web: http://localhost:{result['port']}")
            print(f"🔧 PID Uvicorn: {result['uvicorn_pid']}")
            if result["ollama_pid"]:
                print(
                    f"🤖 PID Ollama: {result['ollama_pid']} ({'gestionado' if result['ollama_managed'] else 'externo'})"
                )
            print(
                "\nPresiona Ctrl+C en la terminal para detener, o usa: python nova.py stop"
            )
        except Exception as e:
            print(f"❌ Error al iniciar NOVA: {e}")
            sys.exit(1)
    elif args.command == "stop":
        try:
            stop()
            print("✅ NOVA detenido exitosamente!")
        except Exception as e:
            print(f"❌ Error al detener NOVA: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
