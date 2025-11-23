import sys
from nova.core.launcher import start, stop


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'start':
            start()
        elif sys.argv[1] == 'stop':
            # stop()
        else:
            print('Uso: python nova.py start|stop')
    else:
        print('Uso: python nova.py start|stop')
