# Requirements Document

## Introduction

Este documento define los requisitos para una suite de pruebas unitarias con pytest del módulo `app/v2/use_cases/funnel_flow_validator.py`, con foco en `FunnelFlowValidatorUseCase` y en los validadores que determinan el estado de cada etapa del funnel. La suite debe caracterizar el comportamiento observable actual, aislar las consultas a Strapi y cualquier API externa, cubrir el flujo exitoso, los flujos sin datos, todas las reglas de validación, la agregación de estados y la propagación de excepciones. La implementación de la suite queda fuera de esta fase.

## Glossary

- **Suite_de_Pruebas**: Conjunto de pruebas unitarias pytest para `FunnelFlowValidatorUseCase` y los validadores definidos en `funnel_flow_validator.py`.
- **Caso_de_Uso**: Instancia de `FunnelFlowValidatorUseCase` configurada con un identificador de campaña.
- **Validador**: Implementación de `BaseValidator` que evalúa una etapa y devuelve una tupla compuesta por un indicador de finalización y una lista de errores.
- **Mapa_de_Estado**: Colección interna que mantiene el resultado de las etapas `channel`, `ads_structure`, `audiences`, `ads_experiment`, `ads`, `summary`, `review` y `launchpad`.
- **Respuesta_de_Validación**: Resultado HTTP lógico devuelto por `Caso_de_Uso.execute`, compuesto por el indicador `ok`, el `Mapa_de_Estado`, los datos consolidados del funnel y el código de estado.
- **Cliente_de_Datos**: Dependencia `StrapiClient` utilizada por el Caso_de_Uso mediante `find_by_filters` y `get` para consultar Strapi.
- **Dependencia_Externa**: Cliente, repositorio, servicio de red o API cuya ejecución queda fuera de la unidad bajo prueba.
- **Doble_de_Prueba**: Sustitución controlada creada con `unittest.mock.MagicMock` o con el mocker de pytest.
- **Fixture_Flask**: Fixture pytest reutilizable que crea una aplicación Flask con configuración de pruebas y proporciona el contexto requerido por las pruebas.
- **Estructura_Consolidada**: Lista de ad sets construida por el Caso_de_Uso con ads, audiencias, experimentos, canales de anuncio y el identificador del proyecto de plataforma de medios.
- **Canal_Seleccionado**: Primer canal de anuncio cuyo campo `selected` tiene un valor verdadero.
- **Payload**: Texto contenido en un atributo de canal o en un elemento de medios.
- **Error_de_Validación**: Diccionario que contiene como mínimo los campos `message` y `code`, y que puede contener `metadata`.
- **Validador_Agregado**: Validador de las etapas `summary`, `review` o `launchpad` que resume los resultados de validadores dependientes.
- **pytest**: Framework de ejecución usado por la Suite_de_Pruebas.

## Requirements

### Requirement 1: Infraestructura y aislamiento de las pruebas

**User Story:** Como desarrollador, quiero ejecutar pruebas unitarias aisladas, para que los resultados no dependan de Flask, Strapi, repositorios ni APIs disponibles en el entorno.

#### Acceptance Criteria

1. WHEN pytest recopila y ejecuta la Suite_de_Pruebas sin servicios externos disponibles, THE Suite_de_Pruebas SHALL completar la recopilación y la ejecución usando únicamente el entorno Python local del proyecto.
2. WHEN una prueba construye un Caso_de_Uso, THE Suite_de_Pruebas SHALL sustituir `StrapiClient` por un Doble_de_Prueba antes de invocar cualquier método alcanzable que pueda usar el Cliente_de_Datos.
3. WHEN una prueba alcanza `find_by_filters`, THE Suite_de_Pruebas SHALL devolver la respuesta configurada desde el Doble_de_Prueba sin construir ni invocar un Cliente_de_Datos real.
4. WHEN una prueba alcanza `get`, THE Suite_de_Pruebas SHALL devolver la respuesta configurada desde el Doble_de_Prueba sin construir ni invocar un Cliente_de_Datos real.
5. WHILE pytest ejecuta la Suite_de_Pruebas, THE Suite_de_Pruebas SHALL realizar cero solicitudes de red y cero operaciones contra servicios persistentes.
6. WHEN una Dependencia_Externa adicional resulta alcanzable desde la unidad bajo prueba, THE Suite_de_Pruebas SHALL sustituir la Dependencia_Externa por un Doble_de_Prueba antes de ejecutar el escenario.
7. WHERE una prueba requiere contexto Flask y `tests/conftest.py` carece de una Fixture_Flask compartida, THE Suite_de_Pruebas SHALL definir una única Fixture_Flask reutilizable en `tests/conftest.py`.
8. WHERE una prueba requiere contexto Flask y `tests/conftest.py` ya contiene una Fixture_Flask compartida, THE Suite_de_Pruebas SHALL reutilizar la Fixture_Flask existente sin crear otra fixture equivalente.
9. WHERE una prueba no requiere contexto Flask, THE Suite_de_Pruebas SHALL ejecutar la unidad como prueba pura sin crear una aplicación ni un contexto Flask.
10. WHILE se implementa la Suite_de_Pruebas, THE Suite_de_Pruebas SHALL mantener sin modificaciones los archivos de implementación, incluido `app/v2/use_cases/funnel_flow_validator.py`.

### Requirement 2: Estado inicial y utilidades internas

**User Story:** Como mantenedor, quiero verificar la configuración inicial y las utilidades del caso de uso, para detectar cambios en el contrato de estados y despacho de validadores.

#### Acceptance Criteria

1. WHEN se construye un Caso_de_Uso, THE Suite_de_Pruebas SHALL verificar que el Mapa_de_Estado contiene exactamente y en este orden `channel`, `ads_structure`, `audiences`, `ads_experiment`, `ads`, `summary`, `review` y `launchpad`, sin claves adicionales.
2. WHEN se construye un Caso_de_Uso, THE Suite_de_Pruebas SHALL verificar que cada una de las ocho etapas contiene exactamente `completed=False`, `errors=[]` y `message="Pending validation"`.
3. WHEN se construye un Caso_de_Uso, THE Suite_de_Pruebas SHALL verificar que la colección de validadores contiene exactamente ocho elementos cuyas claves, en orden, son `channel`, `ads_structure`, `audiences`, `ads_experiment`, `ads`, `summary`, `review` y `launchpad`.
4. WHEN `_fetch_bulk` recibe un endpoint y parámetros, THE Suite_de_Pruebas SHALL verificar una única llamada a `get` con el endpoint como primer argumento y los parámetros como argumento nombrado `params`.
5. WHEN `get` devuelve un diccionario con el campo `data`, THE Suite_de_Pruebas SHALL verificar que `_fetch_bulk` devuelve el mismo objeto contenido en `data` sin copiarlo ni transformarlo.
6. WHEN `get` devuelve un diccionario sin el campo `data`, THE Suite_de_Pruebas SHALL verificar que `_fetch_bulk` devuelve `[]`.
7. WHEN `_run_validator` recibe una clave registrada y un contexto, THE Suite_de_Pruebas SHALL verificar que el Validador correspondiente recibe exactamente el mismo objeto de contexto.
8. WHEN un Validador registrado devuelve un indicador y una lista de errores, THE Suite_de_Pruebas SHALL verificar que `_run_validator` reemplaza la entrada completa de la etapa por exactamente `completed` con ese indicador y `errors` con esa misma lista.
9. WHEN `_run_validator` recibe una clave no registrada, THE Suite_de_Pruebas SHALL verificar que la entrada creada contiene exactamente `completed=False` y un único Error_de_Validación con `message="Validator implementation missing"` y `code="SYS_ERR"`.
10. WHEN `_build_response` recibe datos consolidados y todas las entradas del Mapa_de_Estado están completas, THE Suite_de_Pruebas SHALL verificar que la respuesta conserva el mismo objeto de datos y presenta una sola entrada de cada etapa en el orden del Mapa_de_Estado.
11. IF una entrada del Mapa_de_Estado carece de `completed`, THEN THE Suite_de_Pruebas SHALL verificar que `_build_response` agrega `completed=False` a esa entrada sin alterar los demás campos.
12. IF una entrada del Mapa_de_Estado carece de `errors`, THEN THE Suite_de_Pruebas SHALL verificar que `_build_response` agrega `errors=[]` a esa entrada sin alterar los demás campos.
13. WHEN `_get_max_length_allowed` recibe una longitud `n`, THE Suite_de_Pruebas SHALL verificar el resultado exacto `n + min(ceil(n * 0.2), 10)`.
14. WHEN `_get_max_length_allowed` recibe respectivamente `0`, `1`, `49`, `50` y `51`, THE Suite_de_Pruebas SHALL verificar respectivamente los límites `0`, `2`, `59`, `60` y `61`, incluidos los límites de transición del incremento máximo de 10 caracteres.

### Requirement 3: Orquestación y construcción del flujo exitoso

**User Story:** Como desarrollador, quiero verificar la orquestación completa del caso de uso, para asegurar que las respuestas de datos se consolidan y validan correctamente.

#### Acceptance Criteria

1. WHEN el Cliente_de_Datos devuelve el conjunto mínimo de funnel flows, canales, ad sets y relaciones que satisface todas las reglas de negocio, THE Suite_de_Pruebas SHALL verificar que `execute` devuelve `ok=1`, código de estado `200` y exactamente ocho estados con `completed=True` y `errors=[]`.
2. WHEN la consulta de funnel flows devuelve varios identificadores, THE Suite_de_Pruebas SHALL verificar que la consulta `funnel-flow-channels` incluye una sola vez y sin omisiones todos los identificadores en el filtro `funnel_flow_ref`.
3. WHEN la consulta de funnel flows devuelve varios identificadores, THE Suite_de_Pruebas SHALL verificar que la consulta `ad-sets` incluye una clave indexada `filters[funnel_flow_ref][id][$in][i]` por cada identificador, sin omisiones, y `populate="ads,media_platform_project_id"`.
4. WHEN la consulta de ad sets devuelve varios identificadores, THE Suite_de_Pruebas SHALL verificar que la consulta `audience-audiences` incluye una clave indexada `filters[ad_set_ref][id][$in][i]` por cada identificador, sin omisiones, y `populate="channel_ref,ad_set_ref"`.
5. WHEN la consulta de ad sets devuelve varios identificadores, THE Suite_de_Pruebas SHALL verificar que la consulta `experiment-experiments` incluye una clave indexada `filters[ad_set_ref][id][$in][i]` por cada identificador, sin omisiones, y `populate="ad_set_ref,subcategory_ref.category_ref"`.
6. WHEN los ad sets contienen varios ads, THE Suite_de_Pruebas SHALL verificar que la consulta `ad-channels` incluye una clave indexada `filters[ad_ref][id][$in][i]` por cada identificador de ad, sin omisiones, `populate="channel_ref,ad_ref"` y `pagination[pageSize]=1000`.
7. WHEN cada relación válida de audiencia aparece una vez en la respuesta de datos, THE Suite_de_Pruebas SHALL verificar que la Estructura_Consolidada contiene esa audiencia exactamente una vez y solo bajo el ad set referenciado.
8. WHEN cada relación válida de experimento aparece una vez en la respuesta de datos, THE Suite_de_Pruebas SHALL verificar que la Estructura_Consolidada contiene ese experimento exactamente una vez y solo bajo el ad set referenciado.
9. WHEN cada relación válida de canal de anuncio aparece una vez en la respuesta de datos, THE Suite_de_Pruebas SHALL verificar que la Estructura_Consolidada contiene ese canal exactamente una vez y solo bajo el ad referenciado.
10. WHEN un ad set contiene `media_platform_project_id.data.attributes.project_id`, THE Suite_de_Pruebas SHALL verificar que la Estructura_Consolidada conserva el valor de `project_id` sin alteración bajo la clave `media_platform_project_id`.
11. WHEN un canal de anuncio contiene una referencia de canal, datos de medios, atributos, redirección y selección, THE Suite_de_Pruebas SHALL verificar que la Estructura_Consolidada conserva sin alteración los valores de `channel_id`, `channel_name`, `template_id`, `elements`, `images_banner`, `formats`, `channel_attributes`, `url` y `selected`.
12. WHEN un experimento contiene identificador, tipo, subcategoría y categoría, THE Suite_de_Pruebas SHALL verificar que la Estructura_Consolidada conserva sin alteración `id`, `type`, los campos `id`, `name` y `description` de la subcategoría y los campos `id`, `name` y `description` de la categoría.
13. WHEN un ad contiene identificador, nombre y URL de redirección, THE Suite_de_Pruebas SHALL verificar que la Estructura_Consolidada conserva sin alteración `id`, `name` y la URL bajo `attributes.url`.

### Requirement 4: Flujos alternativos y excepciones de obtención de datos

**User Story:** Como mantenedor, quiero cubrir respuestas vacías, referencias inválidas y fallos del servicio de datos, para que la suite caracterice los límites de la orquestación.

#### Acceptance Criteria

1. WHEN la campaña no tiene funnel flows, THE Suite_de_Pruebas SHALL verificar que `execute` devuelve `ok=1`, código de estado `200`, `funnel_flow_data=[]` y exactamente las ocho etapas en orden con `completed=False`, `errors=[]` y `message="Pending validation"`.
2. WHEN la campaña no tiene funnel flows, THE Suite_de_Pruebas SHALL verificar que el Caso_de_Uso omite las consultas de canales, ad sets, audiencias, experimentos y canales de anuncio.
3. WHEN la consulta de ad sets devuelve una colección vacía, THE Suite_de_Pruebas SHALL verificar que el Caso_de_Uso omite las consultas `audience-audiences`, `experiment-experiments` y `ad-channels`.
4. WHEN la consulta de canales devuelve una lista no vacía y la consulta de ad sets devuelve una colección vacía, THE Suite_de_Pruebas SHALL verificar que `execute` devuelve `ok=1`, código `200`, `funnel_flow_data=[]`, `channel` completado sin errores, las etapas `ads_structure`, `audiences`, `ads_experiment` y `ads` incompletas con un único código `ADS_STRUCT_01`, `AUD_01`, `EXP_01` y `ADS_01` respectivamente, y cada Validador_Agregado incompleto con sus cinco códigos `01` a `05` en orden.
5. WHEN existen ad sets sin ads, THE Suite_de_Pruebas SHALL verificar que el Caso_de_Uso ejecuta las consultas de audiencias y experimentos para los identificadores de ad set y omite la consulta `ad-channels`.
6. WHEN una audiencia referencia un ad set desconocido y otra audiencia referencia un ad set conocido, THE Suite_de_Pruebas SHALL verificar que la Estructura_Consolidada excluye solo la audiencia con referencia desconocida y conserva la audiencia con referencia conocida.
7. WHEN un experimento referencia un ad set desconocido y otro experimento referencia un ad set conocido, THE Suite_de_Pruebas SHALL verificar que la Estructura_Consolidada excluye solo el experimento con referencia desconocida y conserva el experimento con referencia conocida.
8. WHEN un canal de anuncio referencia un ad desconocido y otro canal referencia un ad conocido, THE Suite_de_Pruebas SHALL verificar que la Estructura_Consolidada excluye solo el canal con referencia desconocida y conserva el canal con referencia conocida.
9. WHEN una relación representada por un diccionario contiene una estructura anidada defectuosa que produce una excepción durante el mapeo y una relación válida aparece después, THE Suite_de_Pruebas SHALL verificar que el Caso_de_Uso omite la relación defectuosa y procesa la relación válida posterior.
10. IF la consulta `find_by_filters` de `funnel-flows` lanza una excepción, THEN THE Suite_de_Pruebas SHALL verificar que `execute` propaga la misma instancia de excepción y no devuelve una respuesta de éxito.
11. IF la consulta `find_by_filters` de `funnel-flow-channels` lanza una excepción, THEN THE Suite_de_Pruebas SHALL verificar que `execute` propaga la misma instancia de excepción y no devuelve una respuesta de éxito.
12. IF la consulta `get` de `ad-sets` lanza una excepción, THEN THE Suite_de_Pruebas SHALL verificar que `execute` propaga la misma instancia de excepción y no devuelve una respuesta de éxito.
13. IF la consulta `get` de `audience-audiences` lanza una excepción, THEN THE Suite_de_Pruebas SHALL verificar que `execute` propaga la misma instancia de excepción y no devuelve una respuesta de éxito.
14. IF la consulta `get` de `experiment-experiments` lanza una excepción, THEN THE Suite_de_Pruebas SHALL verificar que `execute` propaga la misma instancia de excepción y no devuelve una respuesta de éxito.
15. IF la consulta `get` de `ad-channels` lanza una excepción, THEN THE Suite_de_Pruebas SHALL verificar que `execute` propaga la misma instancia de excepción y no devuelve una respuesta de éxito.

### Requirement 5: Reglas de canal, estructura, audiencias y experimentos

**User Story:** Como responsable de calidad, quiero probar cada regla básica del funnel, para que cada resultado y código de error permanezca verificable.

#### Acceptance Criteria

1. WHEN `ChannelValidator` recibe `None` o una colección vacía, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación con `code="CHA_01"` y sin `metadata`.
2. WHEN `ChannelValidator` recibe un valor no vacío que no es una lista, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación con `code="CHA_02"` y sin `metadata`.
3. WHEN `ChannelValidator` recibe una lista no vacía, THE Suite_de_Pruebas SHALL verificar `completed=True` y exactamente cero errores.
4. WHEN `AdsStructureValidator` recibe `None` o una colección vacía de ad sets, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación con `code="ADS_STRUCT_01"` y sin `metadata`.
5. WHEN un ad set omite `ads` o contiene `ads` igual a `None`, una colección vacía o un valor que no es una lista, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_STRUCT_02` con `metadata.ad_set_name` igual al nombre del ad set.
6. WHEN cada ad set contiene una lista no vacía de ads, THE Suite_de_Pruebas SHALL verificar que `AdsStructureValidator` devuelve `completed=True` y exactamente cero errores.
7. WHEN varios ad sets omiten ads o contienen ads inválidos, THE Suite_de_Pruebas SHALL verificar que `AdsStructureValidator` devuelve `completed=False` y exactamente un Error_de_Validación `ADS_STRUCT_02` por cada ad set afectado.
8. WHEN `AudiencesValidator` recibe `None` o una colección vacía de ad sets, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación con `code="AUD_01"` y sin `metadata`.
9. WHEN un ad set omite `audiences` o contiene `audiences` igual a `None` o una colección vacía, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `AUD_02` con `metadata.ad_set_name` igual al nombre del ad set.
10. WHEN un ad set contiene una colección no vacía de audiencias y ninguna audiencia contiene `preferred_audience.preferred=1`, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `AUD_03` con `metadata.ad_set_name` igual al nombre del ad set.
11. WHEN cada ad set contiene una audiencia con `preferred_audience.preferred=1`, THE Suite_de_Pruebas SHALL verificar que `AudiencesValidator` devuelve `completed=True` y exactamente cero errores.
12. WHEN varios ad sets carecen de audiencias o de una audiencia preferida, THE Suite_de_Pruebas SHALL verificar que `AudiencesValidator` devuelve `completed=False` y exactamente un Error_de_Validación `AUD_02` o `AUD_03`, según la condición, por cada ad set afectado.
13. WHEN `audiences` es un iterable no vacío distinto de una lista y sus elementos proporcionan `get`, THE Suite_de_Pruebas SHALL verificar que `AudiencesValidator` evalúa los elementos por su contenido sin rechazar el tipo del iterable.
14. IF `audiences` es un valor verdadero no iterable, THEN THE Suite_de_Pruebas SHALL verificar que `AudiencesValidator` propaga `TypeError` en lugar de devolver una tupla de validación.
15. IF `AudiencesValidator` recibe una colección no vacía de ad sets o audiencias cuyos elementos no proporcionan el método `get`, THEN THE Suite_de_Pruebas SHALL verificar que el Validador propaga `AttributeError` en lugar de devolver una tupla de validación.
16. WHEN `ExperimentsValidator` recibe `None` o una colección vacía de ad sets, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación con `code="EXP_01"` y sin `metadata`.
17. WHEN un ad set omite `experiments` o contiene `experiments` igual a `None` o una colección vacía, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `EXP_02` con `metadata.ad_set_name` igual al nombre del ad set.
18. WHEN un ad set contiene una colección no vacía compuesta exclusivamente por valores falsos, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `EXP_03` con `metadata.ad_set_name` igual al nombre del ad set.
19. WHEN cada ad set contiene al menos un experimento con valor verdadero, THE Suite_de_Pruebas SHALL verificar que `ExperimentsValidator` devuelve `completed=True` y exactamente cero errores.
20. WHEN varios ad sets carecen de experimentos o contienen exclusivamente experimentos con valores falsos, THE Suite_de_Pruebas SHALL verificar que `ExperimentsValidator` devuelve `completed=False` y exactamente un Error_de_Validación `EXP_02` o `EXP_03`, según la condición, por cada ad set afectado.
21. WHEN `experiments` es un iterable no vacío distinto de una lista, THE Suite_de_Pruebas SHALL verificar que `ExperimentsValidator` considera válida la colección si al menos un elemento tiene valor verdadero.
22. IF `experiments` es un valor verdadero no iterable, THEN THE Suite_de_Pruebas SHALL verificar que `ExperimentsValidator` propaga `TypeError` en lugar de devolver una tupla de validación.
23. IF `ExperimentsValidator` recibe una colección no vacía de ad sets cuyos elementos no proporcionan el método `get`, THEN THE Suite_de_Pruebas SHALL verificar que el Validador propaga `AttributeError` en lugar de devolver una tupla de validación.

### Requirement 6: Reglas de contenido de anuncios

**User Story:** Como responsable de campañas, quiero probar cada regla de contenido de anuncios, para que los anuncios incompletos produzcan diagnósticos específicos.

#### Acceptance Criteria

1. WHEN `AdsContentValidator` recibe `None` o una colección vacía de ad sets, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_01` sin `metadata`.
2. WHEN la validación de audiencias es la única dependencia inválida, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_02` con `metadata={}`.
3. WHEN un ad set con audiencias válidas carece de `media_platform_project_id`, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_09` con `metadata.ad_set_name` igual al nombre del ad set.
4. WHEN `AdsContentValidator` registra `ADS_09` para un ad set, THE Suite_de_Pruebas SHALL verificar que el Validador omite todos los ads del ad set afectado y continúa con el siguiente ad set.
5. WHEN un ad set con audiencias y `media_platform_project_id` válidos carece de ads, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_03` con `metadata.ad_set_name` igual al nombre del ad set.
6. WHEN `AdsContentValidator` registra `ADS_03` para un ad set, THE Suite_de_Pruebas SHALL verificar que el Validador continúa con el siguiente ad set.
7. WHEN un ad omite la URL y satisface las demás reglas, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_06` con `metadata.ad_name` igual al nombre del ad.
8. WHEN `AdsContentValidator` registra `ADS_06`, THE Suite_de_Pruebas SHALL verificar que el Validador continúa evaluando variantes, atributos y medios del mismo ad.
9. WHEN un ad con URL válida omite `ad_channels` o contiene una colección vacía, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_04` con `metadata.ad_set_name` y `metadata.ad_name` iguales a los nombres correspondientes.
10. WHEN `AdsContentValidator` registra `ADS_04`, THE Suite_de_Pruebas SHALL verificar que el Validador omite atributos y medios del ad afectado y continúa con el siguiente ad.
11. WHEN un ad contiene variantes y ninguna variante tiene `selected` con valor verdadero, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_04_01` con `metadata.ad_set_name` y `metadata.ad_name` iguales a los nombres correspondientes.
12. WHEN `AdsContentValidator` registra `ADS_04_01`, THE Suite_de_Pruebas SHALL verificar que el Validador omite atributos y medios del ad afectado y continúa con el siguiente ad.
13. WHEN un Canal_Seleccionado contiene `channel_attributes=[]` y medios válidos, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_05` con `metadata.ad_name` y `metadata.channel_name` iguales a los nombres correspondientes.
14. WHEN `channel_attributes` es `None` o un valor no iterable, THE Suite_de_Pruebas SHALL verificar que `AdsContentValidator` agrega la condición `ADS_05` y después propaga `TypeError`, interrumpiendo `validate_completion` sin devolver estado ni lista de errores.
15. WHEN un atributo del Canal_Seleccionado contiene un Payload vacío y el resto del ad es válido, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_05_01` con `metadata.ad_name` y `metadata.channel_name` iguales a los nombres correspondientes.
16. WHEN `AdsContentValidator` detecta un Payload vacío, THE Suite_de_Pruebas SHALL verificar que el Validador deja de recorrer los payloads y atributos restantes del Canal_Seleccionado y continúa con la validación de medios.
17. WHEN un único Payload de atributo distinto de CTA supera `max_char` y el resto del ad es válido, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_05_02` con `metadata.ad_name`, `metadata.channel_name`, `metadata.payload_length`, `metadata.max_allowed_length` y `metadata.attribute_name` exactos.
18. WHERE el nombre del atributo es CTA con cualquier combinación de mayúsculas y minúsculas, WHEN el Payload supera `max_char`, THE Suite_de_Pruebas SHALL verificar que `AdsContentValidator` no agrega `ADS_05_02` para ese Payload y continúa el recorrido.
19. WHEN uno de `elements`, `images_banner` o `formats` está ausente, es `None`, no es una lista o es una lista vacía y los otros dos campos son válidos, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_07` con `metadata.ad_name`, `metadata.media_element` y `metadata.channel_name` exactos.
20. WHEN varios campos entre `elements`, `images_banner` y `formats` son inválidos, THE Suite_de_Pruebas SHALL verificar exactamente un Error_de_Validación `ADS_07` por cada campo inválido y la continuación del recorrido con los campos restantes.
21. WHEN un formato contiene `visual_id=""` y `visual_url` no vacío, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_07_01` con `metadata.ad_name`, `metadata.media_element="formats"` y `metadata.channel_name` exactos.
22. WHEN un formato contiene `visual_url=""` y `visual_id` no vacío, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_07_02` con `metadata.ad_name`, `metadata.media_element="formats"` y `metadata.channel_name` exactos.
23. WHEN un formato contiene simultáneamente `visual_id=""` y `visual_url=""`, THE Suite_de_Pruebas SHALL verificar exactamente dos Error_de_Validación con códigos `ADS_07_01` y `ADS_07_02` y la continuación del recorrido de formatos.
24. WHEN un elemento contiene un `original_payload` no vacío de longitud `n`, THE Suite_de_Pruebas SHALL verificar que el límite calculado es exactamente `n + min(ceil(n * 0.2), 10)`.
25. WHEN un elemento contiene un Payload cuya longitud supera el límite calculado desde `original_payload` y el resto del ad es válido, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_08_02` con `metadata.ad_name`, `metadata.channel_name`, `metadata.payload_length`, `metadata.max_allowed_length` y `metadata.element_name` exactos.
26. WHEN un elemento contiene `intention=None`, un límite calculable y un Payload dentro del límite, THE Suite_de_Pruebas SHALL verificar `completed=False` y exactamente un Error_de_Validación `ADS_08_01` con `metadata.ad_name`, `metadata.media_element="elements"` y `metadata.channel_name` exactos.
27. WHEN `AdsContentValidator` registra `ADS_08_01`, THE Suite_de_Pruebas SHALL verificar que el Validador deja de recorrer los elementos restantes de la lista y continúa con el siguiente campo de medios o ad.
28. IF un elemento con Payload verdadero se evalúa antes de que la ejecución de `validate_completion` haya calculado un límite `max`, THEN THE Suite_de_Pruebas SHALL verificar que `AdsContentValidator` propaga `UnboundLocalError` e interrumpe la validación sin devolver estado ni lista de errores.
29. WHEN un ad satisface las reglas de audiencias, proyecto, ads, URL, variante seleccionada, atributos, Payload, medios, formatos e intención, THE Suite_de_Pruebas SHALL verificar que `AdsContentValidator` devuelve `completed=True` y exactamente cero errores.
30. WHEN un ad incumple varias reglas independientes cuyos recorridos no ejecutan `continue`, `break` ni una excepción, THE Suite_de_Pruebas SHALL verificar `completed=False` y la acumulación de exactamente un Error_de_Validación por cada infracción aplicable en el orden de evaluación del código.
31. WHEN varios ad sets o ads producen errores y ninguna condición interrumpe `validate_completion`, THE Suite_de_Pruebas SHALL verificar que `AdsContentValidator` continúa con los elementos posteriores y conserva todos los Error_de_Validación acumulados.

### Requirement 7: Validadores agregados y respuesta final

**User Story:** Como consumidor del resultado, quiero verificar los estados resumidos, para que cada etapa agregada refleje las dependencias del funnel.

#### Acceptance Criteria

1. WHEN las cinco dependencias de cada Validador_Agregado devuelven `completed=True`, THE Suite_de_Pruebas SHALL verificar que `SummaryContentValidator`, `ReviewContentValidator` y `LaunchPadContentValidator` devuelven cada uno `completed=True` y exactamente cero errores.
2. WHEN solo la dependencia de canal devuelve `completed=False`, THE Suite_de_Pruebas SHALL verificar que los tres Validadores_Agregados devuelven `completed=False` y exactamente un error con código `SUM_01`, `REV_01` y `LAUNCH_01`, respectivamente.
3. WHEN solo la dependencia de estructura de ads devuelve `completed=False`, THE Suite_de_Pruebas SHALL verificar que los tres Validadores_Agregados devuelven `completed=False` y exactamente un error con código `SUM_02`, `REV_02` y `LAUNCH_02`, respectivamente.
4. WHEN solo la dependencia de audiencias devuelve `completed=False`, THE Suite_de_Pruebas SHALL verificar que los tres Validadores_Agregados devuelven `completed=False` y exactamente un error con código `SUM_03`, `REV_03` y `LAUNCH_03`, respectivamente.
5. WHEN solo la dependencia de experimentos devuelve `completed=False`, THE Suite_de_Pruebas SHALL verificar que los tres Validadores_Agregados devuelven `completed=False` y exactamente un error con código `SUM_04`, `REV_04` y `LAUNCH_04`, respectivamente.
6. WHEN solo la dependencia de contenido de ads devuelve `completed=False`, THE Suite_de_Pruebas SHALL verificar que los tres Validadores_Agregados devuelven `completed=False` y exactamente un error con código `SUM_05`, `REV_05` y `LAUNCH_05`, respectivamente.
7. WHEN una dependencia aislada falla en `SummaryContentValidator`, THE Suite_de_Pruebas SHALL verificar que el error correspondiente contiene `metadata={}` y ningún código de una dependencia completada.
8. WHEN una dependencia aislada falla en `ReviewContentValidator`, THE Suite_de_Pruebas SHALL verificar que el error correspondiente contiene `metadata={}` y ningún código de una dependencia completada.
9. WHEN una dependencia aislada falla en `LaunchPadContentValidator`, THE Suite_de_Pruebas SHALL verificar que el error correspondiente contiene `metadata={}` y ningún código de una dependencia completada.
10. WHEN varias dependencias de un Validador_Agregado devuelven `completed=False`, THE Suite_de_Pruebas SHALL verificar que el Validador_Agregado devuelve `completed=False`, exactamente un error por cada dependencia fallida y ningún error por las dependencias completadas.
11. WHEN varias dependencias fallan, THE Suite_de_Pruebas SHALL verificar que los códigos agregados aparecen en el orden canal, estructura de ads, audiencias, experimentos y contenido de ads.
12. WHEN `execute` completa la ejecución con datos, THE Suite_de_Pruebas SHALL verificar que la Respuesta_de_Validación contiene exactamente una entrada para cada una de las ocho etapas, sin duplicados ni etapas adicionales, y la Estructura_Consolidada resultante.

### Requirement 8: Calidad y mantenibilidad de la suite

**User Story:** Como equipo de desarrollo, quiero una suite determinista y legible, para facilitar el diagnóstico de regresiones.

#### Acceptance Criteria

1. THE Suite_de_Pruebas SHALL definir nombres de función únicos con el prefijo `test_` que identifiquen la condición ejercitada y el resultado esperado.
2. THE Suite_de_Pruebas SHALL usar en cada escenario datos mínimos que incluyan únicamente los campos necesarios para alcanzar la rama y observar el resultado especificado.
3. WHEN varios escenarios reutilizan una fixture o función constructora, THE Suite_de_Pruebas SHALL recibir una instancia nueva de cada lista y diccionario mutable en cada invocación.
4. WHEN una prueba verifica una consulta al Cliente_de_Datos, THE Suite_de_Pruebas SHALL comprobar exactamente el nombre del endpoint, el argumento `filters` o `params`, todas las claves relevantes y los valores correspondientes.
5. WHEN una prueba verifica un Error_de_Validación, THE Suite_de_Pruebas SHALL comprobar exactamente la cantidad de errores, el código y todos los campos de `metadata` exigidos por la regla.
6. WHEN una prueba verifica una excepción, THE Suite_de_Pruebas SHALL comprobar exactamente el tipo o la identidad especificada y la ausencia de una respuesta de éxito.
7. WHEN pytest ejecuta repetidamente el archivo de pruebas con las mismas entradas y distintos órdenes de ejecución, THE Suite_de_Pruebas SHALL producir los mismos resultados sin depender de estado mutable compartido ni del orden de las pruebas.
8. WHEN pytest ejecuta el archivo de pruebas de `funnel_flow_validator.py`, THE Suite_de_Pruebas SHALL finalizar con exactamente cero pruebas `failed`, cero pruebas `skipped` y cero errores de recopilación o ejecución.
