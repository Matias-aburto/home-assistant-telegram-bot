# Home Assistant Bot (Telegram)

Bot de Telegram que actúa como asistente del hogar. Primera función: **listas de tareas (to-do)** por usuario. Cada persona que use el bot tiene su propia lista.

## Requisitos

- Python 3.10+
- Cuenta de Telegram
- Token de bot (obtener con [@BotFather](https://t.me/BotFather))

## Instalación

1. Clona o descarga el proyecto y entra en la carpeta:
   ```bash
   cd home-assistant
   ```

2. Crea y activa un entorno virtual (recomendado):
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   # source venv/bin/activate   # Linux/macOS
   ```

3. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Configura el token del bot:
   - Copia `.env.example` a `.env`
   - En [@BotFather](https://t.me/BotFather) crea un bot con `/newbot` y copia el token
   - Pega el token en `.env`:
     ```
     TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...
     ```

## Ejecución

```bash
python bot.py
```

Deja la terminal abierta. Para detener el bot: `Ctrl+C`.

## Uso (lista de tareas)

| Comando | Descripción |
|--------|-------------|
| `/start` | Bienvenida y ayuda |
| `/todo <texto>` | Añadir tarea (ej: `/todo Comprar leche`) |
| `/list` o `/todos` | Ver tu lista de tareas |
| `/done <número>` | Marcar o desmarcar tarea (ej: `/done 2`) |
| `/delete <número>` | Borrar tarea (ej: `/delete 1`) |

Los números en `/done` y `/delete` son los que salen en la lista al usar `/list`.

## Datos

- Las tareas se guardan en `todos.db` (SQLite) en la carpeta del proyecto.
- Cada usuario de Telegram tiene su propia lista (identificada por su `user_id`).

## Próximos pasos

El bot está pensado para crecer: recordatorios, integración con Home Assistant, etc. La estructura permite añadir más módulos y comandos más adelante.
