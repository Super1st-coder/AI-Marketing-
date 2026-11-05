# Implementation Plan: Facebook Save Pre-Check Texts Tests

## Overview

Implementar en Python una suite pytest de caracterización para `FacebookSavePreCheckTextsUseCase` y el subconjunto heredado de `FacebookSavePreCheckBaseUseCase` (constructor, `_get_ad_channel`, `_get_campaign_setup`, `_set_channel_id`, `_build_response`) que esa subclase invoca. El archivo objetivo es `tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py`, dentro del proyecto `sinergia`, conforme a `sinergia/.kiro/steering/structure.md`. Todos los artefactos de esta especificación (`requirements.md`, `design.md`, este `tasks.md`) residen en `sinergia/.kiro/specs/facebook-save-pre-check-texts-tests/`. La suite parcheará `AdChannelRepository`, `CampaignChannelPublishRepository` y `redis_client` sobre `app.v2.use_cases.meta_ads`, ejercitará el comportamiento real (sin parche) de `MetaAdsValidator.is_unique_texts`, `is_valid_length` e `is_valid_texts_amount` (ninguno realiza solicitudes de red), y no modificará ningún archivo de producción. A diferencia de la suite hermana de imágenes, esta clase no tiene métodos `_validate_texts_dynamic`/`_validate_texts_standard` propios: toda la validación DYNAMIC está inline en `execute()` y la rama STANDARD es un `pass` explícito, por lo que los escenarios de validación de texto se ejercitan siempre a través de `execute()` completo.

## Tasks

- [x] 1. Preparar builders y arnés local de la suite
  - [x] 1.1 Crear el módulo de pruebas y los builders de payload frescos
    - Crear `tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py`.
    - Implementar `make_pre_check_texts_data`, `make_text_entry`, `make_ad_channel`, `make_campaign_setup`, `make_asset_feed_spec`, `make_object_story_spec`, `make_ad_creative`, `make_ad`, `make_creative`, usando un centinela privado `ABSENT` para distinguir campo omitido de campo presente con `None`.
    - Garantizar que cada invocación produce listas y diccionarios nuevos, sin defaults mutables compartidos entre pruebas.
    - _Requirements: 18.2, 18.3_

  - [x] 1.2 Implementar la fixture `use_case_factory` y los helpers de aislamiento/aserción
    - Implementar `use_case_factory` con `unittest.mock.patch` sobre `app.v2.use_cases.meta_ads.AdChannelRepository` y `app.v2.use_cases.meta_ads.CampaignChannelPublishRepository`, entregando `(use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance)` con una instancia nueva de `FacebookSavePreCheckTextsUseCase` por invocación, usando `make_pre_check_texts_data()` cuando el llamador no provee `pre_check_texts_data`.
    - Implementar `patch_redis_client` parcheando `app.v2.use_cases.meta_ads.redis_client`, exponiendo el `MagicMock` para configurar `.get.return_value`/`.get.side_effect`.
    - Implementar `patch_text_validators`, un context manager/fixture que envuelve `app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts`, `.is_valid_length` e `.is_valid_texts_amount` con dobles que delegan a la implementación real (`Mock(wraps=...)`) mientras registran en una lista compartida `call_order` cada invocación con su nombre de método y argumentos, para verificar orden exacto sin alterar el comportamiento real.
    - Implementar el guard opcional `deny_network` (`autouse=True` de alcance función) que sustituya `requests.sessions.Session.request` por una función que lance `AssertionError`, como defensa adicional aunque ninguna ruta de código alcanzable por esta clase realiza solicitudes de red.
    - Implementar `assert_exception_type_and_message`, `assert_repository_called_once_with` y `assert_no_text_validator_calls`.
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
    - Construir `FacebookSavePreCheckTextsUseCase` directamente (sin la fixture `use_case_factory`, parcheando los repositorios de forma inline) con `pre_check_texts_data=None` explícito y comprobar que se propaga `AttributeError` al invocar `None.get('campaign_id')`.
    - Construir dos instancias de `FacebookSavePreCheckBaseUseCase` sin proveer `pre_check_data` en ninguna de las dos invocaciones (parcheando los repositorios de forma inline), mutar `titles` de la primera, y verificar si la segunda refleja o no ese cambio, documentando el resultado observado en un comentario junto a la aserción, sin proponer corrección.
    - _Requirements: 2.9, 2.10_

- [x] 3. Probar `_get_ad_channel`
  - [x] 3.1 Probar la llamada exacta, la identidad, el `DataNotFoundException` y el cortocircuito
    - Verificar la llamada exacta `ad_channel_repository.get_by_campaign_and_ad_channel_id(self.campaign_id, self.adset_id, self.ad_id, self.adchannel_id)`.
    - Verificar identidad del Ad_Channel retornado cuando es verdadero.
    - Verificar `DataNotFoundException` con mensaje exacto `"Creative not found!"` cuando el repositorio devuelve `None`/`{}`.
    - Verificar, dentro de `execute()`, que un Ad_Channel ausente propaga la excepción sin invocar `_set_channel_id`, `campaign_publish_repository.get_by_campaign_id_and_channel_id`, ninguno de los tres métodos de `Validador_Meta`, ni `ad_channel_repository.update`.
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Probar `_get_campaign_setup`
  - [x] 4.1 Probar la llamada exacta, la identidad, el mensaje interpolado y el cortocircuito
    - Verificar la llamada exacta `campaign_publish_repository.get_by_campaign_id_and_channel_id(self.campaign_id, self.channel_id)`.
    - Verificar identidad del Campaign_Setup retornado cuando es verdadero.
    - Verificar `DataNotFoundException` con el mensaje exacto `f"Campaign Setup not found for campaign_id: {self.campaign_id} and channel_id: {self.channel_id}"` cuando el repositorio devuelve un valor falsy.
    - Verificar, dentro de `execute()`, que un Campaign_Setup ausente propaga la excepción sin invocar ninguno de los tres métodos de `Validador_Meta` ni `ad_channel_repository.update`, pero después de que `_get_ad_channel` y `_set_channel_id` ya se ejecutaron.
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
    - Verificar `NotAccessException` cuando el Cliente_Redis devuelve un valor falsy, sin invocar `_get_ad_channel`, `_get_campaign_setup`, ninguna validación de textos, ni `_save_creative_to_publish`.
    - Verificar que un `DataNotFoundException` de `_get_ad_channel` impide invocar `_save_creative_to_publish` y `_build_response`.
    - Verificar que un `DataNotFoundException` de `_get_campaign_setup` impide invocar `_save_creative_to_publish` y `_build_response`, confirmando que la extracción de `creative`/`asset_feed`/`story_spec` sí ocurrió antes.
    - Verificar que, al completar sin excepción, `execute()` invoca `_save_creative_to_publish` y luego `_build_response`, ambos con el mismo objeto `creative` por identidad, y retorna exactamente el resultado de `_build_response` por identidad.
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Ejecutar `./venv/bin/python -m pytest --collect-only -q tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py` y `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py` desde `sinergia/`, sin modo watch ni interactivo.

- [x] 8. Probar la rama DYNAMIC — validación de Textos_de_Título
  - [x] 8.1 Probar las tres llamadas exactas y la sobreescritura de `titles`
    - Verificar, ejercitando `execute()` completo con `meta_campaign_mode="DYNAMIC"` y `asset_feed` verdadero, que `MetaAdsValidator.is_unique_texts` se invoca con `[t.get('text') for t in self.titles]` y que `asset_feed['unique_titles']` queda asignado con el valor booleano retornado, usando el comportamiento real.
    - Verificar que `MetaAdsValidator.is_valid_length` se invoca con los argumentos exactos `('titles', self.titles)`, que su valor de retorno se descarta, y que cada elemento de `self.titles` queda mutado in-place con `valid_length` según el máximo de 255 caracteres.
    - Verificar que `MetaAdsValidator.is_valid_texts_amount` se invoca con los argumentos exactos `('titles', self.titles)` y que `asset_feed['titles_valid_amount']` queda asignado con el valor booleano retornado.
    - Verificar que `asset_feed['titles']` queda sobreescrito exactamente con `self.titles` por identidad, incluso si `asset_feed['titles']` tenía previamente un valor distinto.
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 8.2 Probar la matriz real de límites 0/5/6 de `is_valid_texts_amount` para `titles`
    - Parametrizar `self.titles` con 0, 5 y 6 entradas con `text` único y no vacío, usando la implementación real sin parche, y verificar `asset_feed['titles_valid_amount']` en `False`, `True`, `False` respectivamente.
    - _Requirements: 7.5, 7.6, 7.7_

  - [x] 8.3 Probar unicidad, texto ausente/vacío y longitud excedida para `titles`
    - Verificar, con dos entradas de `text` idéntico (verdadero, no vacío) en `self.titles`, que `asset_feed['unique_titles']` queda en `False` usando el comportamiento real de `is_unique_texts`.
    - Verificar, con `self.titles` vacía o con entradas cuyo `text` es `None`/`""` mezcladas con entradas únicas, que dichas entradas se filtran de la comparación de unicidad sin propagar excepción, y que el resultado de `is_unique_texts` es `True` cuando no quedan duplicados verdaderos tras el filtrado.
    - Verificar, con una entrada de `self.titles` cuyo `text` excede 255 caracteres, que dicha entrada queda mutada in-place con `valid_length=False`; y con una entrada de longitud entre 1 y 255, que queda con `valid_length=True`; y con una entrada de `text` ausente o vacío, que queda con `valid_length=False`.
    - _Requirements: 7.8, 7.9, 7.10_

- [x] 9. Probar la rama DYNAMIC — validación de Textos_de_Cuerpo
  - [x] 9.1 Probar las tres llamadas exactas, la sobreescritura de `bodies` y el límite de longitud 1024
    - Verificar que `MetaAdsValidator.is_unique_texts` se invoca con `[t.get('text') for t in self.bodies]` y que `asset_feed['unique_bodies']` queda asignado con el valor booleano retornado.
    - Verificar que `MetaAdsValidator.is_valid_length` se invoca con los argumentos exactos `('bodies', self.bodies)`, y que cada elemento de `self.bodies` queda mutado in-place con `valid_length` según el máximo de 1024 caracteres (distinto del máximo de 255 de `titles`/`descriptions`).
    - Verificar que `MetaAdsValidator.is_valid_texts_amount` se invoca con los argumentos exactos `('bodies', self.bodies)` y que `asset_feed['bodies_valid_amount']` queda asignado con el valor booleano retornado.
    - Verificar que `asset_feed['bodies']` queda sobreescrito exactamente con `self.bodies` por identidad, incluso si `asset_feed['bodies']` tenía previamente un valor distinto.
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 9.2 Probar la matriz real de límites 0/5/6 y el contraste de longitud 255 vs 1024
    - Parametrizar `self.bodies` con 0, 5 y 6 entradas con `text` único y no vacío, y verificar `asset_feed['bodies_valid_amount']` en `False`, `True`, `False` respectivamente, usando la implementación real.
    - Construir un texto de longitud aproximada de 300 caracteres y ejercitar dos escenarios `execute()` independientes: uno con ese texto en `self.titles` (verificar `valid_length=False`, excede 255) y otro con ese mismo texto en `self.bodies` (verificar `valid_length=True`, dentro de 1024), demostrando el límite distinto documentado en `design.md`.
    - Verificar, con una entrada de `self.bodies` cuyo `text` excede 1024 caracteres, que dicha entrada queda mutada in-place con `valid_length=False`.
    - _Requirements: 8.5, 8.6_

- [x] 10. Probar la rama DYNAMIC — validación de Textos_de_Descripción
  - [x] 10.1 Probar las tres llamadas exactas, la sobreescritura de `descriptions` y la matriz real de límites 0/5/6
    - Verificar que `MetaAdsValidator.is_unique_texts` se invoca con `[t.get('text') for t in self.descriptions]` y que `asset_feed['unique_descriptions']` queda asignado con el valor booleano retornado.
    - Verificar que `MetaAdsValidator.is_valid_length` se invoca con los argumentos exactos `('descriptions', self.descriptions)`, y que cada elemento de `self.descriptions` queda mutado in-place con `valid_length` según el máximo de 255 caracteres.
    - Verificar que `MetaAdsValidator.is_valid_texts_amount` se invoca con los argumentos exactos `('descriptions', self.descriptions)` y que `asset_feed['descriptions_valid_amount']` queda asignado con el valor booleano retornado.
    - Verificar que `asset_feed['descriptions']` queda sobreescrito exactamente con `self.descriptions` por identidad, incluso si `asset_feed['descriptions']` tenía previamente un valor distinto.
    - Parametrizar `self.descriptions` con 0, 5 y 6 entradas, verificando `asset_feed['descriptions_valid_amount']` en `False`, `True`, `False` respectivamente, usando la implementación real.
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 11. Probar el orden exacto entre los tres campos y la continuación tras la validación DYNAMIC
  - [x] 11.1 Probar el registro de orden de las 9 llamadas y la continuación hacia persistencia/respuesta
    - Usando `patch_text_validators`, ejecutar `execute()` con `titles`, `bodies` y `descriptions` no vacíos y `asset_feed` verdadero en modo DYNAMIC, y verificar que el registro de orden contiene exactamente la secuencia de 9 tuplas en el orden: `is_unique_texts(titles)`, `is_valid_length('titles', ...)`, `is_valid_texts_amount('titles', ...)`, `is_unique_texts(bodies)`, `is_valid_length('bodies', ...)`, `is_valid_texts_amount('bodies', ...)`, `is_unique_texts(descriptions)`, `is_valid_length('descriptions', ...)`, `is_valid_texts_amount('descriptions', ...)`.
    - Verificar que, tras completar la validación de los tres campos, `execute()` continúa hacia `_save_creative_to_publish`/`_build_response` sin interrupción, y que la Respuesta_de_Precheck resultante refleja los nueve valores asignados sobre `asset_feed` ya mutado.
    - _Requirements: 10.1, 10.2_

  - [x] 11.2 Escribir las property tests opcionales para `is_valid_texts_amount` e `is_unique_texts`
    - **Property 1: `is_valid_texts_amount` es verdadero si y solo si la cantidad de textos está en [1, 5]**
    - **Validates: Requirements 7.5, 7.6, 7.7, 8.5, 9.5**
    - Implementar con `hypothesis==6.112.2`, `@settings(max_examples=100, deadline=None)`, generando `type` en `{"titles", "bodies", "descriptions"}` y listas de 0 a 15 elementos de contenido irrelevante, comparando `is_valid_texts_amount(type, texts) == (1 <= len(texts) <= 5)`.
    - **Property 2: `is_unique_texts` es verdadero si y solo si los textos no vacíos no tienen duplicados**
    - **Validates: Requirements 7.8, 7.9**
    - Implementar con `hypothesis==6.112.2`, generando listas de strings (incluyendo `None`/`""`), comparando `is_unique_texts(texts) == (len(filtrados) == len(set(filtrados)))` donde `filtrados = [t for t in texts if t]`.
    - Declarar en el comentario de cada test: `Feature: facebook-save-pre-check-texts-tests, Property N: <descripción>`.
    - Esta tarea es opcional y no obligatoria para la especificación (ver design.md → Correctness Properties); las matrices de las tareas 8.2, 8.3, 9.2, 10.1 ya cubren los mismos requisitos con ejemplos concretos.

- [x] 12. Probar la rama DYNAMIC con `asset_feed` ausente, `None` o `{}`
  - [x] 12.1 Probar la no invocación de los tres validadores y la continuación sin error
    - Verificar, con `asset_feed=None`, que ninguno de los tres métodos de `Validador_Meta` se invoca, y que `execute()` continúa sin error hacia `_save_creative_to_publish`/`_build_response`.
    - Verificar el mismo resultado con `asset_feed={}`.
    - Verificar el mismo resultado cuando la clave `asset_feed_spec` está completamente ausente en `ad_creative`.
    - _Requirements: 11.1, 11.2, 11.3_

- [x] 13. Probar la rama STANDARD — no-op explícito
  - [x] 13.1 Probar la ausencia de invocación de validadores y la continuación
    - Verificar que, con `meta_campaign_mode="STANDARD"` y `story_spec` verdadero, ninguno de los tres métodos de `Validador_Meta` se invoca (la rama STANDARD es un `pass` explícito sin método propio a invocar), y que `story_spec` no recibe ninguna clave nueva.
    - Verificar que `execute()` continúa sin error hacia `_save_creative_to_publish`/`_build_response`, y que la Respuesta_de_Precheck no refleja ninguna validación de textos aplicada.
    - Verificar que, con `story_spec` falsy (`None` o `{}`), ninguno de los tres métodos se invoca y `execute()` continúa sin error.
    - _Requirements: 12.1, 12.2, 12.3_

- [x] 14. Probar `meta_campaign_mode` desconocido
  - [x] 14.1 Probar la ausencia de ambas ramas y la continuación sin mutación
    - Parametrizar `meta_campaign_mode` con cadena vacía, `None`, un valor arbitrario distinto de `"DYNAMIC"`/`"STANDARD"`, y la clave completamente ausente; verificar que ninguno de los tres métodos de `Validador_Meta` se invoca, independientemente de si `asset_feed`/`story_spec` son verdaderos o falsy.
    - Verificar que `execute()` continúa directamente hacia `_save_creative_to_publish`/`_build_response` sin ninguna mutación de `asset_feed_spec`/`object_story_spec`.
    - _Requirements: 13.1, 13.2_

- [x] 15. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Ejecutar `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py` desde `sinergia/`, sin modo watch ni interactivo.

- [x] 16. Probar las estructuras `creative`/`ads`/`adCreative` malformadas
  - [x] 16.1 Implementar la matriz de 4 niveles del bloque de validación
    - Verificar `IndexError` en `creative.get('ads', [])[0]` cuando `ads` está ausente o es una lista vacía, confirmando qué dobles ya fueron invocados antes de la excepción según el orden real del código.
    - Verificar `AttributeError` al invocar `.get('asset_feed_spec')`/`.get('object_story_spec')` sobre `None` cuando `adCreative` está presente con valor `None` explícito, antes de `_save_creative_to_publish`.
    - Verificar la ausencia de excepción cuando `adCreative={}`: `asset_feed`/`story_spec` quedan en `None`, ninguna rama de validación se ejecuta, y `execute()` continúa hacia `_save_creative_to_publish`/`_build_response`.
    - Verificar el mismo resultado que el caso anterior cuando la clave `adCreative` está completamente ausente en `creative['ads'][0]`.
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

- [x] 17. Probar el pass-through del bloque `try/except Exception as e: raise e`
  - [x] 17.1 Probar la equivalencia de tipo y mensaje end-to-end
    - Reutilizar el escenario de `AttributeError` de la tarea 16.1 (Requirement 14.2) para verificar, desde `execute()`, que el tipo y el mensaje (`str(exception)`) observados son idénticos a los de la excepción originada dentro del bloque `try`.
    - Documentar en el docstring o comentario de la prueba por qué este resultado es equivalente al comportamiento que se observaría si el bloque `try/except` no existiera.
    - _Requirements: 15.1, 15.2_

- [x] 18. Probar `_save_creative_to_publish`
  - [x] 18.1 Probar la llamada exacta, los defaults por nivel y la invocación aislada con `TypeError`
    - Verificar la llamada exacta `ad_channel_repository.update(ad_channel_id, {'channel_creative': creative})`, con `creative` por identidad y `ad_channel_id` extraído de `creative.get('ads')[0].get('adCreative', {}).get('asset_feed_spec', {}).get('ad_channel_id', 0)`.
    - Verificar que un valor verdadero de `asset_feed_spec['ad_channel_id']` se usa exactamente como primer argumento.
    - Parametrizar la ausencia de `adCreative`, `asset_feed_spec` o `ad_channel_id` por separado (con `creative['ads']` no vacía), verificando el default `0` en cada caso.
    - Invocar `_save_creative_to_publish` directamente y de forma aislada (sin pasar por `execute()`) con un `creative` cuya clave `ads` está ausente, verificando que se propaga `TypeError`, y documentar en el comentario por qué este camino no es alcanzable desde `execute()` (el bloque de validación previo ya habría lanzado `IndexError` para el mismo `creative`, Requirement 14.1).
    - _Requirements: 16.1, 16.2, 16.3, 16.4_

- [x] 19. Probar `_build_response`
  - [x] 19.1 Probar las claves completas, los valores reflejados, los defaults y la unión de `link_urls`
    - Verificar que la Respuesta_de_Precheck contiene exactamente las claves listadas en el Requirement 17.1, sin adicionales ni faltantes.
    - Verificar el reflejo exacto de valores explícitos de `asset_feed_spec`.
    - Verificar los defaults exactos por campo omitido (`False` para los cinco `*_valid_amount`, `0` para los cinco `*_max_amount`, `False`/`0`/`[]` según corresponda).
    - Verificar la unión por comas (`','.join(...)`) de `link_urls` para `proposal_url`, en el mismo orden.
    - Verificar que `proposal_locations` es `[]` cuando `creative` omite esa clave.
    - Verificar, en un escenario completo de `execute()` en rama DYNAMIC, que la Respuesta_de_Precheck refleja los valores de `titles`/`bodies`/`descriptions` y sus indicadores `unique_*`/`*_valid_amount` ya mutados por la validación inline.
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6_

  - [x] 19.2 Probar las invocaciones aisladas que exponen `AttributeError`
    - Invocar `_build_response` directamente sobre una instancia construida vía `use_case_factory`, sin pasar por `execute()`, con `creative['ads'][0]['adCreative']=None` explícito, verificando `AttributeError` al invocar `.get('asset_feed_spec', {})` sobre `None`.
    - Invocar `_build_response` de la misma forma con la clave `adCreative` completamente ausente en `ads_to_publish`, verificando el mismo `AttributeError`.
    - Documentar en el comentario de cada prueba por qué este escenario no es alcanzable de forma natural desde `execute()` con un `creative` construido consistentemente.
    - _Requirements: 17.7, 17.8_

- [x] 20. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Ejecutar `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py` desde `sinergia/`, sin servidor, watcher ni modo interactivo.

- [x] 21. Validar colección, aislamiento y repetibilidad de la suite
  - [x] 21.1 Ejecutar la validación pytest completa y corregir únicamente el código de pruebas
    - Ejecutar `./venv/bin/python -m pytest --collect-only -q tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py`.
    - Ejecutar `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py` y exigir cero `failed`, cero `skipped` y cero errores.
    - Repetir con `PYTHONHASHSEED=1` y `PYTHONHASHSEED=777` usando el mismo comando no interactivo para detectar estado compartido u orden accidental.
    - Confirmar que el guard de red (`deny_network`) no detecta ninguna fuga, que no se creó infraestructura Flask ni `tests/conftest.py`, y que `app/v2/use_cases/meta_ads.py`, `app/v2/use_cases/facebook_validator_service.py`, `app/v2/repository/ad_channel.py`, `app/v2/repository/campaign_channel_publish.py` y el resto de producción permanecen sin cambios.
    - _Requirements: 1.1, 1.4, 1.5, 1.6, 1.7, 18.1, 18.4, 18.5, 18.6, 18.7_

- [x] 22. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tarea 11.2 lleva `*` porque las property tests son opcionales según `design.md`/`requirements.md` (Testing Strategy → Property-Based Tests); todas las demás tareas de prueba no llevan `*` porque la suite pytest es el entregable principal de esta feature.
- No se debe modificar `app/v2/use_cases/meta_ads.py`, `app/v2/use_cases/facebook_validator_service.py`, `app/v2/repository/ad_channel.py`, `app/v2/repository/campaign_channel_publish.py`, ningún otro archivo de producción, `requirements.md` ni `design.md`.
- Toda la suite reside en `tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py`, dentro del proyecto `sinergia`, conforme a `sinergia/.kiro/steering/structure.md`; todos los artefactos de esta especificación residen en `sinergia/.kiro/specs/facebook-save-pre-check-texts-tests/`.
- No se debe crear `tests/conftest.py` ni una aplicación/contexto Flask salvo que la implementación demuestre una dependencia real; en ese caso, se debe detener y replantear con el usuario antes de añadir infraestructura.
- Datos_de_Campaña_Vacíos (`complete_campaign_data={}` siempre), el default mutable `pre_check_data: PreCheckDataDict = {}`, las asimetrías `.get(..., {})`/`.get(...)` sin default entre `execute()`, `_save_creative_to_publish` y `_build_response`, el pass-through `try/except Exception as e: raise e`, y la ausencia de métodos `_validate_texts_dynamic`/`_validate_texts_standard` propios se caracterizan como comportamiento actual; no se corrigen.
- `MetaAdsValidator.is_unique_texts`, `is_valid_length` e `is_valid_texts_amount` nunca se parchean para alterar su comportamiento; el helper `patch_text_validators` (usado únicamente en la tarea 11.1) los envuelve solo para registrar orden, delegando siempre a la implementación real.
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
    { "id": 11, "tasks": ["9.1"] },
    { "id": 12, "tasks": ["9.2"] },
    { "id": 13, "tasks": ["10.1"] },
    { "id": 14, "tasks": ["11.1"] },
    { "id": 15, "tasks": ["11.2"] },
    { "id": 16, "tasks": ["12.1"] },
    { "id": 17, "tasks": ["13.1"] },
    { "id": 18, "tasks": ["14.1"] },
    { "id": 19, "tasks": ["16.1"] },
    { "id": 20, "tasks": ["17.1"] },
    { "id": 21, "tasks": ["18.1"] },
    { "id": 22, "tasks": ["19.1"] },
    { "id": 23, "tasks": ["19.2"] },
    { "id": 24, "tasks": ["21.1"] }
  ]
}
```
