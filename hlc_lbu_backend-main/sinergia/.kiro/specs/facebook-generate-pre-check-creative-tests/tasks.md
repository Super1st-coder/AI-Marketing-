# Implementation Plan: Facebook Generate Pre-Check Creative Tests

## Overview

Implementar en Python una suite pytest de caracterización para `FacebookGeneratePreCheckCreativeUseCase` y el subconjunto heredado de `FacebookTestCreativeUploadUseCase` que esa clase invoca, exclusivamente en la capa de pruebas. El archivo objetivo es `tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py`, dentro del proyecto `sinergia`, conforme a `sinergia/.kiro/steering/structure.md`. La suite parcheará `AdChannelRepository`, `CampaignChannelPublishRepository`, `redis_client`, `MetaAdsPayloadBuilder`, `FacebookGetAdAccountDetailsUseCase` y `FacebookMinimumBudgetUseCase` sobre `app.v2.use_cases.meta_ads`, bloqueará cualquier fuga de red hacia `MetaAdsValidator.validate_images_precheck`/`validate_images`, y no modificará código productivo.

## Tasks

- [x] 1. Preparar builders y arnés local de la suite
  - [x] 1.1 Crear el módulo de pruebas y los builders de payload frescos
    - Crear `tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py`.
    - Implementar `make_campaign_data_dict`, `make_asset_feed_spec`, `make_object_story_spec`, `make_link_data`, `make_ad_creative`, `make_ad`, `make_ad_set`, `make_meta_payload`, `make_ad_account_info`, `make_minimum_budget_response`, usando un centinela privado `ABSENT` para distinguir campo omitido de campo presente con `None`.
    - Garantizar que cada invocación produce listas y diccionarios nuevos, sin defaults mutables compartidos.
    - _Requirements: 1.1, 1.8, 14.1, 14.2, 14.3_

  - [x] 1.2 Implementar la fixture `use_case_factory` y el helper `patch_execute_dependencies`
    - Implementar `use_case_factory` con `unittest.mock.patch` sobre `app.v2.use_cases.meta_ads.AdChannelRepository` y `app.v2.use_cases.meta_ads.CampaignChannelPublishRepository`, entregando `(use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance)` con una instancia nueva por invocación.
    - Implementar `patch_execute_dependencies` que parchee conjuntamente `redis_client`, `MetaAdsPayloadBuilder`, `FacebookGetAdAccountDetailsUseCase` y `FacebookMinimumBudgetUseCase` sobre `app.v2.use_cases.meta_ads`, exponiendo cada `MagicMock` para configurar `return_value`/`side_effect`.
    - Implementar un guard `autouse` local que sustituya `requests.sessions.Session.request` para fallar rápido ante cualquier fuga de red accidental.
    - Verificar con una prueba de humo que construir el caso de uso y capturar `NotAccessException`/`PermissionDeniedException`/etc. con `text` explícito no requiere contexto Flask ni `tests/conftest.py`; si la ejecución demuestra lo contrario, detener la implementación y plantear el cambio de requisitos/diseño antes de añadir infraestructura Flask.
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 14.3_

- [x] 2. Probar la construcción del caso de uso y el estado heredado
  - [x] 2.1 Probar atributos asignados y valores por defecto
    - Verificar `ad_account_id`, `page_id`, `objective`, `optimization_goal`, `lead_gen_form_id`, `whatsapp_number_id`, `creative_type`, `billing_event=None`, `channel_id=None`.
    - Verificar que `lead_gen_form_id`/`whatsapp_number_id` quedan en `None` cuando `Datos_de_Campaña` los omite.
    - Verificar que el Repositorio_de_Canal y el Repositorio_de_Publicación parcheados se instancian exactamente una vez cada uno.
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 2.2 Probar el `AttributeError` con `complete_campaign_data=None`
    - Construir `FacebookGeneratePreCheckCreativeUseCase` directamente (sin la fixture `use_case_factory`) con `complete_campaign_data=None` y comprobar que se propaga `AttributeError`.
    - _Requirements: 2.5_

- [x] 3. Probar `_get_decoded_access_token` y `_build_meta_payload`
  - [x] 3.1 Probar la obtención del token decodificado y su fallo
    - Verificar la llamada exacta `redis_client.get(f"facebook_access_token:{user_id}")` y el resultado decodificado con `utf-8` cuando hay token.
    - Verificar `NotAccessException` con el mensaje exacto cuando el token es falsy.
    - Verificar que, dentro de `execute()`, un token ausente impide invocar `MetaAdsPayloadBuilder`, `FacebookGetAdAccountDetailsUseCase` y `FacebookMinimumBudgetUseCase`.
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 3.2 Probar `_build_meta_payload`
    - Verificar la instanciación de `MetaAdsPayloadBuilder` con `(campaign_id, objective, optimization_goal, creative_type)` y las llamadas condicionales a `select_ad_account`/`select_page` según `ad_account_id`/`page_id` sean verdaderos o falsy.
    - Verificar la asignación de `billing_event`/`channel_id` desde el doble y la identidad del payload retornado.
    - Verificar que una excepción de `build_meta_payload()` se envuelve en `StrapiException` con el texto original incluido.
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 4. Probar `_get_account_details` y la matriz de códigos de error
  - [x] 4.1 Implementar el caso exitoso y la matriz parametrizada de errores
    - Verificar el caso `status_details=200` con identidad del diccionario retornado y la llamada exacta `execute(user_id, ad_account_id)`.
    - Parametrizar `error.code` en `190`, `200`, `100`, `613`, un código no mapeado y `error` ausente; comparar tipo de excepción y mensaje exacto para cada caso, incluido el fallback `"Unknown error"` cuando falta `error.message`.
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 5. Probar `_get_minimum_budget`
  - [x] 5.1 Implementar los escenarios de estado, coincidencia de moneda y ausencia de coincidencia
    - Verificar `PermissionDeniedException` cuando `status_budgets != 200`.
    - Verificar la conversión `min_daily_budget_imp / 100` para el primer elemento coincidente en orden de aparición, incluido el default `0` cuando el campo falta.
    - Verificar `DataNotFoundException` cuando ningún elemento coincide con la moneda de la cuenta.
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 6. Probar el manejo de ads sin creativo
  - [x] 6.1 Implementar la matriz de valores falsy de `adCreative`
    - Parametrizar `adCreative` ausente, `None` y `{}`; verificar, para una ejecución donde ese es el único ad, que la Respuesta_Final contiene `ok=0`, y la ausencia de invocación de `MetaAdsValidator` para ese ad.
    - Verificar que la iteración continúa con el siguiente ad sin interrumpir el ad set ni la campaña (por ejemplo, comprobando `ok=1` cuando el resto de la ejecución es válida).
    - Verificar, en un escenario separado donde el ad sin creativo es `ads[0]` de su `ad_set`, que `execute()` propaga `AttributeError` al construir `creatives`, caracterizando este comportamiento como actual.
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 7. Probar la rama DYNAMIC completa
  - [x] 7.1 Probar títulos, cuerpos y descripciones
    - Verificar las llamadas exactas a `is_unique_texts`/`is_valid_length` por colección y la asignación de `unique_titles`/`unique_bodies`/`unique_descriptions`.
    - Forzar `ValueError` en cada doble y verificar, para cada colección, que la asignación de éxito correspondiente está ausente del `asset_feed` propio de la prueba y que la Respuesta_Final contiene `ok=0` para una ejecución donde ese es el único ad.
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 7.2 Probar CTAs, imágenes y cantidad de assets
    - Verificar la llamada exacta a `validate_cta` por cada entrada de `call_to_action_types` con `throw=False` y la asignación de `cta['valid']`.
    - Verificar que ninguna entrada de `call_to_action_types` recibe la clave `valid` cuando `self.objective` no está en `META_ODAX_CTA_MAPPING`, que la Respuesta_Final contiene `ok=0` para una ejecución donde ese es el único ad, y que la iteración de CTAs continúa (verificable por la cantidad de llamadas a `validate_cta`).
    - Verificar la llamada exacta a `validate_images_precheck` con la lista completa de imágenes (parcheada para evitar red real) y que la Respuesta_Final contiene `ok=0` cuando lanza `ValueError`.
    - Verificar la llamada exacta a `is_valid_amount` y que la Respuesta_Final contiene `ok=0` cuando lanza `ValueError`.
    - _Requirements: 8.4, 8.5, 8.6, 8.7, 8.8, 8.9_

  - [x] 7.3 Probar presupuesto mínimo, URL y el slug duplicado interno `assets-budget-error`
    - Verificar `min_daily_budget`/`daily_budget_valid` cuando `ad_set.daily_budget` es comparable con `min_budget`.
    - Verificar que `min_daily_budget` queda asignado pero `daily_budget_valid` está ausente, y que la Respuesta_Final contiene `ok=0`, cuando `daily_budget` no es comparable (por ejemplo `None`).
    - Verificar la llamada exacta a `is_valid_link_url` con la unión por comas de `website_url` y la asignación de `link_url_valid`.
    - Verificar, con un comentario explícito sobre el comportamiento actual, que un elemento inválido en `link_urls` (sin `.get`) deja `link_url_valid` ausente (mientras `daily_budget_valid` permanece presente en ese escenario) y produce `ok=0`, dado que internamente reutiliza el mismo slug `assets-budget-error` que el fallo de presupuesto y por tanto no es distinguible por slug desde fuera de `execute()`.
    - Verificar que un ad DYNAMIC completamente válido produce `ok=1` y deja presentes simultáneamente todas las mutaciones de éxito (`unique_titles`, `unique_bodies`, `unique_descriptions`, `cta['valid']`, `daily_budget_valid`, `link_url_valid`).
    - _Requirements: 8.10, 8.11, 8.12, 8.13, 8.14_

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Ejecutar `./venv/bin/python -m pytest --collect-only -q tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` y `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` desde `sinergia/`, sin modo watch.

- [x] 9. Probar la rama STANDARD completa
  - [x] 9.1 Probar el caso sin `link_data` y la llamada a `validate_cta`
    - Verificar que `object_story_spec` con `link_data` falsy produce `ok=1` (sin ningún error de esta rama) y no invoca `validate_cta`, `validate_images` ni `validate_assets_amount`.
    - Verificar la llamada exacta a `validate_cta` con `(call_to_action.get('type'), self.objective)` sin `throw`, y que la Respuesta_Final contiene `ok=0` cuando lanza `ValueError`, comprobando que la evaluación continúa hacia la validación de `image_url`.
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 9.2 Probar `image_url`, su ausencia y `validate_assets_amount`
    - Verificar la llamada exacta a `validate_images` con `image_url` como argumento único (parcheada para evitar red real) y que la Respuesta_Final contiene `ok=0` cuando lanza `ValueError`, comprobando que `validate_assets_amount` sigue siendo invocado a continuación.
    - Verificar que `ok=0` cuando `image_url` está ausente, sin invocar `validate_images`, comprobando que `validate_assets_amount` sigue siendo invocado a continuación.
    - Verificar la llamada exacta a `validate_assets_amount` con `(None, self.creative_type, story_spec=story_spec)` y que la Respuesta_Final contiene `ok=0` cuando lanza `ValueError`.
    - Verificar que un ad STANDARD completamente válido con `link_data` produce `ok=1`.
    - _Requirements: 9.4, 9.5, 9.6, 9.7, 9.8, 9.9_

- [x] 10. Probar el bloque de creación (dry-run) y el tipo de creativo desconocido
  - [x] 10.1 Probar la mutación de `page_id`, el resultado exitoso y `execution-error`
    - Verificar la mutación de `object_story_spec['page_id']` cuando `self.page_id` y `object_story_spec` son verdaderos, y su ausencia cuando alguno es falsy.
    - Verificar que un ad sin errores de validación que completa el bloque de creación produce `ok=1` (el `Resultado_de_Ad` detallado, incluida la ausencia de `creative_id`/`meta_response`/`errors`, no es observable desde la Respuesta_Final).
    - Forzar una excepción en el bloque de creación (por ejemplo `object_story_spec` como cadena de texto) y verificar que la Respuesta_Final contiene `ok=0` (el `slug="execution-error"` es interno y no observable); cuidar que este ad tenga `adCreative` presente para no disparar el `AttributeError` de Requirement 7.3.
    - Verificar que un `creative_type` distinto de `DYNAMIC`/`STANDARD` (incluida cadena vacía) evita toda validación de las tareas 7 y 9 y avanza directo al bloque de creación (produciendo `ok=1` si no hay otros errores).
    - Verificar, en un escenario que combine un ad `Failed` y un ad `Created` dentro del mismo `ad_set` con el `Failed` como `ads[0]`, que `creatives` aun así contiene una entrada para ese `ad_set` (construida desde `ads[0]`), documentando esta construcción incondicional.
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 11. Probar la agregación de resultados y el código de estado final
  - [x] 11.1 Implementar la matriz `ok`/código HTTP
    - Verificar `ok=1` cuando todos los resultados son `"Created"` y `ok=0` cuando al menos uno es `"Failed"`, incluida una combinación mixta.
    - Verificar que el código de estado HTTP es siempre `200`, tanto con `ok=1` como con `ok=0`.
    - _Requirements: 11.1, 11.2, 11.3_

- [x] 12. Probar los efectos secundarios de persistencia y las dos inconsistencias de `TypeError`
  - [x] 12.1 Probar `save_or_update` y la inyección de `lead_gen_form_id`/`whatsapp_number_id`
    - Verificar la llamada exacta a `campaign_publish_repository.save_or_update` con `filter_data` y el diccionario de publicación completo, incluidas las claves condicionales `meta_lead_form_id`/`meta_whatsapp_id`.
    - _Requirements: 12.1, 12.2, 12.5_

  - [x] 12.2 Probar `ad_channel_repository.update` por ad set y la construcción de `creatives`
    - Verificar la llamada exacta a `update` por cada ad set, en orden, con el `ad_channel_id` extraído (o `0` por defecto) y `data={'channel_creative': ad_set}`.
    - Verificar los campos completos de cada entrada de `creatives` listados en el diseño, incluidos los defaults `False`/`0`/`[]`.
    - Verificar los campos completos de la sección `campaign` de la respuesta.
    - _Requirements: 12.3, 12.6, 12.7_

  - [x] 12.3 Probar `valid_ctas` y las dos inconsistencias de `TypeError`
    - Verificar que `valid_ctas` coincide por conjunto con `META_ODAX_CTA_MAPPING[objective]["recommended_ctas"]` cuando `objective` es válido.
    - Verificar que `execute()` propaga `TypeError` cuando `objective` no es una clave válida, después de que `save_or_update` y todas las llamadas a `update` ya se ejecutaron.
    - Verificar que `execute()` propaga `TypeError` cuando `meta_payload['campaign']` omite la clave `ad_sets` por completo, después de que `save_or_update` se invocó exactamente una vez.
    - _Requirements: 12.4, 12.8, 12.9_

- [x] 13. Probar escenarios combinados con múltiples ad sets y ads
  - [x] 13.1 Implementar los escenarios vacíos y mixtos
    - Verificar que `ad_sets` ausente o vacía produce `results=[]`, `has_errors=False` y `ok=1`.
    - Verificar que múltiples ad sets con ads válidos e inválidos producen `ok=0`, y que cada ad se procesa de forma independiente sin mezclar sus resultados, mediante aserciones de argumentos de llamada sobre los dobles de `MetaAdsValidator` (por ejemplo `side_effect` distinto por ad, verificando que cada llamada recibió los datos de su propio ad).
    - Verificar que `creatives` contiene una entrada por ad set con `idx` secuencial desde `0`, en el mismo orden de `meta_payload['campaign']['ad_sets']`.
    - _Requirements: 13.1, 13.2, 13.3_

- [x] 14. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Ejecutar `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` desde `sinergia/`, sin servidor, watcher ni modo interactivo.

- [x] 15. Validar colección, aislamiento y repetibilidad de la suite
  - [x] 15.1 Ejecutar la validación pytest completa y corregir únicamente el código de pruebas
    - Ejecutar `./venv/bin/python -m pytest --collect-only -q tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py`.
    - Ejecutar `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` y exigir cero `failed`, cero `skipped` y cero errores.
    - Repetir con `PYTHONHASHSEED=1` y `PYTHONHASHSEED=777` usando el mismo comando no interactivo para detectar estado compartido u orden accidental.
    - Confirmar que el guard de red no detecta ninguna fuga, que no se creó infraestructura Flask ni `tests/conftest.py`, y que `app/v2/use_cases/meta_ads.py` y el resto de producción permanecen sin cambios.
    - _Requirements: 1.1, 1.5, 1.8, 14.3, 14.7, 14.8_

- [x] 16. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Las tareas de pruebas no llevan `*` porque la suite pytest es el entregable principal de esta feature.
- No se debe modificar `app/v2/use_cases/meta_ads.py`, `app/v2/use_cases/facebook_validator_service.py`, `app/v2/repository/ad_channel.py`, `app/v2/repository/campaign_channel_publish.py`, ningún otro archivo de producción, `requirements.md`, `design.md` ni `requirements.txt`.
- Toda la suite reside en `tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py`, dentro del proyecto `sinergia`, conforme a `sinergia/.kiro/steering/structure.md`.
- No se debe crear `tests/conftest.py` ni una aplicación/contexto Flask salvo que la implementación demuestre una dependencia real; en ese caso, se debe detener y replantear con el usuario antes de añadir infraestructura.
- Los slugs `assets-budget-error` (duplicado entre presupuesto y URL) y los `TypeError` de `valid_ctas`/`ad_sets` se caracterizan como comportamiento actual, no se corrigen.
- Todos los comandos pytest son ejecuciones únicas y no interactivas; no se deben iniciar servidores, watchers ni aplicaciones.
- Cada tarea amplía el mismo módulo de pruebas de manera secuencial; el grafo evita escrituras concurrentes al archivo.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["2.1"] },
    { "id": 3, "tasks": ["2.2"] },
    { "id": 4, "tasks": ["3.1"] },
    { "id": 5, "tasks": ["3.2"] },
    { "id": 6, "tasks": ["4.1"] },
    { "id": 7, "tasks": ["5.1"] },
    { "id": 8, "tasks": ["6.1"] },
    { "id": 9, "tasks": ["7.1"] },
    { "id": 10, "tasks": ["7.2"] },
    { "id": 11, "tasks": ["7.3"] },
    { "id": 12, "tasks": ["8"] },
    { "id": 13, "tasks": ["9.1"] },
    { "id": 14, "tasks": ["9.2"] },
    { "id": 15, "tasks": ["10.1"] },
    { "id": 16, "tasks": ["11.1"] },
    { "id": 17, "tasks": ["12.1"] },
    { "id": 18, "tasks": ["12.2"] },
    { "id": 19, "tasks": ["12.3"] },
    { "id": 20, "tasks": ["13.1"] },
    { "id": 21, "tasks": ["14"] },
    { "id": 22, "tasks": ["15.1"] },
    { "id": 23, "tasks": ["16"] }
  ]
}
```
