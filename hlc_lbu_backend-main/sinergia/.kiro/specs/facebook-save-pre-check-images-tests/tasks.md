# Implementation Plan: Facebook Save Pre-Check Images Tests

## Overview

Implementar en Python una suite pytest de caracterización para `FacebookSavePreCheckImagesUseCase` y el subconjunto heredado de `FacebookSavePreCheckBaseUseCase` (constructor, `_get_ad_channel`, `_get_campaign_setup`, `_set_channel_id`, `_build_response`) que esa subclase invoca. El archivo objetivo es `tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py`, dentro del proyecto `sinergia`, conforme a `sinergia/.kiro/steering/structure.md`. Todos los artefactos de esta especificación (`requirements.md`, `design.md`, este `tasks.md`) residen en `sinergia/.kiro/specs/facebook-save-pre-check-images-tests/`. La suite parcheará `AdChannelRepository`, `CampaignChannelPublishRepository` y `redis_client` sobre `app.v2.use_cases.meta_ads`, ejercitará el comportamiento real (sin parche) de `MetaAdsValidator.is_valid_images_amount`, parcheará únicamente `requests.get` en `app.v2.use_cases.facebook_validator_service` para aislar la red usada por `MetaAdsValidator.validate_images_precheck`, y no modificará ningún archivo de producción.

## Tasks

- [x] 1. Preparar builders y arnés local de la suite
  - [x] 1.1 Crear el módulo de pruebas y los builders de payload frescos
    - Crear `tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py`.
    - Implementar `make_pre_check_images_data`, `make_image_entry`, `make_ad_channel`, `make_campaign_setup`, `make_asset_feed_spec`, `make_object_story_spec`, `make_ad_creative`, `make_ad`, `make_creative`, usando un centinela privado `ABSENT` para distinguir campo omitido de campo presente con `None`.
    - Garantizar que cada invocación produce listas y diccionarios nuevos, sin defaults mutables compartidos entre pruebas.
    - _Requirements: 15.2, 15.3_

  - [x] 1.2 Implementar la fixture `use_case_factory` y los helpers de aislamiento/aserción
    - Implementar `use_case_factory` con `unittest.mock.patch` sobre `app.v2.use_cases.meta_ads.AdChannelRepository` y `app.v2.use_cases.meta_ads.CampaignChannelPublishRepository`, entregando `(use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance)` con una instancia nueva de `FacebookSavePreCheckImagesUseCase` por invocación, usando `make_pre_check_images_data()` cuando el llamador no provee `pre_check_images_data`.
    - Implementar `patch_redis_client` parcheando `app.v2.use_cases.meta_ads.redis_client`, exponiendo el `MagicMock` para configurar `.get.return_value`/`.get.side_effect`.
    - Implementar `patch_image_fetch` parcheando `app.v2.use_cases.facebook_validator_service.requests.get` (no `MetaAdsValidator`), configurable con una respuesta exitosa simulada o con un `side_effect` de `requests.exceptions.RequestException`.
    - Implementar el guard opcional `deny_network` (`autouse=True` de alcance función) que sustituya `requests.sessions.Session.request` por una función que lance `AssertionError`, como defensa adicional cuando `patch_image_fetch` no esté activo.
    - Implementar `assert_exception_type_and_message`, `assert_repository_called_once_with` y `assert_no_validator_calls`.
    - Verificar con una prueba de humo que construir el caso de uso y capturar las excepciones caracterizadas (`DataNotFoundException`, `NotAccessException`) con `text` explícito no requiere contexto Flask ni `tests/conftest.py`; si la ejecución demuestra lo contrario, detener la implementación y plantear el cambio de requisitos/diseño antes de añadir infraestructura Flask.
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

- [x] 2. Probar la construcción del Caso de Uso y el estado heredado
  - [x] 2.1 Probar atributos propios, defaults y Datos_de_Campaña_Vacíos
    - Verificar `adset_id`, `ad_id`, `adchannel_id`, `images`, `bodies`, `titles`, `descriptions`, `call_to_action_types`, `locations` asignados exactamente desde Datos_de_Precheck completos.
    - Verificar los defaults `daily_budget=0`, `proposal_url=''`, y lista vacía nueva para cada colección omitida.
    - Verificar `campaign_id`/`user_id` propagados correctamente hacia el Caso_de_Uso_Bisabuelo.
    - Verificar que `ad_account_id`, `page_id`, `objective`, `optimization_goal`, `lead_gen_form_id`, `whatsapp_number_id`, `billing_event`, `channel_id` quedan todos en `None` sin excepción, caracterizando Datos_de_Campaña_Vacíos (`{}`).
    - Verificar que el Repositorio_de_Canal y el Repositorio_de_Publicación parcheados se instancian exactamente una vez cada uno.
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_

  - [x] 2.2 Probar el `AttributeError` explícito y el default mutable de la firma
    - Construir `FacebookSavePreCheckImagesUseCase` directamente (sin la fixture `use_case_factory`, parcheando los repositorios de forma inline) con `pre_check_images_data=None` explícito y comprobar que se propaga `AttributeError` al invocar `None.get('campaign_id')`.
    - Construir dos instancias de `FacebookSavePreCheckBaseUseCase` sin proveer `pre_check_data` en ninguna de las dos invocaciones (parcheando los repositorios de forma inline), mutar `images` de la primera, y verificar si la segunda refleja o no ese cambio, documentando el resultado observado en un comentario junto a la aserción, sin proponer corrección.
    - _Requirements: 2.9, 2.10_

- [x] 3. Probar `_get_ad_channel`
  - [x] 3.1 Probar la llamada exacta, la identidad, el `DataNotFoundException` y el cortocircuito
    - Verificar la llamada exacta `ad_channel_repository.get_by_campaign_and_ad_channel_id(self.campaign_id, self.adset_id, self.ad_id, self.adchannel_id)`.
    - Verificar identidad del Ad_Channel retornado cuando es verdadero.
    - Verificar `DataNotFoundException` con mensaje exacto `"Creative not found!"` cuando el repositorio devuelve `None`/`{}`.
    - Verificar, dentro de `execute()`, que un Ad_Channel ausente propaga la excepción sin invocar `_set_channel_id`, `campaign_publish_repository.get_by_campaign_id_and_channel_id`, ni `ad_channel_repository.update`.
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Probar `_get_campaign_setup`
  - [x] 4.1 Probar la llamada exacta, la identidad, el mensaje interpolado y el cortocircuito
    - Verificar la llamada exacta `campaign_publish_repository.get_by_campaign_id_and_channel_id(self.campaign_id, self.channel_id)`.
    - Verificar identidad del Campaign_Setup retornado cuando es verdadero.
    - Verificar `DataNotFoundException` con el mensaje exacto `f"Campaign Setup not found for campaign_id: {self.campaign_id} and channel_id: {self.channel_id}"` cuando el repositorio devuelve un valor falsy.
    - Verificar, dentro de `execute()`, que un Campaign_Setup ausente propaga la excepción sin invocar los validadores ni `ad_channel_repository.update`, pero después de que `_get_ad_channel` y `_set_channel_id` ya se ejecutaron.
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 5. Probar `_set_channel_id`
  - [x] 5.1 Probar la extracción anidada, los defaults por nivel y el orden dentro de `execute()`
    - Verificar la asignación exacta de `self.channel_id` cuando `attributes.channel_ref.data.id` está presente con valor verdadero.
    - Parametrizar la ausencia de cada una de las claves `attributes`, `channel_ref`, `data`, `id` por separado, verificando que `self.channel_id` queda en `0` sin excepción en cada caso.
    - Verificar, dentro de `execute()`, que `_set_channel_id` ocurre después de `_get_ad_channel` y antes de `_get_campaign_setup`, de forma que el `channel_id` usado por `_get_campaign_setup` sea el recién asignado.
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 6. Probar la orquestación de `execute()` y el cortocircuito ante fallos
  - [x] 6.1 Probar el orden completo y los cuatro escenarios de cortocircuito
    - Verificar el orden exacto: `_get_decoded_access_token`, `_get_ad_channel`, `_set_channel_id`, extracción de `creative`, `_get_campaign_setup`, bloque de validación condicional, `_save_creative_to_publish`, `_build_response`.
    - Verificar `NotAccessException` cuando el Cliente_Redis devuelve un valor falsy, sin invocar `_get_ad_channel`, `_get_campaign_setup`, ninguna validación de imágenes, ni `_save_creative_to_publish`.
    - Verificar que un `DataNotFoundException` de `_get_ad_channel` impide invocar `_save_creative_to_publish` y `_build_response`.
    - Verificar que un `DataNotFoundException` de `_get_campaign_setup` impide invocar `_save_creative_to_publish` y `_build_response`, confirmando que la extracción de `creative`/`asset_feed`/`story_spec` sí ocurrió antes.
    - Verificar que, al completar sin excepción, `execute()` invoca `_save_creative_to_publish` y luego `_build_response`, ambos con el mismo objeto `creative` por identidad, y retorna exactamente el resultado de `_build_response` por identidad.
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Ejecutar `./venv/bin/python -m pytest --collect-only -q tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py` y `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py` desde `sinergia/`, sin modo watch ni interactivo.

- [x] 8. Probar la rama DYNAMIC — validación de imágenes
  - [x] 8.1 Probar la invocación, la sobreescritura de `images` y la asignación de `images_valid_amount`
    - Verificar que `_validate_images_dynamic` es invocado con `asset_feed` por identidad cuando `meta_campaign_mode="DYNAMIC"` y `asset_feed` es verdadero.
    - Verificar la llamada exacta a `MetaAdsValidator.validate_images_precheck(self.images)` por identidad de lista, sin permitir una solicitud HTTP real.
    - Verificar que `asset_feed['images']` queda sobreescrito exactamente con `self.images` por identidad, incluso cuando `asset_feed['images']` tenía previamente un valor distinto.
    - Verificar la llamada exacta a `MetaAdsValidator.is_valid_images_amount(self.images)` y la asignación exacta de `asset_feed['images_valid_amount']` con el valor booleano retornado.
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 8.2 Probar la matriz real de límites 0/10/11 de `is_valid_images_amount`
    - Parametrizar `self.images` con 0, 10 y 11 entradas mínimas (por ejemplo `[{} for _ in range(n)]`), usando la implementación real sin parche, y verificar `asset_feed['images_valid_amount']` en `False`, `True`, `False` respectivamente.
    - _Requirements: 7.5, 7.6, 7.7_

  - [x] 8.3 Probar `url` ausente sin red, el fallo de red simulado y la continuación hacia persistencia/respuesta
    - Verificar, con entradas de `self.images` sin `url`, que no se dispara una solicitud HTTP y que el bucle continúa sin agregar `valid`/`error` a esas entradas, usando el comportamiento real de `validate_images_precheck`.
    - Activar `patch_image_fetch` con `side_effect` de `requests.exceptions.RequestException` sobre `app.v2.use_cases.facebook_validator_service.requests.get`, con una entrada de `self.images` que tenga `url` verdadero, y verificar que dicha entrada queda mutada in-place con `valid=False`/`error="Could not fetch image"`, sin que `_validate_images_dynamic` ni `execute()` propaguen excepción.
    - Verificar que, tras `_validate_images_dynamic` exitoso, `execute()` continúa hacia `_save_creative_to_publish`/`_build_response` sin interrupción y que la Respuesta_de_Precheck se construye a partir del `asset_feed` ya mutado.
    - _Requirements: 7.8, 7.9, 7.10_

  - [x] 8.4 Escribir la property test opcional para `is_valid_images_amount`
    - **Property 1: `is_valid_images_amount` es verdadero si y solo si la cantidad de imágenes está en [1, 10]**
    - **Validates: Requirements 7.5, 7.6, 7.7**
    - Implementar con `hypothesis==6.112.2`, `@settings(max_examples=100, deadline=None)`, generando listas de 0 a 20 elementos de contenido irrelevante, comparando `is_valid_images_amount(images) == (1 <= len(images) <= 10)`.
    - Declarar en el comentario del test: `Feature: facebook-save-pre-check-images-tests, Property 1: is_valid_images_amount es verdadero si y solo si la cantidad de imágenes está en [1, 10]`.
    - Esta tarea es opcional y no obligatoria para la especificación (ver design.md → Correctness Properties); la matriz de la tarea 8.2 ya cubre los mismos requisitos con ejemplos concretos.

- [x] 9. Probar la rama DYNAMIC con `asset_feed` ausente, `None` o `{}`
  - [x] 9.1 Probar la no invocación de validadores y la continuación sin error
    - Verificar, con `asset_feed=None`, que `_validate_images_dynamic` no se invoca, que ninguno de los dos validadores se invoca, y que `execute()` continúa sin error hacia `_save_creative_to_publish`/`_build_response`.
    - Verificar el mismo resultado con `asset_feed={}}`.
    - Verificar el mismo resultado cuando la clave `asset_feed_spec` está completamente ausente en `ad_creative` (produciendo `None` por el `.get('asset_feed_spec')` sin default).
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 10. Probar la rama STANDARD — no-op de validación de imágenes
  - [x] 10.1 Probar la invocación, el no-op verificado y la continuación
    - Verificar que `_validate_images_standard` es invocado con `story_spec` por identidad cuando `meta_campaign_mode="STANDARD"` y `story_spec` es verdadero.
    - Verificar que ningún validador de `MetaAdsValidator` se invoca y que `story_spec` no recibe ninguna clave nueva.
    - Verificar que `execute()` continúa sin error hacia `_save_creative_to_publish`/`_build_response`, y que la Respuesta_de_Precheck no refleja ninguna validación de imágenes aplicada.
    - Verificar que, con `story_spec` falsy (`None` o `{}}`), `_validate_images_standard` no se invoca y `execute()` continúa sin error.
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 11. Probar `meta_campaign_mode` desconocido
  - [x] 11.1 Probar la ausencia de ambas ramas y la continuación sin mutación
    - Parametrizar `meta_campaign_mode` con cadena vacía, `None`, un valor arbitrario distinto de `"DYNAMIC"`/`"STANDARD"`, y la clave completamente ausente; verificar que ni `_validate_images_dynamic` ni `_validate_images_standard` se invocan, independientemente de si `asset_feed`/`story_spec` son verdaderos o falsy.
    - Verificar que `execute()` continúa directamente hacia `_save_creative_to_publish`/`_build_response` sin ninguna mutación de `asset_feed_spec`/`object_story_spec`.
    - _Requirements: 10.1, 10.2_

- [x] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Ejecutar `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py` desde `sinergia/`, sin modo watch ni interactivo.

- [x] 13. Probar las estructuras `creative`/`ads`/`adCreative` malformadas
  - [x] 13.1 Implementar la matriz de 4 niveles del bloque de validación
    - Verificar `IndexError` en `creative.get('ads', [])[0]` cuando `ads` está ausente o es una lista vacía, confirmando qué dobles ya fueron invocados antes de la excepción según el orden real del código.
    - Verificar `AttributeError` al invocar `.get('asset_feed_spec')`/`.get('object_story_spec')` sobre `None` cuando `adCreative` está presente con valor `None` explícito, antes de `_save_creative_to_publish`.
    - Verificar la ausencia de excepción cuando `adCreative={}}`: `asset_feed`/`story_spec` quedan en `None`, ninguna rama de validación se ejecuta, y `execute()` continúa hacia `_save_creative_to_publish`/`_build_response`.
    - Verificar el mismo resultado que el caso anterior cuando la clave `adCreative` está completamente ausente en `creative['ads'][0]`.
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [x] 14. Probar el pass-through del bloque `try/except Exception as e: raise e`
  - [x] 14.1 Probar la equivalencia de tipo y mensaje end-to-end
    - Reutilizar el escenario de `AttributeError` de la tarea 13.1 (Requirement 11.2) para verificar, desde `execute()`, que el tipo y el mensaje (`str(exception)`) observados son idénticos a los de la excepción originada dentro del bloque `try`.
    - Documentar en el docstring o comentario de la prueba por qué este resultado es equivalente al comportamiento que se observaría si el bloque `try/except` no existiera, a diferencia de un patrón de envoltura que sí alteraría el tipo.
    - _Requirements: 12.1, 12.2_

- [x] 15. Probar `_save_creative_to_publish`
  - [x] 15.1 Probar la llamada exacta, los defaults por nivel y la invocación aislada con `TypeError`
    - Verificar la llamada exacta `ad_channel_repository.update(ad_channel_id, {'channel_creative': creative})`, con `creative` por identidad y `ad_channel_id` extraído de `creative.get('ads')[0].get('adCreative', {}).get('asset_feed_spec', {}).get('ad_channel_id', 0)`.
    - Verificar que un valor verdadero de `asset_feed_spec['ad_channel_id']` se usa exactamente como primer argumento.
    - Parametrizar la ausencia de `adCreative`, `asset_feed_spec` o `ad_channel_id` por separado (con `creative['ads']` no vacía), verificando el default `0` en cada caso.
    - Invocar `_save_creative_to_publish` directamente y de forma aislada (sin pasar por `execute()`) con un `creative` cuya clave `ads` está ausente, verificando que se propaga `TypeError`, y documentar en el comentario por qué este camino no es alcanzable desde `execute()` (el bloque de validación previo ya habría lanzado `IndexError` para el mismo `creative`, Requirement 11.1).
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

- [x] 16. Probar `_build_response`
  - [x] 16.1 Probar las claves completas, los valores reflejados, los defaults y la unión de `link_urls`
    - Verificar que la Respuesta_de_Precheck contiene exactamente las claves listadas en el Requirement 14.1, sin adicionales ni faltantes.
    - Verificar el reflejo exacto de valores explícitos de `asset_feed_spec`, incluida la proyección de `images` a `[{'url', 'valid', 'error'}]`.
    - Verificar los defaults exactos por campo omitido (`False` para los cinco `*_valid_amount`, `0` para los cinco `*_max_amount`, `False`/`0`/`[]` según corresponda).
    - Verificar la unión por comas (`','.join(...)`) de `link_urls` para `proposal_url`, en el mismo orden.
    - Verificar que `proposal_locations` es `[]` cuando `creative` omite esa clave.
    - Verificar, en un escenario completo de `execute()` en rama DYNAMIC, que la Respuesta_de_Precheck refleja los valores `valid`/`error` ya mutados por `_validate_images_dynamic`.
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

  - [x] 16.2 Probar las invocaciones aisladas que exponen `AttributeError`
    - Invocar `_build_response` directamente sobre una instancia construida vía `use_case_factory`, sin pasar por `execute()`, con `creative['ads'][0]['adCreative']=None` explícito, verificando `AttributeError` al invocar `.get('asset_feed_spec', {})` sobre `None`.
    - Invocar `_build_response` de la misma forma con la clave `adCreative` completamente ausente en `ads_to_publish`, verificando el mismo `AttributeError`.
    - Documentar en el comentario de cada prueba por qué este escenario no es alcanzable de forma natural desde `execute()` con un `creative` construido consistentemente.
    - _Requirements: 14.7, 14.8_

- [x] 17. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Ejecutar `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py` desde `sinergia/`, sin servidor, watcher ni modo interactivo.

- [x] 18. Validar colección, aislamiento y repetibilidad de la suite
  - [x] 18.1 Ejecutar la validación pytest completa y corregir únicamente el código de pruebas
    - Ejecutar `./venv/bin/python -m pytest --collect-only -q tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py`.
    - Ejecutar `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py` y exigir cero `failed`, cero `skipped` y cero errores.
    - Repetir con `PYTHONHASHSEED=1` y `PYTHONHASHSEED=777` usando el mismo comando no interactivo para detectar estado compartido u orden accidental.
    - Confirmar que el guard de red (`deny_network`) no detecta ninguna fuga, que no se creó infraestructura Flask ni `tests/conftest.py`, y que `app/v2/use_cases/meta_ads.py`, `app/v2/use_cases/facebook_validator_service.py`, `app/v2/repository/ad_channel.py`, `app/v2/repository/campaign_channel_publish.py` y el resto de producción permanecen sin cambios.
    - _Requirements: 1.1, 1.4, 1.5, 1.6, 1.7, 15.1, 15.4, 15.5, 15.6, 15.7_

- [x] 19. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tarea 8.4 lleva `*` porque la property test es opcional según `design.md`/`requirements.md` (Testing Strategy → Property-Based Tests); todas las demás tareas de prueba no llevan `*` porque la suite pytest es el entregable principal de esta feature.
- No se debe modificar `app/v2/use_cases/meta_ads.py`, `app/v2/use_cases/facebook_validator_service.py`, `app/v2/repository/ad_channel.py`, `app/v2/repository/campaign_channel_publish.py`, ningún otro archivo de producción, `requirements.md` ni `design.md`.
- Toda la suite reside en `tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py`, dentro del proyecto `sinergia`, conforme a `sinergia/.kiro/steering/structure.md`; todos los artefactos de esta especificación residen en `sinergia/.kiro/specs/facebook-save-pre-check-images-tests/`.
- No se debe crear `tests/conftest.py` ni una aplicación/contexto Flask salvo que la implementación demuestre una dependencia real; en ese caso, se debe detener y replantear con el usuario antes de añadir infraestructura.
- Datos_de_Campaña_Vacíos (`complete_campaign_data={}` siempre), el default mutable `pre_check_data: PreCheckDataDict = {}`, las asimetrías `.get(..., {})`/`.get(...)` sin default entre `execute()`, `_save_creative_to_publish` y `_build_response`, y el pass-through `try/except Exception as e: raise e` se caracterizan como comportamiento actual; no se corrigen.
- `MetaAdsValidator.is_valid_images_amount` nunca se parchea; solo se parchea `requests.get` en `app.v2.use_cases.facebook_validator_service` para aislar la red usada por `validate_images_precheck`.
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
    { "id": 5, "tasks": ["4.1"] },
    { "id": 6, "tasks": ["5.1"] },
    { "id": 7, "tasks": ["6.1"] },
    { "id": 8, "tasks": ["8.1"] },
    { "id": 9, "tasks": ["8.2"] },
    { "id": 10, "tasks": ["8.3"] },
    { "id": 11, "tasks": ["8.4"] },
    { "id": 12, "tasks": ["9.1"] },
    { "id": 13, "tasks": ["10.1"] },
    { "id": 14, "tasks": ["11.1"] },
    { "id": 15, "tasks": ["13.1"] },
    { "id": 16, "tasks": ["14.1"] },
    { "id": 17, "tasks": ["15.1"] },
    { "id": 18, "tasks": ["16.1"] },
    { "id": 19, "tasks": ["16.2"] },
    { "id": 20, "tasks": ["18.1"] }
  ]
}
```
