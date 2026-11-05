# Implementation Plan: Meta Ads Standard Save Pre-Check Texts/CTAs/Budget/Proposal URL/Locations

**Ubicación obligatoria (Requirement 1.1, 1.5):** este documento reside en `sinergia/.kiro/specs/meta-ads-standard-save-precheck-texts-ctas-budget-proposal-url-locations/tasks.md` y describe cambios exclusivamente dentro del árbol `sinergia/`. Toda ruta de archivo mencionada en las tareas siguientes se expresa con el segmento `sinergia/` explícito; ninguna ruta es relativa a la raíz del monorepo `docker-deploy`.

## Overview

Este plan implementa las cinco Ramas_STANDARD (hoy un `pass`) de `execute()` de Caso_de_Uso_Textos, Caso_de_Uso_CTAs, Caso_de_Uso_Budget, Caso_de_Uso_URL y Caso_de_Uso_Locations, siguiendo el diseño aprobado en `design.md`. Conforme al "Principio de aislamiento" de `design.md` (Requirement 1.2, 1.3, 7), las cinco clases son mutuamente independientes: cada una modifica únicamente su propio bloque `elif` dentro de `execute()` (más, para CTAs, un único método privado nuevo definido en su propia subclase), sin introducir ninguna abstracción compartida entre ellas ni tocar `_build_response`, `facebook_validator_service.py` ni `FacebookSavePreCheckImagesUseCase`. Por esta razón, el plan se organiza en cinco bloques secuenciales por Caso_de_Uso (implementación productiva → suite de pruebas propia, nueva o ampliada → checkpoint), en el mismo orden en que aparecen los Requirements 2-6 de `requirements.md` y los Componentes 1-5 de `design.md`, y cierra con una tarea final que ejecuta las cinco suites de pruebas con el intérprete de `sinergia/venv`.

Conforme a la sección "Testing Strategy" de `design.md` ("Por qué no se exigen pruebas basadas en propiedades (PBT)"), esta especificación NO requiere ninguna suite de pruebas basadas en propiedades (Hypothesis): el comportamiento de las cinco Ramas_STANDARD es una extensión directa y de bajo alcance combinatorio (cardinalidad exacta 1, comparabilidad de tipo, o un único ad set) de patrones ya cubiertos por propiedades en las especificaciones hermanas `meta-ads-standard-precheck-validation` y `meta-ads-standard-save-precheck-images`, tal como ya resuelve `requirements.md` en su propia sección "Property-Based Tests". Por esta razón, ninguna tarea de este plan referencia una Correctness Property de `design.md` como suite a implementar; las Properties 1-5 documentadas allí quedan únicamente con fines de trazabilidad.

Todas las tareas de prueba de este plan son de implementación obligatoria (no opcional): el Requirement 8 exige explícitamente la totalidad de los escenarios de prueba enumerados como criterios de aceptación mínimos de cada Suite_de_Pruebas, por lo que ninguna sub-tarea de prueba se marca con el postfijo `*`.

Archivos productivos afectados:
- `sinergia/app/v2/use_cases/meta_ads.py` (exclusivamente dentro del método `execute()` de cada una de las cinco clases y, para `FacebookSavePreCheckCTAsUseCase`, adicionalmente dentro del método privado nuevo `_validate_ctas_standard`)

Archivos de prueba afectados:
- `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py` (ampliado; ya existe)
- `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_ctas.py` (nuevo)
- `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_budget.py` (nuevo)
- `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_proposal_url.py` (nuevo)
- `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_locations.py` (nuevo)

## Tasks

- [x] 1. Implementar la Rama_STANDARD de Caso_de_Uso_Textos
  - [x] 1.1 Reemplazar el cuerpo `pass` del bloque `elif ... STANDARD.value and story_spec:` de `FacebookSavePreCheckTextsUseCase.execute()` en `sinergia/app/v2/use_cases/meta_ads.py` por la implementación inline descrita en el Componente 1 de `design.md`: reasignar `link_data = story_spec.get('link_data')` a un diccionario vacío nuevo cuando sea `None` (reasignado a `story_spec['link_data']`), y luego, para cada uno de title/body/description (mediante el bucle sobre tuplas `(candidates, link_key, valid_key, singular_type)` de `design.md`), anotar `link_data[valid_key] = False` sin invocar `MetaAdsValidator.is_valid_length` cuando `len(candidates) != 1`, o invocar `MetaAdsValidator.is_valid_length(singular_type, [text_item])` y anotar `link_data[valid_key]`/`link_data[link_key]` (este último solo si la validación resulta exitosa) cuando `len(candidates) == 1`
    - No invocar `MetaAdsValidator.is_unique_texts` ni `.is_valid_texts_amount` para esta rama
    - No introducir ningún método privado nuevo (permanece inline dentro de `execute()`)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.8_

- [x] 2. Ampliar Suite_de_Pruebas_Textos con la Rama_STANDARD
  - [x] 2.1 Añadir a `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py` el builder `make_link_data(**overrides)` (mismos campos por defecto en `None`: `name`, `message`, `description`, `image_url`, `link`, `call_to_action`), sin modificar ningún builder/fixture existente del archivo (`make_pre_check_texts_data`, `make_text_entry`, `make_ad_channel`, `make_campaign_setup`, `make_asset_feed_spec`, `make_object_story_spec`, `make_ad_creative`, `make_ad`, `make_creative`, `use_case_factory`, `patch_redis_client`, `patch_text_validators`, `deny_network`)
    - _Requirements: 8.1_
  - [x] 2.2 Reemplazar por completo la clase `TestStandardBranchNoOp` e implementar el escenario de éxito: Valor_Candidato == 1 con longitud válida, para cada uno de title/body/description (parametrizado o en pruebas separadas); verificar `link_data['name']/['message']/['description']` y `link_data['title_valid']/['body_valid']/['description_valid']` anotados
    - _Requirements: 2.2, 2.3, 2.7_
  - [x] 2.3 Implementar, parametrizado, el escenario de Valor_Candidato == 0 y Valor_Candidato > 1 (por campo): verificar `*_valid = False`, que `MetaAdsValidator.is_valid_length` no fue invocado para ese campo, y que `link_data['name']/['message']/['description']` no se modifica
    - _Requirements: 2.4_
  - [x] 2.4 Implementar el escenario de Valor_Candidato == 1 con longitud inválida (según `is_valid_length`): verificar `*_valid = False` y que `link_data['name']/['message']/['description']` NO se sobrescribe con el texto inválido
    - _Requirements: 2.8_
  - [x] 2.5 Implementar el escenario en el que `story_spec` carece de la clave `link_data`, o es `None`: verificar ausencia de excepción y que se crea/reasigna un `link_data` nuevo compartido por los tres campos
    - _Requirements: 2.5_
  - [x] 2.6 Implementar el escenario de `execute()` completo en modo STANDARD, sin parchear la lógica interna, verificando que la Respuesta_de_Precheck final refleja `titles`/`bodies`/`descriptions` conforme a las anotaciones esperadas
    - _Requirements: 8.3_
  - [x] 2.7 Añadir, sin modificar las aserciones de los escenarios de Rama_DYNAMIC ya existentes en el archivo, un escenario que confirme que la Rama_DYNAMIC de Caso_de_Uso_Textos continúa comportándose exactamente igual que antes de esta especificación, y otro que confirme que la lógica STANDARD no se ejecuta cuando `campaign_setup['attributes']['meta_campaign_mode']` es `"DYNAMIC"`
    - _Requirements: 7.1, 7.3, 7.4_
  - [x] 2.8 Implementar el escenario en el que se ejercita la validación real de longitud de texto (sin parchear `MetaAdsValidator.is_valid_length`), verificando ausencia de solicitudes HTTP reales mediante el mismo patrón de aislamiento de red ya usado por las suites existentes (`deny_network`)
    - _Requirements: 8.5_

- [x] 3. Checkpoint - Caso_de_Uso_Textos completo
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implementar la Rama_STANDARD de Caso_de_Uso_CTAs
  - [x] 4.1 Añadir el método privado nuevo `_validate_ctas_standard(self, link_data, objective, optimization_goal)` dentro de `FacebookSavePreCheckCTAsUseCase` en `sinergia/app/v2/use_cases/meta_ads.py`, conforme al Componente 2 de `design.md`: `len(self.call_to_action_types) == 0` elimina/omite `link_data['call_to_action']` (`link_data.pop('call_to_action', None)`) y retorna; `len(self.call_to_action_types) > 1` retorna sin tocar `link_data['call_to_action']`; `len(...) == 1` invoca `MetaAdsValidator.validate_cta_for_goal(cta_text=..., objective=objective, goal=optimization_goal, throw=False)` envuelto en `try/except Exception: valid_cta = False`, y anota `link_data['call_to_action'] = {'type': {'value': cta_value, 'valid': valid_cta}}`. Reemplazar el cuerpo `pass` del bloque `elif ... STANDARD.value and story_spec:` de `execute()` para leer `campaign_objective`/`optimization_goal` desde `campaign_setup.get('attributes', {})` (no desde `self.objective`/`self.optimization_goal`), crear/reasignar `link_data` cuando esté ausente/`None` (mismo patrón del Componente 1), e invocar `self._validate_ctas_standard(link_data, campaign_objective, optimization_goal)`
    - No invocar `MetaAdsValidator.is_valid_ctas_amount` para esta rama
    - El método privado nuevo se define exclusivamente dentro de `FacebookSavePreCheckCTAsUseCase`, nunca en `FacebookSavePreCheckBaseUseCase` ni en ninguna otra superclase
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 5. Crear Suite_de_Pruebas_CTAs (`test_facebook_save_pre_check_ctas.py`)
  - [x] 5.1 Crear `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_ctas.py`, replicando el estilo de builders/fixtures ya usado por `test_facebook_save_pre_check_texts.py`/`test_facebook_save_pre_check_images.py`: `make_pre_check_ctas_data`, `make_ad_channel`, `make_campaign_setup`, `make_asset_feed_spec`, `make_object_story_spec`, `make_link_data`, `make_ad_creative`, `make_ad`, `make_creative`, `use_case_factory`, `patch_redis_client`, `deny_network`
    - _Requirements: 8.2_
  - [x] 5.2 Implementar el escenario de un CTA_Candidato único (Valor_Candidato == 1) para el cual `MetaAdsValidator.validate_cta_for_goal` (ejercitado realmente o con retorno controlado mediante parcheo) resulta en `valid=True`: verificar que `link_data['call_to_action']` queda anotado como `{'type': {'value': ..., 'valid': True}}`
    - _Requirements: 3.2, 3.3_
  - [x] 5.3 Implementar el escenario análogo con `valid=False`: verificar la misma forma de anotación con `valid=False`
    - _Requirements: 3.2, 3.3_
  - [x] 5.4 Implementar, parametrizado, el escenario de Valor_Candidato == 0 (verificar que `link_data['call_to_action']` queda ausente/eliminado, sin invocar `validate_cta_for_goal`) y de Valor_Candidato > 1 (verificar que un valor previo de `link_data['call_to_action']` se preserva sin modificar, sin invocar `validate_cta_for_goal`)
    - _Requirements: 3.4_
  - [x] 5.5 Implementar el escenario en el que `story_spec` carece de la clave `link_data`, o es `None`: verificar ausencia de excepción y creación/reasignación de un `link_data` nuevo
    - _Requirements: 3.5_
  - [x] 5.6 Implementar el escenario de `execute()` completo en modo STANDARD, sin parchear `_validate_ctas_standard`, verificando que la Respuesta_de_Precheck final refleja `call_to_action_types` conforme a la anotación esperada
    - _Requirements: 8.3_
  - [x] 5.7 Implementar un escenario que confirme que la Rama_DYNAMIC de Caso_de_Uso_CTAs (`_validate_ctas`) continúa invocándose exactamente igual que antes de esta especificación, y otro que confirme que `_validate_ctas_standard` no se invoca cuando `campaign_setup['attributes']['meta_campaign_mode']` es `"DYNAMIC"`
    - _Requirements: 7.1, 7.3, 7.4_

- [x] 6. Checkpoint - Caso_de_Uso_CTAs completo
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implementar la Rama_STANDARD de Caso_de_Uso_Budget
  - [x] 7.1 Reemplazar el cuerpo `pass` del bloque `elif ... STANDARD.value and story_spec:` de `FacebookSavePreCheckBudgetUseCase.execute()` en `sinergia/app/v2/use_cases/meta_ads.py` por la implementación inline descrita en el Componente 3 de `design.md`: invocar `self._get_account_details()` y `self._get_minimum_budget(...)` exactamente una vez cada uno para calcular `min_budget`, anotar `story_spec['min_daily_budget'] = min_budget` incondicionalmente, y, únicamente cuando `isinstance(self.daily_budget, (int, float)) and not isinstance(self.daily_budget, bool)`, anotar `story_spec['daily_budget_valid'] = (self.daily_budget >= min_budget)` y `creative['daily_budget'] = self.daily_budget`
    - No introducir ningún método privado nuevo (permanece inline dentro de `execute()`)
    - El guard `isinstance` evita por completo la expresión que produciría `TypeError` para un `self.daily_budget` no numérico/`bool`, en lugar de capturarlo después de que ocurra, conforme a la nota de diseño del Componente 3
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 8. Crear Suite_de_Pruebas_Budget (`test_facebook_save_pre_check_budget.py`)
  - [x] 8.1 Crear `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_budget.py`, replicando el estilo de builders/fixtures ya usado por las suites hermanas: `make_pre_check_budget_data`, `make_ad_channel`, `make_campaign_setup`, `make_asset_feed_spec`, `make_object_story_spec`, `make_link_data`, `make_ad_creative`, `make_ad`, `make_creative`, `use_case_factory`, `patch_redis_client`, `deny_network`
    - _Requirements: 8.2_
  - [x] 8.2 Implementar el escenario en el que `self.daily_budget` es comparable y suficiente (`>= min_budget`): verificar `story_spec['daily_budget_valid'] is True`, `story_spec['min_daily_budget']` y `creative['daily_budget']`
    - _Requirements: 4.3_
  - [x] 8.3 Implementar el escenario en el que `self.daily_budget` es comparable e insuficiente (`< min_budget`): verificar `story_spec['daily_budget_valid'] is False`
    - _Requirements: 4.3_
  - [x] 8.4 Implementar el escenario en el que `self.daily_budget` no es comparable (por ejemplo `None`, o de tipo `bool`): verificar que `story_spec['daily_budget_valid']` queda sin anotar, sin lanzar una excepción no controlada, y que `story_spec['min_daily_budget']` sí se anota
    - _Requirements: 4.4_
  - [x] 8.5 Implementar el escenario en el que `Object_Story_Spec` está vacío o carece de valores previos: verificar ausencia de excepción no controlada
    - _Requirements: 4.5_
  - [x] 8.6 Implementar el escenario de `execute()` completo en modo STANDARD, verificando que la Respuesta_de_Precheck final refleja `daily_budget_valid` conforme a la anotación esperada
    - _Requirements: 8.3_
  - [x] 8.7 Implementar un escenario que confirme que la Rama_DYNAMIC de Caso_de_Uso_Budget continúa comportándose exactamente igual que antes de esta especificación, y otro que confirme que la lógica STANDARD no se ejecuta cuando `campaign_setup['attributes']['meta_campaign_mode']` es `"DYNAMIC"`
    - _Requirements: 7.1, 7.3, 7.4_

- [x] 9. Checkpoint - Caso_de_Uso_Budget completo
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implementar la Rama_STANDARD de Caso_de_Uso_URL
  - [x] 10.1 Reemplazar el cuerpo `pass` del bloque `elif ... STANDARD.value and story_spec:` de `FacebookSavePreCheckProposalURLUseCase.execute()` en `sinergia/app/v2/use_cases/meta_ads.py` por la implementación inline descrita en el Componente 4 de `design.md`: crear/reasignar `link_data` cuando esté ausente/`None` (mismo patrón del Componente 1), y, cuando `self.proposal_url` es truthy, anotar `link_data['link'] = self.proposal_url` e invocar `MetaAdsValidator.is_valid_link_url(self.proposal_url)` anotando su resultado en `link_data['link_url_valid']`; cuando `self.proposal_url` es falsy, anotar únicamente `link_data['link_url_valid'] = False` sin invocar `is_valid_link_url` ni modificar `link_data['link']`
    - No invocar `MetaAdsValidator.is_valid_proposal_url` (usar exclusivamente `is_valid_link_url`)
    - No introducir ningún método privado nuevo (permanece inline dentro de `execute()`)
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 11. Crear Suite_de_Pruebas_URL (`test_facebook_save_pre_check_proposal_url.py`)
  - [x] 11.1 Crear `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_proposal_url.py`, replicando el estilo de builders/fixtures ya usado por las suites hermanas: `make_pre_check_proposal_url_data`, `make_ad_channel`, `make_campaign_setup`, `make_asset_feed_spec`, `make_object_story_spec`, `make_link_data`, `make_ad_creative`, `make_ad`, `make_creative`, `use_case_factory`, `patch_redis_client`, `deny_network`
    - _Requirements: 8.2_
  - [x] 11.2 Implementar el escenario con URL_Candidata válida: verificar `link_data['link']` y `link_data['link_url_valid'] is True`
    - _Requirements: 5.1_
  - [x] 11.3 Implementar el escenario con URL_Candidata inválida (formato incorrecto conforme a `is_valid_link_url`): verificar `link_data['link']` y `link_data['link_url_valid'] is False`
    - _Requirements: 5.1_
  - [x] 11.4 Implementar el escenario con URL_Candidata ausente/falsy (`None` o cadena vacía): verificar `link_data['link_url_valid'] is False`, que `link_data['link']` no se modifica, y que `MetaAdsValidator.is_valid_link_url` no fue invocado
    - _Requirements: 5.2_
  - [x] 11.5 Implementar el escenario en el que `story_spec` carece de la clave `link_data`, o es `None`: verificar ausencia de excepción y creación/reasignación de un `link_data` nuevo
    - _Requirements: 5.3_
  - [x] 11.6 Implementar el escenario de `execute()` completo en modo STANDARD, verificando que la Respuesta_de_Precheck final refleja `proposal_url_valid` conforme a la anotación esperada
    - _Requirements: 8.3_
  - [x] 11.7 Implementar un escenario que confirme que la Rama_DYNAMIC de Caso_de_Uso_URL continúa comportándose exactamente igual que antes de esta especificación, y otro que confirme que la lógica STANDARD no se ejecuta cuando `campaign_setup['attributes']['meta_campaign_mode']` es `"DYNAMIC"`
    - _Requirements: 7.1, 7.3, 7.4_

- [x] 12. Checkpoint - Caso_de_Uso_URL completo
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Implementar la Rama_STANDARD de Caso_de_Uso_Locations
  - [x] 13.1 Reemplazar el cuerpo `pass` del bloque `elif ... STANDARD.value and story_spec:` de `FacebookSavePreCheckLocationsUseCase.execute()` en `sinergia/app/v2/use_cases/meta_ads.py` por la implementación inline descrita en el Componente 5 de `design.md`: invocar `geo_locations = self._build_geo_locations()` y asignar `creative['targeting']['geo_locations'] = geo_locations` **sin ningún `try/except` adicional** al ya existente en `execute()` (propagación deliberada de la misma excepción que ya propagaría hoy la Rama_DYNAMIC ante un `creative['targeting']` ausente o no-diccionario), y, únicamente si esa asignación no lanza, anotar a continuación `story_spec['locations'] = self.locations` y `story_spec['locations_valid'] = len(self.locations) > 0`, en ese orden
    - No introducir ningún método privado nuevo, ni ningún `try/except` que envuelva `creative['targeting']['geo_locations'] = geo_locations` (comportamiento de no-catch deliberado)
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 14. Crear Suite_de_Pruebas_Locations (`test_facebook_save_pre_check_locations.py`)
  - [x] 14.1 Crear `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_locations.py`, replicando el estilo de builders/fixtures ya usado por las suites hermanas: `make_pre_check_locations_data`, `make_ad_channel`, `make_campaign_setup`, `make_asset_feed_spec`, `make_object_story_spec`, `make_link_data`, `make_ad_creative`, `make_ad`, `make_creative`, `use_case_factory`, `patch_redis_client`, `deny_network`
    - _Requirements: 8.2_
  - [x] 14.2 Implementar el escenario con al menos una ubicación candidata: verificar `story_spec['locations_valid'] is True` y que `creative['targeting']['geo_locations']` refleja el resultado de `_build_geo_locations()`
    - _Requirements: 6.1, 6.2_
  - [x] 14.3 Implementar el escenario con cero ubicaciones candidatas: verificar `story_spec['locations_valid'] is False`
    - _Requirements: 6.1, 6.2_
  - [x] 14.4 Implementar el escenario en el que `creative` carece de la clave `targeting`, o su valor no es un diccionario: verificar que se propaga la misma excepción no controlada que ya propagaría hoy la Rama_DYNAMIC de este mismo Caso_de_Uso para ese escenario, y que `story_spec['locations']`/`['locations_valid']` no se anotan
    - _Requirements: 6.4_
  - [x] 14.5 Implementar el escenario de `execute()` completo en modo STANDARD, verificando que la Respuesta_de_Precheck final refleja `locations`/`locations_valid` conforme a la anotación esperada
    - _Requirements: 8.3_
  - [x] 14.6 Implementar un escenario que confirme que la Rama_DYNAMIC de Caso_de_Uso_Locations continúa comportándose exactamente igual que antes de esta especificación, y otro que confirme que la lógica STANDARD no se ejecuta cuando `campaign_setup['attributes']['meta_campaign_mode']` es `"DYNAMIC"`
    - _Requirements: 7.1, 7.3, 7.4_

- [x] 15. Checkpoint - Caso_de_Uso_Locations completo
  - Ensure all tests pass, ask the user if questions arise.

- [x] 16. Ejecución final de las cinco suites de pruebas
  - [x] 16.1 Ejecutar, desde `sinergia/` y con el intérprete de `sinergia/venv`, `./venv/bin/python -m pytest --collect-only -q` seguido de `./venv/bin/python -m pytest -q -ra` para cada uno de los cinco archivos (`test_facebook_save_pre_check_texts.py`, `test_facebook_save_pre_check_ctas.py`, `test_facebook_save_pre_check_budget.py`, `test_facebook_save_pre_check_proposal_url.py`, `test_facebook_save_pre_check_locations.py`), corrigiendo cualquier `failed`/`skipped`/error de recopilación encontrado hasta obtener cero en las tres categorías en cada archivo, sin modificar las aserciones de ninguna prueba de Rama_DYNAMIC ya existente distinta de la sustitución de `TestStandardBranchNoOp` (Requirement 2.7)
    - _Requirements: 8.10_

## Notes

- Ninguna sub-tarea de prueba está marcada con `*`: el Requirement 8 exige la totalidad de estos escenarios como criterios de aceptación mínimos obligatorios de cada Suite_de_Pruebas, no como cobertura opcional de MVP.
- Ninguna tarea de este plan implementa pruebas basadas en propiedades (Hypothesis): `design.md`/`requirements.md` ya deciden explícitamente que PBT no aplica a esta especificación; las Correctness Properties 1-5 de `design.md` quedan documentadas únicamente con fines de trazabilidad.
- Cada tarea referencia los Requirements/criterios de aceptación exactos que satisface.
- Las tareas 1, 4, 7, 10 y 13 modifican exclusivamente `sinergia/app/v2/use_cases/meta_ads.py`, cada una dentro del bloque `elif` de `execute()` de su propia subclase (y, para CTAs, adicionalmente dentro de `_validate_ctas_standard`, método nuevo definido solo en esa subclase); ninguna toca archivos de prueba ni el bloque `if ... DYNAMIC.value` de ninguna clase.
- Las tareas 2, 5, 8, 11 y 14 amplían/crean, cada una, un único archivo de prueba propio de su Caso_de_Uso; ningún archivo de prueba es compartido entre dos de estas tareas.
- Los checkpoints (tareas 3, 6, 9, 12 y 15) son puntos de sincronización, no tareas de código: por eso no aparecen en el Task Dependency Graph.
- La tarea 16 (ejecución final) depende de que todas las tareas de implementación y de prueba anteriores (1-2, 4-5, 7-8, 10-11, 13-14) estén completas.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "4.1"] },
    { "id": 2, "tasks": ["2.2", "5.1", "7.1"] },
    { "id": 3, "tasks": ["2.3", "5.2", "8.1", "10.1"] },
    { "id": 4, "tasks": ["2.4", "5.3", "8.2", "11.1", "13.1"] },
    { "id": 5, "tasks": ["2.5", "5.4", "8.3", "11.2", "14.1"] },
    { "id": 6, "tasks": ["2.6", "5.5", "8.4", "11.3", "14.2"] },
    { "id": 7, "tasks": ["2.7", "5.6", "8.5", "11.4", "14.3"] },
    { "id": 8, "tasks": ["2.8", "5.7", "8.6", "11.5", "14.4"] },
    { "id": 9, "tasks": ["8.7", "11.6", "14.5"] },
    { "id": 10, "tasks": ["11.7", "14.6"] },
    { "id": 11, "tasks": ["16.1"] }
  ]
}
```
