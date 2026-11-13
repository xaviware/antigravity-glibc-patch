# Antigravity IDE — Parche de Compatibilidad GLIBC 2.27 (Ubuntu 18.04 / Peppermint 10)

Script en Python (sin dependencias externas) para permitir la ejecución de los módulos nativos de **Antigravity IDE** en distribuciones Linux con **GLIBC 2.27** (como Ubuntu 18.04 LTS, Peppermint OS 10, Linux Mint 19.x o Debian Buster/Stretch).

---

## El Problema

En sistemas con `glibc 2.27`, algunos módulos nativos de Node.js precompilados incluidos en Antigravity IDE fueron enlazados contra `glibc >= 2.28` únicamente por el símbolo `fcntl64@GLIBC_2.28`. Esto provoca fallos silenciosos o errores al iniciar componentes críticos del IDE:

```text
version `GLIBC_2.28' not found (required by .../pty.node)
version `GLIBC_2.28' not found (required by .../vscode-sqlite3.node)
```

Como consecuencia:
1. **`pty.node` (`node-pty`)**: La terminal integrada no abre ni responde.
2. **`vscode-sqlite3.node` (`@vscode/sqlite3`)**: Falla el almacenamiento de estado local del IDE (historial, sesiones, configuración de workspace).

---

## ¿Qué hace este script?

 En arquitecturas de 64 bits (`x86_64`), `fcntl64` y `fcntl` son funcionalmente equivalentes a nivel de ABI. `fix_glibc_antigravity_ide.py` modifica directamente las cabeceras y tablas ELF de los binarios afectados para:

1. **Renombrar el símbolo dinámico** en `.dynstr`: cambia `fcntl64\0` por `fcntl\0\0\0` (manteniendo intactos los offsets de la tabla de cadenas).
2. **Reasignar el índice de versión** en `.gnu.version` (`versym`): apunta el símbolo `fcntl` a `GLIBC_2.2.5` (índice `4`) en lugar de `GLIBC_2.28`.
3. **Eliminar el requisito de `GLIBC_2.28`** en `.gnu.version_r` (`verneed`): ajusta el contador `vn_cnt` y el puntero `vn_aux` de la entrada de `libc.so.6` para saltar el requerimiento de `GLIBC_2.28`.
4. **Verificar el resultado** ejecutando `ldd -r` sobre cada binario parcheado para confirmar que no queden símbolos sin resolver ni referencias a `GLIBC_2.28`.

> **Nota:** El script es **idempotente** (puedes ejecutarlo múltiples veces de forma segura; detecta si los archivos ya fueron parcheados).

---

## Requisitos

- **SO / Arquitectura:** Linux `x86_64` con `glibc 2.27`
- **Python:** Python 3.6+ (solo utiliza librería estándar: `os`, `struct`, `subprocess`, `sys`)
- **Ruta por defecto del IDE:** `~/.local/share/antigravity-ide`

---

## Uso

1. Clona este repositorio:
   ```bash
   git clone https://github.com/xaviware/antigravity-glibc-patch.git
   cd antigravity-glibc-patch
   ```

2. (Opcional) Haz una copia de seguridad de los binarios originales:
   ```bash
   cp ~/.local/share/antigravity-ide/resources/app/node_modules/node-pty/build/Release/pty.node{,.bak}
   cp ~/.local/share/antigravity-ide/resources/app/node_modules/@vscode/sqlite3/build/Release/vscode-sqlite3.node{,.bak}
   ```

3. Ejecuta el parche:
   ```bash
   python3 fix_glibc_antigravity_ide.py
   ```

   Salida esperada:
   ```text
   [OK] Parcheado: /home/usuario/.local/share/antigravity-ide/resources/app/node_modules/node-pty/build/Release/pty.node
   [OK] Parcheado: /home/usuario/.local/share/antigravity-ide/resources/app/node_modules/@vscode/sqlite3/build/Release/vscode-sqlite3.node
   ```

4. Reinicia **Antigravity IDE**.

> **Nota tras actualizaciones:** Cada vez que Antigravity IDE se actualice y sobrescriba sus módulos en `~/.local/share/antigravity-ide`, vuelve a ejecutar `python3 fix_glibc_antigravity_ide.py`.

---

## Licencia

Distribuido bajo la licencia [MIT](LICENSE).

