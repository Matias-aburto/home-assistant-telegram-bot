# Home Assistant Telegram Bot

Bot de Telegram que actúa como asistente del hogar. Gestiona listas compartidas por chat (grupo o privado) usando texto muy sencillo:

- 💵 Lista de cosas por comprar
- 🔨 Lista de cosas por hacer
- 🎁 Wishlist (deseos)

En un grupo, todos ven y editan las mismas listas.

## Requisitos

- Python 3.10+ (en Render se recomienda 3.11, ver `runtime.txt`)
- Cuenta de Telegram
- Token de bot (obtener con [@BotFather](https://t.me/BotFather))

## Instalación local

1. Clona o descarga el proyecto y entra en la carpeta:
   ```bash
   cd home-assistant-telegram-bot
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
     ```env
     TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...
     ```

## Ejecución local

```bash
python bot.py
```

Deja la terminal abierta. Para detener el bot: `Ctrl+C`.

## Despliegue en Render (Worker)

1. Sube este repo a GitHub (ya preparado para ello).
2. En Render:
   - Crea un **Background Worker** desde este repositorio.
   - Start command:
     ```bash
     python bot.py
     ```
   - Variables de entorno:
     - `TELEGRAM_BOT_TOKEN` = el token de tu bot.
3. Asegúrate de desactivar el **Group Privacy** de tu bot en [@BotFather](https://t.me/BotFather) para que pueda leer mensajes normales en grupos.

## Despliegue en Fly.io

1. Instala la CLI de Fly.io y autentícate:
   ```bash
   flyctl auth login
   ```

2. Desde la carpeta del proyecto, crea la app (usando el `Dockerfile` incluido):
   ```bash
   flyctl launch --no-deploy
   ```
   - Cuando pregunte por base de datos o servicios extra, puedes decir que no.

3. Configura el token del bot como secreto:
   ```bash
   flyctl secrets set TELEGRAM_BOT_TOKEN=tu_token_aqui
   ```

4. Despliega:
   ```bash
   flyctl deploy
   ```

Fly usará el `Dockerfile` para construir la imagen y ejecutará:
```bash
python bot.py
```

## Uso básico

- Escribe `ayuda` para ver las instrucciones dentro del chat.
- Escribe `lista` para elegir qué lista ver (hacer, comprar, wishlist).
- Por defecto, lo que escribas va a la **lista de compras** (también varios ítems por comas o líneas).
- Para otras listas usa el emoji:
  - `arreglar puerta 🔨` → por hacer
  - `libro de cocina 🎁` → wishlist
- El emoji 💵 sigue siendo válido para compras pero ya no es obligatorio.

## Datos

- Las listas se guardan en `todos.db` (SQLite) en la carpeta del proyecto.
- Cada chat (grupo o privado) tiene sus propias listas compartidas.

## Próximos pasos

El bot está pensado para crecer: recordatorios, integración con Home Assistant, etc. La estructura permite añadir más módulos y comandos más adelante.
