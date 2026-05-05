"""Handlers de Telegram."""
from __future__ import annotations

import io
import json
import logging
from decimal import Decimal
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from src.bot import auth, formatter
from src.config import settings
from src.datos.loader import cargar_empresa, actualizar_precio_material, actualizar_precio_mano_obra, listar_materiales_con_descripcion, listar_mo_con_descripcion
from src.metricas import tokens
from src.orquestador import minimax_client, router
from src.orquestador.agente import AgenteConversacional
from src.persistencia import db
from src.pdf import generador

log = logging.getLogger(__name__)

TMP_OUT = settings.db_path.parent.parent / "out"
CONFIANZA_MIN = 0.70
OUTLIER_FACTOR = 1.30


async def cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or update.message is None:
        return
    empresa_id = auth.resolver_empresa(user.id)
    datos = cargar_empresa(empresa_id)
    await update.message.reply_text(
        f"Hola, {user.first_name}. Bot de presupuestos conectado a *{datos.config.nombre}*.\n\n"
        "Escribí un pedido como:\n"
        "`techo chapa galvanizada 7x10 con perfil C100`\n\n"
        "Comandos: /empresa /tokens /help",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_empresa(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return
    empresa_id = auth.resolver_empresa(update.effective_user.id)
    datos = cargar_empresa(empresa_id)
    await update.message.reply_text(
        f"Empresa: {datos.config.nombre} ({empresa_id})\n"
        f"Moneda: {datos.config.moneda}\n"
        f"Materiales disponibles: {len(datos.materiales_disponibles)}\n"
        f"Tarifas de mano de obra: {len(datos.precios_mano_obra)}"
    )


async def cmd_tokens(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return
    if not auth.es_admin(update.effective_user.id):
        await update.message.reply_text("Solo admin.")
        return
    r = tokens.resumen()
    await update.message.reply_text(
        f"Presupuestos: {r['presupuestos']}\n"
        f"Llamadas MiniMax: {r['calls_minimax']}\n"
        f"Tokens in/out: {r['tokens_input']} / {r['tokens_output']}\n"
        f"USD gastado: ${r['usd_gastado']:.4f} / ${r['budget_usd']:.2f} ({r['porcentaje']}%)\n"
        f"USD restante: ${r['usd_restante']:.4f}"
    )


# Palabras clave para detectar flujo de precio en caption
_PALABRAS_PRECIO = {"precio", "precios", "lista", "cotiz", "cotización", "actualizar", "actualiza"}


async def on_foto(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """ Maneja mensajes con foto (vision). """
    if update.effective_user is None:
        return
    
    # Obtener caption (texto junto con la imagen)
    caption = update.message.caption or ""
    photo = update.message.photo
    document = update.message.document
    
    # Si hay documento (podría ser imagen), preferimo photo
    if not photo and document:
        # Intentar obtener el file
        try:
            file = await ctx.bot.get_file(document.file_id)
            photo_bytes = await file.download_as_bytearray()
            photo_bytes = bytes(photo_bytes)
            mime = document.mime_type or "image/jpeg"
        except Exception as e:
            log.warning("Error descargando documento: %s", e)
            await update.message.reply_text("❌ No pude descargar la imagen.")
            return
    elif photo:
        # Tomar la foto de mayor resolución
        foto = photo[-1]
        try:
            file = await ctx.bot.get_file(foto.file_id)
            photo_bytes = await file.download_as_bytearray()
            photo_bytes = bytes(photo_bytes)
            mime = "image/jpeg"
        except Exception as e:
            log.warning("Error descargando foto: %s", e)
            await update.message.reply_text("❌ No pude descargar la imagen.")
            return
    else:
        await update.message.reply_text("❌ No encontré imagen adjunta.")
        return
    
    # Verificar empresa
    user_id = update.effective_user.id
    try:
        empresa_id = auth.resolver_empresa(user_id)
    except PermissionError as e:
        await update.message.reply_text(str(e))
        return
    
    datos = cargar_empresa(empresa_id)
    
    # Detectar si es flujo de precio
    es_flujo_precio = any(p in caption.lower() for p in _PALABRAS_PRECIO)
    
    # 1) Analizar imagen con visión
    await update.message.chat.send_action(action="typing")
    try:
        if es_flujo_precio:
            # Si es lista de precios, pasar el texto completo
            texto_completo = caption if caption.strip() else "Analiza esta imagen de lista de precios"
            resp = await minimax_client.parsear_imagen(
                photo_bytes, 
                datos.materiales_disponibles,
                texto_completo,
            )
        else:
            # Flujo normal de presupuesto por imagen
            resp = await minimax_client.parsear_imagen(
                photo_bytes,
                datos.materiales_disponibles,
                caption or None,
            )
    except Exception as e:
        log.exception("Error MiniMax vision")
        await update.message.reply_text(f"Error analizando imagen: {e}")
        return
    
    log.info("Vision NLU: %s (conf=%.2f)", resp.accion, resp.confianza)
    
    # 2) Aclaración o confianza baja
    if resp.accion == "aclaracion":
        pregunta = resp.parametros.get("pregunta", "¿Podés dar más detalles?")
        await update.message.reply_text(f"❓ {pregunta}")
        return
    
    if resp.confianza < CONFIANZA_MIN:
        await update.message.reply_text(
            f"No pude entender la imagen (confianza {resp.confianza:.0%}). "
            f"Interpreté: {resp.accion} {resp.parametros}. Intentá con más texto en el caption."
        )
        return
    
    # 3) Si es flujo de precio, manejar actualización de precios
    if es_flujo_precio and resp.accion in ("actualizar_precio", "actualizar_mano_obra"):
        await _procesar_actualizacion_precio(update, resp, empresa_id, caption)
        return
    
    # 4) Cálculo normal de presupuesto
    try:
        resultado = router.despachar(resp.accion, resp.parametros, empresa_id)
    except router.AccionDesconocida as e:
        await update.message.reply_text(f"No tengo calculadora para eso: {e}")
        return
    except ValueError as e:
        await update.message.reply_text(f"No pude calcular: {e}")
        return
    
    # 5) Outlier check
    mediana = db.mediana_total(empresa_id, resultado.rubro)
    if mediana and float(resultado.total) > mediana * OUTLIER_FACTOR:
        resultado.advertencias.append(
            f"Total {float(resultado.total)/mediana:.0%} por encima de la mediana ({mediana:.0f})"
        )
    
    # 6) Persistir
    pid, id_corto = db.guardar_presupuesto(
        empresa_id=empresa_id,
        telegram_user_id=user_id,
        input_texto=f"[IMAGEN] {caption}",
        minimax_json=resp.raw,
        minimax_confianza=resp.confianza,
        resultado=resultado,
        tokens_input=resp.tokens_input,
        tokens_output=resp.tokens_output,
        usd_estimado=resp.usd_estimado,
        latencia_ms=resp.latencia_ms,
    )
    
    # 7) Responder
    texto_ok = formatter.formatear_presupuesto(resultado, id_corto)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Generar PDF", callback_data=f"pdf:{pid}")],
        [
            InlineKeyboardButton("✅ Correcto", callback_data=f"fb_ok:{pid}"),
            InlineKeyboardButton("❌ Incorrecto", callback_data=f"fb_bad:{pid}"),
        ],
    ])
    await update.message.reply_text(texto_ok, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)


async def _procesar_actualizacion_precio(update: Update, resp, empresa_id: str, texto_original: str) -> None:
    """Procesa solicitud de actualización de precio desde visión."""
    params = resp.parametros
    codigo = params.get("codigo_material") or params.get("codigo_tarea")
    nuevo_precio = params.get("nuevo_precio")
    
    if not codigo or not nuevo_precio:
        await update.message.reply_text(
            "❌ No pude entender qué precio actualizar. "
            "Indicá el código y el nuevo precio en el caption."
        )
        return
    
    try:
        nuevo_precio = float(nuevo_precio)
    except (ValueError, TypeError):
        await update.message.reply_text(f"❌ Precio inválido: {nuevo_precio}")
        return
    
    # Determinar tipo de actualización
    es_material = resp.accion == "actualizar_precio"
    
    if es_material:
        ok = actualizar_precio_material(empresa_id, codigo, Decimal(str(nuevo_precio)))
        tipo = "material"
    else:
        ok = actualizar_precio_mano_obra(empresa_id, codigo, Decimal(str(nuevo_precio)))
        tipo = "mano de obra"
    
    if ok:
        await update.message.reply_text(
            f"✅ Actualizado {tipo} *{codigo}* a ${nuevo_precio:.2f}"
        )
    else:
        await update.message.reply_text(
            f"❌ No encontré {tipo} con código *{codigo}*"
        )


async def on_mensaje(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    import re
    from src.orquestador.prompts import _RESET_RE
    from src.persistencia.db import guardar_sesion, obtener_sesion, limpiar_sesion

    if update.effective_user is None or update.message is None or update.message.text is None:
        return

    user_id = update.effective_user.id
    texto = update.message.text

    try:
        empresa_id = auth.resolver_empresa(user_id)
    except PermissionError as e:
        await update.message.reply_text(str(e))
        return

    datos = cargar_empresa(empresa_id)

    # --- Detección de sesión activa ---
    sesion = obtener_sesion(user_id)

    if sesion and re.search(_RESET_RE, texto, re.IGNORECASE):
        limpiar_sesion(user_id)
        await update.message.reply_text("🆕 Listo, empezamos de cero. ¿Qué necesitás presupuestar?")
        return

    if sesion and sesion["accion"] not in ("", "__imagenes__"):
        await update.message.chat.send_action(action="typing")
        try:
            resp = await minimax_client.parsear_modificacion(texto, sesion)
        except Exception as e:  # noqa: BLE001
            log.exception("Error parsear_modificacion")
            resp = None

        if resp and resp.accion != "nuevo_presupuesto":
            # Es una modificación — recalcular con los params actualizados
            prefijo = "✏️ *Presupuesto actualizado:*\n\n"
            try:
                resultado = router.despachar(resp.accion, resp.parametros, empresa_id)
            except (router.AccionDesconocida, ValueError) as e:
                await update.message.reply_text(f"No pude recalcular la modificación: {e}")
                return

            pid, id_corto = db.guardar_presupuesto(
                empresa_id=empresa_id, telegram_user_id=user_id, input_texto=texto,
                minimax_json=resp.raw, minimax_confianza=resp.confianza, resultado=resultado,
                tokens_input=resp.tokens_input, tokens_output=resp.tokens_output,
                usd_estimado=resp.usd_estimado, latencia_ms=resp.latencia_ms,
            )
            guardar_sesion(user_id, empresa_id, resp.accion, resp.parametros, pid)

            texto_ok = formatter.formatear_presupuesto(resultado, id_corto)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📄 Generar PDF", callback_data=f"pdf:{pid}")],
                [
                    InlineKeyboardButton("✅ Correcto", callback_data=f"fb_ok:{pid}"),
                    InlineKeyboardButton("❌ Incorrecto", callback_data=f"fb_bad:{pid}"),
                ],
            ])
            await update.message.reply_text(
                prefijo + texto_ok, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb
            )
            return
        # Si resp es None o accion=="nuevo_presupuesto" → caer al flujo NLU estándar

    # --- Flujo NLU estándar ---
    # 1) NLU con MiniMax
    await update.message.chat.send_action(action="typing")
    try:
        resp = await minimax_client.parsear(texto, datos.materiales_disponibles)
    except Exception as e:  # noqa: BLE001
        log.exception("Error MiniMax")
        await update.message.reply_text(f"Error consultando el orquestador: {e}")
        return

    log.info("NLU: %s (conf=%.2f, tokens=%d/%d, $%.5f)",
             resp.accion, resp.confianza, resp.tokens_input, resp.tokens_output, resp.usd_estimado)

    # 2) Aclaración o confianza baja
    if resp.accion == "aclaracion":
        pregunta = resp.parametros.get("pregunta", "¿Podés dar más detalles?")
        await update.message.reply_text(f"❓ {pregunta}")
        return

    if resp.confianza < CONFIANZA_MIN:
        await update.message.reply_text(
            f"No estoy seguro de haber entendido (confianza {resp.confianza:.0%}). "
            f"Interpreté: {resp.accion} {resp.parametros}. Reformulá, por favor."
        )
        return

    # 3) Cálculo
    try:
        resultado = router.despachar(resp.accion, resp.parametros, empresa_id)
    except router.AccionDesconocida as e:
        await update.message.reply_text(f"No tengo una calculadora para eso todavía. {e}")
        return
    except ValueError as e:
        await update.message.reply_text(f"No pude calcular: {e}")
        return

    # 4) Outlier check
    mediana = db.mediana_total(empresa_id, resultado.rubro)
    if mediana and float(resultado.total) > mediana * OUTLIER_FACTOR:
        resultado.advertencias.append(
            f"Total {float(resultado.total)/mediana:.0%} por encima de la mediana "
            f"({mediana:.0f}). Revisá precios."
        )
        if settings.admin_telegram_chat_id:
            await _ctx.bot.send_message(
                settings.admin_telegram_chat_id,
                f"⚠️ Outlier en {empresa_id}: {resultado.rubro} = {resultado.total} "
                f"(mediana {mediana:.0f})",
            )

    # 5) Persistir
    pid, id_corto = db.guardar_presupuesto(
        empresa_id=empresa_id,
        telegram_user_id=user_id,
        input_texto=texto,
        minimax_json=resp.raw,
        minimax_confianza=resp.confianza,
        resultado=resultado,
        tokens_input=resp.tokens_input,
        tokens_output=resp.tokens_output,
        usd_estimado=resp.usd_estimado,
        latencia_ms=resp.latencia_ms,
    )

    # Guardar sesión para permitir modificaciones en el próximo mensaje
    guardar_sesion(user_id, empresa_id, resp.accion, resp.parametros, pid)

    # 6) Responder
    texto_ok = formatter.formatear_presupuesto(resultado, id_corto)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Generar PDF", callback_data=f"pdf:{pid}")],
        [
            InlineKeyboardButton("✅ Correcto", callback_data=f"fb_ok:{pid}"),
            InlineKeyboardButton("❌ Incorrecto", callback_data=f"fb_bad:{pid}"),
        ],
    ])
    await update.message.reply_text(texto_ok, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)

    # 7) Alerta de tokens
    if tokens.debe_alertar() and settings.admin_telegram_chat_id:
        r = tokens.resumen()
        await _ctx.bot.send_message(
            settings.admin_telegram_chat_id,
            f"⚠️ Consumo MiniMax al {r['porcentaje']}% (${r['usd_gastado']}/${r['budget_usd']})",
        )


async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q is None or q.data is None:
        return
    await q.answer()
    accion, _, pid_s = q.data.partition(":")
    pid = int(pid_s) if pid_s.isdigit() else 0

    if accion == "pdf" and pid:
        await _enviar_pdf(update, ctx, pid)
    elif accion == "fb_ok" and pid:
        db.guardar_feedback(pid, preciso=True)
        await q.edit_message_reply_markup(reply_markup=None)
        if q.message:
            await q.message.reply_text("✅ Gracias por el feedback.")
    elif accion == "fb_bad" and pid:
        db.guardar_feedback(pid, preciso=False)
        if q.message:
            await q.message.reply_text(
                "Gracias. ¿Qué estuvo mal? Podés escribirme el total correcto o describir el error."
            )


async def _enviar_pdf(update: Update, ctx: ContextTypes.DEFAULT_TYPE, pid: int) -> None:
    from src.persistencia.db import cursor
    from src.rubros.base import ResultadoPresupuesto as _R

    with cursor() as c:
        row = c.execute(
            "SELECT empresa_id, resultado_json FROM presupuestos WHERE id=?", (pid,)
        ).fetchone()
    if not row:
        return
    resultado = _R.model_validate_json(row["resultado_json"])
    datos = cargar_empresa(row["empresa_id"])

    TMP_OUT.mkdir(parents=True, exist_ok=True)
    pdf_path = generador.generar_pdf(resultado, datos, TMP_OUT)

    if update.effective_chat:
        await ctx.bot.send_document(
            chat_id=update.effective_chat.id,
            document=pdf_path.open("rb"),
            filename=pdf_path.name,
        )
    _actualizar_pdf_path(pid, pdf_path)


def _actualizar_pdf_path(pid: int, path: Path) -> None:
    from src.persistencia.db import cursor
    with cursor() as c:
        c.execute("UPDATE presupuestos SET pdf_path=? WHERE id=?", (str(path), pid))


# =============================================================================
# Agente Conversacional (tool use)
# =============================================================================


# Instancia global del agente
_agente_conversacional: AgenteConversacional | None = None


def _get_agente() -> AgenteConversacional:
    global _agente_conversacional
    if _agente_conversacional is None:
        _agente_conversacional = AgenteConversacional(modelo=settings.minimax_model)
    return _agente_conversacional


async def on_mensaje(chat_id: int, user_id: int, empresa_id: str, texto: str) -> str:
    """Procesa mensaje usando el agente conversacional con tool use.
    
    Args:
        chat_id: ID del chat de Telegram
        user_id: ID del usuario
        empresa_id: ID de la empresa
        texto: Mensaje del usuario
        
    Returns:
        Respuesta formateada para enviar al usuario
    """
    agente = _get_agente()
    return await agente.procesar(str(user_id), empresa_id, texto)


def registrar(app) -> None:  # type: ignore[no-untyped-def]
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("empresa", cmd_empresa))
    app.add_handler(CommandHandler("tokens", cmd_tokens))
    app.add_handler(CallbackQueryHandler(on_callback))
    # Foto debe estar antes de TEXT para manejar imagen + caption
    app.add_handler(MessageHandler(filters.PHOTO, on_foto))
    # También documentos de tipo imagen (enviados sin compresión)
    app.add_handler(MessageHandler(filters.Document.IMAGE, on_foto))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_mensaje))
