# Implementation Plan: ad-variant-image-edit-pipeline

## Overview

Implementación incremental en Python 3.11 bajo `fury/app` (raíz de imports) del pipeline asíncrono que edita la imagen base de una variante de anuncio con NanoBanana2, describe cada variación con el agente `ad_variant_image_prompter` y la sube a Sinergia. El orden va de lo determinista y aislado (dependencias de prueba, schemas, excepciones, `edit_instruction`, clientes de Sinergia y mocks, `edit_image_variations`, agente y validador) a la orquestación (helpers y corrutina `_run_edit_ad_variant_image_pipeline`, tarea Celery) y termina conectando los endpoints en `variants.py` y el cambio mínimo en `jobs.py`.

Restricciones transversales (ver `fury/.kiro/steering/tech.md` y `structure.md`):
- Docstring de módulo, type hints modernos, `logger = get_logger(__name__)` con prefijo `[{task_id}]`, helpers privados con `_`, constantes `UPPER_SNAKE`.
- `generate_images_from_prompts`, `core/auth.py`, `main.py`, `api/v2/router.py` y `services/celery_app.py` no se modifican. No hay settings nuevas ni flag `USE_*`.
- La ruta de Sinergia `GET .../variant/{variant_id}/image/{id_base_image}` queda fuera de alcance (spec separada); aquí solo se consume y se prueba con Mock_Sinergia. Desde la tarea 15 la subida usa la función existente `upload_image_to_library` (ruta `POST /api/v2/service/hiluca/ad/{ad_id}/image/upload`) y la ruta `POST .../variant/{variant_id}/image/upload` deja de usarse.
- Pruebas sin red ni LLM, como funciones `test_*` con `assert`, ejecutables desde `fury/app` con `PYTHONPATH=. pytest tests/` y `PYTHONPATH=. python -m tests.<módulo>`. Las pruebas de propiedades viven en módulos `test_*_properties.py` separados, con `@settings(max_examples=100, deadline=None)` y el comentario `# Feature: ad-variant-image-edit-pipeline, Property N: <título>`.

## Tasks

- [ ] 1. Dependencias de prueba e infraestructura de fakes
  - [x] 1.1 Crear `fury/app/requirements-dev.txt`
    - Contenido: comentario "Dev/test only — NOT installed by the Dockerfile", `-r requirements.txt`, `pytest==9.1.1`, `hypothesis==6.168.5` (versiones exactas)
    - No modificar `requirements.txt` ni el `Dockerfile`
    - _Requirements: 13.1_

  - [x] 1.2 Crear el módulo de helpers compartidos `fury/app/tests/_edit_pipeline_fakes.py` (no es `test_*`)
    - `FakeRedis` en memoria que registre cada `set(key, value, ex)` y sirva `_load`
    - `FakeTask` con `update_state` registrado, `retry` simulado y `request.retries`/`request.id`
    - Fakes guionizados de `get_ad_variant_image`, `upload_ad_variant_image_from_edit`, `_download_base_image`, `edit_image_variations` y `_run_agent`, con contadores y argumentos registrados
    - Sink de loguru que capture líneas de log; guard de red que parchee `httpx.AsyncClient.send`, `httpx.Client.send` y `socket.socket.connect` lanzando `AssertionError("unmocked network call")`
    - Context manager `patched_pipeline(...)` que haga monkeypatch de los atributos de `services.job_runner_service`, `agents.nano_banana_agent`, `agents.tools.*` y de `settings` (`USE_MOCK_SINERGIA`, `DEBUG`, `FURY_INTERNAL_API_KEY`, `SINERGIA_SERVICE_API_KEY`) y los restaure en `finally`
    - _Requirements: 13.1, 13.2_

- [x] 2. Schemas del request y del resultado
  - [x] 2.1 Añadir los modelos a `schemas/pipeline_schemas.py`
    - `ExpandZoomOption(str, Enum)` con exactamente `TOP`, `BOTTOM`, `LEFT`, `RIGHT`, `ZOOM_2X`, `ZOOM_1_5X`, `ZOOM_1_25X` (valor == nombre)
    - `AdVariantImageEditCreate` con IDs `ge=1`, `image_name`/`id_base_image` `min_length=1, max_length=255`, `n_variations` `ge=1, le=10`, `custom_prompt` `max_length=2000`, `expand_zoom_option` opcional
    - `field_validator(mode="before")` que recorte `image_name`/`id_base_image` y normalice `custom_prompt` vacío o en blanco a `None`; `model_validator(mode="after")` con el mensaje "Se requiere custom_prompt, expand_zoom_option o ambos"
    - `AdVariantImageEditJobData`, `AdVariantImageEditJobResponse`, `RegisteredVariant`, `AdVariantImageEditResult` (`variations` con `min_length=1`) y la constante `AD_VARIANT_IMAGE_EDIT_RESULT_KEYS: frozenset[str]`
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.7, 1.8, 1.9, 1.10, 1.11, 1.12, 10.1, 10.2_

  - [x] 2.2 Escribir pruebas unitarias en `tests/test_ad_variant_image_edit_schemas.py`
    - `ExpandZoomOption` con exactamente 7 miembros y valor == nombre; `"top"` y `"ZOOM_3X"` rechazados
    - Payloads concretos válidos e inválidos (cada obligatorio ausente, `"abc"` en un entero, ID 0, `n_variations` 0 y 11, `custom_prompt` `None`/`""`/`"   "` sin opción, longitudes 256 y 2001) con `loc` del campo culpable
    - _Requirements: 1.1–1.12_

  - [x] 2.3 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_schemas_properties.py`
    - **Property 1: El schema acepta exactamente los payloads válidos**
    - Predicado de referencia escrito en la prueba; generadores con cadenas de solo espacios y longitudes frontera 250–260 y 1995–2005
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.10, 1.11, 13.14**

  - [x] 2.4 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_schemas_properties.py`
    - **Property 2: Normalización de cadenas idempotente**
    - **Validates: Requirements 1.12**

- [x] 3. Excepciones del pipeline
  - [x] 3.1 Añadir las subclases de `FuryException` a `core/exceptions.py`
    - Base `AdVariantImageEditError` con `code`, `status_code`, `step` y `retryable` como atributos de clase, `__init__(self, message: str, details: dict[str, Any] | None = None)` y `__reduce__` que devuelva `(self.__class__, (self.message, self.details))`, con `args == (message,)`
    - Subclases según la tabla del diseño: `BaseImageFetchError` (502, reintentable), `BaseImageMismatchError` (409, `retryable=False`), `BaseImageUrlMissingError` (422, `retryable=False`, step `download`), `BaseImageDownloadError` (502), `ImageEditingFailedError` (502), `VariationUploadFailedError` (502), `EditJobEnqueueError` (503, `enqueue`), `EditPipelineInternalError` (500, `INTERNAL_ERROR`)
    - Cada `code` no vacío y distinto por causa
    - _Requirements: 4.9, 5.3, 5.5, 7.9, 9.8, 11.5, 12.1, 12.8, 2.5, 12.3_

  - [x] 3.2 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_task.py`
    - **Property 16: Round-trip de pickle de las excepciones**
    - `pickle.loads(pickle.dumps(e))` conserva clase, `message`, `code`, `status_code`, `details`; `type(e)(*e.args)` conserva clase y `message`
    - **Validates: Requirements 12.8**

  - [x] 3.3 Escribir pruebas unitarias de la tabla de excepciones en `tests/test_ad_variant_image_edit_task.py`
    - `code` únicos y no vacíos, `status_code` en [400, 599], `step` y `retryable` esperados por clase
    - _Requirements: 11.5, 12.1_

- [x] 4. Expansion_Translator determinista
  - [x] 4.1 Crear `services/edit_instruction.py`
    - `_PRESERVE_CLAUSE` (conservar relación de aspecto y no modificar el contenido existente) y `EXPANSION_INSTRUCTIONS: dict[ExpandZoomOption, str]` con los 7 textos fijos del diseño (lado nombrado para `TOP/BOTTOM/LEFT/RIGHT`; factor 2, 1.5 y 1.25 con contenido en los cuatro lados para los zoom)
    - `translate_expand_zoom_option(option)` y `build_edit_instruction(expand_zoom_option, custom_prompt)`: solo opción → traducción; solo prompt → prompt; ambos → traducción + `" "` + prompt; `(None, None)` → `ValueError`
    - Funciones puras: sin LLM, aleatoriedad, reloj ni contexto de la request
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

  - [x] 4.2 Escribir pruebas unitarias en `tests/test_edit_instruction.py`
    - 7 traducciones no vacías y distintas, cada una con las cláusulas de aspect ratio y no modificación, y el lado o factor explícito; composición en los 3 casos y `ValueError` para `(None, None)`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6, 6.7, 6.8, 13.4, 13.5_

  - [x] 4.3 Escribir prueba de propiedad en `tests/test_edit_instruction_properties.py`
    - **Property 3: Composición determinista de la Edit_Instruction**
    - **Validates: Requirements 6.5, 6.6, 6.7, 6.8, 6.9, 13.3, 13.4, 13.5**

- [x] 5. Cliente de Sinergia y Mock_Sinergia
  - [x] 5.1 Añadir a `agents/tools/campaign_tools.py` `_ad_variant_base_path`, `get_ad_variant_image` y `upload_ad_variant_image_from_edit`
    - `get_ad_variant_image(brand_id, campaign_id, ad_id, channel_id, variant_id, image_name, id_base_image)`: un único `_sinergia_get` a `{base}/image/{id_base_image}`; devuelve exactamente `{"id", "url", "prompt"}` como `str` (de `data` o del cuerpo sin sobre; ausente/`null` → `""`); propaga excepciones y lanza `ValueError` si el cuerpo no es dict
    - `upload_ad_variant_image_from_edit(..., image_name, payload)`: `_sinergia_post` a `{base}/image/upload` con `{"image": payload, "image_name": image_name}`; devuelve exactamente `{"image_id", "url"}` sin modificar; propaga excepciones; loguea solo path, `variant_id` e `image_id`, nunca el payload
    - No modificar `_sinergia_get` / `_sinergia_post`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.10, 9.1, 9.2, 9.3, 12.6_

  - [x] 5.2 Añadir a `agents/tools/mock_sinergia.py` las funciones homónimas con firma idéntica
    - `get_ad_variant_image` determinista: `{"id": id_base_image, "url": _MOCK_AD_VARIANT_BASE_IMAGE_URL (firmada con X-Amz-*), "prompt": <texto fijo>}`
    - `upload_ad_variant_image_from_edit` con `itertools.count(1)`: `image_id` y `url` no vacíos y distintos en cada invocación del proceso
    - _Requirements: 4.5, 4.6, 9.6_

  - [x] 5.3 Escribir pruebas unitarias en `tests/test_ad_variant_sinergia_tools.py`
    - Path exacto y body `{"image", "image_name"}` con `_sinergia_get`/`_sinergia_post` parcheados; propagación de excepciones (sin devolver `{}`); `inspect.signature` de mock == real para ambas funciones
    - _Requirements: 4.1, 4.2, 4.4, 9.1, 9.2, 13.18_

  - [x] 5.4 Escribir prueba de propiedad en `tests/test_ad_variant_sinergia_tools.py`
    - **Property 6: El cliente de Sinergia normaliza la respuesta**
    - **Validates: Requirements 4.3, 9.3**

  - [x] 5.5 Escribir prueba de propiedad en `tests/test_ad_variant_sinergia_tools.py`
    - **Property 7: Mocks de Sinergia deterministas y únicos**
    - **Validates: Requirements 4.6, 9.6**

- [x] 6. Image_Editor con NanoBanana2
  - [x] 6.1 Añadir `edit_image_variations` a `agents/nano_banana_agent.py` sin tocar `generate_images_from_prompts` ni `make_nano_banana_agent`
    - Constantes `NANO_BANANA2_MODEL` y `_EDIT_RATE_LIMIT_BACKOFF_S = (1, 2, 4)`; `_is_image_rate_limit_error` (APIError 429 + marcadores de `helpers.agent._is_rate_limit_error`)
    - `_call_nano_banana2_edit(client, image_bytes, mime_type, edit_instruction, timeout_s)` con `Part.from_bytes` + `Part.from_text`, `response_modalities=["IMAGE"]`, AFC deshabilitado, sin `aspect_ratio`, `asyncio.wait_for(asyncio.to_thread(...), timeout_s + 15)`; punto de inyección para pruebas
    - `edit_image_variations(base_image_bytes, base_mime_type, edit_instruction, n_variations, *, task_id="-", sleep=asyncio.sleep)`: `timeout_s = max(10, settings.IMAGE_GEN_TIMEOUT_SECONDS)`; `n_variations` corrutinas con `gather(return_exceptions=True)`; cada intento adquiere `_image_semaphore()` y lo libera antes del backoff; hasta 3 reintentos solo por rate limit; otros errores, timeout o respuesta sin imagen `image/` → variación fallida sin reintento
    - Devuelve `[{"index", "image_b64", "mime_type"}]` ordenada por `index` (1-based), posiblemente vacía; nunca lanza por fallo de variación; `ValueError` si `n_variations ∉ [1, 10]` o binario vacío
    - Logs `[{task_id}]` solo con índice, MIME, tamaño y tipo de error
    - _Requirements: 6.11, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [x] 6.2 Escribir pruebas unitarias en `tests/test_nano_banana_edit_variations.py`
    - Rate limit seguido de éxito → 2 llamadas y la variación devuelta (con `sleep` simulado); timeout calculado como `max(10, setting)`; firma de `generate_images_from_prompts` intacta
    - _Requirements: 7.2, 7.4, 7.6, 13.10_

  - [x] 6.3 Escribir prueba de propiedad en `tests/test_nano_banana_edit_variations.py`
    - **Property 10: Contabilidad de solicitudes del Image_Editor**
    - Parchear `_call_nano_banana2_edit` y `sleep`; medir concurrencia máxima con límite `c ∈ [1, 4]`
    - **Validates: Requirements 7.1, 7.3, 7.4, 7.5, 7.7, 13.10**

- [x] 7. Variant_Prompter y su validador
  - [x] 7.1 Crear `agents/ad_variant_image_prompter_agent.py`
    - Docstring de módulo, `_FALLBACK_MODEL = "gemini/gemini-2.5-flash"` y `_FALLBACK_INSTRUCTION` (solo contenido visible, política de Meta, devolver ÚNICAMENTE `{"image_prompt": ...}`)
    - `make_ad_variant_image_prompter_agent(custom_prompt: str | None = None)` con `get_agent_config_from_langfuse("fury.ad_variant_image_prompter", ...)`, `LiteLlm(model=cfg["model"])`, `name="ad_variant_image_prompter"`, `tools=[]` y ambos safety guards; sin singleton a nivel de módulo
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 7.2 Añadir `validate_ad_variant_image_prompter_response` a `services/ads_validators.py`
    - Constante `AD_VARIANT_IMAGE_PROMPT_MAX_CHARS = 2000`; acepta solo un objeto JSON (tolerando fences ```json```) con `image_prompt` `str` de 1–2000 caracteres tras `strip`; `data` con `image_prompt` recortado
    - Errores con `error_code` en `EMPTY_RESPONSE`, `INVALID_JSON`, `NOT_AN_OBJECT`, `MISSING_FIELD`, `INVALID_TYPE`, `EMPTY_FIELD`, `TOO_LONG` y mensaje que identifique la condición
    - _Requirements: 8.5, 8.6_

  - [x] 7.3 Escribir pruebas unitarias en `tests/test_ad_variant_image_prompter_validator.py`
    - Casos de 13.17 (válido, sin campo, vacío, no `str`, >2000, texto no JSON)
    - Factory con `get_agent_config_from_langfuse` parcheado: nombre Langfuse, `tools == []`, guards adjuntos, modelo con prefijo de proveedor, sin instanciar al importar
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 13.17_

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Helpers del pipeline en `services/job_runner_service.py`
  - [x] 9.1 Añadir constantes y helpers privados
    - `_EDIT_STEPS`, `_EDIT_PROGRESS_STEPS`, `_BASE_IMAGE_DOWNLOAD_TIMEOUT_S = 30`
    - `_edit_cp_load` / `_edit_cp_store` sobre `_load`/`_store` con `_cp_key(task_id, ad_id, step)` y `ex=_CHECKPOINT_TTL`; con `task is None` toleran errores de Redis (warning, sin checkpoint), con Celery los propagan (D8)
    - `_redact_text` (URLs embebidas vía `_strip_signed_urls`, data-URI → `data:<mime>;base64,<redacted N chars>`, valores de `SINERGIA_SERVICE_API_KEY` y `FURY_INTERNAL_API_KEY` → `***`, truncado a 300)
    - `_DownloadRejected` y `_download_base_image(url, task_id)` con `httpx.AsyncClient(timeout=30, follow_redirects=True)`: acepta 2xx, ≥1 byte y `Content-Type` ausente o `image/*`; MIME sin parámetros o `image/png`; log `[{task_id}]` con URL saneada y tamaño/MIME o causa
    - `_to_data_uri`, `_variation_image_name` (sufijo 1-based antes de la extensión), `_extract_image_prompt` (str JSON o dict, vía `_parse_json_response`), `_is_retryable_edit_error`, `_progress(task, task_id, step, detail)`
    - _Requirements: 5.1, 5.2, 5.4, 5.6, 9.5, 11.7, 11.11, 12.4, 12.5, 12.6_

  - [x] 9.2 Escribir prueba de propiedad en `tests/test_ad_variant_image_prompter_validator_properties.py`
    - **Property 14: Oráculo del Prompter_Validator y de la extracción**
    - Incluye que `_extract_image_prompt` devuelve el mismo valor para texto JSON y dict parseado
    - **Validates: Requirements 8.5, 8.6, 8.8, 13.17**

  - [x] 9.3 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_pipeline_properties.py`
    - **Property 9: Clasificación de la descarga**
    - Usar `httpx.MockTransport` con status 100–599, cuerpos de 0–N bytes, `Content-Type` arbitrario (con `; charset=`) y errores de transporte/timeout
    - **Validates: Requirements 5.2, 5.4, 5.5, 13.6**

- [x] 10. Corrutina `_run_edit_ad_variant_image_pipeline`
  - [x] 10.1 Implementar la corrutina en `services/job_runner_service.py` con `@observe(name="fury.ad_variant_image_edit_pipeline")`
    - Imports perezosos dentro de la función: prompter, `edit_image_variations`, validador, `build_edit_instruction` y `get_ad_variant_image`/`upload_ad_variant_image_from_edit` desde `mock_sinergia` o `campaign_tools` según `settings.USE_MOCK_SINERGIA`
    - Edit_Instruction con `build_edit_instruction` (sin checkpoint); leer los 4 checkpoints; `needs_download` = no existe `image_editing`, `prompt_analysis` ni `upload`
    - `fetch_base_image`: si `needs_download`, invocar siempre `get_ad_variant_image` (URL fresca en memoria); excepción → `BaseImageFetchError`; `id` distinto → `BaseImageMismatchError`; `url` en blanco → `BaseImageUrlMissingError`; guardar `{id, url saneada, prompt}` solo si no existía el checkpoint; si no hay que descargar, tomar el `prompt` del checkpoint (o `""` con warning)
    - `download`: solo con la URL fresca del intento, nunca la del checkpoint; fallo → `BaseImageDownloadError`
    - `image_editing`: `[]` → `ImageEditingFailedError` sin checkpoint; si no, checkpoint antes de seguir
    - `prompt_analysis`: agente creado una vez; `_run_agent` por variación con data-URI, MIME, Edit_Instruction, prompt base (o "not available") y el validador; fallback a la Edit_Instruction con warning; checkpoint con la misma longitud
    - `upload`: secuencial; `payload` con claves exactas `image_data`, `image_name` (con sufijo), `mime_type`, `image_prompt`; omitir variaciones con excepción o sin `image_id`/`url` (log saneado); ninguna OK → `VariationUploadFailedError` sin checkpoint; si hay alguna, guardar checkpoint `upload` con URL saneada
    - `done`: devolver `AdVariantImageEditResult(...).model_dump(mode="json")`; emitir `_progress` para los 6 pasos en orden aunque se omitan (`detail="checkpoint"`/`"skipped"`)
    - `details` de cada error con `task_id`, `id_base_image`, `step` y `cause` saneada
    - _Requirements: 4.4, 4.5, 4.7, 4.8, 4.9, 5.1, 5.3, 5.4, 5.5, 6.9, 6.10, 6.11, 7.8, 7.9, 7.11, 7.12, 8.7, 8.8, 8.9, 8.10, 8.11, 8.12, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.8, 11.7, 11.8, 11.9, 11.10, 11.11, 11.12, 12.1, 12.4, 12.5, 12.6_

  - [x] 10.2 Escribir pruebas de escenario en `tests/test_ad_variant_image_edit_pipeline.py`
    - Escenarios 13.3, 13.5, 13.6 (red, timeout, no-2xx), 13.7, 13.8, 13.9, 13.11, 13.12, 13.13 y 13.16
    - Reutilización de `prompt_analysis` tras fallo total de subida; reintento con checkpoint `fetch_base_image` y sin `image_editing`: `get_ad_variant_image` 1 vez y descarga con la URL fresca (13.23); secuencia de progreso en orden
    - _Requirements: 13.3, 13.5, 13.6, 13.7, 13.8, 13.9, 13.11, 13.12, 13.13, 13.16, 13.23_

  - [x] 10.3 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_pipeline_properties.py`
    - **Property 8: Guardas no reintentables de la Base_Image**
    - **Validates: Requirements 4.9, 5.3, 11.5, 13.7**

  - [x] 10.4 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_pipeline_properties.py`
    - **Property 11: Invariante end-to-end del resultado**
    - Generar `n`, F_gen (propio), F_pr y F_up con `assume` de al menos una subida OK
    - **Validates: Requirements 6.10, 6.11, 7.8, 8.7, 8.8, 8.9, 8.10, 8.12, 9.4, 9.5, 9.7, 9.9, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.8, 13.3, 13.9, 13.11, 13.12, 13.19**

  - [x] 10.5 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_pipeline_properties.py`
    - **Property 12: Fallos totales por paso**
    - **Validates: Requirements 7.9, 7.10, 9.8, 13.8, 13.13**

  - [x] 10.6 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_pipeline_properties.py`
    - **Property 13: Reanudación por checkpoints equivalente**
    - Prefijos de `[fetch_base_image, image_editing, prompt_analysis, upload]` con valores de una ejecución de referencia; verificar claves `fury:cp:{task_id}:{ad_id}:{step}`, `ex == 7200` y la secuencia de `meta.step`
    - **Validates: Requirements 4.7, 4.8, 7.11, 7.12, 8.11, 11.7, 11.8, 11.9, 11.10, 11.11, 13.16**

  - [x] 10.7 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_pipeline_properties.py`
    - **Property 18: Nada sensible en logs, checkpoints ni details**
    - URLs firmadas con `X-Amz-*` generadas, `SINERGIA_SERVICE_API_KEY` aleatoria y fallos inyectados en cualquier paso; incluye la propiedad de `_redact_text` sobre texto arbitrario y el prefijo `[{task_id}]` en cada línea
    - **Validates: Requirements 4.7, 5.6, 7.7, 9.7, 12.4, 12.5, 12.6, 13.22**

  - [x] 10.8 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_pipeline_properties.py`
    - **Property 19: El reintento descarga siempre desde una URL fresca**
    - **Validates: Requirements 4.8, 4.9, 5.1, 5.4, 11.8, 13.23**

- [x] 11. Tarea Celery `run_edit_ad_variant_image_pipeline`
  - [x] 11.1 Implementar la tarea en `services/job_runner_service.py`
    - `@celery_app.task(name="services.job_runner_service.run_edit_ad_variant_image_pipeline", bind=True, max_retries=3)` sin sobrescribir `acks_late` ni `soft_time_limit` (el módulo ya está en `celery_app.include`)
    - `update_state(PROGRESS, meta={"step": "starting", "variant_id", "id_base_image"})` antes de ejecutar; event loop nuevo por intento con `run_until_complete`, `shutdown_asyncgens()` y cierre en `finally`
    - Política D7: no reintentable → log y `raise` sin `self.retry`; `self.request.retries >= self.max_retries` → log de tipo y mensaje original (vía `_redact_text`) y `raise exc`; si no, `raise self.retry(exc=exc, countdown=2 ** self.request.retries)`; `except MaxRetriesExceededError` defensivo que relanza `exc`
    - Sin `traceback.format_exc()` en logs
    - _Requirements: 4.4, 5.4, 5.5, 7.9, 7.10, 9.8, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 12.5_

  - [x] 11.2 Escribir prueba de propiedad y pruebas del decorador en `tests/test_ad_variant_image_edit_task.py`
    - **Property 15: Política de reintentos de la tarea**
    - Invocar la tarea con `push_request(id=..., retries=r)` / `pop_request()`, `retry` y `update_state` parcheados y la corrutina sustituida por un fake; comprobar además `name`, `max_retries == 3` y que no se sobrescriben `acks_late`/`soft_time_limit`
    - **Validates: Requirements 4.4, 5.4, 7.9, 9.8, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6**

- [x] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Endpoints y consulta del job
  - [x] 13.1 Añadir los endpoints a `api/v2/endpoints/variants.py` (router existente con `prefix="/variants"`, sin tocar `router.py`)
    - `POST /image/edit` (201, `response_model=AdVariantImageEditJobResponse`, `Depends(verify_internal_api_key)`): `apply_async(kwargs=body.model_dump(mode="json"))`; excepción → `EditJobEnqueueError` sin `edit_job_id` ni `poll_url`; respuesta con `edit_job_id`, `status: "RUNNING"` y `poll_url: f"/api/v2/jobs/{task_id}"`
    - `POST /image/edit/run-local` (200, misma dependencia de auth): 404 si `not settings.DEBUG`; `task_id = str(uuid.uuid4())`; `await _run_edit_ad_variant_image_pipeline(task=None, task_id=..., **body.model_dump(mode="json"))`; relanzar `FuryException`; cualquier otra → `EditPipelineInternalError` con `details={"task_id", "error_type"}` sin `str(exc)`; éxito → `{"ok": 1, "data": result}`
    - No invocar Sinergia, NanoBanana2 ni el agente dentro de la request del endpoint 201; no modificar `core/auth.py` ni `main.py`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 12.2, 12.3_

  - [x] 13.2 Aplicar el cambio mínimo en `api/v2/endpoints/jobs.py`
    - En `SUCCESS`, devolver `"result": info` solo si `info` es `dict` y `frozenset(info) == AD_VARIANT_IMAGE_EDIT_RESULT_KEYS`; el resto de pipelines conserva `"Ok"` sin cambios
    - _Requirements: 10.7_

  - [x] 13.3 Escribir pruebas unitarias en `tests/test_ad_variant_image_edit_endpoints.py` con `TestClient(app)`
    - 201 con `apply_async` invocado 1 vez con los 10 campos (13.20); cada payload inválido de 13.14 → 422 sin `apply_async`; 503 con `FURY_INTERNAL_API_KEY` vacía; `apply_async` que lanza → 5xx sin `edit_job_id`/`poll_url`; dos requests idénticas → dos IDs distintos
    - Sin cabecera → status en `{401, 403}`; clave inválida → 401; ambos sin `apply_async` ni pipeline (13.21)
    - Run-local: 404 con `DEBUG=False` y pipeline invocado 0 veces (13.15); 200 con `{"ok": 1, "data": ...}` con `DEBUG=True`
    - `jobs.py`: devuelve el resultado completo para este pipeline y `"Ok"` para otros dicts
    - _Requirements: 2.1–2.7, 3.1–3.6, 10.7, 13.14, 13.15, 13.20, 13.21_

  - [x] 13.4 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_endpoints.py`
    - **Property 4: El encolado preserva el request**
    - **Validates: Requirements 1.1, 2.1, 2.2, 13.20**

  - [x] 13.5 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_endpoints.py`
    - **Property 5: La autenticación precede a todo**
    - Aceptar 401 o 403 para cabecera ausente y exigir 401 para clave incorrecta, con cualquier cuerpo JSON y cualquier `DEBUG`
    - **Validates: Requirements 2.3, 3.2, 13.21**

  - [x] 13.6 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_endpoints.py`
    - **Property 17: Mapeo de errores del Run_Local_Endpoint**
    - **Validates: Requirements 3.7, 12.2, 12.3**

- [x] 14. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Ejecutar desde `fury/app`: `pip install -r requirements-dev.txt`, `PYTHONPATH=. pytest tests/` y `PYTHONPATH=. python -m tests.<módulo>` para los módulos nuevos.

- [x] 15. Cambio: subida vía `upload_image_to_library` + paso `resolve_urls`
  - [x] 15.1 Eliminar `upload_ad_variant_image_from_edit` y hacer únicos los ids del mock de `upload_image_to_library`
    - Borrar `upload_ad_variant_image_from_edit` de `agents/tools/campaign_tools.py`; conservar `_ad_variant_base_path`, `_unwrap_sinergia_body` y `_as_str` (los usa `get_ad_variant_image`)
    - Borrar `upload_ad_variant_image_from_edit` y `_mock_ad_variant_upload_counter` de `agents/tools/mock_sinergia.py`; actualizar el comentario de cabecera de la sección
    - En `mock_sinergia.upload_image_to_library`, devolver `f"IMG_mock_{ad_id}_{n}"` con `n` de un `itertools.count(1)` de módulo (`_mock_library_upload_counter`), conservando firma y `print` existentes (D13, A4 confirmado)
    - _Requirements: 4.10, 9.1, 9.6_

  - [x] 15.2 Sanear el log de depuración de `upload_image_to_library` en `agents/tools/campaign_tools.py`
    - Añadir `_describe_image_data(value)` → `"data-uri:<mime> len=N"`, `"url len=N"`, `"text len=N"` o `"none"`, sin contenido ni query
    - Sustituir en el `logger.debug` el fragmento `image_data.get('image_data')[:100]` por `_describe_image_data(...)`; no tocar la petición, el `try/except` ni el valor devuelto (D15)
    - _Requirements: 12.9_

  - [x] 15.3 Actualizar las pruebas unitarias de `tests/test_ad_variant_sinergia_tools.py`
    - Eliminar `_upload`, `test_upload_posts_exact_path_and_body`, `test_upload_propagates_exceptions` y `test_upload_raises_on_non_dict_body_instead_of_returning_empty`
    - `test_mock_signatures_match_real_client`: comparar `get_ad_variant_image` y `upload_image_to_library`, y comprobar que ningún módulo expone `upload_ad_variant_image_from_edit`
    - `test_real_signatures_match_contract`: `upload_image_to_library` con parámetros `["ad_id", "image_data"]`
    - Nuevos: `upload_image_to_library` con `_sinergia_post` parcheado → path `/api/v2/service/hiluca/ad/{ad_id}/image/upload`, body `{"image": image_data}`, retorno `data.image_id`, `""` sin `image_id` y `""` si `_sinergia_post` lanza; log DEBUG sin base64 con un data-URI concreto (13.29)
    - _Requirements: 9.1, 9.2, 9.3, 9.6, 12.9, 13.18, 13.29_

  - [x] 15.4 Actualizar la prueba de propiedad en `tests/test_ad_variant_sinergia_tools.py`
    - **Property 6: El cliente de Sinergia normaliza la respuesta**
    - Mantener `test_property_6_get_normalizes_response`; eliminar `test_property_6_upload_returns_exact_keys_unmodified`
    - **Validates: Requirements 4.3**

  - [x] 15.5 Actualizar la prueba de propiedad en `tests/test_ad_variant_sinergia_tools.py`
    - **Property 7: Mocks de Sinergia deterministas y únicos**
    - `test_property_7_mock_get_is_deterministic` sin cambios de fondo; reescribir `test_property_7_mock_upload_ids_unique` sobre `mock_sinergia.upload_image_to_library(ad_id, image_data)` (k `str` no vacíos y distintos)
    - **Validates: Requirements 4.6, 9.6, 14.13**

  - [x] 15.6 Escribir prueba de propiedad en `tests/test_ad_variant_sinergia_tools.py`
    - **Property 21: El log de `upload_image_to_library` no filtra contenido**
    - Sink de loguru a nivel DEBUG; generar data-URI con base64 de 1–5000 caracteres, Signed_URL con `X-Amz-*` arbitrarios y texto; `_sinergia_post` con `image_id`, sin `image_id` o que lanza
    - **Validates: Requirements 9.2, 9.3, 12.9, 13.29**

  - [x] 15.7 Añadir `VariationUrlResolutionError` a `core/exceptions.py`
    - Subclase de `VariationUploadFailedError` con `code = "AD_VARIANT_IMAGE_URL_RESOLUTION_FAILED"`, `status_code = 502`, `step = "resolve_urls"`, `retryable = True`; hereda `__init__(message, details)` y `__reduce__`
    - _Requirements: 12.1, 12.8, 14.7_

  - [x] 15.8 Actualizar las pruebas de excepciones en `tests/test_ad_variant_image_edit_task.py`
    - Incluir `VariationUrlResolutionError` en la tabla de códigos únicos (`code`, `status_code` en [400, 599], `step`, `retryable`) y en los generadores de Property 15 y Property 16 si enumeran las clases explícitamente
    - Comprobar `issubclass(VariationUrlResolutionError, VariationUploadFailedError)`
    - _Requirements: 11.4, 12.1, 12.8, 14.7_

  - [x] 15.9 Adaptar `tests/_edit_pipeline_fakes.py`
    - Sustituir `FakeUploadAdVariantImage` por `FakeUploadImageToLibrary` (`PARAMS = ("ad_id", "image_data")`, devuelve `str`; por defecto ids únicos; guiones con `""`, valores no `str` y excepciones)
    - `FakeSleep`: async callable que registra los segundos solicitados y retorna sin esperar
    - `FakeGetAdVariantImage`: distinguir la llamada de Base_Image (`id_base_image` del request) de las URL_Resolution; por defecto, para otro id, devolver `{"id": <id>, "url": <URL firmada fresca>, "prompt": ""}`; admitir guiones por `image_id` y exponer `base_calls` / `resolution_calls`
    - `patched_pipeline(...)`: parchear `upload_image_to_library` en `agents.tools.campaign_tools` y `agents.tools.mock_sinergia`, y `_edit_sleep` en `services.job_runner_service` con `FakeSleep`; dejar de parchear `upload_ad_variant_image_from_edit`; actualizar el docstring del módulo
    - _Requirements: 13.2_

  - [x] 15.10 Añadir constantes y Edit_Sleep en `services/job_runner_service.py`
    - `_LIBRARY_INDEX_DELAY_S = 15`, `_RESOLVE_URL_RETRIES = 3`, `_RESOLVE_URL_RETRY_DELAY_S = 5`
    - `_edit_sleep: Callable[[float], Awaitable[None]] = asyncio.sleep` a nivel de módulo, siempre invocado como `_edit_sleep(...)` (nunca capturado como default de parámetro)
    - `_resolve_variation_url(get_ad_variant_image, *, task_id, brand_id, campaign_id, ad_id, channel_id, variant_id, image_name, image_id) -> tuple[str | None, int, str]`: hasta 1 + `_RESOLVE_URL_RETRIES` consultas, `await _edit_sleep(_RESOLVE_URL_RETRY_DELAY_S)` antes de cada repetición, acepta solo dict con `id == image_id` y `url` no vacía tras `strip`; nunca lanza; causa saneada con `_redact_text`
    - _Requirements: 14.2, 14.3, 14.4, 14.5, 14.12, 12.10_

  - [x] 15.11 Actualizar `_EDIT_STEPS` y `_EDIT_PROGRESS_STEPS` en `services/job_runner_service.py`
    - `_EDIT_STEPS = ("fetch_base_image", "image_editing", "prompt_analysis", "upload", "resolve_urls")`
    - `_EDIT_PROGRESS_STEPS = ("fetch_base_image", "download", "image_editing", "prompt_analysis", "upload", "resolve_urls", "done")`; actualizar el comentario de cabecera de la sección
    - _Requirements: 11.7, 11.11_

  - [x] 15.12 Implementar la subida con retorno `str` y el checkpoint `upload` sin `url` en `_run_edit_ad_variant_image_pipeline`
    - Imports perezosos: `get_ad_variant_image` y `upload_image_to_library as upload_image_to_library_tool`; quitar `upload_ad_variant_image_from_edit` y el bloque comentado
    - Leer también el checkpoint `resolve_urls`; `needs_download` falso si existe `image_editing`, `prompt_analysis`, `upload` o `resolve_urls`; con `resolve_urls` presente, `prompt_analysis` y `upload` se emiten como `skipped`
    - Bucle secuencial: `resp = await upload_image_to_library_tool(ad_id, payload)` dentro de `try/except`; aceptar solo `isinstance(resp, str) and resp.strip()` (corrige D14: hoy se lee `resp.get(...)` sobre un `str`); log saneado por variación omitida
    - 0 subidas → `VariationUploadFailedError` sin checkpoint; si no, `_edit_cp_store(... "upload", [{"id", "prompt"}])` en el orden del editor antes de `resolve_urls`
    - Con checkpoint `upload` presente: 0 llamadas a `upload_image_to_library_tool` y `_progress(..., "upload", "checkpoint")`
    - _Requirements: 9.4, 9.5, 9.7, 9.8, 9.9, 9.10, 9.11, 11.8, 11.10, 11.12_

  - [x] 15.13 Implementar el paso `resolve_urls` y el `done` en `_run_edit_ad_variant_image_pipeline`
    - Con checkpoint `resolve_urls`: `_progress(..., "resolve_urls", "checkpoint")`, `registered` = checkpoint, sin Edit_Sleep ni URL_Resolution
    - Sin él: `_progress(..., "resolve_urls", ...)`, `await _edit_sleep(_LIBRARY_INDEX_DELAY_S)` una vez (también al reanudar desde `upload`), y `_resolve_variation_url` secuencial por Uploaded_Image con el `image_name` del Edit_Request
    - Log por variación con `id`, URL tras `_strip_signed_urls` y número de consultas; omitidas con causa saneada
    - 0 resueltas → `VariationUrlResolutionError` con `_edit_error_details(task_id, id_base_image, "resolve_urls", "0/N urls resolved")`, sin checkpoint `resolve_urls`; si no, `_edit_cp_store(... "resolve_urls", _strip_signed_urls(registered))`
    - `done` con `AdVariantImageEditResult(..., variations=registered)`; actualizar el docstring de la corrutina con el paso nuevo
    - _Requirements: 10.1, 10.3, 10.5, 10.6, 11.8, 11.10, 11.11, 12.1, 12.4, 12.10, 14.1, 14.3, 14.4, 14.6, 14.7, 14.8, 14.9, 14.10, 14.11_

  - [x] 15.14 Actualizar las pruebas de escenario en `tests/test_ad_variant_image_edit_pipeline.py`
    - Adaptar a `FakeUploadImageToLibrary`, `FakeSleep` y la URL_Resolution: `test_custom_prompt_only_three_variations_done` (13.3: `id` del fake de subida, `url` de la URL_Resolution), `test_download_failures_raise_download_error_without_editing_or_upload`, `test_all_variations_fail_raises_image_editing_error`, `test_partial_upload_failures_keep_successful_one` (13.12: una excepción y un `""`), `test_all_uploads_fail_then_retry_reuses_prompt_analysis` (13.13: sin Edit_Sleep ni URL_Resolution), `test_preloaded_checkpoints_skip_to_upload` (13.16: contar solo llamadas de Base_Image), `test_retry_with_fetch_checkpoint_refreshes_url` (13.23), `test_progress_sequence_in_order` (7 pasos con `resolve_urls`)
    - Nuevos: `test_library_index_delay_called_once_with_15s` (13.24), `test_url_resolution_retries_then_succeeds` y `test_url_resolution_exhausted_omits_variation` (13.25), `test_resume_from_upload_checkpoint_does_not_reupload` (13.26), `test_resume_from_resolve_urls_checkpoint` (13.27), `test_all_url_resolutions_fail_raises_and_retry_does_not_reupload` (13.28), `test_upload_checkpoint_has_only_id_and_prompt` (13.30)
    - _Requirements: 13.3, 13.6, 13.8, 13.12, 13.13, 13.16, 13.23, 13.24, 13.25, 13.26, 13.27, 13.28, 13.30_

  - [x] 15.15 Actualizar la prueba de propiedad en `tests/test_ad_variant_image_edit_pipeline_properties.py`
    - **Property 11: Invariante end-to-end del resultado**
    - `test_property_11_end_to_end_result_invariant`: subida vía `FakeUploadImageToLibrary` (F_up con excepción, `""` y no `str`), F_res de fallos permanentes de URL_Resolution, `len == n − |F_gen| − |F_up| − |F_res|`, `url` de la URL_Resolution
    - Nombres (tras 15.21): además de `len(set(names)) == len(names)`, comprobar que cada `payload["image_name"] == _variation_image_name(kwargs["image_name"], index)`, que termina en `_{index}` y que, con el fixture `banner.png`, es `banner_{index}` (sin `.png`)
    - **Validates: Requirements 4.11, 6.10, 6.11, 7.8, 8.7, 8.8, 8.9, 8.10, 8.12, 9.4, 9.5, 9.7, 9.9, 9.12, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.8, 14.3, 14.4, 14.6, 14.11, 13.3, 13.9, 13.11, 13.12, 13.19**

  - [x] 15.16 Actualizar la prueba de propiedad en `tests/test_ad_variant_image_edit_pipeline_properties.py`
    - **Property 12: Fallos totales por paso**
    - `test_property_12_total_failures_per_step`: añadir el caso "todas las URL_Resolution fallan" (`VariationUrlResolutionError`, checkpoint `upload` presente, sin `resolve_urls`) y comprobar 0 Edit_Sleep en el fallo total de subida
    - **Validates: Requirements 7.9, 7.10, 9.8, 14.7, 13.8, 13.13, 13.28**

  - [x] 15.17 Actualizar la prueba de propiedad en `tests/test_ad_variant_image_edit_pipeline_properties.py`
    - **Property 13: Reanudación por checkpoints equivalente**
    - `test_property_13_checkpoint_resume_equivalent`: prefijos de 5 pasos (con `resolve_urls`), 0 subidas si `upload ∈ S`, Edit_Sleep `[15]` salvo si `resolve_urls ∈ S`, valor de `upload` con claves `{id, prompt}`, sin `_store` sobre `upload` al reanudar y secuencia de 7 `meta.step`
    - **Validates: Requirements 4.7, 4.8, 7.11, 7.12, 8.11, 9.10, 9.11, 11.7, 11.8, 11.9, 11.10, 11.11, 14.1, 14.8, 14.9, 14.10, 13.16, 13.26, 13.27, 13.30**

  - [x] 15.18 Actualizar la prueba de propiedad en `tests/test_ad_variant_image_edit_pipeline_properties.py`
    - **Property 18: Nada sensible en logs, checkpoints ni details**
    - `test_property_18_nothing_sensitive_in_logs_checkpoints_details`: URLs firmadas también en la URL_Resolution, excepciones de URL_Resolution con URLs y data-URI en el mensaje, y revisión de los checkpoints `upload` y `resolve_urls`; `test_property_18_redact_text_arbitrary_text` sin cambios
    - **Validates: Requirements 4.7, 5.6, 7.7, 9.7, 12.4, 12.5, 12.6, 12.10, 14.6, 13.22**

  - [x] 15.19 Actualizar la prueba de propiedad en `tests/test_ad_variant_image_edit_pipeline_properties.py`
    - **Property 19: El reintento descarga siempre desde una URL fresca**
    - `test_property_19_retry_downloads_from_fresh_url` y `test_property_19_each_attempt_downloads_from_its_own_fresh_url`: contar solo las llamadas a `get_ad_variant_image` con el `id_base_image` del request (excluir URL_Resolution); revisar también `test_property_8_base_image_non_retryable_guards` con el mismo criterio
    - **Validates: Requirements 4.8, 4.9, 5.1, 5.4, 11.8, 13.23**

  - [x] 15.20 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_resolve_urls_properties.py` (módulo nuevo)
    - **Property 20: Resolución de URLs con reintentos acotados**
    - Checkpoint `upload` precargado con 1–10 ids distintos; guiones por id de 1–6 resultados (excepción, no dict, id distinto, `url` ausente/en blanco, válida); verificar consultas `min(p, 4)`, esperas `[15] + [5] * Σ(consultas − 1)`, orden, omisiones logueadas y checkpoint `resolve_urls`; bloque `if __name__ == "__main__":` como el resto de módulos
    - **Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 14.10, 14.11, 9.11, 13.24, 13.25, 13.26, 13.28**

  - [x] 15.21 Implementar el nuevo `_variation_image_name` y `_IMAGE_NAME_EXTENSIONS` en `services/job_runner_service.py`
    - Constante de dominio `_IMAGE_NAME_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp", ".gif")` junto a las demás constantes del pipeline
    - `_variation_image_name(image_name, index)`: si `image_name.lower()` termina en alguna extensión de la constante y `len(image_name) > len(ext)`, devolver `image_name[:-len(ext)] + f"_{index}"`; si no (incluido el stem vacío, p. ej. `.png`), devolver `image_name + f"_{index}"`. Elimina como máximo una extensión y conserva cualquier otro sufijo con punto (D17)
    - Sustituir la implementación con `os.path.splitext` y actualizar el docstring con los ejemplos de `design.md` (§11); no tocar `upload_image_to_library` ni Sinergia; mantener `import os` (se usa en otras partes del módulo)
    - _Requirements: 9.5, 9.12, 9.13_

  - [x] 15.22 Escribir pruebas unitarias en `tests/test_ad_variant_image_edit_helpers.py` (módulo nuevo, sin Hypothesis)
    - `banner.png`, 1 → `banner_1`; `banner.JPG`, 2 → `banner_2`; `banner`, 3 → `banner_3`; `promo v1.2`, 1 → `promo v1.2_1`; `photo.tar.png`, 1 → `photo.tar_1`; `.png`, 1 → `.png_1`
    - Cada extensión de `_IMAGE_NAME_EXTENSIONS` en minúsculas, mayúsculas y mezcla da el mismo resultado; `_IMAGE_NAME_EXTENSIONS` contiene exactamente las 5 extensiones
    - Sin doble extensión: `_variation_image_name(n, 1) + mimetypes.guess_extension("image/png") == "banner_1.png"` para `n` en `banner.png` y `banner.jpg` (la extensión sigue al contenido real)
    - Bloque `if __name__ == "__main__":` como el resto de módulos
    - _Requirements: 9.5, 9.12, 9.13, 13.31_

  - [x] 15.23 Escribir prueba de propiedad en `tests/test_ad_variant_image_edit_helpers_properties.py` (módulo nuevo)
    - **Property 22: Nombre de variación sin extensión de imagen**
    - Generar `s` arbitrarias (con puntos, espacios y Unicode), `base` no vacías que no terminan en una extensión conocida, extensiones de `_IMAGE_NAME_EXTENSIONS` con mayúsculas aleatorias, MIME de imagen con `mimetypes.guess_extension` definido e índices `index ≠ j` en [1, 10]; verificar `== stem(s) + f"_{index}"`, `f(base + e) == f(base) == base + f"_{index}"`, extensión final única tras añadir la del MIME, caso de stem vacío y nombres distintos por índice; `@settings(max_examples=100, deadline=None)` y comentario `# Feature: ad-variant-image-edit-pipeline, Property 22: Nombre de variación sin extensión de imagen`
    - **Validates: Requirements 9.5, 9.12, 9.13, 13.31, 13.32**

  - [x] 15.24 Actualizar las pruebas que asumen `banner_N.png` en `tests/test_ad_variant_image_edit_pipeline.py`
    - `test_one_variation_fails_returns_two`: `["banner_1", "banner_3"]` en lugar de `["banner_1.png", "banner_3.png"]`
    - `test_partial_upload_failures_keep_successful_one`: `h.upload.payloads[1]["image_name"] == "banner_2"` (sobre la versión ya adaptada por 15.14, que no toca los asserts de nombre)
    - Buscar `banner_` y `["image_name"]` en `tests/` y adaptar cualquier otro assert sobre `image_name` con extensión (la Property 11 se cubre en 15.15)
    - Nuevo `test_variation_name_has_no_double_extension` (13.32): con `image_name` `banner.png` y `banner.jpg` y variaciones `image/png`, `payload["image_name"] == "banner_1"` y `payload["image_name"] + mimetypes.guess_extension(payload["mime_type"]) == "banner_1.png"`
    - _Requirements: 9.5, 9.12, 13.9, 13.12, 13.32_

- [x] 16. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Ejecutar desde `fury/app`: `PYTHONPATH=. pytest tests/` y `PYTHONPATH=. python -m tests.<módulo>` para los módulos tocados en la tarea 15 (incluidos `tests.test_ad_variant_image_edit_helpers` y `tests.test_ad_variant_image_edit_helpers_properties`); comprobar que ninguna prueba espera en tiempo real (Edit_Sleep simulada), que `grep -r upload_ad_variant_image_from_edit app/` no devuelve resultados y que ningún assert de `tests/` espera un `image_name` de variación con extensión (`banner_N.png`).

## Notes

- Las sub-tareas marcadas con `*` son opcionales (pruebas y sus fakes) y pueden omitirse para un MVP más rápido; la 1.2 es prerequisito de las pruebas del pipeline, la tarea y los endpoints.
- Cada tarea referencia criterios concretos de `requirements.md` para trazabilidad; las pruebas de propiedades referencian las Properties 1–22 de `design.md`.
- Las tareas 1–14 describen la implementación original y se mantienen como completadas; algunas de sus descripciones (p. ej. 5.1, 5.2, 5.5 y 10.1 sobre `upload_ad_variant_image_from_edit`) quedan superadas por la tarea 15, que es la referencia vigente.
- Las sub-tareas de prueba de la tarea 15 no se marcan con `*`: actualizan pruebas existentes que se rompen al eliminar `upload_ad_variant_image_from_edit` y al cambiar el retorno de la subida, así que son necesarias para que la suite siga en verde.
- Estado de los supuestos de la tarea 15 (ver `requirements.md`): A1 resuelto / fuera de alcance (lo cubre la spec de Sinergia de `get_ad_variant_image`; esta spec depende de ella), A2 confirmado (15 s), A3 confirmado (1 consulta + 3 reintentos: máximo 4 consultas y 3 esperas de 5 s por imagen), A4 confirmado (ids `IMG_mock_{ad_id}_{n}`) y A5 resuelto / fuera de alcance (el usuario actualiza Sinergia para persistir `image_prompt`; la doble extensión se corrige en Fury con 15.21–15.24, D17).
- Riesgo aceptado: el peor caso de `resolve_urls` (15 + 75·n s, ≈ 765 s con n = 10) puede superar `task_soft_time_limit=900` junto con los demás pasos (Decisión confirmada 16); no genera tareas.
- Las sub-tareas 15.21–15.24 tampoco se marcan con `*`: 15.24 corrige asserts existentes que dejarían de pasar con el nuevo nombre.
- La validación real con Gemini (NanoBanana2 y Variant_Prompter) y con las rutas reales de Sinergia queda fuera de esta lista: el host de desarrollo puede estar geobloqueado y las rutas de Sinergia pertenecen a otra spec.
- Las tareas que escriben en el mismo archivo (`job_runner_service.py`, módulos `test_*_properties.py`, `test_ad_variant_image_edit_task.py`, `test_ad_variant_sinergia_tools.py`, etc.) están en waves distintas del grafo.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "2.1", "3.1", "5.1", "5.2", "6.1", "7.1", "7.2"] },
    { "id": 1, "tasks": ["2.2", "2.3", "3.2", "4.1", "5.3", "6.2", "7.3", "9.1", "13.2"] },
    { "id": 2, "tasks": ["2.4", "3.3", "4.2", "5.4", "6.3", "9.2", "9.3", "10.1"] },
    { "id": 3, "tasks": ["4.3", "5.5", "10.2", "10.3", "11.1"] },
    { "id": 4, "tasks": ["10.4", "11.2", "13.1"] },
    { "id": 5, "tasks": ["10.5", "13.3"] },
    { "id": 6, "tasks": ["10.6", "13.4"] },
    { "id": 7, "tasks": ["10.7", "13.5"] },
    { "id": 8, "tasks": ["10.8", "13.6"] },
    { "id": 9, "tasks": ["15.1", "15.7", "15.9", "15.10"] },
    { "id": 10, "tasks": ["15.2", "15.8", "15.11"] },
    { "id": 11, "tasks": ["15.3", "15.12"] },
    { "id": 12, "tasks": ["15.4", "15.13"] },
    { "id": 13, "tasks": ["15.5", "15.14", "15.21"] },
    { "id": 14, "tasks": ["15.6", "15.15", "15.20", "15.22", "15.24"] },
    { "id": 15, "tasks": ["15.16", "15.23"] },
    { "id": 16, "tasks": ["15.17"] },
    { "id": 17, "tasks": ["15.18"] },
    { "id": 18, "tasks": ["15.19"] }
  ]
}
```
