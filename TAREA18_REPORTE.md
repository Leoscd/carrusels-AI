# TAREA 18 — Reporte de Implementación

## Resumen

**Objetivo:** Reemplazar el pipeline NLU rígido por un agente conversacional con tool use.

---

## Archivos Creados/Modificados

| Archivo | Cambios | Estado |
|---------|---------|--------|
| `src/orquestador/tools.py` | +490 líneas | ✅ |
| `src/orquestador/agente.py` | +217 líneas | ✅ |
| `src/persistencia/db.py` | +51 líneas | ✅ |
| `src/persistencia/schema.sql` | +8 líneas | ✅ |
| `src/bot/handlers.py` | +33 líneas | ✅ |
| `tests/test_herramientas.py` | +58 líneas | ✅ |
| `tests/test_agente.py` | +68 líneas | ✅ |

**Total:** 7 archivos, ~925 líneas añadidas

---

## Problemas Encontrados

### 1. Notion API
- Error: `status 400, invalid_json` al crear páginas
- Solución: Guardar en memoria local en vez de Notion

### 2. Playwright (renderizado de slides)
- Error: `libnspr4.so not found` - librerías del sistema faltantes
- Solución: No se pudo renderizar; usuario debe abrir localmente

### 3. GitHub Upload
- Error: Algunos uploads fallaron (transfer.sh disable)
- Solución: Subir a GitHub repo

### 4. Tarea 18 - Sub-agentes
- Algunos sub-agentes no completaron en primer intento
- Solución: Relanzar tarea completa

---

## Carrusel Instagram

- **Repo:** `https://github.com/Leoscd/carrusels-AI/blob/master/content/curso-ia-arq.html`
- **8 slides** sobre "De 0 a Prompt en Arquitectura"
- **Modo:** Borrador (falta exportar PNGs)

---

## Pendientes

| Item | Estado |
|------|--------|
| Test agente completo | Necesita testing real |
| Exportar carrusel a PNG | Sin Playwright |
| Notion agenda | Error API |