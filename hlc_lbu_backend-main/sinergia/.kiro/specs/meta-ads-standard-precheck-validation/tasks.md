# Implementation Plan: Meta Ads Standard Pre-Check Validation

**Ubicación obligatoria (Requirement 1.1, 1.5):** este documento reside en `sinergia/.kiro/specs/meta-ads-standard-precheck-validation/tasks.md` y describe cambios exclusivamente dentro del árbol `sinergia/`. Toda ruta de archivo mencionada en las tareas siguientes se expresa con el segmento `sinergia/` explícito; ninguna ruta es relativa a la raíz del monorepo `docker-deploy`.

## Overview

Este plan implementa la Rama_STANDARD de `FacebookGeneratePreCheckCreativeUseCase.execute()` hasta paridad funcional con la Rama_DYNAMIC, siguiendo el diseño aprobado en `design.md`. El orden de tareas sigue la secuencia de dependencias del diseño: primero la propagación de `ad_channel_id` en `MetaAdsPayloadBuilder` (colaborador externo), luego la guardia de combinación soportada, luego los métodos privados de validación por campo, luego el cableado dentro de `execute()`, luego la construcción de `creatives[]` y la lectura de `ad_channel_id`, y finalmente la suite de pruebas completa (archivo principal + archivo nuevo de `MetaAdsPayloadBuilder`) y la verificación de no regresión.

Todas las tareas de prueba de este plan son de implementación obligatoria (no opcional): Requirement 15 exige explícitamente la totalidad de los escenarios de prueba enumerados como criterios de aceptación de esta especificación, por lo que ninguna sub-tarea de prueba se marca con el postfijo `*`.

Archivos productivos afectados:
- `sinergia/app/v2/use_cases/facebook_validator_service.py`
- `sinergia/app/v2/use_cases/meta_ads.py`

Archivos de prueba afectados:
- `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` (ampliado)
- `sinergia/tests/v2/unit/use_cases/test_meta_ads_payload_builder_standard_ad_channel_id.py` (nuevo)

## Tasks

- [x] 1. Propagar `ad_channel_id` en `MetaAdsPayloadBuilder`
  - [x] 1.1 Añadir el campo `ad_channel_id: Optional[int] = None` a la dataclass `ObjectStorySpec` en `sinergia/app/v2/use_cases/facebook_validator_service.py`
    - _Requirements: 11.1_
  - [x] 1.2 Modificar la rama `elif self.creative_type == CreativeType.STANDARD.value:` de `MetaAdsPayloadBuilder.build_creative` (`sinergia/app/v2/use_cases/facebook_validator_service.py`) para asignar `ad_channel_id=asset_feed_spec.ad_channel_id if asset_feed_spec else None` al `ObjectStorySpec` construido, sin modificar la rama `DYNAMIC` ni `build_asset_feed_spec`
    - _Requirements: 11.1, 11.2_

- [x] 2. Definir las combinaciones objetivo/optimización soportadas para STANDARD
  - [x] 2.1 Añadir la constante de clase `_STANDARD_SUPPORTED_COMBINATIONS` (las 4 tuplas `(objective, optimization_goal)`) y el método `_is_standard_combination_supported` a `FacebookGeneratePreCheckCreativeUseCase` en `sinergia/app/v2/use_cases/meta_ads.py`
    - _Requirements: 2.1, 2.2, 2.3_

- [x] 3. Insertar la guardia previa al bucle que lanza `MetaException("META011", ...)`
  - [x] 3.1 En `FacebookGeneratePreCheckCreativeUseCase.execute()` (`sinergia/app/v2/use_cases/meta_ads.py`), insertar la verificación `if self.creative_type == CreativeType.STANDARD.value and not self._is_standard_combination_supported(): raise MetaException("META011", ...)` dentro del mismo bloque donde ya se lanzan `META001`-`META010` (antes de `results = []` / `for ad_set in ad_sets:`), incluyendo en el mensaje la combinación `self.objective`/`self.optimization_goal` evaluada
    - _Requirements: 2.2, 13.1, 13.2, 13.3, 13.4_

- [x] 4. Implementar los métodos privados de validación STANDARD por campo
  - [x] 4.1 Implementar `_standard_candidate_values` (staticmethod puro) en `FacebookGeneratePreCheckCreativeUseCase` (`sinergia/app/v2/use_cases/meta_ads.py`), implementando literalmente la definición de Valor_Candidato del Glossary
    - _Requirements: 3.1, 4.1, 5.1, 6.1_
  - [x] 4.2 Implementar `_validate_standard_text_field(link_data, raw_value, field_name, annotation_key, error_slug, current_ad_errors)`, parametrizable para título/cuerpo/descripción, reutilizando `MetaAdsValidator.is_valid_length`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 10.1, 10.2_
  - [x] 4.3 Implementar `_validate_standard_image(link_data, current_ad_errors)`, reutilizando `MetaAdsValidator.validate_images_precheck` sobre una lista sintética de un elemento
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 10.1, 10.2_
  - [x] 4.4 Implementar `_validate_standard_url(link_data, current_ad_errors)`, usando `MetaAdsValidator.is_valid_link_url` y evitando invocarlo con un valor falsy
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 10.1, 10.2_
  - [x] 4.5 Implementar `_validate_standard_daily_budget(ad_set, object_story_spec, min_budget, current_ad_errors)`, reutilizando `min_budget` ya calculado por `_get_minimum_budget` y acotando la captura a `except TypeError`
    - _Requirements: 8.1, 8.2, 8.3, 10.1, 10.2_
  - [x] 4.6 Implementar `_validate_standard_cta(link_data, current_ad_errors)`, usando `MetaAdsValidator.validate_cta_for_goal` y anotando `valid` sobre el propio diccionario `call_to_action`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.3_
  - [x] 4.7 Implementar `_validate_standard_creative(ad_set, object_story_spec, min_budget, current_ad_errors)` como orquestador que invoca 4.2-4.6 en el orden título → cuerpo → descripción → imagen → URL → presupuesto → CTA, tratando `link_data` ausente como diccionario vacío reasignado a `object_story_spec['link_data']`
    - _Requirements: 10.1, 10.4_

- [x] 5. Conectar la Rama_STANDARD dentro de `execute()`
  - [x] 5.1 Reemplazar el cuerpo de `elif self.creative_type == "STANDARD" and story_spec:` en `FacebookGeneratePreCheckCreativeUseCase.execute()` (`sinergia/app/v2/use_cases/meta_ads.py`) por una única llamada a `self._validate_standard_creative(ad_set, story_spec, min_budget, current_ad_errors)`, preservando el guard externo `and story_spec:` sin cambios
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 6. Checkpoint - núcleo de validación STANDARD
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Construir `creatives[]` con despacho DYNAMIC/STANDARD
  - [x] 7.1 Extraer `_build_dynamic_creative_entry(self, idx, ad_set_to_publish, ad_creative)` en `sinergia/app/v2/use_cases/meta_ads.py` como copia literal del diccionario `creative_to_publish` ya existente dentro de `execute()`, sin ningún cambio de comportamiento observable
    - _Requirements: 12.1, 14.1, 14.2, 14.3_
  - [x] 7.2 Implementar `_build_standard_creative_entry(self, idx, ad_set_to_publish, ad_creative)` en `sinergia/app/v2/use_cases/meta_ads.py`, extrayendo desde `object_story_spec`/`link_data` conforme a la tabla de mapeo de `design.md` (Requirement 12), con los valores por defecto documentados para toda clave ausente
    - _Requirements: 12.2, 12.3, 12.4_
  - [x] 7.3 Insertar el despacho `if self.creative_type == CreativeType.STANDARD.value: ... else: ...` en el bucle de construcción de `creatives[]` dentro de `execute()`, invocando 7.1/7.2 según corresponda
    - _Requirements: 12.1, 12.2, 14.1, 14.2_

- [x] 8. Leer `ad_channel_id` en `_save_creative_to_publish`
  - [x] 8.1 Modificar `_save_creative_to_publish` (`sinergia/app/v2/use_cases/meta_ads.py`) de forma aditiva, agregando una rama `if self.creative_type == CreativeType.STANDARD.value:` que lee `ad_channel_id` desde `object_story_spec.get('ad_channel_id', 0)`, preservando byte a byte la rama `else` existente para cualquier otro `creative_type`
    - _Requirements: 11.3, 11.4, 11.5, 14.2_

- [x] 9. Checkpoint - núcleo productivo de la Rama_STANDARD completo
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Preparar la infraestructura de pruebas del archivo principal
  - [x] 10.1 Añadir a `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` los builders/parametrizaciones nuevos: la lista `STANDARD_SUPPORTED_COMBINATIONS` (con ids legibles), `make_standard_link_data_full`, y las estrategias Hypothesis `unsupported_objective_optimization_pairs`, `standard_candidate_values_with_wrong_count` y `arbitrary_text`
    - _Requirements: 15.1, 15.2_
  - [x] 10.2 Reescribir el helper `_run_single_standard_ad` para aceptar `objective`/`optimization_goal` con un valor por defecto perteneciente a `_STANDARD_SUPPORTED_COMBINATIONS`, y eliminar las 9 pruebas existentes de `TestExecuteStandardBranch` (reemplazadas en su totalidad, no ampliadas, conforme a la decisión de diseño documentada en `design.md`)
    - _Requirements: 14.5, 15.1_

- [x] 11. Probar la guardia de combinación soportada
  - [x] 11.1 Implementar `TestStandardCombinationSupport` en el archivo principal: **Property 1 (Excepción única y previa al bucle ante combinación no soportada)** vía Hypothesis invocando `execute()` completo dentro de `pytest.raises(MetaException)` verificando `code == "META011"` y `assert_not_called` sobre los 4 colaboradores de `MetaAdsValidator` y sobre `_save_campaign_channel_publish`/`_save_creative_to_publish`, más 4 ejemplos explícitos (uno por combinación soportada) y 1 ejemplo con `objective`/`optimization_goal` ambos `None`
    - **Validates: Property 1 — Requirements 2.2, 13.1, 13.2, 13.4, 15.6**

- [x] 12. Probar la validación de campos de texto STANDARD
  - [x] 12.1 Implementar `TestStandardTextFieldValidation` en el archivo principal, parametrizada por campo (título/cuerpo/descripción): **Property 2 (conteo de candidatos ≠1)** y **Property 3 (equivalencia de longitud con `is_valid_length`)** vía Hypothesis, más los ejemplos explícitos de longitud excedida y de cantidad 0/≥2 exigidos por Requirement 15
    - **Validates: Properties 2, 3 — Requirements 3.1-3.5, 4.1-4.5, 5.1-5.5, 15.3, 15.4**

- [x] 13. Probar la validación de imagen STANDARD
  - [x] 13.1 Implementar `TestStandardImageValidation` en el archivo principal: **Property 2 (rama imagen)** y **Property 4 (espejo del resultado de `validate_images_precheck`)**, más el ejemplo dedicado de imagen marcada inválida (distinguible del error de cantidad)
    - **Validates: Properties 2, 4 — Requirements 6.1-6.7, 15.4, 15.12**

- [x] 14. Probar la validación de URL STANDARD
  - [x] 14.1 Implementar `TestStandardUrlValidation` en el archivo principal: **Property 4 (rama URL, espejo de `is_valid_link_url`)**, más el ejemplo dedicado de URL inválida y el ejemplo de URL ausente
    - **Validates: Property 4 — Requirements 7.1-7.4, 15.5**

- [x] 15. Probar la validación de presupuesto diario STANDARD
  - [x] 15.1 Implementar `TestStandardDailyBudgetValidation` en el archivo principal: **Property 6 (comparación numérica válida vs. tipo no comparable)**, más el ejemplo dedicado con `daily_budget=None`
    - **Validates: Property 6 — Requirements 8.1, 8.2, 15.13**

- [x] 16. Probar la validación de CTA STANDARD
  - [x] 16.1 Implementar `TestStandardCtaValidation` en el archivo principal: **Property 4 (rama CTA)**, más los 3 escenarios exigidos por Requirement 15.11 (CTA válido, inválido, ausente) y 1 ejemplo de CTA truthy no-dict
    - **Validates: Property 4 — Requirements 9.1-9.5, 15.11**

- [x] 17. Probar el contrato de anotación sobre `object_story_spec`
  - [x] 17.1 Implementar `TestStandardAnnotationContract` en el archivo principal: **Property 5 (contrato de tres estados observables)**, invocando `_validate_standard_creative` directamente con `MetaAdsValidator` mockeado por completo bajo una combinación objetivo/optimización siempre soportada, generando combinaciones aleatorias de resultado por colaborador
    - **Validates: Property 5 — Requirements 10.1, 10.2, 10.3, 10.4**

- [x] 18. Probar la construcción de `creatives[]` para STANDARD
  - [x] 18.1 Implementar `TestStandardCreativesEntry` en el archivo principal: **Property 8 (construcción total sin excepciones de `CreativeToPublish` para STANDARD)** vía Hypothesis sobre `object_story_spec` parcial/total/ausente, más el ejemplo dedicado de Requirement 15.7
    - **Validates: Property 8 — Requirements 12.2, 12.3, 12.4, 15.7**

- [x] 19. Probar los escenarios de éxito por combinación soportada
  - [x] 19.1 Implementar `TestStandardCombinationSuccessScenarios` en el archivo principal: los 4 escenarios de éxito completos (uno por combinación soportada) usando `make_standard_link_data_full`, verificando `ok=1` y las 7 anotaciones de éxito presentes y en `True` simultáneamente
    - _Requirements: 2.1, 10.2, 15.2_

- [x] 20. Probar la lectura de `ad_channel_id` dentro de `execute()`
  - [x] 20.1 Implementar `TestExecuteStandardAdChannelIdReading` en el archivo principal (junto a `TestExecutePersistenceSideEffects`/`TestExecuteCombinedScenarios`): **Property 7 (rama de lectura)**, cubriendo el caso límite `ad_channel_id=None` presente explícitamente frente a clave ausente, tanto en `_save_creative_to_publish` como en `_build_standard_creative_entry`
    - **Validates: Property 7 (lectura) — Requirements 11.3, 11.4, 11.5**

- [x] 21. Checkpoint - archivo principal de pruebas completo
  - Ensure all tests pass, ask the user if questions arise.

- [x] 22. Probar la propagación de `ad_channel_id` en `MetaAdsPayloadBuilder`
  - [x] 22.1 Crear `sinergia/tests/v2/unit/use_cases/test_meta_ads_payload_builder_standard_ad_channel_id.py` con `TestBuildCreativeStandardAdChannelIdPropagation`: **Property 7 (rama builder)**, cubriendo valores de `ad_channel_id` (`None`, `0`, enteros positivos) y el caso `build_asset_feed_spec` retornando `None`, aislando `StrapiClient` sin acceso real a Strapi
    - **Validates: Property 7 (builder) — Requirements 11.1, 11.2**

- [x] 23. Verificar la no regresión de la Rama_DYNAMIC y del resto de `execute()`
  - [x] 23.1 Ejecutar la suite completa de `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` y confirmar que las clases `TestExecuteDynamicBranch`, `TestExecuteAggregationAndStatus`, `TestExecutePersistenceSideEffects`, `TestExecuteCombinedScenarios`, `TestExecuteCreationBlock`, `TestExecuteMissingCreative`, `TestConstructorAndInheritedState`, `TestGetDecodedAccessToken`, `TestBuildMetaPayload`, `TestGetAccountDetails` y `TestGetMinimumBudget` continúan pasando sin modificar sus aserciones, salvo el ajuste puntual permitido por Requirement 12.1 si alguna depende de la forma literal del bucle de `creatives[]` antes de la extracción de 7.1
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [x] 24. Ejecución final de la suite completa
  - [x] 24.1 Ejecutar, desde `sinergia/`, `./venv/bin/python -m pytest --collect-only -q tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py tests/v2/unit/use_cases/test_meta_ads_payload_builder_standard_ad_channel_id.py` y `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py tests/v2/unit/use_cases/test_meta_ads_payload_builder_standard_ad_channel_id.py`, confirmando cero pruebas `failed`, cero `skipped` y cero errores de recopilación o ejecución
    - _Requirements: 15.10_

## Notes

- Ninguna sub-tarea de prueba está marcada con `*`: Requirement 15 exige la totalidad de estos escenarios como criterios de aceptación obligatorios de esta especificación, no como cobertura opcional de MVP.
- Cada tarea referencia los Requirements/criterios de aceptación exactos que satisface; las tareas de prueba adicionalmente referencian la Correctness Property de `design.md` que validan.
- Las tareas 1-9 modifican exclusivamente `sinergia/app/v2/use_cases/facebook_validator_service.py` y `sinergia/app/v2/use_cases/meta_ads.py`; ninguna toca archivos de prueba.
- Las tareas 10-21 amplían `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py`; la tarea 22 crea `sinergia/tests/v2/unit/use_cases/test_meta_ads_payload_builder_standard_ad_channel_id.py` como archivo nuevo y separado, conforme a la decisión de diseño documentada en `design.md`.
- Los checkpoints (tareas 6, 9 y 21) son puntos de sincronización, no tareas de código: por eso no aparecen en el Task Dependency Graph.
- La tarea 23 (no regresión) y la tarea 24 (ejecución final) dependen de que todas las tareas de prueba anteriores (10-22) estén completas.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "2.1"] },
    { "id": 2, "tasks": ["3.1", "22.1"] },
    { "id": 3, "tasks": ["4.1"] },
    { "id": 4, "tasks": ["4.2"] },
    { "id": 5, "tasks": ["4.3"] },
    { "id": 6, "tasks": ["4.4"] },
    { "id": 7, "tasks": ["4.5"] },
    { "id": 8, "tasks": ["4.6"] },
    { "id": 9, "tasks": ["4.7"] },
    { "id": 10, "tasks": ["5.1"] },
    { "id": 11, "tasks": ["7.1"] },
    { "id": 12, "tasks": ["7.2"] },
    { "id": 13, "tasks": ["7.3"] },
    { "id": 14, "tasks": ["8.1"] },
    { "id": 15, "tasks": ["10.1"] },
    { "id": 16, "tasks": ["10.2"] },
    { "id": 17, "tasks": ["11.1"] },
    { "id": 18, "tasks": ["12.1"] },
    { "id": 19, "tasks": ["13.1"] },
    { "id": 20, "tasks": ["14.1"] },
    { "id": 21, "tasks": ["15.1"] },
    { "id": 22, "tasks": ["16.1"] },
    { "id": 23, "tasks": ["17.1"] },
    { "id": 24, "tasks": ["18.1"] },
    { "id": 25, "tasks": ["19.1"] },
    { "id": 26, "tasks": ["20.1"] },
    { "id": 27, "tasks": ["23.1"] },
    { "id": 28, "tasks": ["24.1"] }
  ]
}
```
