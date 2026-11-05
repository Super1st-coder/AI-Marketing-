# Implementation Plan: Meta Ads Standard Launch Campaign

**Ubicación obligatoria (Requirement 1.1, 1.4):** este documento reside en `sinergia/.kiro/specs/meta-ads-standard-launch-campaign/tasks.md` y describe cambios exclusivamente dentro del árbol `sinergia/`. Toda ruta de archivo mencionada en las tareas siguientes se expresa con el segmento `sinergia/` explícito; ninguna ruta es relativa a la raíz del monorepo `docker-deploy`.

## Overview

Este plan implementa las tres brechas de paridad STANDARD/DYNAMIC del paso de lanzamiento real hacia la Graph API de Meta, todas dentro de la clase `FacebookLaunchCampaignUseCase` de `sinergia/app/v2/use_cases/meta_ads.py`, siguiendo el diseño aprobado en `design.md`. El orden de tareas sigue los tres Componentes del diseño, que son mutuamente independientes entre sí:

- **Componente 1 → tarea 1:** rama STANDARD del gate `_is_campaign_valid` (Requirement 2).
- **Componente 2 → tarea 2:** rama STANDARD de `_build_response` más el método privado nuevo `_build_standard_creative_published` con su tabla de mapeo fuente→campo de 31 claves (Requirement 3).
- **Componente 3 → tarea 4:** endurecimiento del bloque `except` de `execute()` más el método privado nuevo, puro y estático `_is_meta_auth_error` (Requirement 5).

El Requirement 4 **no requiere ningún cambio de código productivo**: documenta que `_publish_media`, `_build_object_story_spec`, `_build_asset_feed_spec` y `_publish_ad_creative` se preservan verbatim, incluida la posible `KeyError` de `_publish_media`. Por eso la tarea 5 de este plan es de **verificación exclusivamente**, sin ninguna modificación de esos métodos.

Conforme al Requirement 1.2 y al "Principio de aislamiento" de `design.md`, la implementación toca únicamente dos archivos, y dentro del archivo productivo únicamente el cuerpo de `FacebookLaunchCampaignUseCase` (tres métodos ya existentes más dos métodos privados nuevos y aditivos). Ni `sinergia/app/v2/resources/external.py` ni `sinergia/app/v2/async_tasks/celery_tasks.py` se modifican (Requirement 1.5 y sección Out of Scope de `requirements.md`).

Las tareas de prueba 8-12 son de implementación **obligatoria** (sin postfijo `*`): el Requirement 6 enumera sus 17 criterios como criterios de aceptación mínimos de la Suite_de_Pruebas, no como cobertura opcional. La tarea 14, en cambio, es **opcional** en su totalidad (sub-tareas con postfijo `*`): tanto la sección "Property-Based Tests" de `requirements.md` como la sección "Correctness Properties" de `design.md` resuelven explícitamente que un conjunto de propiedades con Hypothesis **no es un requisito obligatorio** de esta especificación; las Properties 1-3 quedan documentadas como candidatas útiles (funciones puras, en memoria, sin E/S) y no condicionan la finalización del plan.

Archivos productivos afectados:
- `sinergia/app/v2/use_cases/meta_ads.py` (exclusivamente dentro de `FacebookLaunchCampaignUseCase`: `_is_campaign_valid`, `_build_response`, el bloque `except` de `execute()`, y los dos métodos privados nuevos `_build_standard_creative_published` e `_is_meta_auth_error`)

Archivos de prueba afectados:
- `sinergia/tests/v2/unit/use_cases/test_facebook_launch_campaign.py` (archivo nuevo)

## Tasks

- [x] 1. Implementar la Rama_STANDARD del gate `_is_campaign_valid`
  - [x] 1.1 En `FacebookLaunchCampaignUseCase._is_campaign_valid` (`sinergia/app/v2/use_cases/meta_ads.py`), convertir la rama `else: valid = True` en un `elif self.campaign_mode == CreativeType.STANDARD.value:` explícito conforme al Componente 1 de `design.md`, conservando el `else: valid = True` final para cualquier otro modo, y sin tocar el bloque `if self.campaign_mode == CreativeType.DYNAMIC.value:` ya existente
    - Normalizar a `{}` cada eslabón de la cadena `object_story_spec` → `link_data` → `call_to_action` → `call_to_action['type']` mediante `or {}` más una comprobación `isinstance(..., dict)`, de modo que las 8 lecturas posteriores nunca lancen
    - Evaluar las 8 condiciones del Requirement 2.1 con comparación estricta `is not True` (`title_valid`, `body_valid`, `description_valid`, `image_valid`, `link_url_valid` en `link_data`; `daily_budget_valid`, `locations_valid` en `object_story_spec`; `valid` en `call_to_action['type']`), retornando `False` para el conjunto completo de `creatives_to_publish` en cuanto un solo ad falle ("todo o nada"), y registrando el error con `logger.error`
    - No introducir ninguna llamada nueva a `MetaAdsValidator` ni ninguna validación de negocio adicional
    - No modificar el bloque de `execute()` que ya lanza `IncorrectValidationException("The campaign is not ready to launch.")` ante `is_ready` falso (Requirement 2.3 se satisface estructuralmente)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 2. Implementar la construcción del Creative_Publicado STANDARD en `_build_response`
  - [x] 2.1 Añadir el método privado nuevo `_build_standard_creative_published(self, idx, ad_set_published, ads_published)` dentro de `FacebookLaunchCampaignUseCase` (`sinergia/app/v2/use_cases/meta_ads.py`), conforme al Componente 2 de `design.md`: normalizar con `or {}` los cuatro niveles `adCreative` → `object_story_spec` → `link_data` → `call_to_action`, y retornar exactamente el conjunto fijo de 31 claves del Requirement 3.2, en el mismo orden y con las expresiones fuente y los valores por defecto de la tabla "Mapeo exacto fuente→campo del Creative_Publicado STANDARD" de `design.md`
    - Emitir los cinco `*_max_amount` con la constante `1` (no `0`), y `unique_titles`/`unique_bodies`/`unique_descriptions` como alias de `title_valid`/`body_valid`/`description_valid`, conforme a las notas de diseño del Componente 2
    - NO emitir `promoted_object_valid` y usar `ad_set_published.get('name')` (no el nombre compuesto), las dos divergencias deliberadas respecto de `_build_standard_creative_entry` documentadas en `design.md`
    - _Requirements: 3.2, 3.3_
  - [x] 2.2 Insertar, dentro del bucle `for i, ad_set_published in enumerate(data):` de `FacebookLaunchCampaignUseCase._build_response` (`sinergia/app/v2/use_cases/meta_ads.py`), el despacho `if self.campaign_mode == CreativeType.STANDARD.value:` que invoca `self._build_standard_creative_published(i, ad_set_published, ads_published)`, preservando en la rama `else` el cuerpo DYNAMIC actual **literalmente, carácter por carácter** (incluido su `ad_creative = ads_published.get('adCreative')` sin normalizar)
    - Conservar sin cambios `ads_published = ad_set_published.get('ads')[0]` (una única entrada por Ad_Set_a_Publicar), el diccionario `campaign` de nivel superior, `creatives_no`, `meta_url` y la estructura de retorno
    - Despachar por `self.campaign_mode` (ya asignado por `_get_campaign_setup`), no por presencia de `asset_feed_spec`
    - _Requirements: 3.1, 3.4, 3.5_

- [x] 3. Checkpoint - Componentes 1 y 2 implementados
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Endurecer la ruta de invocación del Rollback_de_Lanzamiento en el bloque `except` de `execute()`
  - [x] 4.1 Añadir el método privado nuevo, puro y estático `_is_meta_auth_error(exception)` dentro de `FacebookLaunchCampaignUseCase` (`sinergia/app/v2/use_cases/meta_ads.py`), conforme al Componente 3 de `design.md`: leer `text` con `getattr(exception, 'text', None)`, retornar `False` de inmediato cuando `text` no sea instancia de `dict`, y buscar los marcadores `code == 31` / `error_subcode == 3858385` tanto en el propio diccionario `text` (forma plana) como en el diccionario anidado bajo la clave `error` (forma externa producida por `RESTClientException(response.json())`)
    - El método SHALL NOT contener lógica de eliminación HTTP propia, no conoce `_delete_object` y no toca `requests`
    - _Requirements: 5.3, 5.4, 5.5, 5.6_
  - [x] 4.2 Reescribir el bloque `except Exception as e:` de `FacebookLaunchCampaignUseCase.execute()` (`sinergia/app/v2/use_cases/meta_ads.py`) conforme al Componente 3 de `design.md`: conservar el `logger.error` inicial, invocar `self._rollback_publish(meta_campaign_id, created_ad_creative_ids, decoded_access_token)` de forma **incondicional** y **antes** de clasificar la excepción, dentro de un `try/except Exception as rollback_error:` acotado que registre el fallo sin propagarlo; a continuación, si `self._is_meta_auth_error(e)` es verdadero lanzar `SinergiaException('META31', 'Autentica tu cuenta en el administrador de anuncios')`, y en cualquier otro caso `raise e` sin alterar tipo, mensaje ni atributos
    - Eliminar por completo el acceso no protegido `isinstance(e.text, dict)` del código actual
    - No modificar `_rollback_publish`, `_delete_object` ni `_update_campaign_setup` (Requirements 5.1, 5.2); el `try/except` acotado protege únicamente el sitio de invocación
    - Requirements 5.10, 5.11 y 5.12 se satisfacen estructuralmente: la Zona 1 no pasa por el manejador, `_rollback_publish` es un no-op cuando `meta_campaign_id` es `None` y `created_ad_creative_ids` está vacía, el manejador no consulta `self.campaign_mode`, y todas sus rutas terminan lanzando, por lo que `_update_campaign_setup` nunca se alcanza
    - _Requirements: 5.1, 5.2, 5.7, 5.8, 5.9, 5.10, 5.11, 5.12, 5.13_

- [x] 5. Verificar (sin modificar) la preservación de `_publish_media` y de los constructores de payload
  - [x] 5.1 Verificación exclusivamente, sin ningún cambio de código: confirmar por lectura directa de `sinergia/app/v2/use_cases/meta_ads.py` que `_publish_media`, `_build_object_story_spec`, `_build_asset_feed_spec`, `_publish_ad_creative` y `_upload_image` permanecen byte a byte idénticos tras las tareas 1, 2 y 4, incluido el comportamiento no controlado que `_publish_media` ya produce hoy (posible `KeyError` al acceder a `object_story_spec['link_data']` o a `link_data['image_url']`) y la eliminación incondicional de la clave `image_url`
    - Esta tarea SHALL NOT introducir ninguna guarda nueva en `_publish_media` ni modificar ningún otro método; el Requirement 4 se satisface por preservación, no por implementación
    - La `KeyError` de `_publish_media` se ejercita como escenario de prueba en la tarea 10.3, no como cambio productivo
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 6. Checkpoint - núcleo productivo completo (Componentes 1, 2 y 3)
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Crear la Suite_de_Pruebas con su infraestructura de dobles y builders
  - [x] 7.1 Crear el archivo nuevo `sinergia/tests/v2/unit/use_cases/test_facebook_launch_campaign.py`, replicando el estilo de fixtures y de parcheo de `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py`: sentinel privado `ABSENT` (para distinguir "clave omitida" de "clave presente con valor `None`"), builders sin estado compartido (`make_standard_link_data`, `make_standard_object_story_spec`, `make_dynamic_asset_feed_spec`, `make_ad_creative`, `make_ad`, `make_ad_set_to_publish`, `make_ad_channel`, `make_campaign_setup`, y el builder de conveniencia `make_fully_valid_standard_ad_set()` con las 8 condiciones del Requirement 2.1 en `True`), la fixture `use_case_factory` que parchea las **tres** clases de repositorio que el constructor instancia (`app.v2.use_cases.meta_ads.AdChannelRepository`, `app.v2.use_cases.meta_ads.CampaignChannelPublishRepository`, `app.v2.use_cases.meta_ads.CampaignRepository`), el context manager `patch_redis_client` (`app.v2.use_cases.meta_ads.redis_client`, con `.get.return_value = b"some-access-token"`), y la fixture `deny_network` con `autouse=True` a nivel de módulo que reemplaza `requests.sessions.Session.request` por una función que lanza `AssertionError`
    - Definir la constante `EXPECTED_KEYS` con las 31 claves del Requirement 3.2, para las comparaciones exactas de conjunto de las tareas 9.1 y 9.2
    - Afirmar sobre excepciones de `SinergiaException` mediante `exc_info.value.text`/`exc_info.value.code`, **nunca** mediante `str(exc_info.value)` (motivo verificado en `sinergia/app/exceptions/base.py`: `str(exc)` es siempre el literal `"()"`)
    - Para los escenarios de `execute()` se parchean los helpers `_publish_campaign`/`_publish_adset`/`_publish_media`/`_publish_ad_creative`/`_publish_ad` con `patch.object`, evitando construir respuestas HTTP completas
    - _Requirements: 6.1, 6.16_

- [x] 8. Probar el gate `_is_campaign_valid` para STANDARD
  - [x] 8.1 Implementar `TestIsCampaignValidStandard::test_single_false_condition_invalidates`, parametrizada por cada una de las 8 condiciones del Requirement 2.1 evaluada individualmente como no válida (manteniendo las otras siete en `True`) a partir de `make_fully_valid_standard_ad_set()`, cubriendo para cada condición las 3 variantes de invalidez (clave ausente / valor `None` / valor `False`) y verificando `_is_campaign_valid() is False` en cada caso
    - _Requirements: 6.2_
  - [x] 8.2 Implementar `TestIsCampaignValidStandard::test_all_eight_conditions_true_returns_true`, con 2 Ad_Set_a_Publicar cuyos ads tienen las 8 condiciones en `True` simultáneamente, verificando `_is_campaign_valid() is True`
    - _Requirements: 6.3_
  - [x] 8.3 Implementar `TestIsCampaignValidStandard::test_malformed_ad_creative_chain`, parametrizada con `adCreative` ausente y con `adCreative.get('object_story_spec')` ausente, extendida a `link_data`/`call_to_action` con valor `None` y con un tipo distinto a `dict`, verificando en todos los casos `_is_campaign_valid() is False` sin lanzar ninguna excepción
    - _Requirements: 6.15_

- [x] 9. Probar la construcción del Creative_Publicado STANDARD en `_build_response`
  - [x] 9.1 Implementar `TestBuildResponseStandard::test_full_object_story_spec_maps_every_field` con un Ad_Set_a_Publicar STANDARD completo: `assert set(entry.keys()) == EXPECTED_KEYS` (31 claves, sin comparación por subconjunto) más una aserción de igualdad exacta por cada clave contra el valor de entrada del fixture, conforme a la tabla de mapeo de `design.md`
    - _Requirements: 6.4_
  - [x] 9.2 Implementar `TestBuildResponseStandard::test_absent_data_uses_documented_defaults`, parametrizada en los 3 escenarios del Requirement 6.5: (a) `object_story_spec` completamente ausente, (b) `object_story_spec` presente pero `link_data` ausente, (c) `link_data` presente pero `call_to_action` ausente; verificando en cada uno ausencia de excepción, el conjunto fijo de 31 claves, y los valores por defecto documentados (`[]` para listas, `False` para booleanos de validez, `0`/`''` para escalares, `1` para los cinco `*_max_amount`)
    - _Requirements: 6.5_

- [x] 10. Probar el Rollback_de_Lanzamiento
  - [x] 10.1 Implementar `TestRollbackOnPartialFailure::test_rest_client_exception_after_creatives_triggers_full_rollback`: doble de `_publish_ad` con `side_effect=RESTClientException({'error': {'code': 100}})` tras un `_publish_campaign` exitoso y la creación de al menos un ad creative; verificar (a) `_delete_object` invocado exactamente una vez con el `meta_campaign_id`, (b) exactamente una vez por cada ad creative ya creado (conteo exacto, ni más ni menos), (c) el orden campaña-antes-de-creatives mediante `mock_delete_object.call_args_list`, (d) que la excepción original se relanza sin modificar (comparación por identidad), y (e) que `_update_campaign_setup` no fue invocado
    - Parchear `_delete_object` (**no** `_rollback_publish`), de modo que el `_rollback_publish` real se ejercite y su orden de eliminación quede verificado
    - _Requirements: 6.6_
  - [x] 10.2 Implementar `TestRollbackNotReachable::test_failure_before_campaign_creation`, parametrizada en las dos zonas del Requirement 5.10: fallo fuera del bloque `try` (doble de `_get_campaign_setup` que lanza) y fallo dentro del `try` con `meta_campaign_id is None` (doble de `_publish_campaign` que lanza); verificar en ambos que `_delete_object` no fue invocado ninguna vez, que `_update_campaign_setup` no fue invocado, y que la excepción original se relanza sin modificar
    - _Requirements: 6.7_
  - [x] 10.3 Implementar `TestRollbackOnPartialFailure::test_key_error_without_text_attribute`: doble de `_publish_media` con `side_effect=KeyError('link_data')` (equivalente a la `KeyError` que `_publish_media` ya puede producir conforme al Requirement 4.3), verificando (a) rollback completo con el `meta_campaign_id` y con cada ad creative ya creado, (b) que la excepción propagada desde `execute()` es la `KeyError` original y **no** un `AttributeError`, y (c) que `_update_campaign_setup` no fue invocado
    - _Requirements: 6.8_
  - [x] 10.4 Implementar `TestRollbackOnPartialFailure::test_delete_object_failure_does_not_mask_original`: doble de `_delete_object` con `side_effect=Exception('rollback boom')`, verificando que `execute()` propaga la excepción original del fallo de publicación y no la del rollback (este es el criterio que motiva el `try/except` del sitio de invocación de la tarea 4.2)
    - _Requirements: 6.12_
  - [x] 10.5 Implementar `TestRollbackOnPartialFailure::test_dynamic_mode_rollback_is_identical`, espejo de la tarea 10.1 con `self.campaign_mode == CreativeType.DYNAMIC.value` y un fixture DYNAMIC, verificando el mismo conjunto exacto de invocaciones de `_delete_object` que en el caso STANDARD
    - _Requirements: 6.13_

- [x] 11. Probar la clasificación de error de autenticación de Meta (META31)
  - [x] 11.1 Implementar `TestMetaAuthErrorClassification::test_nested_code_31_raises_meta31`: fallo tras un `_publish_campaign` exitoso y al menos un ad creative creado, con `text = {'error': {'code': 31}}` (forma anidada externa producida por `RESTClientException(response.json())`); verificar que `execute()` lanza `SinergiaException` con `code == 'META31'` y `text == 'Autentica tu cuenta en el administrador de anuncios'`
    - _Requirements: 6.9_
  - [x] 11.2 Implementar `TestMetaAuthErrorClassification::test_recognized_forms`, parametrizada con `{'error': {'error_subcode': 3858385}}` y con la forma plana `{'code': 31}`, verificando que ambas activan la clasificación; añadir el contraejemplo `{'error': {'code': 190}}` que NO debe activarla
    - _Requirements: 6.10_
  - [x] 11.3 Implementar `TestMetaAuthErrorClassification::test_rollback_runs_before_meta31`: para el escenario de la tarea 11.1, verificar (a) que `_delete_object` SÍ fue invocado con el `meta_campaign_id` y con cada ad creative ya creado (el rollback se ejecuta antes de lanzar `SinergiaException('META31', ...)`), y (b) que `_update_campaign_setup` no fue invocado
    - _Requirements: 6.11_

- [x] 12. Probar la no regresión de la Rama_DYNAMIC
  - [x] 12.1 Implementar `TestDynamicNonRegression` con dos casos sobre un fixture DYNAMIC fijo: `_is_campaign_valid` comparado por igualdad exacta del booleano retornado, y `_build_response` comparado por igualdad exacta del diccionario completo del Creative_Publicado contra un valor esperado fijo
    - _Requirements: 6.14_

- [x] 13. Checkpoint - Suite_de_Pruebas obligatoria completa (17 criterios del Requirement 6)
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Pruebas basadas en propiedades (opcionales, no condicionan la finalización)
  - [x] 14.1 Implementar con Hypothesis (`@settings(max_examples=100, deadline=None)`) la **Property 1: El gate STANDARD es exactamente la conjunción de las 8 condiciones**, invocando `_is_campaign_valid` directamente (sin pasar por `execute()`) sobre combinaciones generadas de los 8 campos de anotación (ausente / `None` / `False` / `True` / truthy no booleano)
    - **Property 1: El gate STANDARD es exactamente la conjunción de las 8 condiciones**
    - **Validates: Requirements 2.1, 2.2, 2.5**
  - [x] 14.2 Implementar con Hypothesis la **Property 2: La construcción del Creative_Publicado STANDARD es total y de clave fija**, invocando `_build_standard_creative_published` directamente sobre cualquier subconjunto (incluido el vacío, `None`, o la ausencia total de `adCreative`) de las claves de `object_story_spec`/`link_data`/`call_to_action`
    - **Property 2: La construcción del Creative_Publicado STANDARD es total y de clave fija**
    - **Validates: Requirements 3.2, 3.3**
  - [x] 14.3 Implementar con Hypothesis la **Property 3: La clasificación de la excepción es total y nunca produce una excepción secundaria**, invocando `_is_meta_auth_error` directamente con excepciones cuyo atributo `text` es de cualquier tipo (`dict`, `str`, `None`, `list`, numérico, objeto arbitrario) o está ausente por completo
    - **Property 3: La clasificación de la excepción es total y nunca produce una excepción secundaria**
    - **Validates: Requirements 5.3, 5.4, 5.5**

- [x] 15. Ejecución final de la suite
  - [x] 15.1 Ejecutar, desde `sinergia/` y con el intérprete de `sinergia/venv`, en modo no interactivo y sin watch: `./venv/bin/python -m pytest --collect-only -q tests/v2/unit/use_cases/test_facebook_launch_campaign.py`, luego `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_facebook_launch_campaign.py`, y finalmente la verificación de no regresión de las suites hermanas que ejercitan el mismo archivo productivo `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/`; corregir cualquier `failed`/`skipped`/error de recopilación hasta obtener cero en las tres categorías, sin modificar las aserciones de ninguna prueba preexistente de `sinergia/tests/v2/unit/use_cases/`
    - _Requirements: 6.17_

## Notes

- Ninguna sub-tarea de las tareas 8-12 está marcada con `*`: el Requirement 6 exige esos 17 criterios como criterios de aceptación mínimos obligatorios de la Suite_de_Pruebas.
- Todas las sub-tareas de la tarea 14 están marcadas con `*`: son opcionales y pueden omitirse. Tanto `requirements.md` (sección "Property-Based Tests") como `design.md` (sección "Correctness Properties") resuelven que las pruebas basadas en propiedades no son un requisito obligatorio de esta especificación.
- Cada tarea referencia los Requirements/criterios de aceptación exactos que satisface.
- Las tareas 1, 2 y 4 modifican exclusivamente `sinergia/app/v2/use_cases/meta_ads.py`, dentro del cuerpo de `FacebookLaunchCampaignUseCase` y únicamente en los tres métodos autorizados por el Requirement 1.2 (`_is_campaign_valid`, `_build_response`, bloque `except` de `execute()`) más los dos métodos privados nuevos y aditivos (`_build_standard_creative_published`, `_is_meta_auth_error`); ninguna toca archivos de prueba.
- La tarea 5 es de verificación exclusivamente: el Requirement 4 se satisface por preservación de `_publish_media`/`_build_object_story_spec`/`_build_asset_feed_spec`/`_publish_ad_creative`/`_upload_image`, no por implementación.
- Ninguna tarea modifica `sinergia/app/v2/resources/external.py` ni `sinergia/app/v2/async_tasks/celery_tasks.py` (Requirement 1.5 y sección Out of Scope de `requirements.md`).
- Las tareas 7-12 y 14 escriben todas sobre el mismo archivo nuevo `sinergia/tests/v2/unit/use_cases/test_facebook_launch_campaign.py`, por lo que aparecen en ondas distintas del Task Dependency Graph.
- Los escenarios de rollback parchean `_delete_object`, nunca `_rollback_publish`, de modo que el `_rollback_publish` real se ejercite y su orden de eliminación quede verificado (Requirements 5.1, 6.6c).
- Los Componentes 1 y 2 (tareas 1 y 2) son independientes entre sí y del Componente 3 (tarea 4). Las tareas de prueba de rollback (10.x, 11.x) ejercitan `execute()` de extremo a extremo, por lo que dependen de que la infraestructura de fixtures/builders de la tarea 7.1 exista primero y de que el Componente 3 esté implementado.
- Los checkpoints (tareas 3, 6 y 13) son puntos de sincronización, no tareas de código: por eso no aparecen en el Task Dependency Graph.
- La tarea 15 (ejecución final) depende de que todas las tareas de implementación y de prueba obligatorias anteriores (1, 2, 4, 5, 7-12) estén completas.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2"] },
    { "id": 3, "tasks": ["4.1"] },
    { "id": 4, "tasks": ["4.2"] },
    { "id": 5, "tasks": ["5.1", "7.1"] },
    { "id": 6, "tasks": ["8.1"] },
    { "id": 7, "tasks": ["8.2"] },
    { "id": 8, "tasks": ["8.3"] },
    { "id": 9, "tasks": ["9.1"] },
    { "id": 10, "tasks": ["9.2"] },
    { "id": 11, "tasks": ["10.1"] },
    { "id": 12, "tasks": ["10.2"] },
    { "id": 13, "tasks": ["10.3"] },
    { "id": 14, "tasks": ["10.4"] },
    { "id": 15, "tasks": ["10.5"] },
    { "id": 16, "tasks": ["11.1"] },
    { "id": 17, "tasks": ["11.2"] },
    { "id": 18, "tasks": ["11.3"] },
    { "id": 19, "tasks": ["12.1"] },
    { "id": 20, "tasks": ["14.1"] },
    { "id": 21, "tasks": ["14.2"] },
    { "id": 22, "tasks": ["14.3"] },
    { "id": 23, "tasks": ["15.1"] }
  ]
}
```
