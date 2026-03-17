#!/usr/bin/env python3
"""Valida entorno antes de correr scripts P6-Standalone-Automation."""

import sys

REQUIRED = ['openpyxl']
OPTIONAL = ['pytest']


def check():
    errors = []
    for pkg in REQUIRED:
        try:
            __import__(pkg)
            print(f'✓ {pkg}')
        except ImportError:
            errors.append(pkg)
            print(f'✗ {pkg} (requerido)')

    for pkg in OPTIONAL:
        try:
            __import__(pkg)
            print(f'✓ {pkg} (opcional)')
        except ImportError:
            print(f'○ {pkg} (opcional, no instalado)')

    if errors:
        print(f'\nERROR: Instalar paquetes faltantes: pip install {" ".join(errors)}')
        sys.exit(1)

    print('\n✓ Entorno OK')


if __name__ == '__main__':
    check()
