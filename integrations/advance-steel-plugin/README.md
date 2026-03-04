# Advance Steel Plugin Base (C#)

Base mínimo para comenzar integración local con Autodesk Advance Steel mediante plugin .NET.

## Estructura

- `src/AdvanceSteelHello/AdvanceSteelHello.csproj`
- `src/AdvanceSteelHello/Commands.cs`

## Requisitos

- Autodesk Advance Steel instalado
- Visual Studio 2022 (Desktop development with .NET)
- .NET Framework 4.8 Developer Pack

## 1) Configurar rutas de referencias

En el `.csproj`, ajusta los `HintPath` según tu instalación real.
Rutas típicas (ejemplo):

- `C:\Program Files\Autodesk\Advance Steel 2024\...
- `C:\Program Files\Autodesk\AutoCAD 2024\`

Debes apuntar al menos a:

- `acdbmgd.dll`
- `acmgd.dll`

> Si quieres usar clases específicas de Advance Steel, agrega también sus DLL del producto (depende versión).

## 2) Compilar

Desde Visual Studio: Build -> Build Solution

Salida esperada: `bin\Debug\AdvanceSteelHello.dll`

## 3) Cargar en Advance Steel

1. Abre Advance Steel
2. Ejecuta comando: `NETLOAD`
3. Selecciona `AdvanceSteelHello.dll`
4. Ejecuta comando: `SIMTEXX_HELLO`

Deberías ver un mensaje en la línea de comandos de Advance Steel.

## 4) Siguiente iteración sugerida

- Leer selección de elementos
- Exportar propiedades a JSON/CSV
- Crear endpoint local (FastAPI) para integrarlo con tus flujos Python
