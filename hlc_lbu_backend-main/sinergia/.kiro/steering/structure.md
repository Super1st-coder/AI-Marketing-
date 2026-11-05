---
inclusion: always
---

# Estructura del proyecto

Aplicación Flask (`flask_restplus`) organizada en capas. El código nuevo va en `app/v2/`; `app/v1/` es legado y solo se toca si la tarea lo exige.

## Capas de `app/v2/` y dependencias

Las dependencias van en un único sentido: `resources` / `async_tasks` → `use_cases` → `repository` → `models`. Nunca importar una capa superior desde una inferior.

| Directorio | Rol | Puede depender de |
|---|---|---|
| `app/v2/resources/` | Controladores: endpoints Flask (`Resource` + namespace de `v2_api`). Solo parsean la petición, aplican decoradores de auth, llaman a un use case y devuelven la respuesta. | `use_cases` |
| `app/v2/async_tasks/` | Tareas asíncronas Celery (`@shared_task`) en `celery_tasks.py`. Envuelven use cases. | `use_cases` |
| `app/v2/use_cases/` | Lógica de negocio pura: cálculos, validaciones, orquestación. | `repository`, `models`, `app/tools`, `app/exceptions` |
| `app/v2/repository/` | Acceso a datos (Strapi vía `StrapiClient`). Sin lógica de negocio. | `models`, `app/tools` |
| `app/v2/models/` | Entidades, DTOs, esquemas y constantes (`constant.py`, `brand_scheme.py`). | — |

Directorios de soporte compartidos:
- `app/tools/`: clientes e integraciones (`strapi.py`, `fury.py`, `s3.py`, `gcs.py`, `abyssale.py`, `service_auth.py`, ...).
- `app/exceptions/base.py`: excepciones de dominio (`DataNotFoundException`, `ParametersNotFoundException`, ...).

## Convenciones por capa

### Resources
- Un archivo por dominio (`ad.py`, `campaign.py`, `buyer_person.py`, ...).
- No contienen lógica de negocio ni llamadas a repositorios; delegan en `SomeUseCase(...).execute(...)`.
- Endpoints internos servicio-a-servicio van en `service.py` (namespace `service`, protegidos con `@service_api_key_required`).

### Use cases
- Una clase por caso de uso, con sufijo `UseCase` (p. ej. `SelectAdUseCase`) y un método público `execute(...)`.
- Los repositorios se instancian en `__init__` (`self.ad_repo = AdRepository()`), lo que facilita mockearlos en tests.
- Los errores se señalan lanzando excepciones de `app.exceptions.base`, no devolviendo códigos de error.
- Logger por módulo: `logger = logging.getLogger(__name__)`.

### Repository
- Una clase por content type de Strapi, sufijo `Repository`, heredando de `StrapiClient` y definiendo `self.content_type`.
- Métodos con nombres descriptivos (`get_by_id`, `get_by_ad_and_channel_id`, `update`); devuelven `None` cuando no hay datos en lugar de lanzar excepciones.

### Async tasks
- Llaman al use case y devuelven `{'ok': 1, 'data': ...}` en éxito o `{'ok': 0, 'message': {...}}` en error.

## Tests

- `tests/`: raíz de pruebas (pytest).
- `tests/conftest.py`: configuración global, fixtures de la app Flask y clientes de prueba.
- `tests/v2/unit/use_cases/`: pruebas unitarias de los use cases. Archivo `test_<caso_de_uso>.py`. Deben ser puras: repositorios y clientes externos mockeados, sin red, Redis ni Strapi reales.
- `tests/v2/integration/`: pruebas de integración.

## Reglas al añadir funcionalidad

1. Coloca cada pieza en su capa; si un endpoint necesita lógica, crea o amplía un use case.
2. Reutiliza repositorios y clientes de `app/tools` existentes antes de crear nuevos.
3. Respeta el sentido de dependencias entre capas.
4. Añade los tests unitarios del use case en `tests/v2/unit/use_cases/`.
