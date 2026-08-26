# EchoBot - Publicaciones Automáticas en Telegram

Un bot de Telegram diseñado para publicar mensajes de forma periódica en canales y grupos, con soporte para contenido multimedia, botones, eliminación automática y copias de seguridad. Ideal para automatizar la difusión de contenido en comunidades de venta o información.

## ¿Qué hace exactamente?

Permite crear publicaciones con texto, imágenes, vídeos, audio o documentos, asignarlas a múltiples canales o grupos (o ambos), y programar su envío cada X minutos. También puede eliminar automáticamente los mensajes después de un tiempo definido, y todo se controla desde un panel de Telegram con botones. No necesita una interfaz web, aunque puede usar MongoDB para guardar copias de seguridad.

## Características clave

- **Publicación periódica**: cada publicación tiene su propio intervalo (en minutos).
- **Múltiples destinos**: una misma publicación puede enviarse a varios canales y/o grupos a la vez.
- **Formato enriquecido**: negrita, cursiva, subrayado, monoespaciado y botones con enlaces, usando etiquetas simples como `{{n}}texto{{n}}` y `{{b}}%Texto%&URL&{{b}}`.
- **Multimedia**: admite fotos, vídeos, audio, documentos y notas de voz.
- **Eliminación automática**: cada publicación puede tener un tiempo de eliminación posterior al envío.
- **Programación con hora exacta**: permite fijar una fecha y hora concretas para la próxima publicación.
- **Copias de seguridad**: guarda y restaura el estado completo (canales + publicaciones) usando MongoDB.
- **Sin interfaz web**: todo se maneja mediante comandos y botones desde Telegram.
- **Funciona en canales (requiere ser administrador) y en grupos (solo necesita ser miembro, a menos que el grupo restrinja a administradores)**.

## Requisitos

- Python 3.8 o superior.
- Una cuenta de Telegram con un bot creado (mediante @BotFather).
- (Opcional) Una base de datos MongoDB para las copias de seguridad.

## Instalación local

Clona el repositorio y sigue los pasos:

```bash
git clone https://github.com/tu-usuario/echobot-telegram.git
cd echobot-telegram
```

Crea y activa un entorno virtual (opcional pero recomendado):

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
# o
venv\Scripts\activate      # Windows
```

Instala las dependencias:

```bash
pip install -r requirements.txt
```

Crea el archivo `.env` en la raíz del proyecto con las siguientes variables (sin comillas):

```env
TOKEN=TU_TOKEN_AQUI
ADMIN_ID=TU_ID_DE_TELEGRAM_AQUI
# HOST_URL=opcional_solo_si_usas_mongodb
# WEBHOOK_URL=opcional_solo_si_usas_webhook
# PORT=5000
```

Cómo obtener el token y tu ID de Telegram:

- **Token**: habla con @BotFather en Telegram, crea un bot y te dará un token como `123456:ABC-DEF...`.
- **Tu ID**: habla con @userinfobot o @getmyid_bot, te darán tu número de ID.

Ejecuta el bot:

```bash
python main.py
```

Deberías ver logs como "Bot creado y handlers registrados" y "Arrancando con polling". Si todo va bien, el bot ya está en línea. Busca tu bot en Telegram y envía `/start` para probar.

## Guía de uso

Una vez que el bot esté en marcha, usa los siguientes comandos desde el chat privado con él:

- `/start`: mensaje de bienvenida.
- `/panel`: abre el menú principal con botones.
- `/host`: muestra la hora del servidor y la hora de Perú (útil para verificar la zona horaria).

### Menú principal

Desde `/panel` puedes:

1. **Canales**: ver la lista de canales/grupos registrados, añadir nuevos o eliminar existentes.
2. **Crear Post**: inicia el asistente para crear una publicación (selección de canales, contenido, intervalo y tiempo de eliminación).
3. **Ver posts creados**: lista todas las publicaciones existentes, permite ver su detalle, enviarlas ahora, modificar su intervalo o eliminar canales asociados.
4. **Iniciar/Detener hilo de publicación**: arranca o detiene el proceso que revisa y envía las publicaciones periódicamente.
5. **Copias de seguridad**: guarda o restaura el estado completo usando MongoDB (si está configurado).

### Crear una publicación paso a paso

1. Ve a `/panel` → "Crear Post".
2. Selecciona uno o varios canales/grupos de la lista.
3. Envía el contenido: puede ser texto (con formato), o un archivo (foto, vídeo, audio, etc.) acompañado de un texto opcional.
4. Ingresa el intervalo de publicación en **minutos** (ej. 120 para cada 2 horas). Si pones 0, solo se publicará una vez.
5. Opcionalmente, ingresa el tiempo de eliminación en minutos (debe ser menor que el intervalo de publicación). Si no quieres eliminación, escribe 0.
6. La publicación se crea y se añade a la lista. Para que se publique, debes iniciar el hilo desde el menú principal.

### Formato de texto y botones

El bot interpreta estas etiquetas en el texto de la publicación:

- `{{n}}texto{{n}}` → **negrita**
- `{{s}}texto{{s}}` → <u>subrayado</u>
- `{{i}}texto{{i}}` → *cursiva*
- `{{m}}texto{{m}}` → `monoespaciado`
- `{{b}}%Texto del botón%&https://ejemplo.com&{{b}}` → botón con enlace

Ejemplo:

```
{{n}}Oferta especial{{n}}
{{s}}Solo por hoy{{s}}
{{b}}%Comprar ahora%&https://tusitio.com&{{b}}
```

## Despliegue en Render (gratuito)

Render ofrece un plan gratuito para workers. Sigue estos pasos para tener el bot 24/7 sin necesidad de mantener tu PC encendida.

### 1. Sube el código a un repositorio en GitHub (público o privado).

### 2. Ve a [render.com](https://render.com) y crea una cuenta (puedes usar GitHub).

### 3. En el panel, haz clic en **"New +"** y selecciona **"Background Worker"**.

### 4. Conecta tu repositorio de GitHub y selecciona la rama principal.

### 5. Render detectará automáticamente el `Procfile` que ya está en el repositorio. Si no, créalo con:

```
worker: python main.py
```

### 6. Añade las mismas variables de entorno que usaste localmente (Token, ADMIN_ID, HOST_URL si aplica). En Render, ve a la sección **"Environment"** y agrégalas una por una.

### 7. Haz clic en **"Create Worker"**. Render construirá el entorno e iniciará el bot en unos minutos.

### 8. Una vez que el estado cambie a "Live", el bot estará funcionando. Busca tu bot en Telegram y verifica que responde.

### Nota sobre el plan gratuito de Render

El worker puede dormirse tras 15 minutos sin actividad. Para mantenerlo despierto, puedes usar un servicio externo como [UptimeRobot](https://uptimerobot.com/) que haga una petición a un endpoint dummy cada 5 minutos. O simplemente no te preocupes: el bot se reactiva automáticamente cuando recibe un mensaje.

## Permisos necesarios en Telegram

- **Canales**: el bot debe ser **administrador** con permiso de **publicar mensajes**. Sin esto, no podrá enviar nada.
- **Grupos**: el bot solo necesita ser **miembro**, a menos que el grupo tenga activada la opción "Solo administradores pueden enviar mensajes". En ese caso, también necesitará ser administrador.

El bot comprueba estos permisos al inicio y al añadir un nuevo chat, y elimina automáticamente los que no cumplan.

## Estructura del proyecto

```
EchoBot/
├── main.py              # Punto de entrada
├── Procfile             # Para Render
├── requirements.txt     # Dependencias
├── .env.example         # Variables de entorno de ejemplo
├── src/
│   ├── config.py        # Configuración desde variables de entorno
│   ├── database.py      # SQLite para canales
│   ├── persistence.py   # Guardado/carga con dill
│   ├── scheduler.py     # Hilo de publicación
│   ├── publisher.py     # Envío y eliminación de mensajes
│   ├── utils.py         # Funciones auxiliares (envío de mensajes largos, horarios, comprobación de permisos)
│   ├── bot.py           # Creación del bot y registro de handlers
│   └── handlers/
│       ├── commands.py  # Comandos /start, /panel, /host
│       ├── callbacks.py # Router principal de callbacks
│       ├── channels.py  # Gestión de canales (añadir, listar, eliminar)
│       ├── publications.py # Creación, modificación y eliminación de publicaciones
│       └── backup.py    # Copias de seguridad con MongoDB
```

## Posibles problemas y soluciones

### Error de conexión a la API de Telegram (timeout)

Si ves `TimeoutError` o `ConnectionResetError`, tu red está bloqueando o limitando la conexión a `api.telegram.org`. Prueba:

- Aumentar los timeouts en `bot.py` (ya está configurado con 60 segundos).
- Usar una VPN.
- Configurar un proxy: en `bot.py`, añade `apihelper.PROXY = {'https': 'http://proxy:puerto'}`.

### El bot no acepta un grupo porque "no soy administrador"

Sí, el bot se comporta así: para grupos normales solo exige ser miembro; la advertencia "no soy administrador" aparece si el grupo está restringido o si intentas añadir un canal. Si ves ese error en un grupo donde el bot es miembro, comprueba que el grupo no tenga activada la opción "solo administradores pueden enviar mensajes".

### Los mensajes no llegan al grupo

El bot debe ser miembro del grupo. Si no lo es, añádelo manualmente. También verifica que el grupo no esté restringido a solo administradores.

## Licencia

Este proyecto se distribuye bajo la licencia MIT. Úsalo, modifícalo y mejóralo a tu antojo, pero no olvides dar crédito.

## Agradecimientos

A Meidan, por plantear la necesidad que dio origen a este proyecto. A los administradores de grupos de venta, por no bloquear al bot (todavía). Y a ti, por leer hasta aquí.
```
