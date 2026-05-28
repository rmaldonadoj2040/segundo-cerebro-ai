# 🧠 Segundo Cerebro — Guía paso a paso

> Comentaste **"cerebro"** y aquí está todo. Esta guía te lleva de cero a tener tu
> propio **Segundo Cerebro** funcionando en Obsidian: tú pegas tus notas, el sistema
> las ordena, conecta tus ideas y hasta te responde preguntas sobre lo que sabes.
>
> No necesitas ser programador. Vas a copiar y pegar comandos. Si algo se traba,
> al final hay una sección **"Si te trabas"** con la solución a los errores más comunes.

**Repositorio (el código vive aquí):**
👉 https://github.com/rmaldonadoj2040/segundo-cerebro-ai

---

## ¿Qué es esto exactamente?

Es un sistema que toma tus notas sueltas en texto (lo que lees, escuchas, anotas)
y automáticamente:

1. **Las ordena** y traduce todo a español.
2. **Extrae los conceptos, autores, libros, tecnologías y tensiones** que aparecen.
3. **Conecta las ideas entre sí** con enlaces, como un mapa mental.
4. **Genera un "vault" de Obsidian**: una carpeta navegable con todo conectado.
5. **Te deja preguntarle cosas** y te responde usando solo *tus* notas.

El resultado lo abres en **Obsidian** (una app gratuita) y ves tu conocimiento
como una red de ideas conectadas.

---

## Lo que vas a necesitar

| Cosa | ¿Para qué? | ¿Gratis? |
|---|---|---|
| **Python 3.11 o más nuevo** | Es el motor que hace correr el sistema | ✅ Sí |
| **Obsidian** | Para ver y navegar tu cerebro | ✅ Sí |
| **El código del proyecto** (GitHub) | El sistema en sí | ✅ Sí |
| **Una llave de OpenAI** *(opcional)* | Para que la IA genere contenido real | 💵 Cuesta centavos por uso |

> **Importante:** puedes probar TODO sin gastar un peso usando el **modo demo**
> (más abajo). La llave de OpenAI solo hace falta cuando quieras procesar *tus*
> notas reales con IA de verdad.

---

## Antes de empezar: instala lo básico

### 1) Python 3.11+

Primero revisa si ya lo tienes. Abre tu terminal y escribe:

```bash
python3 --version
```

- Si dice `Python 3.11.x` o más nuevo → ✅ listo, salta al siguiente paso.
- Si dice 3.10 o menos, o da error → instala una versión nueva:
  - **Mac:** instala desde [python.org/downloads](https://www.python.org/downloads/) o con Homebrew: `brew install python@3.12`
  - **Windows:** descarga desde [python.org/downloads](https://www.python.org/downloads/) y **marca la casilla "Add Python to PATH"** durante la instalación.

> ¿No sabes abrir la terminal?
> - **Mac:** abre Spotlight (⌘ + Espacio), escribe "Terminal" y dale Enter.
> - **Windows:** busca "PowerShell" en el menú de inicio.

### 2) Obsidian

Descárgalo gratis en [obsidian.md](https://obsidian.md/). No lo configures todavía;
lo usaremos al final.

---

## Paso 1 — Descargar el proyecto

Tienes dos formas. Elige la que te resulte más cómoda.

**Opción A — Descargar el ZIP (más fácil, sin comandos):**
1. Entra a https://github.com/rmaldonadoj2040/llm-knowledge-studio
2. Botón verde **"Code"** → **"Download ZIP"**.
3. Descomprime el ZIP en una carpeta fácil de encontrar (ej. tu Escritorio).

**Opción B — Con git (si ya lo tienes instalado):**
```bash
git clone https://github.com/rmaldonadoj2040/llm-knowledge-studio.git
```

Ahora **entra a la carpeta del proyecto** desde la terminal:
```bash
cd llm-knowledge-studio
```

> 💡 Tip: si no sabes la ruta, escribe `cd ` (con espacio) y **arrastra la carpeta**
> desde el explorador a la terminal. Te pega la ruta sola.

---

## Paso 2 — Preparar el entorno

Esto crea un "espacio aislado" para que el proyecto no se mezcle con el resto de
tu computadora. Copia y pega los comandos uno por uno.

**Mac / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Cuando veas `(.venv)` al inicio de la línea de tu terminal, estás dentro del
entorno. 👍

---

## Paso 3 — Configurar la llave

Copia el archivo de configuración de ejemplo:

**Mac / Linux:**
```bash
cp .env.example .env
```
**Windows:**
```powershell
copy .env.example .env
```

Ahora abre el archivo `.env` con cualquier editor de texto. Vas a elegir **uno**
de estos tres modos:

### Modo 1 — Demo gratis (recomendado para tu primera vez)
Déjalo tal cual viene:
```
OPENAI_API_KEY=mock
```
El sistema generará contenido de ejemplo, **sin conexión y sin costo**. Perfecto
para ver cómo funciona todo antes de gastar nada.

### Modo 2 — IA real con OpenAI (cuando quieras procesar tus notas de verdad)
```
OPENAI_API_KEY=sk-tu-llave-aqui
LLM_MODEL=gpt-4o-mini
```
Consigues tu llave en [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
El modelo `gpt-4o-mini` es barato (centavos por documento).

### Modo 3 — 100% local y gratis (avanzado)
Si usas [Ollama](https://ollama.com/) o LM Studio en tu compu:
```
OPENAI_API_KEY=local
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3
```

> Guarda el archivo `.env`. **Nunca lo compartas ni lo subas a internet:** ahí va tu llave.

---

## Paso 4 — Tu primera prueba (sin costo)

Antes de tocar tus notas reales, corre la **demo**. Usa textos de ejemplo, no toca
nada tuyo y no cuesta nada:

```bash
python3 scripts/run_demo.py
```

Esto va a:
- Tomar unos documentos de ejemplo.
- Construir un cerebro de prueba en la carpeta `demo_workspace/`.
- Validar que todo quedó bien conectado.
- Hacerle una pregunta de ejemplo y responderla.

Si termina diciendo **"Demo complete."**, ¡felicidades! El sistema funciona en tu
máquina. 🎉

Para verlo: abre Obsidian → **"Open folder as vault"** → elige la carpeta
`demo_workspace/vault/`. Abre `Inicio.md` y activa la **Vista de Grafo** para ver
las ideas conectadas.

---

## Paso 5 — Crea TU cerebro con tus notas

Ahora sí, con tus propias notas.

### 5.1 Cambia al Modo 2 (IA real)
Edita `.env` y pon tu llave de OpenAI (ver Paso 3, Modo 2).

### 5.2 Mete tus notas al sistema
Por cada archivo de texto (`.md`) que quieras agregar:
```bash
python3 scripts/ingest_file.py ruta/a/tu-nota.md
```
> ¿No tienes archivos `.md`? Crea uno simple: abre cualquier editor, pega tus
> ideas o un resumen de un video/libro, y guárdalo con extensión `.md`
> (ej. `mis-ideas.md`).

### 5.3 Procesa todo
```bash
python3 scripts/run_daily.py --verbose
```
Esto normaliza tus notas, extrae conceptos, los conecta y construye tu vault en
la carpeta `vault/`.

### 5.4 Revisa que todo quedó bien
```bash
python3 scripts/validate_vault.py
```
Te avisa si hay enlaces rotos o notas vacías.

---

## Paso 6 — Ábrelo en Obsidian

1. Abre Obsidian.
2. **"Open folder as vault"** → elige la carpeta `vault/` del proyecto.
3. Empieza por `Inicio.md` (es tu tablero principal).
4. Haz clic en los enlaces `[[así]]` para navegar entre ideas.
5. Abre la **Vista de Grafo** (ícono de círculos conectados) y mira tu cerebro. 🕸️

---

## Paso 7 — Hazle preguntas a tu cerebro

Lo mejor: puedes preguntarle cosas y te responde usando **solo tus notas**:

```bash
python3 scripts/ask.py "¿Qué tensión hay entre velocidad y profundidad?"
```

Cambia la pregunta por la que quieras. Las respuestas se guardan en `outputs/`.

---

## Comandos útiles (chuleta)

| Comando | Para qué sirve |
|---|---|
| `python3 scripts/run_demo.py` | Prueba gratis sin tocar tus notas |
| `python3 scripts/ingest_file.py <archivo.md>` | Agregar una nota al sistema |
| `python3 scripts/run_daily.py --verbose` | Procesar todo y construir el vault |
| `python3 scripts/validate_vault.py` | Revisar que no haya enlaces rotos |
| `python3 scripts/ask.py "<pregunta>"` | Preguntarle a tu cerebro |
| `python3 scripts/reset_demo.py` | Borrar solo la demo y empezar de nuevo |

> 💡 Recuerda: cada vez que abras una terminal nueva, primero activa el entorno con
> `source .venv/bin/activate` (Mac/Linux) o `.venv\Scripts\activate` (Windows).

---

## Si te trabas 🛟

**`python3: command not found`**
En Windows prueba con `python` en vez de `python3`. Si sigue fallando, reinstala
Python marcando *"Add Python to PATH"*.

**`No LLM API key found.`**
Te falta configurar el `.env`. Para probar sin costo, pon `OPENAI_API_KEY=mock`.

**`tomllib / tomli not available` o errores raros al correr**
Casi siempre es la versión de Python. Asegúrate de tener **3.11 o más nuevo**
(`python3 --version`) y vuelve a correr `pip install -r requirements.txt`.

**`No hay nuevas capturas para procesar.`**
No has metido notas todavía. Usa `python3 scripts/ingest_file.py tu-nota.md`.

**No veo `(.venv)` en la terminal**
No activaste el entorno. Corre de nuevo el comando de activación del Paso 2.

**Obsidian no muestra los enlaces conectados**
Asegúrate de abrir la carpeta correcta como vault (`vault/`, o `demo_workspace/vault/`
para la demo) y empieza por `Inicio.md`.

**La terminal me pide la ruta de un archivo y no la sé**
Arrastra el archivo o la carpeta desde el explorador hacia la terminal: pega la
ruta automáticamente.

---

## Privacidad y costos (léelo, importa)

- **Modo demo (`mock`)**: 100% offline, no envía nada a internet, no cuesta nada.
- **Modo OpenAI**: tus notas se envían a OpenAI para procesarse. Cuesta centavos,
  pero revisa qué subes si es información sensible.
- **Tu llave es secreta**: nunca compartas tu archivo `.env` ni la subas a GitHub.
- **Antes de publicar tu vault**: revisa el contenido generado, porque puede incluir
  fragmentos de tus notas privadas.

---

## ¿Y ahora qué?

- Empieza chico: mete 3–5 notas y mira cómo se conectan.
- Conviértelo en hábito: cada vez que aprendas algo, guárdalo como `.md` y vuelve
  a correr `run_daily.py`. Tu cerebro crece solo.
- Explora la Vista de Grafo en Obsidian. Ahí es donde se vuelve mágico. ✨

---

> Si esta guía te sirvió, etiquétame cuando muestres tu cerebro. Me encanta ver
> qué construye la comunidad. 🧠💛
>
> — Rafael
