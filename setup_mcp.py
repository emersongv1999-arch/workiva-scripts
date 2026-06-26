#!/usr/bin/env python3
"""
setup_mcp.py
============
Instala dependencias del MCP de Workiva y muestra la configuración
que debes agregar a Claude Desktop.
"""

import json
import os
import subprocess
import sys


def run(cmd: list[str]) -> int:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.call(cmd)


def main() -> None:
    print("=" * 60)
    print("SETUP — Workiva MCP Server")
    print("=" * 60)

    project_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Elegir Python: preferir venv del proyecto si existe
    venv_python = os.path.join(project_dir, "venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        python_exe = venv_python
        print(f"\n[1] Usando Python del venv: {python_exe}")
    else:
        python_exe = sys.executable
        print(f"\n[1] Python del sistema: {python_exe} ({sys.version.split()[0]})")

    # 2. Instalar dependencias en el Python elegido
    print("\n[2] Instalando dependencias...")
    deps = ["mcp[cli]", "httpx", "python-dotenv"]
    for dep in deps:
        rc = run([python_exe, "-m", "pip", "install", dep, "--quiet"])
        if rc != 0:
            print(f"  ⚠ Error instalando {dep}")

    # 3. Verificar .env
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    print(f"\n[3] Verificando .env en {env_path}...")
    if os.path.exists(env_path):
        with open(env_path) as f:
            keys = [l.split("=")[0] for l in f if "=" in l and not l.startswith("#")]
        required = {"WORKIVA_CLIENT_ID", "WORKIVA_CLIENT_SECRET", "WORKIVA_WORKSPACE_ID"}
        missing  = required - set(keys)
        if missing:
            print(f"  ⚠ Faltan estas variables en .env: {', '.join(missing)}")
        else:
            print("  ✓ .env contiene todas las variables necesarias")
    else:
        print("  ✗ No se encontró .env — crea el archivo con las credenciales")

    # 4. Verificar sintaxis del servidor
    print("\n[4] Verificando sintaxis de workiva_mcp.py...")
    mcp_path = os.path.join(project_dir, "workiva_mcp.py")
    rc = run([python_exe, "-m", "py_compile", mcp_path])
    if rc == 0:
        print("  ✓ Sin errores de sintaxis")
    else:
        print("  ✗ Error de sintaxis — revisa workiva_mcp.py")
        return

    # 5. Mostrar configuración para Claude Desktop
    config = {
        "mcpServers": {
            "workiva": {
                "command": python_exe.replace("\\", "/"),
                "args":    [mcp_path.replace("\\", "/")],
                "env":     {}
            }
        }
    }

    print("\n[5] Configuración para Claude Desktop")
    print("    Archivo: %APPDATA%\\Claude\\claude_desktop_config.json")
    print("    Agrega (o fusiona) este bloque:\n")
    print(json.dumps(config, indent=2))
    print()

    # Intentar encontrar el archivo de config
    appdata = os.environ.get("APPDATA", "")
    cfg_path = os.path.join(appdata, "Claude", "claude_desktop_config.json")
    if os.path.exists(cfg_path):
        print(f"    Archivo encontrado en: {cfg_path}")
        with open(cfg_path) as f:
            try:
                current = json.load(f)
            except json.JSONDecodeError:
                current = {}

        if "workiva" in current.get("mcpServers", {}):
            print("    ✓ 'workiva' ya está registrado en claude_desktop_config.json")
        else:
            print("    → Agregando entrada 'workiva'...")
            current.setdefault("mcpServers", {})
            current["mcpServers"]["workiva"] = config["mcpServers"]["workiva"]
            with open(cfg_path, "w") as f:
                json.dump(current, f, indent=2)
            print("    ✓ Configuración guardada. Reinicia Claude Desktop.")
    else:
        print(f"    No se encontró {cfg_path}")
        print("    Crea el archivo manualmente con el contenido de arriba.")

    print("\n" + "=" * 60)
    print("Listo. Reinicia Claude Desktop para activar el MCP.")
    print("=" * 60)


if __name__ == "__main__":
    main()
