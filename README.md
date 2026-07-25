# Guardian AI

Guardian AI es un prototipo de revisión de código para un equipo de
e-commerce. Combina herramientas determinísticas como Ruff y Pytest con
análisis semántico mediante Gemini, consolida los resultados y decide si un
cambio está listo para avanzar.

## Capacidades demostradas

1. **Revisar cambios de código y brindar feedback útil y accionable.**  
   El sistema ejecuta herramientas determinísticas, analiza el código con un
   proveedor de IA, clasifica hallazgos y presenta un reporte con evidencia,
   decisión y propuestas.

2. **Decidir, con criterios explícitos, si un cambio está listo para avanzar.**  
   La decisión final se basa en la presencia o ausencia de hallazgos
   bloqueantes (regla determinística del Decision Agent).

El sistema también genera **propuestas de corrección** asistidas por IA, pero:

- no se aplican automáticamente;
- por ahora requieren revisión de un usuario.

## Cómo funciona

1. El usuario solicita una revisión desde el frontend (o vía API).
2. Ruff analiza problemas estáticos sobre la ruta del proyecto.
3. Pytest ejecuta las pruebas del proyecto de ejemplo.
4. Gemini (u otro proveedor configurado) analiza el código enviado y la
   evidencia determinística.
5. LangGraph coordina los pasos del workflow.
6. Los hallazgos se clasifican en bloqueantes y no bloqueantes.
7. El sistema decide si el cambio puede avanzar.
8. PostgreSQL guarda revisión, evidencia, hallazgos, propuestas y decisión.
9. El historial permite recuperar revisiones sin volver a ejecutar el análisis.

## Arquitectura

| Capa | Tecnologías |
|---|---|
| **Frontend** | React, Vite, TypeScript, Tailwind CSS |
| **Backend** | Python, FastAPI, LangGraph, SQLAlchemy, Alembic |
| **IA** | `GeminiProvider` (proveedor real principal de la demo), `OpenRouterProvider` (adaptador alternativo), `MockProvider` (tests y ejecución sin proveedor real) |
| **Herramientas** | Ruff, Pytest |
| **Persistencia** | PostgreSQL |
| **Infraestructura** | Docker Compose |

Los adaptadores de IA implementan la interfaz `AIProvider`
(`analyze_code`, `propose_fix`). El orchestrator y el Decision Agent dependen
solo de esa abstracción, no de Gemini u OpenRouter. Cambiar el proveedor se
hace con `AI_PROVIDER` y las variables del adaptador elegido, sin modificar el
workflow de LangGraph.

## Proyecto de ejemplo

La demo trabaja sobre:

```text
examples/ecommerce
```

Es un mini proyecto de e-commerce con defectos intencionales, por ejemplo:

- import sin utilizar;
- validaciones faltantes en `discount_percent`;
- reserva de inventario superior al stock disponible;
- tests preparados para demostrar los fallos.

El alcance actual **no** permite cargar cualquier repositorio desde la
interfaz. La ruta por defecto del formulario es `./examples/ecommerce`, y en
Docker Compose ese directorio se monta en el backend.

## Requisitos

Para levantar el sistema con Docker:

- Docker Desktop
- Docker Compose
- Git
- una API key de Gemini obtenida desde [Google AI Studio](https://aistudio.google.com/apikey)

Python y Node.js no son obligatorios si usás solo Docker Compose. Sí hacen
falta para desarrollo local (ver más abajo).

## Instalación rápida con Docker

### PowerShell (Windows)

```powershell
git clone https://github.com/TotoShafff/guardian-ai.git
cd guardian-ai

Copy-Item .env.example .env
```

Editá `.env` y configurá al menos:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=tu_api_key_aqui
GEMINI_MODEL=gemini-3.5-flash-lite
```

Luego:

```powershell
docker compose up -d --build
docker compose ps
```

### bash (macOS / Linux)

```bash
git clone <url-del-repositorio>
cd guardian-ai

cp .env.example .env
```

Completá las mismas variables en `.env` y ejecutá:

```bash
docker compose up -d --build
docker compose ps
```

### URLs

| Servicio | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API docs (OpenAPI) | http://localhost:8000/docs |

### Apagar

```powershell
docker compose down
```

```bash
docker compose down
```

No incluyas claves reales en el repositorio ni en capturas públicas.

## Variables de entorno

Valores relevantes (verificados contra `.env.example` y `docker-compose.yml`):

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | URL SQLAlchemy/psycopg del backend (`...@db:5432/...` dentro de Compose; `localhost` si el backend corre en el host) |
| `POSTGRES_DB` | Nombre de la base del servicio `db` |
| `POSTGRES_USER` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL |
| `AI_PROVIDER` | Proveedor de IA: `mock`, `gemini` u `openrouter` |
| `GEMINI_API_KEY` | API key de Gemini (requerida si `AI_PROVIDER=gemini`) |
| `GEMINI_MODEL` | Modelo Gemini (por defecto `gemini-3.5-flash-lite`) |
| `GEMINI_BASE_URL` | Endpoint compatible OpenAI de Gemini |
| `GEMINI_TIMEOUT_SECONDS` | Timeout de llamadas a Gemini |
| `OPENROUTER_API_KEY` | API key de OpenRouter (si `AI_PROVIDER=openrouter`) |
| `OPENROUTER_MODEL` | Modelo en OpenRouter |
| `OPENROUTER_BASE_URL` | Base URL de la API de OpenRouter |
| `OPENROUTER_TIMEOUT_SECONDS` | Timeout de llamadas a OpenRouter |
| `VITE_API_BASE_URL` | Base URL que usa el navegador para llamar a la API (por defecto `http://localhost:8000/api`) |

Valores de `AI_PROVIDER`:

| Valor | Uso |
|---|---|
| `mock` | Sin API key ni red hacia un LLM; útil para tests y humo local |
| `gemini` | Proveedor real principal de la demo |
| `openrouter` | Adaptador alternativo |

`mock` no requiere API key.

## Uso de la aplicación

### Nueva revisión

En la pestaña **Nueva revisión**:

1. Completá la **referencia** (identificador legible: rama, ticket o demo).
2. Indicá la **ruta del proyecto** (por defecto `./examples/ecommerce`).
3. Revisá o editá el **código** enviado al análisis semántico.
4. Pulsá **Ejecutar revisión**.
5. Revisá el resultado: decisión, hallazgos, evidencia y propuestas.

Relación entre código y ruta:

- el **código visible** se utiliza para el análisis semántico del proveedor de IA;
- **Ruff y Pytest** trabajan sobre la ruta del proyecto; en la demo controlada,
  eso es `examples/ecommerce` montado en el backend.

No asumas que el sistema analiza cualquier proyecto arbitrario cargado desde la
UI: el escenario soportado de punta a punta es la demo de ejemplo.

### Historial

- cada revisión ejecutada se persiste en PostgreSQL;
- la pestaña **Historial** lista las revisiones guardadas;
- **Ver revisión** recupera el reporte completo con `GET /api/reviews/{review_id}`;
- consultar una revisión guardada **no** vuelve a llamar a Gemini ni ejecuta
  Ruff o Pytest.

## Interpretación del reporte

### Evidencia

Salida verificable de Ruff y Pytest (y metadatos asociados), independiente del
LLM.

### Hallazgos

Interpretación de los problemas encontrados, basada en evidencia determinística
y análisis semántico.

### Bloqueantes

Problemas que impiden que el cambio avance.

### No bloqueantes

Mejoras recomendadas que no detienen el cambio.

### Propuestas de corrección

Cambios sugeridos por Gemini (u otro proveedor).

Las propuestas se generan con IA y requieren revisión del desarrollador. En
esta versión no se aplican ni se validan automáticamente.

## Criterio de decisión

Regla real del sistema (Decision Agent):

- si existen hallazgos con severidad bloqueante, la revisión queda **bloqueada**;
- si no existen hallazgos bloqueantes, puede **aprobarse**.

La clasificación de severidad alimenta esa regla. Gemini no toma por sí solo la
decisión final: el estado `approved` / `blocked` lo define el consolidado
determinístico de hallazgos bloqueantes.

## API principal

Prefijo: `/api`.

| Método | Ruta | Qué hace |
|---|---|---|
| `POST` | `/api/reviews` | Ejecuta una revisión de forma síncrona y persiste el resultado completo |
| `GET` | `/api/reviews` | Lista resúmenes de revisiones persistidas (historial) |
| `GET` | `/api/reviews/{review_id}` | Devuelve una revisión guardada sin reejecutar el workflow |

Documentación interactiva: http://localhost:8000/docs

## Tests

### Backend

```bash
cd apps/backend
ruff check .
pytest
```

### Frontend

```bash
cd apps/frontend
npm run lint
npm test -- --run
npm run build
```

No hay un servicio Compose dedicado a ejecutar la suite completa; los comandos
anteriores asumen entorno de desarrollo local (o el mismo stack de dependencias
instalado en cada app).

## Desarrollo local sin Docker

Podés desarrollar cada app fuera de los contenedores. PostgreSQL sigue siendo
necesario para el backend (por ejemplo, solo el servicio `db` de Compose).

El flujo probado usa una **`.venv` en la raíz del repositorio** (no dentro de
`apps/backend`).

### Backend

Requisitos: Python 3.12+.

Desde la raíz del repositorio:

**PowerShell (Windows)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".\apps\backend[dev]"

# Necesario para que Pytest pueda importar el paquete `ecommerce`
# (equivalente a PYTHONPATH=/app/examples/ecommerce en Compose).
$env:PYTHONPATH = Join-Path $PWD "examples\ecommerce"
```

**bash (macOS / Linux)**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e "./apps/backend[dev]"

# Necesario para que Pytest pueda importar el paquete `ecommerce`
# (equivalente a PYTHONPATH=/app/examples/ecommerce en Compose).
export PYTHONPATH="$PWD/examples/ecommerce"
```

Configurá `DATABASE_URL` apuntando al host (por ejemplo en el `.env` de la
raíz), por ejemplo:

```env
DATABASE_URL=postgresql+psycopg://guardian:guardian@localhost:5432/guardian
AI_PROVIDER=mock
```

Migraciones (desde `apps/backend`, con la venv de la raíz ya activa):

```powershell
cd apps\backend
alembic upgrade head
cd ..\..
```

```bash
cd apps/backend
alembic upgrade head
cd ../..
```

Servidor (desde la **raíz** del repositorio, para que la ruta por defecto
`./examples/ecommerce` del formulario resuelva bien):

```powershell
# Si abriste una shell nueva, reactivá la venv y PYTHONPATH:
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = Join-Path $PWD "examples\ecommerce"

uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# Si abriste una shell nueva, reactivá la venv y PYTHONPATH:
source .venv/bin/activate
export PYTHONPATH="$PWD/examples/ecommerce"

uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

`PYTHONPATH` debe apuntar a `examples/ecommerce` (el directorio que contiene el
paquete `ecommerce/`), no a la raíz del repo. Sin eso, Pytest falla al
recolectar/importar los tests de la demo.

### Frontend

Requisitos: Node.js 22+ (alineado con la imagen Docker del frontend).

```bash
cd apps/frontend
npm ci
npm run dev
```

Por defecto el frontend espera la API en `http://localhost:8000/api`
(`VITE_API_BASE_URL`).

## Decisiones de diseño

- **LangGraph** para orquestar pasos explícitos y explicables.
- **Herramientas determinísticas + IA**, en lugar de depender solo del LLM.
- **PostgreSQL** para historial y trazabilidad del reporte.
- **Abstracción `AIProvider`** para cambiar modelos sin tocar el workflow.
- **Docker Compose** para reproducibilidad en un clon limpio.
- **Proyecto de ejemplo controlado** para una demo repetible.
- **Gemini Flash Lite** por velocidad y capa gratuita en la demo.

## Costos, tiempo, privacidad y operabilidad

**Costo**

- Gemini puede usarse en capa gratuita según el plan de Google AI Studio;
- `mock` evita costo de LLM en tests;
- la infraestructura de la demo corre en local con Docker.

**Tiempo**

- en observaciones locales, una revisión de la demo puede acercarse a unos
  **5 segundos** con Gemini;
- el tiempo varía según proveedor, red y carga.

**Privacidad**

- el código enviado al proveedor externo debe considerarse sensible;
- las claves viven en `.env`;
- `.env` no se versiona;

**Operabilidad**

- Docker Compose levanta frontend, backend y PostgreSQL;
- las migraciones Alembic se ejecutan al iniciar el contenedor backend
  (`alembic upgrade head` antes de Uvicorn);
- este README está pensado para un clon limpio.

## Limitaciones actuales

- trabaja sobre un proyecto de ejemplo fijo;
- no permite subir ZIP ni conectar GitHub;
- no tiene autenticación;
- no aplica automáticamente propuestas;
- depende de disponibilidad y límites del proveedor de IA;
- soporta principalmente el escenario Python de la demo.

## Mejoras futuras

- carga de proyectos;
- integración con GitHub;
- validación ejecutable de propuestas en sandbox;
- procesamiento asíncrono;
- autenticación;
- soporte ampliado para TypeScript;
- métricas y observabilidad.
- extra validación con implemtanción de SonarQube

## Estructura del repositorio

```text
guardian-ai/
├── apps/
│   ├── backend/          # FastAPI + LangGraph + persistencia
│   └── frontend/         # React + Vite
├── examples/
│   └── ecommerce/        # Proyecto demo con defectos intencionales
├── docs/                 # Arquitectura, decisiones, roadmap, tareas
├── docker-compose.yml
└── README.md
```

## Seguridad

- nunca versionar `.env`;
- rotar claves si se exponen;
- no usar este prototipo para ejecutar código arbitrario no confiable;
- en Docker Compose, el volumen `./examples` se monta en el backend como
  **solo lectura**.