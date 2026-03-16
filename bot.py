"""
Bot de Telegram: Home Assistant.
Gestiona listas de tareas (to-do) por usuario.
"""
import os
import re
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from todo_storage import (
    init_db,
    add_todo,
    list_todos,
    toggle_todo,
    delete_todo,
    get_todo,
    LIST_TYPE_HACER,
    LIST_TYPE_COMPRAR,
    LIST_TYPE_WISHLIST,
)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise SystemExit("Falta TELEGRAM_BOT_TOKEN en .env. Copia .env.example a .env y configura el token.")


EMOJI_COMPRAR = "💵"
EMOJI_HACER = "🔨"
EMOJI_WISHLIST = "🎁"


def _parse_number(text: str) -> int | None:
    """Extrae el primer número del texto (índice de la lista para el usuario)."""
    text = (text or "").strip()
    if not text:
        return None
    m = re.match(r"^\s*(\d+)", text)
    return int(m.group(1)) if m else None


def _strip_list_emojis(text: str) -> str:
    """Quita los emojis de lista del texto."""
    return (
        text.replace(EMOJI_COMPRAR, "")
        .replace(EMOJI_HACER, "")
        .replace(EMOJI_WISHLIST, "")
        .strip()
    )


def _parse_multi_items(text: str) -> list[str]:
    """Separa el texto en ítems por líneas o comas. Quita guiones/viñetas al inicio."""
    items = []
    for line in text.split("\n"):
        for part in line.split(","):
            s = part.strip()
            for prefix in ("- ", "* ", "• ", "— "):
                if s.startswith(prefix):
                    s = s[len(prefix) :].strip()
                    break
            if s:
                items.append(s)
    return items


def _build_list_message_and_keyboard(
    chat_id: int,
    list_type: str = LIST_TYPE_HACER,
) -> tuple[str, InlineKeyboardMarkup] | None:
    """Construye el texto y teclado de la lista. list_type: 'hacer', 'comprar' o 'wishlist'."""
    items = list_todos(chat_id, include_done=False, list_type=list_type)
    if not items:
        return None
    lines = [item.display(i) for i, item in enumerate(items, 1)]
    if list_type == LIST_TYPE_COMPRAR:
        title = "💵 *Por comprar:*"
    elif list_type == LIST_TYPE_WISHLIST:
        title = "🎁 *Wishlist:*"
    else:
        title = "🔨 *Por hacer:*"
    msg = f"{title}\n\n" + "\n".join(lines)
    msg += "\n\nToca un botón para marcarlo como hecho."
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(text=f"⬜ {item.text}", callback_data=f"todo_toggle:{item.id}")]
        for item in items
    ])
    return msg, keyboard


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bienvenida y resumen. En un grupo la lista es compartida entre todos."""
    user = update.effective_user
    chat = update.effective_chat
    msg = (
        f"Hola, {user.first_name or 'ahí'} 👋\n\n"
        "Soy tu asistente de listas compartidas (comprar, hacer, wishlist).\n\n"
        "• **lista** — ver listas (te pregunto cuál)\n"
        "• **ayuda** — cómo funciona\n\n"
        "Para *añadir* algo, escribe el texto con el emoji:\n"
        "💵 comprar · 🔨 hacer · 🎁 wishlist\n\n"
    )
    if chat.type in ("group", "supergroup"):
        msg += "👥 En este grupo las listas son *compartidas* entre todos."
    await update.message.reply_text(msg, parse_mode="Markdown")


# Palabras que piden ver la lista (solo la palabra, sin /)
LISTA_KEYWORDS = {"lista", "list", "tareas", "ver lista", "mi lista", "qué tengo"}

# Palabras que muestran la ayuda (solo la palabra, sin /)
HELP_KEYWORDS = {"ayuda", "help"}


def _get_help_text() -> str:
    """Texto de ayuda que explica cómo funciona el sistema."""
    return (
        "📖 *Ayuda — Listas compartidas*\n\n"
        "*Palabras clave* (escribe solo la palabra):\n"
        "• **lista** — eliges qué lista ver (hacer, comprar, wishlist)\n"
        "• **ayuda** — muestra este mensaje\n\n"
        "*Tres listas:*\n"
        "💵 *Por comprar* — cosas a comprar\n"
        "🔨 *Por hacer* — tareas\n"
        "🎁 *Wishlist* — deseos\n\n"
        "*Añadir ítems:*\n"
        "Escribe el texto *con el emoji* de la lista:\n"
        "• leche 💵 → comprar\n"
        "• arreglar ventana 🔨 → hacer\n"
        "• libro de cocina 🎁 → wishlist\n\n"
        "*Varios ítems en un mensaje:*\n"
        "Por comas: _pan, atun, leche 💵_\n"
        "O uno por línea: _-pan_, _-atun_, _-leche 💵_\n\n"
        "*Ver una lista:*\n"
        "• Escribe **lista** y elige con el botón.\n"
        "• O escribe solo **💵**, **🔨** o **🎁** para ver esa lista.\n"
        "• Toca cada ítem en la lista para marcarlo como hecho.\n\n"
        "👥 En grupos, las listas son compartidas entre todos."
    )


async def cmd_todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Añade una tarea: /todo Comprar leche."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = " ".join(context.args).strip() if context.args else ""
    if not text:
        await update.message.reply_text("Escribe la tarea después de /todo, o simplemente escribe la tarea en el chat.")
        return
    item = add_todo(chat_id, user_id, text, list_type=LIST_TYPE_HACER)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔨 Ver por hacer", callback_data="todo_showlist:hacer")]])
    await update.message.reply_text(f"✅ Añadido: {item.text}", reply_markup=keyboard)


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista las tareas pendientes del chat (por hacer)."""
    chat_id = update.effective_chat.id
    built = _build_list_message_and_keyboard(chat_id, list_type=LIST_TYPE_HACER)
    if not built:
        await update.message.reply_text("No hay tareas pendientes. Escribe lo que quieras hacer y lo añado.")
        return
    text, reply_markup = built
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def on_todo_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback de los botones inline para marcar/desmarcar tareas."""
    query = update.callback_query
    chat_id = query.message.chat.id
    data = query.data or ""
    if not data.startswith("todo_toggle:"):
        await query.answer()
        return

    try:
        todo_id = int(data.split(":", 1)[1])
    except ValueError:
        await query.answer()
        return

    updated = toggle_todo(chat_id, todo_id)
    if not updated:
        await query.answer("Esta tarea ya no existe.", show_alert=True)
        return
    await query.answer()
    item = get_todo(chat_id, todo_id)
    list_type = item.list_type if item else LIST_TYPE_HACER
    built = _build_list_message_and_keyboard(chat_id, list_type=list_type)
    if not built:
        await query.edit_message_text("No hay nada pendiente en esta lista.")
        return
    text, reply_markup = built
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def on_show_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback 'Ver lista': envía la lista (hacer o comprar) en un mensaje nuevo."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    data = (query.data or "").strip()
    list_type = LIST_TYPE_HACER
    if data == "todo_showlist:comprar":
        list_type = LIST_TYPE_COMPRAR
    elif data == "todo_showlist:wishlist":
        list_type = LIST_TYPE_WISHLIST
    built = _build_list_message_and_keyboard(chat_id, list_type=list_type)
    if not built:
        await query.message.reply_text("No hay nada pendiente en esta lista.")
        return
    text, reply_markup = built
    await query.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def on_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Texto libre: ayuda/lista por palabra; emoji → lista o añadir; sin emoji → preguntar lista."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()
    if not text:
        return
    # Solo la palabra "ayuda" o "help" → mostrar ayuda
    if text.lower() in HELP_KEYWORDS:
        await update.message.reply_text(_get_help_text(), parse_mode="Markdown")
        return
    rest = text.replace(" ", "").replace("\n", "")
    if rest == EMOJI_COMPRAR:
        built = _build_list_message_and_keyboard(chat_id, list_type=LIST_TYPE_COMPRAR)
        if not built:
            await update.message.reply_text("No hay nada en la lista de compras. Escribe algo con 💵 para añadir.")
            return
        msg, reply_markup = built
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
        return
    if rest == EMOJI_HACER:
        built = _build_list_message_and_keyboard(chat_id, list_type=LIST_TYPE_HACER)
        if not built:
            await update.message.reply_text("No hay tareas pendientes. Escribe lo que quieras hacer y lo añado.")
            return
        msg, reply_markup = built
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
        return
    if rest == EMOJI_WISHLIST:
        built = _build_list_message_and_keyboard(chat_id, list_type=LIST_TYPE_WISHLIST)
        if not built:
            await update.message.reply_text("No hay nada en la wishlist. Escribe algo con 🎁 para añadir.")
            return
        msg, reply_markup = built
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
        return
    if text.lower() in LISTA_KEYWORDS:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔨 Por hacer", callback_data="todo_showlist:hacer"),
                InlineKeyboardButton("💵 Por comprar", callback_data="todo_showlist:comprar"),
            ],
            [InlineKeyboardButton("🎁 Wishlist", callback_data="todo_showlist:wishlist")],
        ])
        await update.message.reply_text("¿Qué lista quieres ver?", reply_markup=keyboard)
        return
    if EMOJI_COMPRAR in text:
        raw_items = _parse_multi_items(text)
        items_clean = [t for t in (_strip_list_emojis(i) for i in raw_items) if t]
        if not items_clean:
            await update.message.reply_text("Escribe qué quieres comprar junto al 💵. Ejemplo: leche 💵")
            return
        for t in items_clean:
            add_todo(chat_id, user_id, t, list_type=LIST_TYPE_COMPRAR)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("💵 Ver por comprar", callback_data="todo_showlist:comprar")]])
        msg = f"✅ Añadidos a compras ({len(items_clean)}): " + ", ".join(items_clean[:5])
        if len(items_clean) > 5:
            msg += f" y {len(items_clean) - 5} más"
        await update.message.reply_text(msg, reply_markup=keyboard)
        return
    if EMOJI_HACER in text:
        raw_items = _parse_multi_items(text)
        items_clean = [t for t in (_strip_list_emojis(i) for i in raw_items) if t]
        if not items_clean:
            await update.message.reply_text("Escribe la tarea junto al 🔨. Ejemplo: arreglar puerta 🔨")
            return
        for t in items_clean:
            add_todo(chat_id, user_id, t, list_type=LIST_TYPE_HACER)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔨 Ver por hacer", callback_data="todo_showlist:hacer")]])
        msg = f"✅ Añadidos ({len(items_clean)}): " + ", ".join(items_clean[:5])
        if len(items_clean) > 5:
            msg += f" y {len(items_clean) - 5} más"
        await update.message.reply_text(msg, reply_markup=keyboard)
        return
    if EMOJI_WISHLIST in text:
        raw_items = _parse_multi_items(text)
        items_clean = [t for t in (_strip_list_emojis(i) for i in raw_items) if t]
        if not items_clean:
            await update.message.reply_text("Escribe el deseo junto al 🎁. Ejemplo: libro de cocina 🎁")
            return
        for t in items_clean:
            add_todo(chat_id, user_id, t, list_type=LIST_TYPE_WISHLIST)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎁 Ver wishlist", callback_data="todo_showlist:wishlist")]])
        msg = f"✅ Añadidos a la wishlist ({len(items_clean)}): " + ", ".join(items_clean[:5])
        if len(items_clean) > 5:
            msg += f" y {len(items_clean) - 5} más"
        await update.message.reply_text(msg, reply_markup=keyboard)
        return
    # Texto sin emoji (ej: "hola como estás") → no hacemos nada, para no molestar


async def on_add_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback al elegir lista para un mensaje sin emoji: todo_add_to:hacer, comprar o wishlist."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    data = (query.data or "").strip()
    if not data.startswith("todo_add_to:"):
        return
    if "comprar" in data:
        list_type = LIST_TYPE_COMPRAR
    elif "wishlist" in data:
        list_type = LIST_TYPE_WISHLIST
    else:
        list_type = LIST_TYPE_HACER
    pending_key = f"pending_add_{user_id}"
    pending = context.chat_data.pop(pending_key, None)
    if not pending:
        await query.edit_message_text("No tengo nada pendiente de añadir. Escribe de nuevo la tarea.")
        return
    # Un solo ítem (text) o varios (items)
    if "items" in pending:
        to_add = pending["items"]
    elif pending.get("text"):
        to_add = [pending["text"]]
    else:
        await query.edit_message_text("No tengo nada pendiente de añadir. Escribe de nuevo la tarea.")
        return
    for t in to_add:
        add_todo(chat_id, user_id, t, list_type=list_type)
    n = len(to_add)
    if list_type == LIST_TYPE_COMPRAR:
        btn = InlineKeyboardButton("💵 Ver por comprar", callback_data="todo_showlist:comprar")
        msg = f"✅ Añadidos a compras ({n}): " + ", ".join(to_add[:5]) + (f" y {n - 5} más" if n > 5 else "")
    elif list_type == LIST_TYPE_WISHLIST:
        btn = InlineKeyboardButton("🎁 Ver wishlist", callback_data="todo_showlist:wishlist")
        msg = f"✅ Añadidos a la wishlist ({n}): " + ", ".join(to_add[:5]) + (f" y {n - 5} más" if n > 5 else "")
    else:
        btn = InlineKeyboardButton("🔨 Ver por hacer", callback_data="todo_showlist:hacer")
        msg = f"✅ Añadidos ({n}): " + ", ".join(to_add[:5]) + (f" y {n - 5} más" if n > 5 else "")
    keyboard = InlineKeyboardMarkup([[btn]])
    await query.edit_message_text(msg, reply_markup=keyboard)


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Marca o desmarca una tarea por número: /done 2."""
    chat_id = update.effective_chat.id
    num = _parse_number(" ".join(context.args) if context.args else "")
    if num is None or num < 1:
        await update.message.reply_text("Uso: /done <número>\nEjemplo: /done 2")
        return
    items = list_todos(chat_id, include_done=False, list_type=LIST_TYPE_HACER)
    if num > len(items):
        await update.message.reply_text(f"No existe la tarea número {num}. Usa /list para ver los números.")
        return
    item = items[num - 1]
    updated = toggle_todo(chat_id, item.id)
    if updated:
        state = "completada ✅" if updated.done else "pendiente ⬜"
        await update.message.reply_text(f"Tarea marcada como {state}: {updated.text}")
    else:
        await update.message.reply_text("No se pudo actualizar la tarea.")


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Elimina una tarea por número: /delete 1."""
    chat_id = update.effective_chat.id
    num = _parse_number(" ".join(context.args) if context.args else "")
    if num is None or num < 1:
        await update.message.reply_text("Uso: /delete <número>\nEjemplo: /delete 1")
        return
    items = list_todos(chat_id, include_done=False, list_type=LIST_TYPE_HACER)
    if num > len(items):
        await update.message.reply_text(f"No existe la tarea número {num}. Usa /list para ver los números.")
        return
    item = items[num - 1]
    if delete_todo(chat_id, item.id):
        await update.message.reply_text(f"🗑 Eliminada: {item.text}")
    else:
        await update.message.reply_text("No se pudo eliminar la tarea.")


def main() -> None:
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("todo", cmd_todo))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("todos", cmd_list))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(CallbackQueryHandler(on_todo_toggle, pattern=r"^todo_toggle:"))
    app.add_handler(CallbackQueryHandler(on_show_list, pattern=r"^todo_showlist:(hacer|comprar|wishlist)$"))
    app.add_handler(CallbackQueryHandler(on_add_to_list, pattern=r"^todo_add_to:(hacer|comprar|wishlist)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_message))
    print("Bot en marcha. Detén con Ctrl+C.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
