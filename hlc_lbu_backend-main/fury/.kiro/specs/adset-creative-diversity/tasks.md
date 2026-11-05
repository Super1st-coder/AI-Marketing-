# Implementation Plan: adset-creative-diversity

## Overview

Implementación incremental en Python (FastAPI + Celery, Pydantic v2) dentro de `fury/app`. Primero se fija una prueba de regresión del Legacy_Path contra el código actual; después se añaden el flag, la validación de entrada y la corrección de `validate_validador_response`; a continuación los helpers puros (`services/adset_diversity.py`, `services/diversity_checker.py`) y los cambios del Image_Generator; y por último la orquestación del Diversity_Path en `services/job_runner_service.py`. Todas las pruebas viven en `fury/app/tests`, se ejecutan desde `fury/app` con `PYTHONPATH=. pytest tests/` y `PYTHONPATH=. python -m tests.<módulo>`, y las propiedades usan `hypothesis` con `@settings(max_examples=100, deadline=None)` y el comentario `# Feature: adset-creative-diversity, Property {n}: {texto}`.

## Tasks

- [x] 1. Infraestructura de pruebas y regresión del Legacy_Path
  - [x] 1.1 Crear los fakes compartidos del Diversity_Path
    - Crear `fury/app/tests/_diversity_pipeline_fakes.py` (no es módulo de test) reutilizando `FakeRedis`, `ScriptedAsyncFake`, `LogCapture` y `network_guard()` de `tests/_edit_pipeline_fakes.py`
    - Añadir `FakeRunAgent` (respuestas por nombre de agente, registro de `(agent_name, message)`, ejecución del `validator` recibido), `FakeAgentFactories` sin Langfuse y fakes de `get_adset_context`, `get_template_context`, `get_a_template_definition`, `get_ctas`, `save_ads`, `delete_variants`, `post_to_abyssale_and_wait`, `generate_images_from_prompts`, `upload_image_to_library_tool` (tal como lo importa `nano_banana_agent`), `gai.Client`, `httpx.get` y `asyncio.sleep`
    - Helper `make_adset_context(ad_ids)` basado en `copy.deepcopy(_MOCK_ADSET)` que añade Ads en `adset.data.ads`, y helper para parchear `job_runner_service` (`_run_agent`, `_redis`, `_load`, `_store`, factories, tools)
    - _Requirements: 12.1, 12.2_

  - [x] 1.2 Escribir la prueba golden del Legacy_Path antes de modificar el pipeline
    - Crear `fury/app/tests/test_phase1_legacy_golden.py`: con el flag en `False` (o ausente), contexto mock y respuestas fijas de `FakeRunAgent`, registrar la secuencia `(agent_name, message)` del código actual y fijarla como referencia literal en la prueba
    - Comprobar que el resultado tiene exactamente las claves `variant_job_id`, `id_adset`, `status`, `abyssale_batch_ids`, `proposals`, `validation_reports`, `saved_ads` (sin `diversity_reports`) y que no se escribe el Checkpoint `adset_territories`
    - Incluir bloque `if __name__ == "__main__"`
    - _Requirements: 2.2, 2.7, 12.13_

- [x] 2. Flag, configuración y excepción del Diversity_Path
  - [x] 2.1 Declarar el Diversity_Flag y la excepción de job
    - Añadir `USE_ADSET_CREATIVE_DIVERSITY: bool = False` en `core/config.py` junto a `USE_TERRITORY_ENGINE`, con comentario
    - Documentar `USE_ADSET_CREATIVE_DIVERSITY=false` en `fury/app/env.example`
    - Añadir `AdsetCreativeDiversityError(FuryException)` en `core/exceptions.py` con `code = "ADSET_DIVERSITY_ERROR"`, `status_code = 500` y `__reduce__` picklable, ajustado al constructor real de `FuryException`
    - _Requirements: 2.1, 2.6, 3.11_

- [x] 3. Validación de entrada y Run_Local_Endpoint
  - [x] 3.1 Implementar `VariantCreate._validate_request`
    - `model_validator(mode="after")` en `schemas/pipeline_schemas.py` sin cambiar las declaraciones de campo; reglas de id_adset, id_variant ≥ 1, `add_variant is not True` → id_variant no vacío e id_ad > 0, y `project_id` obligatorio leyendo `settings.USE_ADSET_CREATIVE_DIVERSITY` con import lazy (D3)
    - Un único `ValueError` con mensajes `"<campo>: <motivo>"` unidos por `; `
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

  - [x] 3.2 Propagar todos los parámetros en run-local
    - En `api/v2/endpoints/variants.py`, `run_variant_local` llama a `_run_phase1(task=None, task_id=uuid4, ...)` con los 7 parámetros; ante excepción registra y responde 500 con `detail=type(exc).__name__` (P9); 404 con `DEBUG=False` sin cambios; `create_variant` sin cambios
    - _Requirements: 1.9, 1.10, 10.1, 10.2, 10.3, 10.4, 10.5_

  - [x] 3.3 Escribir test de propiedad de la validación de VariantCreate
    - **Property 1: Validación de VariantCreate según oráculo**
    - En `tests/test_variant_create_validation_properties.py`, con un oráculo puro y ambos endpoints (`DEBUG=True` para run-local), flag en `True` y `False`
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9**

  - [x] 3.4 Escribir test de propiedad de propagación y error saneado
    - **Property 2: Propagación de parámetros y error saneado en los endpoints**
    - En `tests/test_variant_create_validation_properties.py`
    - **Validates: Requirements 10.1, 10.3, 10.5**

  - [x] 3.5 Escribir tests unitarios de validación de entrada
    - `tests/test_variant_create_validation.py`: casos de 422/aceptación de Req 12.11 en ambos endpoints, cabecera ausente/inválida, 0 llamadas a `apply_async` y `_run_phase1`, defaults intactos
    - _Requirements: 1.1, 1.10, 12.11_

  - [x] 3.6 Escribir tests unitarios de run-local
    - `tests/test_variants_run_local.py`: propagación de los 7 parámetros, 200 con `{"ok": 1, "data": ...}`, 404 con `DEBUG=False`, 500 con solo el nombre de la clase
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 12.12_

- [x] 4. Corrección de `validate_validador_response`
  - [x] 4.1 Reescribir la comprobación de `overall_pass` y `subset_to_regenerate`
    - En `services/ads_validators.py`: presencia con `in`, tipo `bool` para `overall_pass`, presencia y tipo `list` para `subset_to_regenerate`, sin `KeyError`
    - _Requirements: 7.11_

  - [x] 4.2 Escribir test de propiedad del validador de respuesta
    - **Property 15: validate_validador_response acepta overall_pass=False**
    - En `tests/test_ads_validators_validador.py`
    - **Validates: Requirements 7.11**

  - [x] 4.3 Escribir tests unitarios del validador de respuesta
    - En `tests/test_ads_validators_validador.py`: `overall_pass=False` con lista aceptado; ausente, no booleano, `subset_to_regenerate` ausente o no lista rechazados
    - _Requirements: 7.11, 12.18_

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise. Incluye `test_phase1_legacy_golden.py`.

- [x] 6. Helpers puros del Diversity_Path (`services/adset_diversity.py`)
  - [x] 6.1 Implementar tipos y resolución de Ad_Slots
    - Crear `services/adset_diversity.py` con docstring de módulo, `VARIANT_KEY_FMT`, `PLAN_ID_FMT`, `VariantSlot`, `CreativePlan`, `DiversityReport` (con `ad_failed` y `error`, D5) y `AdSlotPlan`
    - `extract_adset_ads` (vía `unwrap_adset`, ids int > 0 sin bool, deduplicado D11, orden ascendente, warning por descarte), `resolve_ad_slots` (Scenario_1/2, slot extra con warning) y `bind_territories` (copia profunda con `ad_id` por slot)
    - _Requirements: 3.1, 3.2, 3.5, 3.6, 3.7, 3.13_

  - [x] 6.2 Escribir test de propiedad de Ad_Slots
    - **Property 3: Resolución de Ad_Slots determinista**
    - En `tests/test_adset_diversity_properties.py`
    - **Validates: Requirements 3.1, 3.2, 3.5, 3.6, 3.7**

  - [x] 6.3 Escribir test de propiedad de estabilidad del territorio
    - **Property 4: Territorio estable por slot**
    - En `tests/test_adset_diversity_properties.py`, sobre `assign_territories(..., n_variantes=1)` y `bind_territories` con Ads en distinto orden
    - **Validates: Requirements 3.4, 3.5, 12.4, 12.6**

  - [x] 6.4 Escribir test de propiedad de disyunción de anclas y ejes
    - **Property 5: Disyunción de anclas y ejes dentro de los límites**
    - En `tests/test_adset_diversity_properties.py`
    - **Validates: Requirements 3.8, 3.9**

  - [x] 6.5 Escribir test de propiedad de Forbidden_Territories
    - **Property 6: Forbidden_Territories son los anclas de los demás slots**
    - En `tests/test_adset_diversity_properties.py`
    - **Validates: Requirements 3.5, 3.10**

  - [x] 6.6 Implementar plantillas, Variant_Slots y Creative_Plan
    - `resolve_project_templates`, `build_variant_slots` (rotación `(ad_slot + k - 1) % len`, `ValueError` con lista vacía o `n_variants < 1`), `build_creative_plan` (id `plan_ad_{ad_id}`, sin `template_id`/`template_selection_reason`, con `variants`) y `first_text`
    - _Requirements: 4.1, 4.3, 4.5, 4.6, 4.9_

  - [x] 6.7 Escribir test de propiedad de rotación de plantillas
    - **Property 7: Rotación de plantillas por Variant_Slot**
    - En `tests/test_adset_diversity_properties.py`, incluido `n_variants > 4`
    - **Validates: Requirements 4.5, 4.6, 4.9**

  - [x] 6.8 Escribir test de propiedad del Creative_Plan
    - **Property 8: El Creative_Plan conserva el territorio**
    - En `tests/test_adset_diversity_properties.py`
    - **Validates: Requirements 4.1, 4.3**

  - [x] 6.9 Implementar validación de forma y merge por `variant_key`
    - `check_variant_items`, `make_variant_validator` (compuesto sobre el validador base, `error_code="ERR_VARIANT_SHAPE"`), `merge_by_variant_key`, `build_variant_proposals` y `merge_variant_creative` (`plan = {**plan, "id": variant_key}`, item con `error` si falta el copy)
    - _Requirements: 5.2, 5.3, 5.8, 5.9, 7.4, 8.2_

  - [x] 6.10 Escribir test de propiedad de forma por Variant_Slot
    - **Property 9: Validación de forma por Variant_Slot**
    - En `tests/test_adset_diversity_properties.py`, para `kind="copy"` y `kind="image_prompt"`, comprobando `AgentValidationError` vía `run_agent` y ausencia de Checkpoint
    - **Validates: Requirements 5.2, 5.3, 5.8**

  - [x] 6.11 Escribir test de propiedad del merge por variante
    - **Property 10: Merge por variant_key sin sobrescrituras**
    - En `tests/test_adset_diversity_properties.py`, incluyendo `build_abyssale_payload` real
    - **Validates: Requirements 5.9, 8.2**

  - [x] 6.12 Implementar los constructores de mensajes
    - `build_estratega_message`, `build_copy_message`, `build_image_prompt_message` y `build_validador_message`, todos con bloque `FULL ADSET CONTEXT`; el del Validador con `id` del plan, `variant_key` de cada propuesta, Forbidden_Territories completos, errores deterministas e instrucciones (a)–(c)
    - _Requirements: 2.5, 4.2, 5.1, 5.7, 7.2, 7.3_

  - [x] 6.13 Escribir test de propiedad del mensaje al Validador
    - **Property 14: Contenido del mensaje al Validador**
    - En `tests/test_adset_diversity_properties.py`
    - **Validates: Requirements 7.3**

  - [x] 6.14 Escribir tests unitarios de `adset_diversity`
    - `tests/test_adset_diversity.py`: ejemplos de slots (mock y real), `n_variants=6` con las 3 plantillas de `_MOCK_TEMPLATES`, Creative_Plan, mensajes con contexto saneado
    - _Requirements: 3.1, 4.5, 4.9, 12.19_

- [x] 7. Diversity_Checker (`services/diversity_checker.py`)
  - [x] 7.1 Implementar tipos y `check_territories`
    - `DiversityIssue`, `DiversityCheckResult` (`ok`, `error_messages`, `warning_messages`, `failing_variant_keys`, `merged`), `anchor_side` y `check_territories` con tolerancia por pool o vocabulario agotado y orden estable de mensajes
    - _Requirements: 6.1, 6.2, 6.3, 6.10_

  - [x] 7.2 Escribir test de propiedad de reglas de territorio
    - **Property 11: Reglas de territorio del Diversity_Checker**
    - En `tests/test_diversity_checker_properties.py`
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.10**

  - [x] 7.3 Implementar `check_variant_slots` y `check_variants`
    - Reglas 6.4–6.9 con `variant_key` afectados; textos prohibidos vacíos ignorados y ancla propia excluida con warning (D6)
    - _Requirements: 6.1, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

  - [x] 7.4 Escribir test de propiedad de reglas de variantes
    - **Property 12: Reglas de variantes del Diversity_Checker**
    - En `tests/test_diversity_checker_properties.py`
    - **Validates: Requirements 6.1, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9**

  - [x] 7.5 Escribir tests unitarios del Diversity_Checker
    - `tests/test_diversity_checker.py`: un caso que cumple y otro que incumple por cada regla 6.2–6.10, warning por agotamiento y casos D6
    - _Requirements: 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 12.7_

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Image_Generator: `image_prompt` en la subida y resiliencia
  - [x] 9.1 Añadir `image_prompt` al payload de subida
    - En `agents/nano_banana_agent.py`, `images_data` con `image_prompt` (str o `""`); log por subida solo con claves, `plan_id`, `image_name` y longitudes de `image_data` e `image_prompt`
    - _Requirements: 9.1, 9.2, 9.6, 9.7_

  - [x] 9.2 Actualizar docstrings del Upload_Tool
    - Docstring de `upload_image_to_library` en `agents/tools/campaign_tools.py` y en `agents/tools/mock_sinergia.py` con `image_prompt`; sin cambios en el cuerpo `{"image": image_data}` ni en el retorno `IMG_mock_{ad_id}_{n}`
    - _Requirements: 9.3, 9.4, 9.5_

  - [x] 9.3 Marcar fallos de generación y sanear logs
    - Helper `_safe_url`; warnings de descarga de `base_image_url` y `product_image_urls` con URL sin query y `type(exc).__name__`, omitiendo la parte fallida
    - Fallo de `gai.Client` → todos los items con `image_url=None`, `image_error=<clase>`; except por item (incluido `TimeoutError`) y `"NoImageInResponse"`; resultados de `gather` con `error=<clase>`; errores de subida (excepción o `""`) registrados sin `image_id`
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.8_

  - [x] 9.4 Escribir test de propiedad del payload de subida
    - **Property 19: image_prompt en el payload de subida**
    - En `tests/test_nano_banana_generation_properties.py`
    - **Validates: Requirements 9.1, 9.2, 9.6, 11.5**

  - [x] 9.5 Escribir test de propiedad de logs sin secretos
    - **Property 20: Logs y errores sin secretos ni binarios**
    - En `tests/test_nano_banana_generation_properties.py`
    - **Validates: Requirements 9.7, 11.8**

  - [x] 9.6 Escribir test de propiedad de descargas fallidas
    - **Property 21: Resiliencia ante descargas fallidas**
    - En `tests/test_nano_banana_generation_properties.py`
    - **Validates: Requirements 11.1, 11.2**

  - [x] 9.7 Escribir test de propiedad del marcado de fallos
    - **Property 22: Marcado de fallos de generación**
    - En `tests/test_nano_banana_generation_properties.py`
    - **Validates: Requirements 11.3, 11.4, 11.5**

  - [x] 9.8 Escribir tests unitarios del Image_Generator
    - `tests/test_nano_banana_generation.py`: `image_prompt` presente/ausente/no str, descarga base con excepción/estado ≠ 200/cuerpo vacío, fallo en una de dos `product_image_urls`, excepción y `asyncio.TimeoutError` simulado en Gemini, respuesta sin `inline_data`, Upload con excepción o `""`, ningún log con base64
    - _Requirements: 9.1, 9.2, 9.7, 11.1, 11.2, 11.3, 11.4, 11.6, 12.9, 12.10, 12.17_

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise. `test_phase1_legacy_golden.py` debe seguir pasando.

- [x] 11. Orquestación del Diversity_Path en `services/job_runner_service.py`
  - [x] 11.1 Bifurcar `_run_phase1` y crear el esqueleto del Diversity_Path
    - `_AdDiversityFailure`, `_DiversityDeps` y `variant_key` en las entradas de `_save_ads_programmatically` solo si el copy lo trae
    - Tras el paso 1, si el flag está activo, imports lazy y `return await _run_adset_diversity_path(...)` (Req 2.4)
    - `_run_adset_diversity_path`: `extract_adset_ads` + `resolve_ad_slots`; Scenario_1 vacío → warning y resultado con listas vacías; `_load_or_assign_territories` (Checkpoint `adset_territories`, `assign_territories(..., n_variantes=1)` una vez, lista vacía → `AdsetCreativeDiversityError` con `id_adset`, `bind_territories`); bucle por Ad con semáforo `ADS_MAX_CONCURRENT_ADS` llamando a `_run_diversity_ad`; resultado con claves legacy + `diversity_reports`; espera final de 15 s
    - El Legacy_Path no cambia: la prueba golden debe seguir pasando
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.7, 3.1, 3.3, 3.11, 3.12, 3.13, 7.12_

  - [x] 11.2 Implementar `_build_or_load_creative_plan`
    - Checkpoint `strategy` (D10, `_project_templates` D14) o Estratega_Adset con `validate_estratega_adset_response` + `apply_descriptions` (`concept` vacío → `AgentValidationError`); `get_template_context` (excepción, `ok=False` o vacío → `_AdDiversityFailure` con `project_id` y `ad_id`); `build_variant_slots`, `build_creative_plan`; `check_territories` (errores del slot) y `check_variant_slots` → `_AdDiversityFailure`; `_store(strategy)`
    - `custom_prompt` a `make_estratega_adset_agent`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 6.11, 8.6_

  - [x] 11.3 Implementar copywriting e image prompts iniciales
    - En `_run_diversity_ad`: Checkpoint `copy` o una invocación al Copywriter con `make_variant_validator(validate_copywriter_response, ..., kind="copy")`; `_validate_ctas` siempre; Checkpoint `image_prompts` o una invocación al Image_Prompter con validador compuesto `kind="image_prompt"`; Checkpoints solo con respuestas válidas
    - `custom_prompt` a `make_copywriter_agent` y `make_image_prompter_agent`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 8.6_

  - [x] 11.4 Implementar `_diversity_validation_loop` y `_regenerate_variants`
    - Hasta 3 iteraciones: `check_variants` antes de cada llamada al Validador (`make_validador_agent()` sin `custom_prompt`, también con `n_variants == 1`); filtrado de `subset_to_regenerate` (D8); regeneración de la unión de claves (D7, D9) con merge por `variant_key`, `_validate_ctas` y actualización de Checkpoints; `AgentValidationError` del Validador intermedio → siguiente iteración, último → relanzar; fallos deterministas persistentes → `_AdDiversityFailure`; fallo semántico persistente o subset vacío → warning y `overall_pass=False`
    - _Requirements: 7.1, 7.2, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10_

  - [x] 11.5 Implementar imágenes, guardado, Abyssale y `delete_variants`
    - `generate_images` en `try/except` → `[]` con log `[{task_id}]` y `ad_id`; Checkpoint `saved_ads` o una llamada a `save_ads` con payloads en orden de Variant_Slots; `merge_variant_creative` → `build_abyssale_payload` → `post_to_abyssale_and_wait` en `try/except` y registro del webhook; `delete_variants(id_variant)` solo si `add_variant is not True`, `id_variant` no vacío, `ad_id == id_ad`, algún `saved` y `batch_id`, con warning del motivo en otro caso
    - Captura de `_AdDiversityFailure` en `_run_diversity_ad` → Diversity_Report con `ad_failed=True` y `error` saneado, sin `save_ads`, Abyssale ni `delete_variants`
    - _Requirements: 5.9, 7.12, 8.1, 8.2, 8.3, 8.4, 8.5, 8.7, 11.7_

  - [x] 11.6 Escribir test de propiedad del bucle de validación
    - **Property 13: Bucle de validación acotado y regeneración selectiva**
    - En `tests/test_adset_diversity_pipeline_properties.py`, con guiones generados de checker, Validador y regeneración
    - **Validates: Requirements 7.1, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10**

  - [x] 11.7 Escribir test de propiedad del filtrado de CTAs
    - **Property 16: Filtrado de CTAs contra el catálogo**
    - En `tests/test_adset_diversity_pipeline_properties.py`, con copy generado y desde Checkpoint
    - **Validates: Requirements 5.4**

  - [x] 11.8 Escribir test de propiedad de cardinalidades
    - **Property 17: Cardinalidades del Diversity_Path**
    - En `tests/test_adset_diversity_pipeline_properties.py`, N ∈ [1, 4], `n_variants` ∈ [1, 8], ambos escenarios
    - **Validates: Requirements 2.5, 3.3, 3.7, 4.9, 7.12, 8.1, 12.3, 12.19**

  - [x] 11.9 Escribir test de propiedad de `delete_variants`
    - **Property 18: Condiciones de delete_variants**
    - En `tests/test_adset_diversity_pipeline_properties.py`, verificando el orden respecto a `post_to_abyssale_and_wait`
    - **Validates: Requirements 8.3, 8.4, 8.5, 8.7**

  - [x] 11.10 Escribir test de propiedad de reanudación
    - **Property 23: Reanudación por Checkpoints**
    - En `tests/test_adset_diversity_pipeline_properties.py`, con subconjuntos de Checkpoints en `FakeRedis`
    - **Validates: Requirements 3.13, 4.8, 5.6, 12.15**

  - [x] 11.11 Escribir tests unitarios del pipeline del Diversity_Path
    - `tests/test_adset_diversity_pipeline.py`: happy path Scenario_1 (N=2, V=2/3) y Scenario_2 con `add_variant=True`; Scenario_2 con `id_ad` ausente; Adset sin Ads; Adset sin anclas; errores de estrategia (sin `concept`, plantillas con excepción o vacías, copies con número distinto); `n_variants=6` en ambos escenarios; `delete_variants` con `add_variant=False` (1 vez tras Abyssale, 0 si `save_ads` o Abyssale fallan); excepción no controlada del Image_Generator; `custom_prompt` en las tres factories y no en el Validador; Validador con `n_variants=1`; `diversity_reports`
    - _Requirements: 4.4, 4.7, 7.2, 8.6, 11.7, 12.3, 12.4, 12.5, 12.8, 12.14, 12.16, 12.19_

- [x] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise. Ejecutar `PYTHONPATH=. pytest tests/` desde `fury/app` y verificar que `test_phase1_legacy_golden.py` sigue pasando sin cambios en su referencia.

### Decisión P11: una plantilla por Ad, distinta entre Ad_Slots

Delta de "Estado de la implementación frente a la Decisión P11" (design.md, D15–D16). El endurecimiento de producción (D17) ya está implementado y no tiene tareas. Todas las pruebas se ejecutan desde `fury/app` con `PYTHONPATH=. env/bin/python -m pytest tests/`.

- [x] 13. Ad_Template por Ad en `services/adset_diversity.py`
  - [x] 13.1 Añadir `ad_template_for_slot` y `slot_ad_templates`
    - `ad_template_for_slot(ad_slot, project_templates) -> str` = `project_templates[ad_slot % len]`; `ValueError` con lista vacía o `ad_slot < 0`
    - `slot_ad_templates(n_slots, project_templates) -> list[str]` = `[ad_template_for_slot(s, ...) for s in range(n_slots)]` (D16)
    - Docstrings con referencia a P11/D15/D16
    - _Requirements: 4.5, 4.6, 6.12_

  - [x] 13.2 Cambiar `build_variant_slots` a una plantilla por Ad
    - Todos los `k` usan `ad_template_for_slot(ad_slot, project_templates)`; se mantiene `{variant_key, template_id}` por slot y los `ValueError` existentes
    - Actualizar el comentario de `VariantSlot.template_id` (ya no `(ad_slot + k - 1) % len`)
    - _Requirements: 4.5, 4.6, 4.9_

  - [x] 13.3 Deduplicar en `resolve_project_templates`
    - Conservar solo la primera aparición de cada identificador, en el orden devuelto; omitir entradas que no son dict o sin `id` ni `template_id` (o vacíos); `[]` si `ok` es `False` o la forma no es válida
    - _Requirements: 4.5, 4.7_

  - [x] 13.4 Adaptar el test de propiedad existente de plantillas por Ad
    - **Property 7: Una plantilla por Ad y resolución de Project_Templates**
    - En `tests/test_adset_diversity_properties.py`, sustituir la aserción `templates[(ad_slot + k - 1) % len(templates)]` por `templates[ad_slot % len(templates)]` en todos los slots y eliminar la comprobación "`n_variants <= len(templates)` → todos los `template_id` distintos"; sin cambiar la estrategia `template_contexts`
    - **Validates: Requirements 4.5, 4.6, 4.9**

  - [x] 13.5 Ampliar el test de propiedad de plantillas por Ad
    - **Property 7: Una plantilla por Ad y resolución de Project_Templates**
    - En `tests/test_adset_diversity_properties.py`, ampliar la estrategia `template_contexts` con identificadores repetidos, entradas sin `id`/`template_id`, valores vacíos, enteros y no-dicts (oráculo: primera aparición, en orden); incluir `n_variants > len(templates)`
    - **Validates: Requirements 4.5, 4.6, 4.9**

  - [x] 13.6 Adaptar los tests unitarios existentes de `adset_diversity` y del Creative_Plan
    - `tests/test_adset_diversity.py`: el caso `n_variants=6` con 3 plantillas pasa a esperar las 6 variantes con `templates[ad_slot % 3]` (se elimina "cada plantilla usada dos veces"); quitar el import y la comprobación de `TEMPLATE_REPEATED` y comprobar solo `result.ok` y `result.errors == ()`
    - `tests/test_adset_diversity_creative_plan.py`: actualizar la aserción de rotación `(ad_slot + k - 1) % len` (todas las variantes con `ids[ad_slot % len(ids)]`) y reescribir `test_repeated_template_slots_fail_the_ad`: con la deduplicación, `[{"id": "T1"}, {"id": "T1"}]` da una sola plantilla, el Ad no falla y todas las variantes usan `T1`
    - _Requirements: 4.5, 4.6, 4.7, 4.9, 12.19_

  - [x] 13.7 Añadir tests unitarios nuevos de `adset_diversity`
    - `tests/test_adset_diversity.py`: casos de deduplicación de `resolve_project_templates` (repetidos, entradas inválidas, `ok: False`) y de `ad_template_for_slot`/`slot_ad_templates` (lista vacía, `ad_slot < 0`, rotación)
    - _Requirements: 4.5, 4.6, 4.7_

  - [x] 13.8 Adaptar los tests unitarios existentes del pipeline a una plantilla por Ad
    - `tests/test_adset_diversity_pipeline.py`: reescribir `_assert_template_rotation` para esperar `templates[ad_slot % len]` en todas las variantes (slots, copies, payloads de `save_ads` y elementos de Abyssale) y ajustar los casos de seis variantes en ambos escenarios
    - Estas pruebas pasan una vez aplicada 14.1 (sin `TEMPLATE_REPEATED`); se verifican en el checkpoint 15
    - _Requirements: 4.5, 4.9, 8.1, 12.19_

- [x] 14. Reglas del Diversity_Checker en `services/diversity_checker.py`
  - [x] 14.1 Sustituir la regla 6.7 por `TEMPLATE_MIXED_IN_AD`
    - Eliminar `TEMPLATE_REPEATED` y añadir `TEMPLATE_MIXED_IN_AD`: en Variant_Slots, copies e image prompts (cada colección por separado), referencia = primer `template_id`, un error por cada item con otro valor, identificando `plan_id`, ambos `variant_key` y sus `template_id`; siempre error, nunca warning por 6.10
    - 6.6: `template_id` vacío, `None` o fuera de Project_Templates → error con `variant_key` y valor recibido
    - _Requirements: 6.6, 6.7_

  - [x] 14.2 Añadir `check_ad_templates` (regla 6.12)
    - `check_ad_templates(slot_templates, project_templates) -> DiversityCheckResult`; por cada par `i < j` con el mismo template → `AD_TEMPLATE_REPEATED` con `ad_slots=(i, j)` y el `template_id`; error si `len(slot_templates) <= len(project_templates)`, warning en otro caso
    - _Requirements: 6.10, 6.12_

  - [x] 14.3 Ajustar las reglas 6.1, 6.2, 6.4, 6.5, 6.8 y 6.9
    - 6.1: pares recorridos con `i < j` sin pares invertidos ni duplicados, cada issue en una sola lista, orden estable (ancla → ejes de `AXIS_VOCAB` → paleta; en variantes 6.5 → 6.4 → 6.6/6.7 → 6.8 → 6.9) y sin mutar la entrada
    - 6.2: comparar `anchor_primary.text` con `strip().casefold()` (el mensaje muestra el texto del slot `i`)
    - 6.4: `plan_id` ausente o `None` es error con `variant_key`, recibido y esperado
    - 6.5: un error por colección (copies, image prompts) con esperado y recibido
    - 6.8: `headline`/`primary_text` vacíos, ausentes, `None` o lista vacía no cuentan como duplicado
    - 6.9: el mensaje indica el campo afectado (`headline`, `primary_text` o ambos), el `variant_key` y el texto prohibido
    - _Requirements: 6.1, 6.2, 6.4, 6.5, 6.8, 6.9_

  - [x] 14.4 Adaptar el test de propiedad existente de reglas de territorio
    - **Property 11: Reglas de territorio del Diversity_Checker**
    - En `tests/test_diversity_checker_properties.py`, el pool `_anchor_texts` ya genera `"ahorro"` y `"Ahorro"`: cambiar la comparación del oráculo `_expected` a `strip().casefold()` (el valor esperado es el texto del slot `i`) para que coincida con la nueva regla 6.2
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.10**

  - [x] 14.5 Ampliar el test de propiedad de reglas de territorio
    - **Property 11: Reglas de territorio del Diversity_Checker**
    - En `tests/test_diversity_checker_properties.py`, generar anclas repetidas que solo difieren en espacios exteriores; comprobar un issue por par `i < j` sin pares invertidos, que la entrada no cambia y que dos llamadas dan el mismo orden
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.10**

  - [x] 14.6 Adaptar el test de propiedad existente de reglas por Ad
    - **Property 12: Reglas por Ad del Diversity_Checker**
    - En `tests/test_diversity_checker_properties.py`, eliminar `TEMPLATE_REPEATED` del import, de la tabla de orden y de las inyecciones de duplicado en items (`dup`) y slots (`sdup`); ajustar el oráculo de las inyecciones 6.6 existentes (`tpl_foreign_*` o `template_id` ausente) y de `plan_id` incorrecto/ausente (6.4) a las reglas 6.4, 6.6 y 6.7 de 14.1/14.3, incluida la posición de `TEMPLATE_MIXED_IN_AD` en la tabla de orden si una plantilla ajena también lo produce según el diseño
    - **Validates: Requirements 6.1, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9**

  - [x] 14.7 Ampliar el test de propiedad de reglas por Ad
    - **Property 12: Reglas por Ad del Diversity_Checker**
    - En `tests/test_diversity_checker_properties.py`, inyectar un `template_id` distinto del Ad_Template pero dentro de Project_Templates en items y slots → `TEMPLATE_MIXED_IN_AD` con cualquier `n_variants` y `len(Project_Templates)`; comprobar que vacíos/`None` no dan 6.8, el campo en el mensaje de 6.9, la no mutación y el determinismo
    - **Validates: Requirements 6.1, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9**

  - [x] 14.8 Escribir test de propiedad del reparto de Ad_Templates
    - **Property 24: Reparto de Ad_Templates entre Ad_Slots**
    - En `tests/test_diversity_checker_properties.py`: `slot_ad_templates` asigna `templates[s % len]`; con `n_slots <= len` todos distintos y `check_ad_templates` sin errores ni warnings; con `n_slots > len` solo warnings; con mapas arbitrarios con repeticiones inyectadas, exactamente un issue por par `i < j` (error o warning según 6.12/6.10), determinista y sin mutar la entrada
    - **Validates: Requirements 4.6, 6.10, 6.12**

  - [x] 14.9 Adaptar los tests unitarios existentes del Diversity_Checker
    - `tests/test_diversity_checker.py`: quitar el import de `TEMPLATE_REPEATED`; el caso de `check_variant_slots` con dos variantes con la misma plantilla pasa a esperar ausencia de errores (o se reescribe con una plantilla distinta del Ad_Template → `TEMPLATE_MIXED_IN_AD`); `n=6` sigue sin errores; revisar los casos existentes de 6.2, 6.4, 6.6, 6.8 y 6.9 que dependan del comportamiento cambiado en 14.3
    - _Requirements: 6.2, 6.4, 6.6, 6.7, 6.8, 6.9, 12.7_

  - [x] 14.10 Añadir tests unitarios nuevos del Diversity_Checker
    - `tests/test_diversity_checker.py`: casos de `TEMPLATE_MIXED_IN_AD` en slots, copies e image prompts; casos cumple/incumple de `check_ad_templates` (error con N ≤ plantillas, warning con 4 slots y 3 plantillas); anclas con mayúsculas/espacios (6.2), `plan_id` ausente (6.4), las dos colecciones mal dimensionadas (6.5), `template_id` vacío (6.6), copies vacíos no duplicados (6.8) y campo en el mensaje (6.9)
    - _Requirements: 6.2, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.12, 12.7, 12.20_

- [x] 15. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise. Ejecutar `PYTHONPATH=. env/bin/python -m pytest tests/` desde `fury/app`; `tests/test_phase1_legacy_golden.py` debe pasar sin cambios en su referencia.

- [x] 16. Regla 6.12 en el Diversity_Path (`services/job_runner_service.py`)
  - [x] 16.1 Llamar a `check_ad_templates` en `_build_or_load_creative_plan`
    - Tras `check_territories` y `check_variant_slots`, llamar a `check_ad_templates(slot_ad_templates(len(ad.all_territories), project_templates), project_templates)` y conservar solo los issues cuyo `ad_slots` incluye el slot del Ad (igual que con `check_territories`)
    - Errores → `_AdDiversityFailure` con la lista completa (sin Copywriter ni Image_Generator); warnings → log `[{task_id}]` y Diversity_Report; sin recalcular cuando se reanuda desde el Checkpoint `strategy` (D16)
    - Import lazy dentro de la corrutina; el Legacy_Path no cambia
    - _Requirements: 2.2, 2.4, 6.10, 6.11, 6.12_

  - [x] 16.2 Añadir tests unitarios de la regla 6.12 en el Creative_Plan
    - `tests/test_adset_diversity_creative_plan.py` (el test existente ya se adaptó en 13.6): añadir un caso que fuerza `AD_TEMPLATE_REPEATED` como error (p. ej. parcheando `slot_ad_templates`) y verifica fallo del Ad sin Copywriter, y otro con más slots que plantillas que solo registra warning
    - _Requirements: 4.5, 6.11, 6.12, 12.20_

  - [x] 16.3 Añadir tests unitarios del pipeline para Req 12.20
    - `tests/test_adset_diversity_pipeline.py` (`_assert_template_rotation` ya se adaptó en 13.8), casos de Req 12.20: (a) N ≤ plantillas → Ad_Templates distintos y sin errores ni warnings de plantilla; (b) 4 Ads y las 3 plantillas de `_MOCK_TEMPLATES` → slots 0 y 3 comparten plantilla, warning registrado, ningún error 6.12 y el job continúa con 4 `save_ads`; (c) Scenario_2: el Ad `id_ad` recibe el Ad_Template de su slot en Scenario_1, distinto de sus hermanos, y el slot extra recibe `templates[len(Adset_Ads) % len]`
    - _Requirements: 4.5, 4.6, 4.9, 8.1, 8.2, 12.3, 12.19, 12.20_

  - [x] 16.4 Actualizar los tests de propiedad del pipeline
    - **Property 17: Cardinalidades del Diversity_Path**
    - **Property 23: Reanudación por Checkpoints**
    - Opcional: las aserciones actuales (`set(slot_templates) <= set(template_ids)`, payloads en orden de slot, reportes sin fallo) siguen cumpliéndose con una plantilla por Ad y la regla 6.12 solo añade warnings, así que no se rompen; esta tarea solo las endurece
    - En `tests/test_adset_diversity_pipeline_properties.py`: en la Property 17, sustituir `set(slot_templates) <= set(template_ids)` por la igualdad de todos los `template_id`/`media_template_id` (slots, copies, payloads y Abyssale) con `template_ids[ad_slot % len(template_ids)]`; en la Property 23, comprobar que el reintento conserva el mismo Ad_Template y los mismos Variant_Slots
    - **Validates: Requirements 3.13, 4.8, 4.9, 5.6, 8.1, 12.3, 12.15, 12.19**

- [x] 17. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise. Ejecutar `PYTHONPATH=. env/bin/python -m pytest tests/` desde `fury/app`; verificar que `tests/test_phase1_legacy_golden.py` sigue pasando sin cambios en su referencia y que no queda ninguna referencia a `TEMPLATE_REPEATED` ni a `(ad_slot + k - 1)` en `services/` ni en `tests/`.

### Decisión P12: orden aleatorio de plantillas por job

Delta de "Estado de la implementación frente a la Decisión P12" (design.md, D12, D14, D15, D16, D18, D19). `ad_template_for_slot`, `slot_ad_templates` y `build_variant_slots` no cambian de firma; `diversity_checker.py`, el Legacy_Path y el camino `USE_TERRITORY_ENGINE` no cambian. Todas las pruebas se ejecutan desde `fury/app` con `PYTHONPATH=. env/bin/python -m pytest tests/`. Convención de pruebas (P12): el orden esperado nunca se fija a mano; se calcula con `template_order(project_templates, task_id)` y el `task_id` de la prueba, o se fija precargando `adset_templates` en el `FakeRedis` o parcheando `services.adset_diversity.template_order`.

- [x] 18. Template_Order sembrado en `services/adset_diversity.py`
  - [x] 18.1 Añadir `template_seed` y `template_order`
    - `template_seed(seed: str) -> int` = `int.from_bytes(hashlib.sha256(f"adset-templates:{seed}".encode("utf-8")).digest()[:8], "big")`; nunca `hash()` (salado por proceso)
    - `template_order(project_templates: Sequence[str], seed: str) -> list[str]`: copia la lista y la baraja con un `random.Random(template_seed(seed))` local; no usa ni altera el `random` global, no muta la entrada, `[]` para lista vacía y la lista de un elemento se devuelve igual
    - Actualizar los docstrings de `ad_template_for_slot`, `slot_ad_templates` y `build_variant_slots`: en el Diversity_Path reciben el Template_Order del job (P12, D15); sin cambios de firma ni de comportamiento
    - _Requirements: 4.5, 4.10, 4.11_

  - [x] 18.2 Escribir test de propiedad de Template_Order
    - **Property 25: Template_Order es una permutación determinista por semilla**
    - En `tests/test_adset_diversity_properties.py`: listas sin repetidos (incluidas vacía y de un elemento) y semillas arbitrarias (UUID4, vacía, Unicode); `sorted(salida) == sorted(entrada)`, lista nueva, misma salida en dos llamadas, entrada sin mutar y `random.getstate()` igual antes y después; con `len ≥ 2`, al menos dos órdenes distintos sobre las 64 semillas `f"task-{i}"`
    - **Validates: Requirements 4.10, 4.11, 12.20**

  - [x] 18.3 Añadir tests unitarios de `template_seed` y `template_order`
    - `tests/test_adset_diversity.py`: `template_seed` con un valor fijo registrado en la prueba (independiente de `PYTHONHASHSEED`); `template_order` sobre `mock_template_ids()`: misma salida para el mismo `task_id`, permutación de las 3 plantillas, dos `task_id` concretos con órdenes distintos (12.20 f), entrada sin mutar, `random` global intacto, lista vacía y de un elemento
    - _Requirements: 4.10, 4.11, 12.20_

  - [x] 18.4 Endurecer el test de propiedad de plantillas por Ad
    - **Property 7: Una plantilla por Ad y resolución de Project_Templates**
    - En `tests/test_adset_diversity_properties.py`, pasar a `build_variant_slots` una permutación `order` de la lista resuelta generada con `st.permutations` (incluye la identidad y el resultado de `template_order`) y esperar `order[ad_slot % len(order)]` en todos los slots
    - **Validates: Requirements 4.5, 4.9**

  - [x] 18.5 Endurecer el test de propiedad del reparto de Ad_Templates (parte pura)
    - **Property 24: Reparto de Ad_Templates entre Ad_Slots**
    - En `tests/test_diversity_checker_properties.py`, generar también una semilla `task_id` y aplicar `slot_ad_templates(n_slots, template_order(templates, task_id))`: slot `s` → `order[s % len(order)]`; con `n_slots ≤ len(templates)` todos distintos y `check_ad_templates(mapa, templates)` sin errores ni warnings; con `n_slots > len(templates)` solo warnings
    - **Validates: Requirements 4.6, 6.1, 6.10, 6.12**

- [x] 19. Plantillas del job en `services/job_runner_service.py`
  - [x] 19.1 Añadir `_JobTemplates`, el campo `templates` y `_load_or_resolve_templates`
    - Dataclass frozen `_JobTemplates(project_templates: tuple[str, ...], template_order: tuple[str, ...], failure: str | None = None)`
    - Nuevo campo `templates: _JobTemplates` en `_DiversityAdInput`, sin valor por defecto (como en el diseño); ver la nota sobre el valor por defecto en Notes
    - Corrutina `_load_or_resolve_templates(deps, job, slots) -> _JobTemplates`: si el Checkpoint `_cp_key(task_id, id_adset, "adset_templates")` es válido (dict con `project_templates` y `template_order` listas de cadenas no vacías, sin repetidos y `template_order` permutación de `project_templates`) se reutiliza sin llamar a `get_template_context` ni a `template_order`; si no es válido, warning `[{task_id}]` y nueva resolución
    - Resolución: `deps.get_template_context(project_id)` una sola vez → `resolve_project_templates` → `template_order(templates, task_id)` → `_store(adset_templates, {"project_templates": [...], "template_order": [...]}, ex=_CHECKPOINT_TTL)`; log `[{task_id}]` con el número de plantillas y el orden (solo ids)
    - Excepción (`type(exc).__name__`, nunca `str(exc)`), `ok == False` o lista vacía → `_JobTemplates((), (), failure=<causa>)` sin escribir el checkpoint ni lanzar (D19); la causa reproduce los textos actuales de `_build_or_load_creative_plan` (`get_template_context raised <Clase>`, `get_template_context returned ok=False`, lista vacía)
    - Imports de `adset_diversity` lazy dentro de la corrutina (D2)
    - _Requirements: 2.4, 4.5, 4.7, 4.10, 4.11, 4.12, 4.13_

  - [x] 19.2 Conectar las plantillas del job al Creative_Plan
    - En `_run_adset_diversity_path`, llamar a `templates = await _load_or_resolve_templates(deps, job, slots)` justo después de `_load_or_assign_territories` (así no se llama con Adset_Ads vacíos ni si `assign_territories` falla) y pasar el mismo objeto en `templates=` de cada `_DiversityAdInput`
    - En `_build_or_load_creative_plan`: eliminar la llamada a `deps.get_template_context` y la resolución por Ad; si `ad.templates.failure` (y no hay checkpoint `strategy` reutilizable) lanzar `_AdDiversityFailure(f"no templates for project_id={project_id} ad_id={ad_id} ({failure})")` **antes** de invocar al Estratega_Adset
    - `order = list(ad.templates.template_order)`, `templates = list(ad.templates.project_templates)`: `build_variant_slots(plan_id, ad.ad_slot, n_variants, order)`, `check_ad_templates(slot_ad_templates(len(ad.all_territories), order), templates)`, `check_variant_slots(plan, templates, n_variants)` y `plan["_project_templates"] = templates` (D14, D16)
    - Actualizar el docstring; el Legacy_Path y el camino `USE_TERRITORY_ENGINE` no cambian y con el flag desactivado no se escribe `adset_templates`
    - _Requirements: 2.2, 2.4, 2.7, 4.5, 4.6, 4.7, 4.10, 4.12, 4.13, 6.6, 6.12_

  - [x] 19.3 Exigir coherencia del checkpoint `strategy` con el Template_Order
    - Además de las condiciones de D10 y `_project_templates` no vacía, el checkpoint `strategy` se reutiliza solo si todos sus Variant_Slots tienen `template_id == ad_template_for_slot(ad.ad_slot, ad.templates.template_order)`; con `template_order` vacío (resolución fallida) no se llama a `ad_template_for_slot` y el checkpoint se considera incoherente
    - Si no coincide: warning `[{task_id}]` con `ad_id` y ambos `template_id`, se ignora y se recalcula el Creative_Plan (Estratega_Adset de nuevo)
    - _Requirements: 4.8, 4.12_

- [x] 20. Adaptar las pruebas existentes a P12
  - [x] 20.1 Añadir el helper de orden esperado a los fakes
    - En `tests/_diversity_pipeline_fakes.py`: `expected_template_order(task_id, templates=None) -> list[str]` = `template_order(templates or mock_template_ids(), task_id)` (import lazy), para que las pruebas usen la misma función que el código
    - _Requirements: 12.2, 12.19, 12.20_

  - [x] 20.2 Adaptar los tests unitarios del Creative_Plan
    - `tests/test_adset_diversity_creative_plan.py`: `_setup` deja de inyectar plantillas vía `FakeGetTemplateContext` en `_DiversityDeps` y construye `templates=jrs._JobTemplates(...)` para el `_DiversityAdInput` a partir de `templates`/`template_script` (resolución con `resolve_project_templates` + `template_order(..., TASK_ID)`, o `failure` con la causa para excepción, `ok=False` y lista vacía)
    - `test_builds_plan_with_rotated_templates_and_stores_checkpoint`: `templates == ids` y `_project_templates == ids` (orden de Sinergia), variantes con `order[1 % len(order)]`
    - `test_checkpoint_reused_without_agent_nor_templates` y `test_empty_concept_raises_agent_validation_error`: sustituir las comprobaciones de `get_tc.call_count` (ya no se llama desde el Creative_Plan) por la ausencia de llamadas a `get_template_context`
    - `test_template_failures_fail_the_ad`: el fallo llega por `_JobTemplates.failure`; mismo mensaje con `PROJECT_ID`, `101` y sin `X-Amz-Signature`
    - `test_repeated_ad_template_with_enough_templates_fails_the_ad`: `t0 = order[0]` (el parche de `slot_ad_templates` recibe el Template_Order)
    - `test_duplicate_template_ids_...`, `test_exhausted_templates_log_ad_template_warning` y `test_ad_template_warning_reaches_failure_report_when_the_ad_fails`: construir `_JobTemplates` con la lista deduplicada / `["T1"]`
    - _Requirements: 4.5, 4.6, 4.7, 4.8, 6.11, 6.12, 12.19, 12.20_

  - [x] 20.3 Añadir `templates` a las construcciones de `_DiversityAdInput` en las demás pruebas
    - Pasar `templates=jrs._JobTemplates(tuple(ids), tuple(ids))` (con los `template_id` de los slots del caso) en: `tests/test_adset_diversity_copy_prompts.py` (`_setup`), `tests/test_adset_diversity_validation_loop.py` (`_setup`), `tests/test_adset_diversity_finish.py` (helper del Ad), `tests/test_adset_diversity_properties.py` (harness de la Property 9) y `tests/test_adset_diversity_pipeline_properties.py` (harness de las Properties 13 y 16)
    - Sin cambiar ninguna aserción: estos pasos no leen `ad.templates`
    - _Requirements: 12.2_

  - [x] 20.4 Adaptar los tests del pipeline a Template_Order
    - `tests/test_adset_diversity_pipeline.py`: `_assert_template_rotation` calcula `order = expected_template_order(task_id)` y espera `order[ad_slot % len(order)]` en slots, copies, payloads de `save_ads` y elementos de Abyssale; `test_scenario_1_happy_path` y `test_six_variants` (ambos escenarios) pasan a usarlo
    - `test_ad_templates_distinct_when_enough_templates`: `ad_templates == order[:len(ad_ids)]` en lugar de `templates[:len(ad_ids)]`
    - `test_ad_templates_rotate_with_warning_when_templates_exhausted`: `[order[s % 3] for s in range(4)]`; slots 0 y 3 siguen compartiendo plantilla con warning
    - `test_scenario_2_id_ad_keeps_scenario_1_ad_template`: los dos `task_id` dan órdenes distintos, así que se reescribe para esperar `order_s2[slot]` (Template_Order del job del Scenario_2), distinto de `order_s2[i]` de los slots hermanos; se elimina la igualdad con `mock_template_ids()[slot]` y con el Ad_Template del Scenario_1
    - `test_scenario_2_extra_slot_gets_next_template_in_rotation`: `order[len(AD_IDS) % len(order)]`
    - `test_project_templates_failure_fails_ad`: mantener las aserciones y añadir que `get_template_context` se llama una vez, que el Estratega_Adset no se invoca y que no existe `adset_templates`
    - _Requirements: 4.5, 4.6, 4.7, 4.9, 4.13, 8.1, 12.3, 12.14, 12.19, 12.20_

  - [x] 20.5 Adaptar el test de propiedad de cardinalidades
    - **Property 17: Cardinalidades del Diversity_Path**
    - En `tests/test_adset_diversity_pipeline_properties.py`, sustituir `template_ids[ad_slot % len(template_ids)]` por `order[ad_slot % len(order)]` con `order = template_order(template_ids, task_id)` en slots, copies, payloads y Abyssale; añadir `env.get_template_context.call_count == 1`
    - **Validates: Requirements 4.5, 4.6, 4.9, 4.10, 8.1, 12.3, 12.19**

  - [x] 20.6 Adaptar el test de propiedad de reanudación
    - **Property 23: Reanudación por Checkpoints**
    - En `tests/test_adset_diversity_pipeline_properties.py`: incluir `adset_templates` en los checkpoints de la ejecución original y sembrarlo en el reintento siempre que se conserve algún `strategy` (D18: `strategy` solo existe si existe `adset_templates`) y, si no, de forma opcional; sustituir `get_template_context.call_count == len(no_strategy)` por `0` si `adset_templates` está sembrado y `1` en otro caso; esperar `order[ad_slot % len(order)]` con `order = template_order(mock_template_ids(), task_id)` en lugar de `templates[ad_slot % len]`
    - **Validates: Requirements 3.13, 4.8, 4.12, 5.6, 12.15, 12.20**

- [x] 21. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise. Ejecutar `PYTHONPATH=. env/bin/python -m pytest tests/` desde `fury/app`; `tests/test_phase1_legacy_golden.py` debe pasar sin cambios en su referencia.

- [x] 22. Pruebas nuevas de P12 en el Diversity_Path
  - [x] 22.1 Añadir tests unitarios de `_load_or_resolve_templates`
    - Nuevo `tests/test_adset_diversity_job_templates.py` (con `network_guard()` y `FakeRedis`): resolución y escritura de `adset_templates` con `{project_templates, template_order}`; checkpoint válido reutilizado sin llamar a `get_template_context` ni a `template_order` (parcheado para fallar); checkpoints inválidos (forma, repetidos, `template_order` que no es permutación) ignorados con warning y resueltos con una llamada; excepción / `ok=False` / lista vacía → `failure` con la causa, sin checkpoint, sin lanzar y sin `str(exc)` en logs; como máximo una llamada a `get_template_context`
    - _Requirements: 4.7, 4.10, 4.11, 4.12, 4.13_

  - [x] 22.2 Añadir tests unitarios del Creative_Plan con plantillas del job
    - `tests/test_adset_diversity_creative_plan.py`: con `_JobTemplates.failure` el Ad falla sin invocar al Estratega_Adset ni escribir `strategy` (D19); un checkpoint `strategy` cuyo Ad_Template no coincide con `ad_template_for_slot(ad_slot, template_order)` se ignora con warning y se recalcula; uno coherente se reutiliza
    - _Requirements: 4.7, 4.8, 4.13_

  - [x] 22.3 Añadir tests del pipeline para Req 12.20 (e)–(h)
    - `tests/test_adset_diversity_pipeline.py`: (e) dos ejecuciones con el mismo `task_id` dan el mismo Template_Order, permutación de `_MOCK_TEMPLATES`; (f) dos `task_id` concretos con órdenes distintos en los Ad_Templates asignados; (g) N ≥ 2 Ads → mismo Template_Order en todos y `get_template_context` llamado una vez; (h) reintento con `adset_templates` precargado (orden distinto del de la semilla) sin llamar a `get_template_context` y con ese orden en los Ads
    - `adset_templates` escrito antes de cualquier `strategy` (orden de escrituras en el `FakeRedis`); resolución fallida con N=2 → cada Ad con `ad_failed`, mensaje con `project_id` y `ad_id`, 0 llamadas al Estratega_Adset y al Copywriter y sin `adset_templates`; checkpoint `strategy` incoherente ignorado en el pipeline
    - Con el Diversity_Flag desactivado no se escribe `adset_templates` (sin modificar `tests/test_phase1_legacy_golden.py`)
    - _Requirements: 2.7, 4.10, 4.11, 4.12, 4.13, 12.20_

  - [x] 22.4 Endurecer el test de propiedad de cardinalidades
    - **Property 17: Cardinalidades del Diversity_Path**
    - En `tests/test_adset_diversity_pipeline_properties.py`, generar `task_id` y comprobar que el Checkpoint `adset_templates` contiene `{project_templates, template_order: order}` y se escribe antes que cualquier `strategy`
    - **Validates: Requirements 4.10, 4.12, 12.20**

  - [x] 22.5 Endurecer el test de propiedad de reanudación
    - **Property 23: Reanudación por Checkpoints**
    - En `tests/test_adset_diversity_pipeline_properties.py`, cuando `len ≥ 2` sembrar `adset_templates` con una permutación distinta de la que produce la semilla y comprobar que el reintento la usa, que `template_order` no se invoca y que se conservan los mismos Ad_Templates y Variant_Slots
    - **Validates: Requirements 4.8, 4.12, 12.15, 12.20**

  - [x] 22.6 Escribir test de propiedad del reparto de Ad_Templates en el pipeline
    - **Property 24: Reparto de Ad_Templates entre Ad_Slots**
    - En `tests/test_adset_diversity_pipeline_properties.py`, *for any* `task_id`: en el Scenario_2 el Ad `id_ad` del Ad_Slot `s` recibe `order[s % len(order)]`, distinto de los de los Ad_Slots hermanos cuando el número de Ad_Slots es ≤ `len(templates)`, y el Ad_Slot extra recibe `order[len(Adset_Ads) % len(order)]`
    - **Validates: Requirements 4.6, 6.12, 12.20**

- [x] 23. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise. Ejecutar `PYTHONPATH=. env/bin/python -m pytest tests/` desde `fury/app`; verificar que `tests/test_phase1_legacy_golden.py` sigue pasando sin cambios en su referencia y que en el Diversity_Path (`_run_adset_diversity_path` y las corrutinas que llama) solo `_load_or_resolve_templates` llama a `get_template_context` (p. ej. `grep -n "get_template_context(" services/job_runner_service.py`: las únicas llamadas restantes son esa y la del camino `USE_TERRITORY_ENGINE` del Legacy_Path).

### Decisión P13/P14: Validador_Adset semántico y Variant_Angle por variante

Delta de "Estado de la implementación frente a P13/P14 (delta pendiente)" (design.md, D20, D21, D22, componente 11). `make_validador_agent`, el prompt `fury.validador`, `check_diversity_and_fidelity`, `check_variant_slots`, `build_variant_proposals`, `check_variant_items`, `repair_variant_items`, `normalize_variant_fields`, `make_variant_validator`, `build_image_prompt_message`, el Legacy_Path y `tests/test_phase1_legacy_golden.py` no cambian (Req 13.5, 14.7). Todas las pruebas se ejecutan desde `fury/app` con `PYTHONPATH=. env/bin/python -m pytest tests/`. Convención de pruebas (P14): los Variant_Slots esperados nunca se escriben a mano con `angle`; se construyen con el helper `expected_slots(plan_id, n, template)` de los fakes, que delega en `assign_variant_angles`.

- [x] 24. Variant_Angle en `services/adset_diversity.py`
  - [x] 24.1 Añadir el vocabulario y las funciones puras de ángulos
    - `VariantAngle` (TypedDict con exactamente `hook`, `headline_structure`, `copy_length`), `ANGLE_KEYS` y `ANGLE_VOCABULARY` (tupla de 6 entradas en el orden fijo de la tabla de D22: `question/buyer_first/short`, `bold_claim/outcome_first/medium`, `mini_story/detail_first/long`, `sensory_scene/product_first/short`, `practical_tip/contrast/medium`, `direct_address/moment_first/long`)
    - `angle_offset(plan_id) = int(sha256(plan_id.encode("utf-8")).hexdigest(), 16) % len(ANGLE_VOCABULARY)`; nunca `hash()`
    - `assign_variant_angles(plan_id, n_variants)`: `[dict(ANGLE_VOCABULARY[(o + k - 1) % len]) for k in 1..n]`, copias nuevas, sin `random` (ni global ni local), sin depender de `task_id` ni de Template_Order; `ValueError` si `n_variants < 1`
    - `is_valid_variant_angle(value)`: `True` solo si es un dict igual (`==`) a un elemento de `ANGLE_VOCABULARY`
    - `ensure_variant_angles(plan) -> tuple[CreativePlan, bool]`: si todos los slots tienen `angle` válido devuelve `(plan, False)` sin copiar; si no, copia del plan con el `angle` de todos los slots recalculado con `assign_variant_angles(plan["id"], len(variants))` y `True`; no toca `variant_key`, `template_id` ni otras claves y no muta la entrada
    - Docstrings con referencia a P14/D22
    - _Requirements: 14.2, 14.3, 14.4, 14.5, 14.9_

  - [x] 24.2 Añadir `angle` a `VariantSlot` y a `build_variant_slots`
    - `VariantSlot` gana `angle: VariantAngle`; `build_variant_slots(plan_id, ad_slot, n_variants, project_templates)` añade `angle = assign_variant_angles(plan_id, n_variants)[k - 1]` en cada slot, sin cambiar de firma ni el `template_id` (D15) ni los `ValueError` existentes
    - `build_creative_plan` conserva la clave `angle` al copiar los slots (comprobar que `VariantSlot(**slot)` no la pierde)
    - _Requirements: 4.5, 14.1, 14.4_

  - [x] 24.3 Incluir los Variant_Angles solo en el mensaje al Copywriter
    - `_slots_payload(slots, *, with_angle=False)`: `{variant_key, template_id}` por slot y, con `with_angle=True`, también `angle`
    - `build_copy_message` usa `with_angle=True` (solo los slots recibidos, así que en regeneración solo viajan los ángulos de los slots regenerados) y añade el bloque `VARIANT ANGLES` de la sección 3 del diseño antes de `_identity_contract`, con las franjas de `copy_length`, la regla de la primera opción de `headline`/`primary_text`, la precedencia del plan, los Forbidden_Territories y "Do NOT copy `angle` into your output"
    - `build_image_prompt_message` no cambia: sigue llamando a `_slots_payload` sin ángulo y su texto queda byte a byte igual
    - _Requirements: 5.1, 14.6, 14.7_

  - [x] 24.4 Adaptar las pruebas existentes de helpers puros a slots con `angle`
    - `tests/test_adset_diversity.py` y `tests/test_adset_diversity_properties.py`: las aserciones que comparan Variant_Slots o `plan["variants"]` por igualdad exacta con `{variant_key, template_id}` pasan a incluir `angle` (vía `assign_variant_angles` o el helper `expected_slots` de la tarea 30.1, si ya existe); las que comparan solo `variant_key`/`template_id` no cambian
    - Revisar `tests/test_diversity_checker.py` y `tests/test_diversity_checker_properties.py`: `check_variant_slots` no cambia, así que solo se ajustan aserciones de igualdad de slots construidos con `build_variant_slots`
    - _Requirements: 4.5, 14.1, 12.25_

  - [x] 24.5 Escribir test de propiedad de la asignación de Variant_Angles
    - **Property 26: Asignación determinista de Variant_Angles**
    - En `tests/test_adset_diversity_angles.py`: `plan_id` arbitrarios (incluidos `plan_ad_{n}`, vacío y Unicode) y `n_variants` hasta más de `2 * len(ANGLE_VOCABULARY)`; oráculo con `hashlib`; distintos dos a dos si `n ≤ len`, `k` y `k + len` iguales si `n > len`; misma salida con distintos `task_id`/Template_Order en el proceso; `random.getstate()` intacto; mutar el resultado no altera `ANGLE_VOCABULARY`; `ensure_variant_angles` con subconjuntos de slots sin `angle` o con valores ajenos (`None`, cadena, dict con claves de menos/de más, valor distinto) → `recomputed == True` y ángulos de `assign_variant_angles`; con ángulos válidos (aunque repetidos) → mismo plan y `False`
    - **Validates: Requirements 14.2, 14.3, 14.5, 14.9, 12.25, 12.28**

  - [x] 24.6 Escribir test de propiedad de los ángulos en el mensaje al Copywriter
    - **Property 28: Variant_Angles en el mensaje al Copywriter**
    - En `tests/test_adset_diversity_angles.py`: *for any* subconjunto no vacío de slots, `Variant_Slots:` contiene exactamente un `{variant_key, template_id, angle}` por slot del subconjunto, en orden, y ningún slot excluido; bloque VARIANT ANGLES con la precedencia del plan; `build_image_prompt_message` sin la clave JSON `"angle"` e igual al texto con slots sin `angle`
    - **Validates: Requirements 5.1, 14.6, 12.26**

  - [x] 24.7 Ampliar el test de propiedad de plantillas por Ad con ángulos
    - **Property 7: Una plantilla por Ad y resolución de Project_Templates**
    - En `tests/test_adset_diversity_properties.py`, añadir que el slot `k` tiene `angle == assign_variant_angles(plan_id, n_variants)[k - 1]` y que el ángulo no depende de `ad_slot` ni de `order`
    - **Validates: Requirements 4.5, 4.9, 14.1**

  - [x] 24.8 Ampliar el test de propiedad del Creative_Plan con ángulos
    - **Property 8: El Creative_Plan conserva el territorio**
    - En `tests/test_adset_diversity_properties.py`, comprobar que el plan construido con slots con `angle`, tras quitar `angle` de cada elemento de `variants`, es igual al construido con los mismos slots sin `angle`
    - **Validates: Requirements 4.1, 4.3, 14.4**

  - [x] 24.9 Ampliar el test de propiedad de forma por Variant_Slot con ángulos
    - **Property 9: Validación de forma por Variant_Slot**
    - En `tests/test_adset_diversity_properties.py`, generar los slots con `build_variant_slots` (con `angle`) y respuestas sin `angle` o con un `angle` arbitrario; el veredicto no cambia y los slots no se modifican
    - **Validates: Requirements 5.2, 5.3, 5.8, 14.7**

- [x] 25. Regla 6.13 en `services/diversity_checker.py`
  - [x] 25.1 Implementar `check_variant_angles`
    - `check_variant_angles(plan, n_variants) -> DiversityCheckResult`, función aparte de `check_variant_slots` (que no cambia); importa `ANGLE_VOCABULARY` de `services.adset_diversity`
    - En orden de slots: sin `angle` o `None` → error `ANGLE_MISSING` con `variant_keys=(key,)`; valor que no es un elemento del vocabulario → error `ANGLE_NOT_IN_VOCABULARY` con el valor recibido; después, por cada par `i < j` con ángulos válidos e iguales → `ANGLE_REPEATED` con `(key_i, key_j)`, error si `n_variants <= len(ANGLE_VOCABULARY)` y warning si lo supera
    - Todos los issues nombran el `id` del plan; no lee copies ni image prompts (14.8); no muta la entrada; salida determinista
    - _Requirements: 6.1, 6.10, 6.13, 14.8_

  - [x] 25.2 Escribir test de propiedad de la regla 6.13
    - **Property 27: Oráculo de la regla 6.13 del Diversity_Checker**
    - En `tests/test_adset_diversity_angles.py`: planes con `n` de 1 a `2 * len + 1` slots, ángulos del vocabulario con repeticiones deliberadas y slots sin `angle` o con valores ajenos, `n_variants` igual a `n` o arbitrario; exactamente los issues del oráculo, sin otros, con el `id` del plan, sin mutar y deterministas; con slots de `build_variant_slots`, sin errores y warnings solo si `n_variants > len`
    - **Validates: Requirements 6.1, 6.10, 6.13, 12.25**

  - [x] 25.3 Ampliar el test de propiedad de reglas por Ad con ángulos en copies
    - **Property 12: Reglas por Ad del Diversity_Checker**
    - En `tests/test_diversity_checker_properties.py`, añadir una clave `angle` arbitraria a copies e image prompts y comprobar que los issues de `check_variants` no cambian
    - **Validates: Requirements 6.1, 14.8**

  - [x] 25.4 Escribir tests unitarios de Variant_Angle
    - `tests/test_adset_diversity_angles.py`: `ANGLE_VOCABULARY` con ≥ 5 entradas, sin repetidos, claves exactas, valores no vacíos tras `strip()`, `hook`/`headline_structure` únicos y ciclo `short → medium → long` de `copy_length`; `angle_offset` con un valor fijo registrado (independiente de `PYTHONHASHSEED`); ángulos de `build_variant_slots` con `n_variants` = 2, 6 y 13; misma salida con dos `task_id` distintos; `ensure_variant_angles` con checkpoint sin `angle`; `check_variant_angles` con ángulo ausente, ajeno, repetido con `n ≤ 6` (error) y con `n = 7` (warning); mensaje al Copywriter inicial y en regeneración (solo los ángulos regenerados); mensaje al Image_Prompter sin `angle`
    - _Requirements: 6.13, 14.1, 14.2, 14.5, 14.6, 14.9, 12.25, 12.26_

- [x] 26. Validador_View y mensaje reducido en `services/adset_diversity.py`
  - [x] 26.1 Implementar `build_validador_view`, `build_validador_views` y el nuevo `build_validador_message`
    - Constantes `VALIDADOR_VIEW_COPY_FIELDS` y `VALIDADOR_VIEW_PROMPT_FIELDS` y TypedDict `ValidadorView`
    - `build_validador_view(slot, proposal)`: `variant_key` y `angle` del slot; `copy` restringido a `headline`, `primary_text`, `description`, `cta`, `template_elements` (solo los presentes); `image_prompts` con solo `element_id` e `image_prompt` de cada elemento dict; copy/image_prompts ausentes o de otro tipo → `{}`/`[]`; sin mutar la entrada
    - `build_validador_views(plan, proposals)`: una vista por Variant_Slot en orden de slots, emparejando por `variant_key`
    - `build_validador_message(plan, proposals, forbidden, adset_context_json, deterministic_warnings)`: en el orden de la sección 3 del diseño (cabecera con `id` y número de variantes, aclaración de similitud intencionada y Variant_Angle, verificaciones (a)–(c), fallo solo por violación concreta y ángulo no seguido no es fallo, formato de salida, `variant_keys`, Forbidden_Territories, `Deterministic diversity warnings (this iteration, informative only)` o `- none`, `Plan:` con `_plan_payload(plan)` una vez, `Variants:` con las vistas en JSON, FULL ADSET CONTEXT); sin `Proposals:`, `image_request`, `product_image_urls`, `base_image_url` ni `plan`/`ad_id`/`plan_id`/`template_id` por propuesta
    - `build_variant_proposals` no cambia (Req 7.14)
    - _Requirements: 2.5, 7.3, 7.14, 13.3_

  - [x] 26.2 Adaptar las pruebas existentes del mensaje al Validador
    - `tests/test_adset_diversity_properties.py`: retirar el test actual de la Property 14 (6.13 del plan anterior), que pasa a reescribirse en `tests/test_adset_diversity_validador_message.py` (26.3)
    - `tests/test_adset_diversity.py`: las aserciones que buscan `Deterministic diversity errors`, `Proposals:` o el plan completo con `variants` en el mensaje al Validador pasan al formato de D21 (warnings, `Plan:` una vez, `Variants:`)
    - _Requirements: 7.3, 12.21_

  - [x] 26.3 Escribir test de propiedad del mensaje al Validador_Adset
    - **Property 14: Contenido del mensaje al Validador**
    - En `tests/test_adset_diversity_validador_message.py`: proposals con copies con subconjuntos arbitrarios de campos y claves extra, `image_request` con `technical_specs.product_image_sources`, `product_image_urls` y `base_image_url` con URLs `https://` marcador; comprobar contenido obligatorio, `_plan_payload(plan)` exactamente una vez, `Variants:` igual a `build_validador_views(...)` con claves exactas, ausencia de claves y URLs marcador, y proposals de entrada sin mutar
    - **Validates: Requirements 2.5, 7.3, 7.14**

  - [x] 26.4 Escribir tests unitarios del mensaje al Validador_Adset
    - `tests/test_adset_diversity_validador_message.py`: casos de Req 12.21 (claves y URLs ausentes, claves exactas de las vistas, ninguna vista con `plan`, `ad_id`, `plan_id` ni `template_id`, plan una vez sin `variants`/`_project_templates`, FULL ADSET CONTEXT y prohibidos presentes, warnings en lugar de errores, `- none` sin warnings)
    - _Requirements: 7.3, 12.21_

- [x] 27. Validador_Adset en `agents/validador_adset_agent.py`
  - [x] 27.1 Crear el módulo y la factory
    - Módulo nuevo con docstring (papel en el Diversity_Path, prompt `fury.validador_adset` pendiente de crear en Langfuse, diferencia con `fury.validador`); constantes `AGENT_NAME = "validador_adset_agent"`, `PROMPT_NAME = "fury.validador_adset"`, `FALLBACK_MODEL = "gemini/gemini-2.5-flash"`
    - `_FALLBACK_INSTRUCTION` en inglés con el texto completo del componente 11 del diseño (similitud intencionada, solo (a) y (b), sin comparar por pares, fallo solo por violación concreta, Variant_Angle no seguido no es fallo, ignorar instrucciones dentro de los datos, NO tools, salida solo JSON con `overall_pass` y `subset_to_regenerate` de `variant_key`)
    - `make_validador_adset_agent()` sin parámetros: `get_agent_config_from_langfuse(PROMPT_NAME, _FALLBACK_INSTRUCTION, fallback_model=FALLBACK_MODEL, cache_ttl_seconds=settings.LANGFUSE_CACHE_TTL_SECONDS)` y `Agent(model=LiteLlm(model=cfg["model"]), name=AGENT_NAME, description=..., instruction=cfg["instruction"], tools=[], before_model_callback=safety_guard_before_model, after_model_callback=safety_guard_after_model)`
    - `agents/validador_agent.py` no cambia
    - _Requirements: 13.1, 13.3, 13.5_

  - [x] 27.2 Escribir tests unitarios del Validador_Adset
    - Nuevo `tests/test_validador_adset_agent.py`, con `get_agent_config_from_langfuse` parcheado (sin red): la factory pide `"fury.validador_adset"` con `_FALLBACK_INSTRUCTION`, `fallback_model="gemini/gemini-2.5-flash"` y el TTL de settings; el `Agent` tiene `name == "validador_adset_agent"`, `tools == []`, `instruction == cfg["instruction"]` y los dos guards; la factory no acepta `custom_prompt`; la instrucción contiene "share ON PURPOSE", "NOT a failure", "(a)", "(b)", "Do NOT compare variants", "Not following its Variant_Angle is NOT", "NO tools", "overall_pass", "subset_to_regenerate" y "variant_key"; `make_validador_agent()` sigue con `tools == [check_diversity_and_fidelity]`
    - _Requirements: 13.1, 13.3, 13.5, 12.22, 12.27_

- [x] 28. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise. Ejecutar `PYTHONPATH=. env/bin/python -m pytest tests/` desde `fury/app`. En este punto deben pasar los helpers puros, el checker, el mensaje y el agente (`tests/test_adset_diversity.py`, `tests/test_adset_diversity_properties.py`, `tests/test_diversity_checker*.py`, `tests/test_adset_diversity_angles.py`, `tests/test_adset_diversity_validador_message.py`, `tests/test_validador_adset_agent.py`) y `tests/test_phase1_legacy_golden.py` sin cambios en su referencia; las pruebas del pipeline que comparan slots con `angle` o guionizan el Validador se adaptan en la tarea 30 y se verifican en el checkpoint 31.

- [x] 29. Orquestación P13/P14 en `services/job_runner_service.py`
  - [x] 29.1 Crear el Validador legacy solo en el Legacy_Path e inyectar el Validador_Adset
    - En `_run_phase1`, mover `validador_agent = make_validador_agent()` del bloque de factories a justo después del bloque `if USE_ADSET_CREATIVE_DIVERSITY: ... return ...`, antes de la extracción legacy de `ads`; el `import` de `make_validador_agent` puede quedarse donde está
    - Dentro del bloque del Diversity_Path, `from agents.validador_adset_agent import make_validador_adset_agent` (lazy) y pasarlo a `_DiversityDeps`
    - `_DiversityDeps`: sustituir el campo `make_validador_agent` por `make_validador_adset_agent: Callable[[], Any]` (sin dejar ambos)
    - El Legacy_Path mantiene la misma secuencia de agentes: `tests/test_phase1_legacy_golden.py` debe pasar sin cambios
    - _Requirements: 2.2, 2.4, 8.6, 13.2, 13.5_

  - [x] 29.2 Aplicar Variant_Angles en `_build_or_load_creative_plan`
    - Checkpoint `strategy` válido (D10) y coherente con Template_Order (D18) → `plan, recomputed = ensure_variant_angles(cached)`; si `recomputed`, warning `[{task_id}] strategy checkpoint for ad={ad_id} without valid Variant_Angles; recomputed` y `_store(strategy, plan)`, sin Estratega_Adset, `get_template_context` ni Template_Order; sin repetir las comprobaciones de 6.11
    - Cálculo nuevo: los slots ya traen `angle` de `build_variant_slots`; añadir `check_variant_angles(plan, n_variants)` (errores y warnings completos) a las comprobaciones previas al Copywriter, fusionado con el resto; errores → `_AdDiversityFailure` con la lista completa; warnings → log y Diversity_Report
    - Imports lazy dentro de la corrutina
    - _Requirements: 4.8, 6.10, 6.11, 6.13, 14.1, 14.5_

  - [x] 29.3 Reescribir `_diversity_validation_loop` con checker primero y Validador_Adset
    - Por iteración (`_DIVERSITY_MAX_RETRIES = 3`): `check_variants` primero; con errores no se invoca al Validador_Adset: si no es la última se regeneran solo `check.failing_variant_keys() & slot_keys` con `_regenerate_variants`, y si es la última se sale y se aplica 7.6 (`_AdDiversityFailure`) como hoy
    - Sin errores: crear el agente con `deps.make_validador_adset_agent()` la primera vez que hace falta (una vez por Ad), mensaje `build_validador_message(plan, build_variant_proposals(...), forbidden, adset_context_json, check.warning_messages())`, `_run_agent(..., validator=validate_validador_response)`; `AgentValidationError` intermedio → siguiente iteración, último → relanzar
    - Usar solo `overall_pass` y `subset_to_regenerate` del veredicto; filtrar el subset a los `variant_key` del Ad con warning `[{task_id}]`, `ad_id` y los valores descartados (D8); `overall_pass=True` → aprobar; subset vacío o última iteración → warning y `overall_pass=False`; si no, regenerar solo el subset (se elimina la unión `det_keys ∪ subset`)
    - `validation_report` = último veredicto o `{}` si nunca se invocó; `Diversity_Report.iterations` y `subset_to_regenerate` según el diseño
    - `_regenerate_variants`, `_generate_variant_copies` y `_generate_variant_prompts` no cambian de firma
    - _Requirements: 7.1, 7.2, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.13, 13.2, 13.4_

- [x] 30. Adaptar las pruebas existentes a P13/P14
  - [x] 30.1 Actualizar los fakes compartidos
    - `tests/_diversity_pipeline_fakes.py`: constante `VALIDADOR_ADSET = "validador_adset_agent"` y `FACTORY_TARGETS[VALIDADOR_ADSET] = ("agents.validador_adset_agent", "make_validador_adset_agent")`; helper `expected_slots(plan_id, n, template) -> list[dict]` que delega en `assign_variant_angles` (import lazy)
    - _Requirements: 12.2, 12.22, 12.25_

  - [x] 30.2 Pasar las siete construcciones de `_DiversityDeps` a `make_validador_adset_agent=`
    - `tests/test_adset_diversity_copy_prompts.py`, `tests/test_adset_diversity_creative_plan.py`, `tests/test_adset_diversity_finish.py`, `tests/test_adset_diversity_job_templates.py`, `tests/test_adset_diversity_properties.py`, `tests/test_adset_diversity_validation_loop.py` y `tests/test_adset_diversity_pipeline_properties.py`: sustituir `make_validador_agent=` por `make_validador_adset_agent=`
    - _Requirements: 13.2_

  - [x] 30.3 Guionizar el Validador_Adset y el flujo con checker primero
    - Las pruebas del Diversity_Path que guionizan `VALIDADOR` (`tests/test_adset_diversity_validation_loop.py`, `tests/test_adset_diversity_pipeline.py` y las demás que lo usen) pasan a `VALIDADOR_ADSET`, y comprueban `factories.count(VALIDADOR) == 0`; `tests/test_phase1_legacy_golden.py` sigue con `VALIDADOR` sin cambios
    - Reescribir los guiones en los que el checker tiene errores: esas iteraciones ya no consumen una respuesta del Validador y regeneran solo las claves del checker (sin unión con el subset); ajustar los recuentos de llamadas y de iteraciones esperados
    - Las aserciones sobre el mensaje al Validador en estas pruebas pasan al formato de D21
    - _Requirements: 7.2, 7.4, 7.6, 13.2_

  - [x] 30.4 Incluir `angle` en las aserciones de Variant_Slots del pipeline
    - `tests/test_adset_diversity_creative_plan.py`, `tests/test_adset_diversity_copy_prompts.py`, `tests/test_adset_diversity_pipeline.py` y `tests/test_adset_diversity_pipeline_properties.py` (Properties 17 y 23): las comparaciones exactas de slots con `{variant_key, template_id}` usan `expected_slots(...)`
    - Los checkpoints `strategy` precargados sin `angle` se completan con los ángulos o se convierten en casos de Req 14.5 (reutilización con recálculo sin Estratega_Adset ni `get_template_context`)
    - _Requirements: 4.8, 14.1, 14.5, 12.28_

  - [x] 30.5 Adaptar el test de propiedad existente del bucle de validación
    - **Property 13: Bucle de validación acotado y regeneración selectiva**
    - En `tests/test_adset_diversity_pipeline_properties.py`, cambiar el oráculo: el Validador_Adset (`count(VALIDADOR_ADSET)`) se invoca solo en las iteraciones sin errores del checker; cada ronda regenera las claves del checker o el subset filtrado, nunca su unión; con errores del checker en la última iteración el Ad falla aunque el Validador_Adset no se haya invocado
    - **Validates: Requirements 7.1, 7.2, 7.4, 7.6, 7.7, 13.2**

- [x] 31. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise. Ejecutar `PYTHONPATH=. env/bin/python -m pytest tests/` desde `fury/app`; `tests/test_phase1_legacy_golden.py` debe pasar sin cambios en su referencia.

- [x] 32. Pruebas nuevas de P13/P14 en el Diversity_Path
  - [x] 32.1 Añadir tests unitarios del pipeline para P13/P14
    - `tests/test_adset_diversity_pipeline.py`: `make_validador_adset_agent` invocado y agente con `tools == []`; `make_validador_agent` 0 veces y `check_diversity_and_fidelity` sustituido (en `agents.tools.validation_tools` y `agents.validador_agent`) por un fake que hace fallar la prueba si se llama; con el flag a `False` el Legacy_Path sigue creando `make_validador_agent()` (12.22); `proposals` del resultado con `image_request` completo (7.14); checkpoint `strategy` con ángulos reutilizado y sin ángulos completado sin Estratega_Adset ni `get_template_context` (12.28); ángulo inválido inyectado parcheando `assign_variant_angles` → Ad fallido sin Copywriter (6.11, 6.13); mensaje al Copywriter con `variant_key` + `angle` por slot (12.26)
    - _Requirements: 6.11, 6.13, 7.14, 8.6, 12.22, 12.26, 12.28, 13.2, 14.5_

  - [x] 32.2 Añadir tests unitarios del bucle con Validador_Adset
    - `tests/test_adset_diversity_validation_loop.py`: errores deterministas solo en la iteración 1 → 0 llamadas al Validador_Adset en la 1, regeneración solo de las claves con error, llamada en la 2; errores en las 3 iteraciones → 0 llamadas y Ad fallido (7.6); total ≤ 3; `make_validador_adset_agent` creado de forma perezosa una vez; subset con ids de plan y claves válidas → solo las válidas y warning; subset solo con ids de plan → sin regeneración y `overall_pass=False` (7.7); veredicto con claves extra ignoradas (13.4)
    - _Requirements: 7.2, 7.5, 7.6, 7.7, 7.13, 13.4, 12.23, 12.24_

  - [x] 32.3 Endurecer el test de propiedad del bucle de validación
    - **Property 13: Bucle de validación acotado y regeneración selectiva**
    - En `tests/test_adset_diversity_pipeline_properties.py`, generar también claves extra en el veredicto y comprobar que `make_validador_adset_agent` se llama como máximo una vez por Ad (0 si ninguna iteración llegó al Validador_Adset), que `make_validador_agent` no se usa y que los `angle` de los Variant_Slots no cambian tras las regeneraciones
    - **Validates: Requirements 7.5, 8.6, 13.2, 13.4**

  - [x] 32.4 Endurecer el test de propiedad de cardinalidades
    - **Property 17: Cardinalidades del Diversity_Path**
    - En `tests/test_adset_diversity_pipeline_properties.py`, comprobar que cada Creative_Plan tiene `assign_variant_angles(plan_ad_{ad_id}, n_variants)`, que el Validador_Adset se invoca exactamente una vez por Ad con fakes conformes y que `make_validador_agent` se llama 0 veces
    - **Validates: Requirements 7.2, 8.6, 14.1**

  - [x] 32.5 Endurecer el test de propiedad de reanudación
    - **Property 23: Reanudación por Checkpoints**
    - En `tests/test_adset_diversity_pipeline_properties.py`, sembrar checkpoints `strategy` con algunos slots sin `angle` o con un `angle` ajeno y comprobar que el reintento no invoca al Estratega_Adset ni a `get_template_context` y produce los ángulos de `assign_variant_angles(plan_id, n_variants)`; con ángulos válidos se conservan los guardados
    - **Validates: Requirements 4.8, 14.5, 12.28**

- [x] 33. Publicación del prompt `fury.validador_adset`
  - [x] 33.1 Permitir crear `fury.validador_adset` desde `scripts/langfuse_update_prompt_contract.py`
    - Opcional: hoy el script solo añade secciones a prompts existentes y sale si el prompt no existe. Añadir un modo `--seed` limitado a `fury.validador_adset` que, si el prompt no existe, publica `_FALLBACK_INSTRUCTION` de `agents.validador_adset_agent` como primera versión (tipo `text`, `config={"model": FALLBACK_MODEL}`), en dry run por defecto y con `--apply`; si ya existe, no hace nada. Sin cambios para los prompts actuales
    - Alternativa sin código: crear el prompt a mano en Langfuse con la instrucción de fallback como semilla (design.md, "Verificación fuera de las pruebas unitarias")
    - _Requirements: 13.1_

- [x] 34. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise. Ejecutar `PYTHONPATH=. env/bin/python -m pytest tests/` desde `fury/app`; verificar que `tests/test_phase1_legacy_golden.py` sigue pasando sin cambios en su referencia y que en el Diversity_Path (`_run_adset_diversity_path`, `_DiversityDeps` y las corrutinas que llama) no queda ninguna referencia a `make_validador_agent` ni a `check_diversity_and_fidelity` (p. ej. `grep -n "make_validador_agent\|check_diversity_and_fidelity" services/job_runner_service.py`: solo el import y la creación del Legacy_Path tras el bloque del Diversity_Path).

### Decisión P15: elementos de imagen resueltos en código

Delta de "Estado de la implementación frente a la Decisión P15 (delta pendiente)" (design.md, D23–D27, componentes 12–15). `normalize_variant_fields`, `repair_variant_items`, `check_variant_items`, el validador compuesto con `kind="copy"`, el payload de `save_ads` (`media_images_banner` sigue con todos los elementos `image`), el prompt `fury.image_prompter` de Langfuse y la referencia de `tests/test_phase1_legacy_golden.py` no cambian (Req 15.7, 15.14, 15.15). P15 no añade Checkpoints. Todas las pruebas se ejecutan desde `fury/app` con `PYTHONPATH=. env/bin/python -m pytest tests/`. Convención de pruebas (P15): los Image_Elements esperados nunca se escriben a mano en las pruebas de pipeline; se calculan con `expected_image_elements(template)` de los fakes (delega en `template_image_elements` con `DEFAULT_DECORATIVE_IMAGE_PATTERNS`), y los Image_Prompters falsos responden con los Image_Elements leídos de su mensaje.

- [x] 35. Image_Elements puros en `services/adset_diversity.py` y configuración
  - [x] 35.1 Declarar `ADSET_DECORATIVE_IMAGE_PATTERNS`
    - En `core/config.py`, junto a `USE_ADSET_CREATIVE_DIVERSITY`: `ADSET_DECORATIVE_IMAGE_PATTERNS: list[str] = ["degradado", "gradient", "overlay", "mask", "shape"]` con el comentario del componente 15 (formato JSON en el entorno, como `CORS_ORIGINS`)
    - En `fury/app/env.example`, la línea `ADSET_DECORATIVE_IMAGE_PATTERNS=["degradado","gradient","overlay","mask","shape"]` con el comentario en español del componente 15
    - _Requirements: 15.12_

  - [x] 35.2 Crear la fixture `TEMPLATE_1BB5C1AD`
    - Nuevo `tests/_template_fixtures.py` (no es módulo de test; misma convención que `_*_fakes.py`, funciona con `python -m tests.<módulo>`): Template_Definition real de `1bb5c1ad` con `root` container, `image_0` image, `degradado_bottom` image, `degradado_top` image, `hook` text, `tagline` text y `logo_0` logo, con `layout["instagram-portrait"]` y `formats`, sin URLs firmadas
    - _Requirements: 12.29_

  - [x] 35.3 Implementar la extracción de Image_Elements
    - `DEFAULT_DECORATIVE_IMAGE_PATTERNS` (tupla con el mismo valor que el setting), `IMAGE_ELEMENT_FORMAT = "instagram-portrait"`, `IMAGE_ELEMENT_TYPE = "image"`, `ImageElementSpec` (TypedDict `total=False`) e `ImageElements` (dataclass frozen con `template_id`, `element_ids`, `specs`, `preview_url`)
    - `element_id_of(element)` = `str(name or id)` si es truthy, `""` en otro caso o si no es dict (mismo criterio que `_build_save_ads_payloads`, D23); `is_template_definition(template)` (dict con `elements` lista)
    - `template_image_elements(template, patterns)`: reglas (a)–(e) de Req 15.2 (`type == "image"` exacto, Element_Id no vacío, patrones `strip().casefold()` no vacíos y no `str` ignorados, `casefold` sobre el Element_Id, primera aparición); `[]` si no cumple `is_template_definition`; lista nueva sin mutar argumentos; sin red ni `settings`
    - `image_element_specs(template, element_ids)` (`width`/`height` de `layout[IMAGE_ELEMENT_FORMAT]` solo si ambos son `int` > 0 y no `bool`), `template_preview_url(template)` (nivel superior o `formats[id == "instagram-portrait"]`, siempre `partition("?")[0]`, `None` si no hay) y `build_image_elements(template_id, template, patterns)`
    - Docstrings con referencia a P15/D23/D25
    - _Requirements: 15.2, 15.4, 15.13_

  - [x] 35.4 Escribir test de propiedad de la extracción de Image_Elements
    - **Property 29: Extracción de Image_Elements según oráculo**
    - En `tests/test_adset_diversity_image_elements.py`: `elements` con dicts y no-dicts, `type` ∈ {`"image"`, `"Image"`, `"IMAGE"`, `"text"`, `"logo"`, `"button"`, `"container"`, `"shape"`, `None`, ausente}, `name`/`id` ausentes, `None`, `""`, cadenas o enteros, repetidos, y patrones vacíos/de espacios/con mayúsculas; oráculo independiente, sin repetidos, subconjunto de los `image`, idempotente y sin mutar `template` ni `patterns` (copia profunda previa)
    - **Validates: Requirements 15.2, 12.29, 12.35**

  - [x] 35.5 Implementar `check_image_elements` y `filter_image_prompts`
    - `check_image_elements(items, image_elements) -> list[str]`: un error por variante dict con `image_prompts` ausente o no lista, elemento no dict, Image_Element ausente, `element_id` ajeno o repetido, o `element_type` ausente o ≠ `"image"`; comparación por igualdad exacta (sin `strip` ni `casefold`); con Image_Elements vacíos solo `[]` es válido; `items` que no es lista → `[]`; sin mutar la entrada
    - Formato del error (D25): `Image prompt {variant_key!r}: element_ids {recibidos} do not match Image_Elements {esperados}` y los motivos; recibidos con `repr` truncado a 64 caracteres (no `str` como `<tipo>`) y como máximo 20
    - `filter_image_prompts(items, element_ids) -> tuple[list[dict], list[tuple[str, str]]]`: copias de cada variante dict con `image_prompts` restringido a elementos dict con `element_id` ∈ `element_ids`, y la lista `(variant_key, element_id)` de los descartados en orden; variantes sin elementos con `image_prompts: []`; sin mutar la entrada
    - _Requirements: 15.5, 15.10, 15.13_

  - [x] 35.6 Escribir test de propiedad del Image_Elements_Checker
    - **Property 30: Oráculo del Image_Elements_Checker**
    - En `tests/test_adset_diversity_image_elements.py`: Image_Elements sin repetidos (incluida la lista vacía) y respuestas generadas perturbando una conforme (quitar, añadir, repetir o renombrar un `element_id`, mayúsculas, espacios, `element_type` cambiado o ausente, `image_prompts` no lista, elementos no dict) o arbitrarias; `[]` si y solo si el multiconjunto de cada variante es igual al conjunto y todos tienen `element_type == "image"`; si no, un error por variante incumplidora con su `variant_key`, los esperados y los recibidos; entrada sin mutar
    - **Validates: Requirements 15.5, 12.31, 12.35**

  - [x] 35.7 Añadir `image_elements` a `make_variant_validator`
    - Parámetro solo palabra clave `image_elements: Sequence[str] | None = None`; con `kind="image_prompt"` y valor no nulo, tras `repair_variant_items` concatena `check_variant_items(...)` + `check_image_elements(data, image_elements)` (si `data` es lista) y, con algún error, devuelve `ERR_VARIANT_SHAPE` con todos
    - Nunca inventa, renombra ni elimina `element_id`; con `kind="copy"` e `image_elements` no nulo → `ValueError` al construir el validador; con `None` el comportamiento es el actual
    - _Requirements: 15.6, 15.7_

  - [x] 35.8 Escribir test de propiedad del validador compuesto con Image_Elements
    - **Property 31: Validador compuesto con Image_Elements**
    - En `tests/test_adset_diversity_image_elements.py`, vía `run_agent` como en la Property 9: respuestas de la Property 30 más fallos de `plan_id`/`variant_key`/`template_id`; acepta si y solo si acepta el validador sin Image_Elements y `check_image_elements` da `[]` sobre los datos reparados; rechazos con `ERR_VARIANT_SHAPE` y los errores de ambos grupos; `element_id` de `result.data` iguales a los de la respuesta; con `image_elements=None` o `kind="copy"` sin Image_Elements, resultado idéntico al actual
    - **Validates: Requirements 15.6, 15.7, 12.31**

  - [x] 35.9 Añadir la línea `Image_Elements:` a `build_image_prompt_message`
    - Parámetro solo palabra clave `image_elements: ImageElements | None = None`; con valor, inserta tras `_identity_contract` y antes de `Plan:` el bloque IMAGE ELEMENTS del componente 12 y una única línea `Image_Elements: {...}` con `_dumps` (`template_id`, `elements` con `element_id` y `width`/`height` si existen, `preview_url` sin query string o ausente)
    - Con Image_Elements vacíos, las tres primeras viñetas se sustituyen por `- Image_Elements is empty: set "image_prompts": [] in EVERY object.` y la línea lleva `"elements": []`
    - Con `image_elements=None` el texto es byte a byte el actual (sigue valiendo la Property 28)
    - _Requirements: 15.4, 15.13_

  - [x] 35.10 Escribir test de propiedad del mensaje al Image_Prompter
    - **Property 32: Línea Image_Elements en el mensaje al Image_Prompter**
    - En `tests/test_adset_diversity_image_elements.py`: `ImageElements` de 0 a 6 elementos, con y sin dimensiones, `preview_url` ausente, en el nivel superior o solo en `formats`, con query strings `X-Amz-Signature`/`X-Amz-Credential`/`Expires`, y subconjuntos de slots y copies; una sola línea `Image_Elements: ` con el JSON esperado, reglas presentes (o la de `[]` con lista vacía), ninguna query string de firma en el texto añadido e igualdad con el mensaje actual cuando `image_elements=None`
    - **Validates: Requirements 15.4, 15.13, 12.30**

  - [x] 35.11 Escribir tests unitarios de Image_Elements
    - `tests/test_adset_diversity_image_elements.py` (con `if __name__ == "__main__"`): `TEMPLATE_1BB5C1AD` → `["image_0"]`; `id` cuando falta `name`; sin `name` ni `id` omitido; repetidos una vez; `Gradient_Top`/`OVERLAY_1` excluidos; patrones `[]` no excluyen nada; patrones vacíos o de espacios ignorados; `"Image"` excluido; sin elementos `image` → `[]`; `image_element_specs` con y sin `layout`; `template_preview_url` en el nivel superior, en `formats` y con query string
    - Mensaje (12.30): línea única con `template_id` e ids en orden, reglas, `[]` con lista vacía, sin URLs firmadas, `image_elements=None` igual al actual
    - Checker y validador (12.31): caso del Ad 102 del job `69d025e1` (`hook`/`tagline` con `["image_0"]`) → `ERR_VARIANT_SHAPE` con `variant_key`, `image_0`, `hook` y `tagline`; ausente, extra, repetido y `element_type` distinto rechazados; conjunto exacto en otro orden aceptado; `image_prompts: []` aceptado con lista vacía; `kind="copy"` con `image_elements` → `ValueError`; `ERR_VARIANT_SHAPE` en `_RETRYABLE_AGENT_CODES`
    - Default de `ADSET_DECORATIVE_IMAGE_PATTERNS` y su línea en `env.example` (15.12); `OUTPUT_CONTRACT_SECTION` contiene la regla nueva solo en "VARIANT MODE" (15.14)
    - _Requirements: 15.2, 15.4, 15.5, 15.6, 15.7, 15.12, 15.14, 12.29, 12.30, 12.31_

- [x] 36. Defensa en Abyssale y contrato del Image_Prompter
  - [x] 36.1 Proteger las capas de texto en `build_abyssale_payload`
    - En `agents/tools/abyssale_tools.py`: reunir primero `text_layers` de `copy.template_elements` y, al recorrer las imágenes con `image_url`, si el `element_id` ya es capa de texto, no escribirla, no añadirla a `image_ids` y registrar `build_abyssale_payload: image skipped for text layer template_id=... element_id=...` (sin URL ni contenido)
    - El resultado no depende del orden de las listas; el último texto repetido sigue ganando; sin cambio de firma ni validación nueva de `template_elements`. Aplica a ambos caminos
    - _Requirements: 15.11, 15.13_

  - [x] 36.2 Ampliar `OUTPUT_CONTRACT_SECTION` del Image_Prompter
    - En `agents/image_prompter_agent.py`, añadir al final de "2. VARIANT MODE" la viñeta del componente 15 (línea `Image_Elements:` como fuente de verdad, una entrada por elemento, `element_id` literal, `element_type` `"image"`, `image_prompts: []` con lista vacía, nunca ids de `template_elements`), sin llaves dobles y sin tocar las reglas existentes
    - _Requirements: 15.14_

  - [x] 36.3 Escribir test de propiedad de las capas de texto en Abyssale
    - **Property 34: build_abyssale_payload nunca escribe una imagen sobre una capa de texto**
    - En `tests/test_adset_diversity_image_elements_pipeline.py`: entradas cuyos `copy.template_elements` e `image.image_prompts` comparten ids, en cualquier orden, con y sin `image_url`; ninguna capa con `image_encoded` tiene un id de texto de la misma entrada, esas capas son `{"payload": <texto>}`, sin el id en `image_ids` y con warning por colisión; las imágenes sin colisión se escriben como hoy
    - **Validates: Requirements 15.11, 12.34, 12.35**

- [x] 37. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise. Ejecutar `PYTHONPATH=. env/bin/python -m pytest tests/` desde `fury/app`. Las funciones nuevas tienen parámetros opcionales con `None` = comportamiento actual, así que ninguna prueba existente debe romperse; `tests/test_phase1_legacy_golden.py` debe pasar sin cambios en su referencia. Ignorar los fallos previos no relacionados de `tests/test_ad_variant_image_edit_task.py`, `tests/test_variant_create_validation*.py` y `tests/test_video_script_service.py`.

- [x] 38. Resolución y propagación de Image_Elements en `services/job_runner_service.py`
  - [x] 38.1 Implementar la caché `_JobTemplateDefinitions`
    - Dataclass frozen `_TemplateDefinitionFailure(template_id, cause)` y adaptador `_as_template_definition_response(raw)`: dict con `ok` → `raw`; dict sin `ok` que cumple `is_template_definition` → `{"ok": True, "template": raw}`; otro valor (incluido `{}`) → `{"ok": False}`
    - `_JobTemplateDefinitions(fetch, patterns)`: un `asyncio.Future` por `template_id` (`asyncio.ensure_future(self._resolve(tid))` en el primer Ad, los demás esperan el mismo, también con `ADS_MAX_CONCURRENT_ADS > 1`); `_resolve` nunca lanza `Exception` y guarda éxito o fallo
    - Clasificación (Req 15.3): excepción → `get_a_template_definition raised <Clase>`; no dict, sin `ok` u `ok is not True` → `get_a_template_definition returned ok == False`; `template` ausente/`None`/no dict o `elements` ausente/no lista → `empty template definition`; `elements == []` o Image_Elements vacíos son válidos; nunca se lee `error` ni `str(exc)`
    - `image_elements(template_id) -> ImageElements | _TemplateDefinitionFailure` (vía `build_image_elements`), `tool_response(template_id)` → `{"ok": True, "template": deepcopy(template)}` o `{"ok": False}` sin `error`, y propiedad `calls` por `template_id`
    - Imports de `adset_diversity` lazy (D2)
    - _Requirements: 15.1, 15.3, 15.13_

  - [x] 38.2 Conectar la caché en `_run_phase1` y en `save_ads`
    - `_DiversityDeps` gana el campo obligatorio `template_definitions: _JobTemplateDefinitions`, sin valor por defecto (una construcción no actualizada falla con `TypeError`)
    - Bloque del Diversity_Path de `_run_phase1`: `patterns = list(getattr(settings, "ADSET_DECORATIVE_IMAGE_PATTERNS", DEFAULT_DECORATIVE_IMAGE_PATTERNS))`; con `USE_MOCK_SINERGIA` envolver `get_a_template_definition` con `_as_template_definition_response`; crear `_JobTemplateDefinitions` una vez y pasar `template_definitions=` y `save_ads_programmatically=functools.partial(_save_ads_programmatically, resolve_template=template_definitions.tool_response)`
    - `_build_save_ads_payloads(copies, *, resolve_template=None)` y `_save_ads_programmatically(..., *, resolve_template=None)`: solo cambia la línea de la llamada a `(resolve_template or get_a_template_definition)(template_id)`; el resto (incluido el recorte de Req 5.5) igual
    - El Legacy_Path no pasa `resolve_template` y no crea la caché: `tests/test_phase1_legacy_golden.py` debe pasar sin cambios
    - _Requirements: 15.1, 15.15_

  - [x] 38.3 Implementar `_resolve_ad_image_elements` y llamarlo en `_run_diversity_ad`
    - `_resolve_ad_image_elements(deps, ad, job, plan) -> ImageElements`: `template_id = plan["variants"][0]["template_id"]`; fallo → log `[{task_id}]` con `template_id`, `ad_id` y causa, y `_AdDiversityFailure(f"template definition unavailable for template_id={template_id} ad_id={ad_id} ({cause})")`; éxito → log con `template_id`, `element_ids` y número de elementos
    - En `_run_diversity_ad`, justo después de `_build_or_load_creative_plan` y antes de `_load_or_generate_copies_and_prompts` (sin Copywriter, Image_Prompter, imágenes, `save_ads` ni Checkpoint `image_prompts` para un Ad fallido); un Ad con Checkpoint `ad_result` válido se devuelve antes y no consulta la caché
    - _Requirements: 15.1, 15.3, 15.13_

  - [x] 38.4 Propagar `image_elements` a la generación, el Checkpoint y las regeneraciones
    - `image_elements: ImageElements | None = None` (solo palabra clave) en `_load_variant_checkpoint`, `_generate_variant_prompts`, `_load_or_generate_copies_and_prompts`, `_diversity_validation_loop` y `_regenerate_variants`; `_run_diversity_ad` siempre pasa el valor resuelto
    - `_generate_variant_prompts`: `build_image_prompt_message(..., image_elements=elements)` y `make_variant_validator(..., kind="image_prompt", image_elements=elements.element_ids)` (inicial con `attempts=_DIVERSITY_AGENT_ATTEMPTS`, regeneraciones con `attempts=1`)
    - `_load_variant_checkpoint` con `kind="image_prompt"`: tras `check_variant_items` aplica `check_image_elements`; con errores, warning `[{task_id}] image_prompts checkpoint for ad={ad_id} fails the Image_Elements check ({n} error(s)); regenerating` y `None` (D26); el Checkpoint `copy` no cambia
    - `_diversity_validation_loop` solo lo reenvía a `_regenerate_variants`, que lo pasa a `_generate_variant_prompts`: un incumplimiento termina en el `AgentValidationError` de Req 7.10 con los prompts previos conservados
    - _Requirements: 15.4, 15.6, 15.8, 15.9_

  - [x] 38.5 Filtrar los prompts antes del Image_Generator en `_finish_diversity_ad`
    - `image_elements: ImageElements | None = None` (solo palabra clave); con valor, `filter_image_prompts(final_prompts, image_elements.element_ids)`, un warning `[{task_id}] image prompt dropped ad={ad_id} variant_key=... element_id=...` por descarte, exclusión de las variantes sin elementos y, si no queda ninguna, `generate_images` no se invoca (`generated_images = []`)
    - `proposals` y Checkpoints siguen usando `final_prompts`; `_run_diversity_ad` pasa el valor resuelto
    - _Requirements: 15.10, 15.13_

- [x] 39. Adaptar las pruebas existentes a P15
  - [x] 39.1 Añadir los helpers de Image_Elements a los fakes
    - En `tests/_diversity_pipeline_fakes.py`: `image_elements_from_message(message)` (lee y parsea la línea `Image_Elements:`; `None` si no existe), `conformant_image_prompts(slots, element_ids)` (una respuesta conforme con `element_type: "image"`) y `expected_image_elements(template)` (import lazy de `template_image_elements` y `DEFAULT_DECORATIVE_IMAGE_PATTERNS`)
    - _Requirements: 12.2, 12.29_

  - [x] 39.2 Añadir `template_definitions=` a las siete construcciones de `_DiversityDeps`
    - `tests/test_adset_diversity_copy_prompts.py`, `tests/test_adset_diversity_creative_plan.py`, `tests/test_adset_diversity_finish.py`, `tests/test_adset_diversity_job_templates.py`, `tests/test_adset_diversity_properties.py`, `tests/test_adset_diversity_validation_loop.py` y `tests/test_adset_diversity_pipeline_properties.py`: `template_definitions=jrs._JobTemplateDefinitions(FakeGetATemplateDefinition(...), DEFAULT_DECORATIVE_IMAGE_PATTERNS)`
    - Sin cambiar ninguna aserción: estas pruebas llaman a los helpers sin `image_elements` (`None` = comportamiento actual)
    - _Requirements: 12.2, 15.1_

  - [x] 39.3 Hacer que los Image_Prompters falsos del pipeline respondan con los Image_Elements del mensaje
    - `tests/test_adset_diversity_pipeline.py` y `tests/test_adset_diversity_pipeline_properties.py`: `_conforming_prompts` deja de responder `element_id: "img"` y usa `conformant_image_prompts(slots, image_elements_from_message(call.message)["elements"])` con `element_type: "image"` (las Properties 17, 18, 23 y 24 y `prompts_with_request` pasan a usarlo sin más cambios; en la Property 23 los Checkpoints `image_prompts` sembrados vienen de la ejecución original, así que se reutilizan)
    - `test_template_without_image_elements_does_not_fail_the_ad`: las plantillas de `_MOCK_TEMPLATES` tienen un Image_Element cada una, así que `image_prompts: []` ya no es válido; reescribir con un `FakeGetATemplateDefinition` cuya plantilla del Ad no tiene elementos `image` (o solo decorativos), comprobando que la línea del mensaje lleva `"elements": []`, que el Ad no falla, que `generate_images` no se invoca y que `save_ads` y Abyssale siguen ejecutándose
    - Los harness de las Properties 13 y 16 llaman a los helpers sin `image_elements` y siguen con `element_id: "img"`
    - _Requirements: 12.2, 12.3, 15.3, 15.4, 15.5_

- [x] 40. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise. Ejecutar `PYTHONPATH=. env/bin/python -m pytest tests/` desde `fury/app`; `tests/test_phase1_legacy_golden.py` debe pasar sin cambios en su referencia. Ignorar los fallos previos no relacionados de `tests/test_ad_variant_image_edit_task.py`, `tests/test_variant_create_validation*.py` y `tests/test_video_script_service.py`.

- [x] 41. Pruebas nuevas de P15 en el Diversity_Path
  - [x] 41.1 Añadir tests unitarios de la resolución de la Template_Definition
    - Nuevo `tests/test_adset_diversity_image_elements_pipeline.py` (con `network_guard()`, `LogCapture` e `if __name__ == "__main__"`), casos de 12.33: excepción con URL firmada en el mensaje, `ok == False` con `error` marcador, valor no dict, dict sin `ok`, `template` ausente/`None` y sin `elements` → Ad fallido con `template_id` y `ad_id`, sin el texto de la excepción ni el `error`, 0 llamadas al Image_Prompter y al generador, sin Checkpoint `image_prompts`, y el otro Ad continúa; N = 2 Ads con la misma plantilla (Template_Order de una plantilla) → una sola llamada a `get_a_template_definition` contando `save_ads`
    - Adaptador del mock (`_as_template_definition_response`): plantilla sin `ok` envuelta, `{}` → fallo; `tool_response` sin `error`
    - _Requirements: 15.1, 15.3, 15.13, 12.33_

  - [x] 41.2 Añadir tests unitarios del Checkpoint `image_prompts` y la regeneración
    - `tests/test_adset_diversity_image_elements_pipeline.py`, casos de 12.32: Checkpoint con `hook` descartado con warning `[{task_id}]`, `ad_id` y número de errores, e Image_Prompter invocado; Checkpoint conforme reutilizado sin invocarlo; regeneración con `element_id` inválidos → `AgentValidationError` de Req 7.10 y prompts previos conservados; `ERR_VARIANT_SHAPE` en el primer intento y respuesta correcta en el segundo → el pipeline avanza
    - _Requirements: 15.6, 15.8, 15.9, 12.31, 12.32_

  - [x] 41.3 Añadir tests unitarios de la defensa en profundidad
    - `tests/test_adset_diversity_image_elements_pipeline.py`, casos de 12.34: `_finish_diversity_ad` con un prompt ajeno → omitido con warning y no llega a `generate_images`; variante sin elementos tras filtrar → excluida; ninguna → `generate_images` no se invoca; `build_abyssale_payload` con `hook` texto + `hook` imagen con `image_url` → `layers["hook"] == {"payload": ...}`, sin `hook` en `image_ids` y warning, también con el Diversity_Flag a `False`
    - _Requirements: 15.10, 15.11, 12.34_

  - [x] 41.4 Escribir test de propiedad del filtrado previo al Image_Generator
    - **Property 33: Solo Image_Elements llegan al Image_Generator**
    - En `tests/test_adset_diversity_image_elements_pipeline.py`, con `_finish_diversity_ad` y un `generate_images` falso: variantes con `element_id` dentro y fuera de Image_Elements, repetidos y no-dicts; todo elemento recibido es un Image_Element, ninguna variante llega vacía, sin entrada no hay llamada, un warning por descarte y entrada sin mutar
    - **Validates: Requirements 15.10, 12.34**

  - [x] 41.5 Escribir test de propiedad de la caché por `template_id` y el fallo por Ad
    - **Property 35: Una resolución por template_id y fallo aislado por Ad**
    - En `tests/test_adset_diversity_image_elements_pipeline.py`, vía `_run_phase1` con `patched_diversity_pipeline`: N ∈ [1, 4] y, por `template_id`, definición válida (con y sin Image_Elements, `elements == []`), excepción con URL firmada y clave, no dict, dict sin `ok`, `ok == False` con `error` marcador, `template` ausente/`None`/sin `elements`; una llamada por `template_id` distinto (incluido `save_ads`), Ads fallidos con `ad_failed`, `template_id` y `ad_id` y sin secretos, 0 llamadas al Image_Prompter y al generador y sin Checkpoint `image_prompts` para ellos, Ads válidos con exactamente sus Image_Elements, y ningún log con la firma, la clave ni el marcador
    - **Validates: Requirements 15.1, 15.3, 15.13, 12.33**

  - [x] 41.6 Escribir test de propiedad del Checkpoint `image_prompts` y la regeneración
    - **Property 36: Reutilización del Checkpoint image_prompts y regeneración con Image_Elements**
    - En `tests/test_adset_diversity_image_elements_pipeline.py`: Checkpoints `image_prompts` precargados conformes a los Variant_Slots con `element_id` generados como en la Property 30; sin Image_Prompter fuera de las regeneraciones si y solo si `check_image_elements` da `[]`, y si no, warning con `[{task_id}]`, `ad_id` y número de errores y Checkpoint final conforme; regeneraciones con respuesta incumplidora conservan los prompts previos y el bucle sigue según Req 7.10
    - **Validates: Requirements 15.8, 15.9, 12.32**

  - [x] 41.7 Ampliar la prueba golden del Legacy_Path para P15
    - En `tests/test_phase1_legacy_golden.py`, sin cambiar la referencia: sustituir `services.adset_diversity.check_image_elements`, `template_image_elements` y `filter_image_prompts` por fakes que hacen fallar la prueba si se llaman, y comprobar que `get_a_template_definition` se invoca una vez por copy (solo desde `_build_save_ads_payloads`), como hoy
    - _Requirements: 15.15, 12.13, 12.36_

- [x] 42. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise. Ejecutar `PYTHONPATH=. env/bin/python -m pytest tests/` desde `fury/app` e ignorar los fallos previos no relacionados de `tests/test_ad_variant_image_edit_task.py`, `tests/test_variant_create_validation*.py` y `tests/test_video_script_service.py`. Verificar que `tests/test_phase1_legacy_golden.py` sigue pasando sin cambios en su referencia y que en el Diversity_Path solo `_JobTemplateDefinitions` llama a `get_a_template_definition` (p. ej. `grep -n "get_a_template_definition" services/job_runner_service.py`: el `fetch` del bloque del Diversity_Path y la llamada por defecto de `_build_save_ads_payloads` del Legacy_Path).

## Notes

- Las sub-tareas marcadas con `*` son opcionales (pruebas) y pueden omitirse para un MVP más rápido; la prueba golden 1.2 no es opcional porque fija el Legacy_Path antes de tocar el pipeline.
- Cada tarea referencia requisitos concretos para la trazabilidad; las decisiones D1–D14 del diseño (D3, D4, D5, D6 y el riesgo de reintentos de `AdsetCreativeDiversityError` confirmados por el usuario) se aplican tal cual.
- Cada propiedad se implementa con un único test `@given(...)` de hypothesis (`hypothesis==6.168.5`, ya en `requirements-dev.txt`).
- Ninguna prueba hace llamadas de red, a LLM ni esperas reales (`network_guard()`).
- Las tareas 1–12 son historial completado; las tareas 13–17 aplican solo el delta de la Decisión P11 (D15, D16). D17 ya está implementado y no tiene tareas.
- En las tareas 13–16, las sub-tareas que adaptan pruebas existentes que dejarían de pasar con el nuevo comportamiento (13.4, 13.6, 13.8, 14.4, 14.6, 14.9) son obligatorias y se completan antes del checkpoint 15; solo las pruebas nuevas o los endurecimientos de pruebas que siguen pasando son opcionales.
- Las tareas 18–23 aplican solo el delta de la Decisión P12 (D12, D14, D15, D16, D18, D19). Las sub-tareas que adaptan pruebas existentes que dejarían de pasar (20.1–20.6) son obligatorias y se completan antes del checkpoint 21. `templates` se declara sin valor por defecto, como en el diseño, para que ningún `_DiversityAdInput` del Diversity_Path se cree sin las plantillas del job; si se le diera un valor por defecto (p. ej. `_JobTemplates((), ())`), la tarea 20.3 dejaría de ser necesaria y solo romperían los tests del Creative_Plan (20.2).
- Las tareas 24–34 aplican solo el delta de P13/P14 (D20, D21, D22). Las sub-tareas que adaptan pruebas existentes que dejarían de pasar (24.4, 26.2, 30.1–30.5) son obligatorias; 24.4 y 26.2 se completan antes del checkpoint 28 y 30.x antes del checkpoint 31. Solo son opcionales las pruebas nuevas, los endurecimientos y la tarea 33.1.
- El campo `make_validador_agent` de `_DiversityDeps` se sustituye (no se añade otro al lado): una construcción no actualizada falla con `TypeError` en lugar de usar el Validador legacy sin avisar.
- El prompt `fury.validador_adset` debe existir en Langfuse antes de ajustar su modelo sin desplegar; mientras no exista, la factory usa `_FALLBACK_INSTRUCTION` y `gemini/gemini-2.5-flash`.
- Las tareas 35–42 aplican solo el delta de la Decisión P15 (D23–D27, componentes 12–15). Las sub-tareas que adaptan pruebas existentes que dejarían de pasar (39.1–39.3) son obligatorias y se completan antes del checkpoint 40: el campo `template_definitions` de `_DiversityDeps` no tiene valor por defecto (como `make_validador_adset_agent` en P13), así que las siete construcciones directas fallarían con `TypeError`, y los Image_Prompters falsos del pipeline que responden `element_id: "img"` (o `image_prompts: []` con las plantillas mock, que tienen un Image_Element cada una) serían rechazados por el Image_Elements_Checker. Son opcionales las pruebas nuevas (35.4, 35.6, 35.8, 35.10, 35.11, 36.3 y 41.x).
- La referencia de `tests/test_phase1_legacy_golden.py` no cambia con P15: el Legacy_Path no crea la caché ni pasa `resolve_template`, y la protección de capas de texto de `build_abyssale_payload` (Req 15.11, el único cambio que también afecta al Legacy_Path) solo altera la salida cuando hay colisión de ids, que la golden no tiene. La ampliación de 41.7 añade comprobaciones sin tocar la referencia.
- Efecto aceptado (D24): con `USE_MOCK_SINERGIA`, los payloads de `save_ads` del Diversity_Path pasan a llevar los elementos de la plantilla (antes `template = {}`), porque la caché adapta la forma del mock. Los Checkpoints `image_prompts` escritos antes de P15 con ids de texto se descartan solos (D26); los `ad_result` previos se siguen reutilizando.
- La verificación en dev/QAS de P15 (job equivalente al `69d025e1`, logs, Langfuse y Abyssale) y una posible ampliación de `ADSET_DECORATIVE_IMAGE_PATTERNS` por entorno no son tareas de código (design.md, "Verificación fuera de las pruebas unitarias").
- En todos los checkpoints se ignoran los fallos previos no relacionados de `tests/test_ad_variant_image_edit_task.py`, `tests/test_variant_create_validation*.py` y `tests/test_video_script_service.py`.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "4.1", "6.1", "7.1", "9.1", "9.2"] },
    { "id": 1, "tasks": ["1.2", "3.1", "4.2", "6.2", "6.6", "7.2", "9.3"] },
    { "id": 2, "tasks": ["3.2", "3.3", "4.3", "6.3", "6.9", "7.3", "9.4"] },
    { "id": 3, "tasks": ["3.4", "3.5", "6.4", "6.12", "7.4", "9.5"] },
    { "id": 4, "tasks": ["3.6", "6.5", "6.14", "7.5", "9.6", "11.1"] },
    { "id": 5, "tasks": ["6.7", "9.7", "11.2"] },
    { "id": 6, "tasks": ["6.8", "9.8", "11.3"] },
    { "id": 7, "tasks": ["6.10", "11.4"] },
    { "id": 8, "tasks": ["6.11", "11.5"] },
    { "id": 9, "tasks": ["6.13", "11.6"] },
    { "id": 10, "tasks": ["11.7"] },
    { "id": 11, "tasks": ["11.8"] },
    { "id": 12, "tasks": ["11.9"] },
    { "id": 13, "tasks": ["11.10", "11.11"] },
    { "id": 14, "tasks": ["13.1", "14.1"] },
    { "id": 15, "tasks": ["13.2", "14.2"] },
    { "id": 16, "tasks": ["13.3", "14.3"] },
    { "id": 17, "tasks": ["13.4", "13.6", "13.8", "14.4", "14.9", "16.1"] },
    { "id": 18, "tasks": ["13.5", "13.7", "14.6", "14.10", "16.2"] },
    { "id": 19, "tasks": ["14.5", "16.3"] },
    { "id": 20, "tasks": ["14.7", "16.4"] },
    { "id": 21, "tasks": ["14.8"] },
    { "id": 22, "tasks": ["18.1", "19.1"] },
    { "id": 23, "tasks": ["18.2", "18.3", "18.5", "19.2", "20.1"] },
    { "id": 24, "tasks": ["19.3", "20.3"] },
    { "id": 25, "tasks": ["18.4", "20.2", "20.4", "20.5"] },
    { "id": 26, "tasks": ["20.6", "22.1"] },
    { "id": 27, "tasks": ["22.2", "22.3", "22.4"] },
    { "id": 28, "tasks": ["22.5"] },
    { "id": 29, "tasks": ["22.6"] },
    { "id": 30, "tasks": ["24.1", "27.1"] },
    { "id": 31, "tasks": ["24.2", "25.1", "27.2", "33.1"] },
    { "id": 32, "tasks": ["24.3", "25.3", "29.1", "30.1"] },
    { "id": 33, "tasks": ["26.1", "24.5", "29.2"] },
    { "id": 34, "tasks": ["24.4", "25.2", "26.3", "29.3"] },
    { "id": 35, "tasks": ["26.2", "24.6", "26.4"] },
    { "id": 36, "tasks": ["24.7", "25.4"] },
    { "id": 37, "tasks": ["24.8"] },
    { "id": 38, "tasks": ["24.9"] },
    { "id": 39, "tasks": ["30.2"] },
    { "id": 40, "tasks": ["30.3"] },
    { "id": 41, "tasks": ["30.4"] },
    { "id": 42, "tasks": ["30.5"] },
    { "id": 43, "tasks": ["32.1", "32.2", "32.3"] },
    { "id": 44, "tasks": ["32.4"] },
    { "id": 45, "tasks": ["32.5"] },
    { "id": 46, "tasks": ["35.1", "35.2", "35.3", "36.1", "36.2"] },
    { "id": 47, "tasks": ["35.4", "35.5", "36.3"] },
    { "id": 48, "tasks": ["35.6", "35.7", "38.1"] },
    { "id": 49, "tasks": ["35.8", "35.9", "38.2", "39.1", "39.2"] },
    { "id": 50, "tasks": ["35.10", "38.3", "39.3"] },
    { "id": 51, "tasks": ["35.11", "38.4"] },
    { "id": 52, "tasks": ["38.5"] },
    { "id": 53, "tasks": ["41.1", "41.7"] },
    { "id": 54, "tasks": ["41.2"] },
    { "id": 55, "tasks": ["41.3"] },
    { "id": 56, "tasks": ["41.4"] },
    { "id": 57, "tasks": ["41.5"] },
    { "id": 58, "tasks": ["41.6"] }
  ]
}
```
