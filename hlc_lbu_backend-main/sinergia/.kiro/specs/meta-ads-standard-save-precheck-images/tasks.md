# Implementation Plan: Meta Ads Standard Save Pre-Check Images

**Ubicación obligatoria (Requirement 1.1, 1.4):** este documento reside en `sinergia/.kiro/specs/meta-ads-standard-save-precheck-images/tasks.md` y describe cambios exclusivamente dentro del árbol `sinergia/`. Toda ruta de archivo mencionada en las tareas siguientes se expresa con el segmento `sinergia/` explícito; ninguna ruta es relativa a la raíz del monorepo `docker-deploy`.

## Overview

Este plan implementa la Rama_STANDARD de `FacebookSavePreCheckImagesUseCase._validate_images_standard` (hoy un `pass`) y extiende `FacebookSavePreCheckBaseUseCase._build_response` para que también produzca la Respuesta_de_Precheck para un ad set STANDARD, siguiendo el diseño aprobado en `design.md`. El orden de tareas sigue la secuencia de dependencias del diseño: primero el método de validación de imagen (independiente), luego el dispatch/extracción de `_build_response` (que lee las anotaciones que produce el primer método), luego la infraestructura de pruebas compartida (`make_link_data`), luego la sustitución completa de `TestValidateImagesStandard`, luego la ampliación de `TestBuildResponse` (incluyendo la actualización de las dos aserciones de `AttributeError` ya existentes), y finalmente la ejecución completa de la suite con el intérprete de `sinergia/venv`.

Conforme a la sección "Testing Strategy" de `design.md` ("Por qué no se exigen pruebas basadas en propiedades (PBT)"), esta especificación NO requiere ninguna suite de pruebas basadas en propiedades (Hypothesis): la cobertura obligatoria es exclusivamente de ejemplo (unit tests), tal como ya resuelve `requirements.md` en su propia sección "Property-Based Tests". Por esta razón, ninguna tarea de este plan referencia una Correctness Property de `design.md` como suite a implementar; las Properties 1-4 documentadas allí quedan únicamente con fines de trazabilidad.

Todas las tareas de prueba de este plan son de implementación obligatoria (no opcional): el Requirement 7 exige explícitamente la totalidad de los escenarios de prueba enumerados como criterios de aceptación de esta especificación, por lo que ninguna sub-tarea de prueba se marca con el postfijo `*`.

Archivos productivos afectados:
- `sinergia/app/v2/use_cases/meta_ads.py`

Archivos de prueba afectados:
- `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py` (ampliado; ningún archivo de prueba nuevo)

## Tasks

- [x] 1. Implementar `_validate_images_standard`
  - [x] 1.1 Reemplazar el cuerpo `pass` de `FacebookSavePreCheckImagesUseCase._validate_images_standard` en `sinergia/app/v2/use_cases/meta_ads.py` por la implementación completa descrita en el Componente 1 de `design.md`: reasignar `link_data = story_spec.get('link_data') or {}` (creado y reasignado a `story_spec['link_data']` cuando esté ausente/`None`), anotar `link_data['image_valid'] = False` y retornar de inmediato cuando `len(self.images) != 1` sin invocar al validador ni tocar `image_url`/`image_error`, y, cuando `len(self.images) == 1`, asignar `link_data['image_url']` desde `self.images[0].get('url')`, invocar `MetaAdsValidator.validate_images_precheck([{'url': image_url}])` y anotar `link_data['image_valid']`/`link_data['image_error']` exactamente desde el resultado (`.get('valid', False)`/`.get('error')`)
    - No introducir ningún método privado nuevo ni reutilizar `_standard_candidate_values` (Valor_Candidato es simplemente `len(self.images)`, conforme a la nota de diseño del Componente 1)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 2. Implementar el dispatch y la extracción STANDARD en `_build_response`
  - [x] 2.1 Reestructurar `FacebookSavePreCheckBaseUseCase._build_response` en `sinergia/app/v2/use_cases/meta_ads.py` conforme a los Componentes 2-4 de `design.md`: preservar la primera línea (`ads_to_publish = creative.get('ads')[0]`), insertar la normalización compartida `ad_creative = ads_to_publish.get('adCreative') or {}` seguida de `object_story_spec = ad_creative.get('object_story_spec')` / `asset_feed_spec = ad_creative.get('asset_feed_spec')`, y despachar con `if object_story_spec or not asset_feed_spec:` hacia la extracción STANDARD nueva (Componente 3, incluyendo las closures locales `_as_single_item_list` definidas dentro del propio método) o hacia la extracción DYNAMIC ya existente copiada **literalmente, carácter por carácter** en la rama `else` (Componente 4)
    - Verificar contra la tabla de verdad de las 4 combinaciones de `design.md` (STANDARD tiene prioridad cuando ambos son verdaderos; STANDARD también se usa cuando ambos son falsy/ausentes)
    - No modificar ningún otro método de `FacebookSavePreCheckBaseUseCase` ni de ninguna otra clase `Save*`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4_

- [x] 3. Checkpoint - núcleo productivo completo
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Preparar la infraestructura de pruebas compartida
  - [x] 4.1 Añadir a `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py` el builder `make_link_data(**overrides)`, copiado/adaptado desde `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` (mismo módulo donde ya existe con la misma forma), construyendo un diccionario fresco con `name`, `message`, `description`, `image_url`, `link`, `call_to_action` en `None` por defecto, componible directamente con `make_object_story_spec(link_data=make_link_data(...))`
    - No modificar ningún builder/fixture existente en el archivo (`make_pre_check_images_data`, `make_image_entry`, `make_ad_channel`, `make_campaign_setup`, `make_object_story_spec`, `make_ad_creative`, `make_ad`, `make_creative`, `use_case_factory`, `patch_redis_client`, `patch_image_fetch`, `deny_network`)
    - _Requirements: 7.1_

- [x] 5. Reemplazar `TestValidateImagesStandard` por los nuevos escenarios de validación de imagen
  - [x] 5.1 Sustituir por completo la clase `TestValidateImagesStandard` (que hoy caracteriza el no-op `pass`) e implementar el escenario de éxito: exactamente 1 Imagen_Candidata válida (`self.images = [make_image_entry(url=...)]`, simulada válida vía `patch_image_fetch`/`_build_valid_test_image_bytes` ya presente en el archivo); verificar `link_data['image_url']`, `link_data['image_valid'] is True`, `link_data['image_error'] is None`
    - _Requirements: 7.2_
  - [x] 5.2 Implementar el escenario de 1 Imagen_Candidata marcada inválida por `MetaAdsValidator.validate_images_precheck` (parcheando `patch_image_fetch(side_effect=requests.exceptions.RequestException(...))` o una respuesta simulada fuera de rango, sin solicitud HTTP real); verificar `link_data['image_valid'] is False` y que `link_data['image_error']` refleja el mensaje anotado
    - _Requirements: 7.3_
  - [x] 5.3 Implementar, parametrizado, el escenario de 0 Imágenes_Candidatas y el de 2 o más Imágenes_Candidatas: verificar en ambos que `link_data['image_valid'] is False`, que `MetaAdsValidator.validate_images_precheck` no fue invocado (`assert_not_called`), y que un `image_url` preexistente en `link_data` permanece sin modificar
    - _Requirements: 7.4_
  - [x] 5.4 Implementar el escenario en el que `object_story_spec` carece por completo de la clave `link_data` (o es `{}`): verificar que `_validate_images_standard` no lanza excepción y que, tras la invocación, `story_spec['link_data']` es un diccionario nuevo con `image_valid=False`/`image_error` anotado, consistente con el escenario de 0 candidatas de la tarea 5.3
    - _Requirements: 7.5_

- [x] 6. Checkpoint - validación de imagen STANDARD implementada y probada
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Ampliar `TestBuildResponse` con los escenarios STANDARD y actualizar las aserciones de `AttributeError`
  - [x] 7.1 Implementar, dentro de `TestBuildResponse`, el escenario de `execute()` completo en modo STANDARD sin parchear `_validate_images_standard` (reutilizando `make_object_story_spec(link_data=make_link_data(...))` con una imagen candidata válida): verificar que la Respuesta_de_Precheck final contiene exactamente el conjunto de claves del Glossary de `requirements.md`, con `images` reflejando el resultado de la validación
    - _Requirements: 7.6_
  - [x] 7.2 Implementar el escenario de `_build_response` invocado directamente con `object_story_spec`/`link_data` parcial o totalmente poblado, incluyendo anotaciones ya presentes de una ejecución previa de `FacebookGeneratePreCheckCreativeUseCase.execute()` (por ejemplo `title_valid=True`, `body_valid=False`, `daily_budget_valid=True`, `call_to_action={'type': {'value': 'SIGN_UP', 'valid': True}}`); verificar que la Respuesta_de_Precheck refleja esos valores conforme a la tabla de mapeo "`CreativeToPublish` para STANDARD" de `design.md`
    - _Requirements: 7.7_
  - [x] 7.3 Implementar el escenario en el que `adCreative` tiene `object_story_spec` y `asset_feed_spec` ausentes/`None`/`{}` simultáneamente, verificando que `_build_response` no lanza excepción y produce exactamente los valores por defecto documentados en `design.md`; **reemplazar** las dos aserciones de `AttributeError` ya existentes en el archivo (`test_direct_isolated_call_raises_attribute_error_when_ad_creative_is_explicit_none` y `test_direct_isolated_call_raises_attribute_error_when_ad_creative_key_absent`) para que verifiquen en su lugar la Respuesta_de_Precheck con valores por defecto, conforme a la justificación de la sección "Error Handling" de `design.md` (Requirement 1.5)
    - _Requirements: 7.8_
  - [x] 7.4 Añadir, sin modificar las aserciones de los escenarios DYNAMIC ya existentes en `TestValidateImagesDynamic`/`TestBuildResponse`, un escenario adicional que confirme que `_validate_images_standard` no es invocado cuando `campaign_setup['attributes']['meta_campaign_mode']` es `"DYNAMIC"` (verificación de invocación mediante `patch.object`, no de `_build_response`)
    - _Requirements: 7.9_

- [x] 8. Checkpoint - suite de pruebas ampliada completa
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Ejecución final de la suite completa
  - [x] 9.1 Ejecutar, desde `sinergia/`, `./venv/bin/python -m pytest --collect-only -q tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py` y `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py` con el intérprete de `sinergia/venv`, corrigiendo cualquier `failed`/`skipped`/error de recopilación encontrado hasta obtener cero en las tres categorías, sin modificar las aserciones de ninguna prueba ya existente distinta de las dos identificadas en la tarea 7.3
    - _Requirements: 7.10, 7.11_

## Notes

- Ninguna sub-tarea de prueba está marcada con `*`: el Requirement 7 exige la totalidad de estos escenarios como criterios de aceptación obligatorios de esta especificación, no como cobertura opcional de MVP.
- Ninguna tarea de este plan implementa pruebas basadas en propiedades (Hypothesis): `design.md`/`requirements.md` ya deciden explícitamente que PBT no aplica a esta especificación; las Correctness Properties 1-4 de `design.md` quedan documentadas únicamente con fines de trazabilidad.
- Cada tarea referencia los Requirements/criterios de aceptación exactos que satisface.
- Las tareas 1-2 modifican exclusivamente `sinergia/app/v2/use_cases/meta_ads.py`, dentro de los dos métodos autorizados por el Requirement 1.2 (`_validate_images_standard` y `_build_response`); ninguna toca archivos de prueba.
- Las tareas 4-7 amplían `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py`; no se crea ningún archivo de prueba nuevo.
- Los checkpoints (tareas 3, 6 y 8) son puntos de sincronización, no tareas de código: por eso no aparecen en el Task Dependency Graph.
- La tarea 9 (ejecución final) depende de que todas las tareas de implementación y de prueba anteriores (1, 2, 4-7) estén completas.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "4.1"] },
    { "id": 2, "tasks": ["5.1"] },
    { "id": 3, "tasks": ["5.2"] },
    { "id": 4, "tasks": ["5.3"] },
    { "id": 5, "tasks": ["5.4"] },
    { "id": 6, "tasks": ["7.1"] },
    { "id": 7, "tasks": ["7.2"] },
    { "id": 8, "tasks": ["7.3"] },
    { "id": 9, "tasks": ["7.4"] },
    { "id": 10, "tasks": ["9.1"] }
  ]
}
```
