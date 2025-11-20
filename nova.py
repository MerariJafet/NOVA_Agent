import sys
from nova.core.launcher import start


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'start':
        start()
    else:
        print('Uso: python nova.py start')
