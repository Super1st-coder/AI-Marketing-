# Requirements Document

## Introduction

Fury necesita obtener la imagen de una variante de anuncio (ad-channel) desde Sinergia para el pipeline de edición de imágenes (`fury/.kiro/specs/ad-variant-image-edit-pipeline`). Fury ya consume la ruta `GET /api/v2/service/hiluca/brand/{brand_id}/campaign/{campaign_id}/ad/{ad_id}/channel/{channel_id}/variant/{variant_id}/image/{image_id}` desde `fury/app/agents/tools/campaign_tools.py::get_ad_variant_image` y espera en `data` un objeto `{"id", "url", "prompt"}`. Esa ruta todavía no existe en Sinergia (decisión D9 de la spec de Fury).

Esta spec añade en Sinergia:

- El endpoint de servicio en `sinergia/app/v2/resources/service.py`, protegido con `@service_api_key_required`.
- El caso de uso `GetAdVariantImageUseCase` en `sinergia/app/v2/use_cases/image_library.py`.
- Un método nuevo en `CampaignRepository` (búsqueda por `campaign_id` + `brand_id`).
- Un método nuevo en `AdChannelRepository` (búsqueda por `variant_id` + `ad_id` + `campaign_id` + `channel_id`).
- Pruebas unitarias en `sinergia/tests/v2/unit/use_cases/`.

Decisiones ya confirmadas por el usuario:

- Se crean métodos de repositorio nuevos, siguiendo las convenciones existentes (heredan de `StrapiClient`, filtros `filters[...][$eq]`, devuelven `None` si no hay datos).
- El campo del prompt en el registro de Image_Library es `image_prompt`. Si falta o es `null`, el prompt devuelto es `""`.
- De la imagen solo se valida que exista. No se valida su pertenencia a la marca, al anuncio ni a la variante.
- Tipos, excepciones, mapeo HTTP, inyección de dependencias y nombres siguen el código existente (ver Glosario).
- La clase se llama `GetAdVariantImageUseCase` (en singular).

Hechos del código inspeccionado que fijan el comportamiento:

- `SinergiaException` y sus subclases se convierten en HTTP 400 con cuerpo `{"ok": 0, "message": {"code": <code>, "text": <text>}}` mediante el `errorhandler` de `sinergia/app/v2/__init__.py`.
- `ParametersNotFoundException` tiene el código `PAR001`, `DataNotFoundException` tiene `DAT001` e `ImageLibraryException` tiene `IMG001`. Las tres están en `sinergia/app/exceptions/base.py`.
- `ImageLibraryRepository.get_image(image_id)` no comprueba el código HTTP de respuesta. Ante una imagen inexistente devuelve el JSON de error de Image_Library, y ante un fallo de red lanza `ImageLibraryException`.
- Relaciones de Strapi: `campaign.brand_ref` → `brand-v2`; `ad-channel.ad_ref2` → `ad`; `ad.ad_set_ref2` → `ad-set`; `ad-set.funnel_flow_ref.campaign_ref` → `campaign`; `ad-channel.channel_ref` → `channel-v2`. `AdChannelRepository.get_by_campaign_and_ad_channel_id` ya usa la ruta de filtro `ad_ref2.ad_set_ref2.funnel_flow_ref.campaign_ref`.

## Glossary

- **Sinergia**: servicio Flask (`flask_restplus`, Python 3.8, Flask 1.1.2) ubicado en `sinergia/`.
- **Fury**: servicio interno que consume el Service_Endpoint con la cabecera `X-Service-API-Key`.
- **Service_Endpoint**: el recurso `GET /hiluca/brand/<int:brand_id>/campaign/<int:campaign_id>/ad/<int:ad_id>/channel/<int:channel_id>/variant/<int:variant_id>/image/<string:image_id>` del namespace `service` (ruta completa `/api/v2/service/hiluca/...`), definido en `sinergia/app/v2/resources/service.py`.
- **Service_Auth**: el decorador `@service_api_key_required` de `app.tools.service_auth`.
- **GetAdVariantImageUseCase**: el caso de uso nuevo en `sinergia/app/v2/use_cases/image_library.py`, con el método público `execute(brand_id, campaign_id, ad_id, channel_id, variant_id, image_id) -> dict`.
- **CampaignRepository**: el repositorio de `sinergia/app/v2/repository/campaign.py` (content type `campaigns`).
- **AdChannelRepository**: el repositorio de `sinergia/app/v2/repository/ad_channel.py` (content type `ad-channels`).
- **ImageLibraryRepository**: el repositorio de `sinergia/app/v2/repository/image_library.py`, con el método existente `get_image(image_id, url_expiry=43200) -> dict`.
- **Campaign_Lookup**: el método nuevo de CampaignRepository que obtiene una campaña filtrando por `filters[id][$eq]=campaign_id` y `filters[brand_ref][id][$eq]=brand_id`. Devuelve el primer elemento de `data` o `None`.
- **Variant_Lookup**: el método nuevo de AdChannelRepository que obtiene un ad-channel filtrando por `filters[id][$eq]=variant_id`, `filters[ad_ref2][id][$eq]=ad_id`, `filters[ad_ref2][ad_set_ref2][funnel_flow_ref][campaign_ref][id][$eq]=campaign_id` y `filters[channel_ref][id][$eq]=channel_id`. Devuelve el primer elemento de `data` o `None`.
- **Image_Record**: el diccionario que devuelve `ImageLibraryRepository.get_image(image_id)`.
- **Existing_Image**: un Image_Record que es un `dict` no vacío y contiene una clave `url` cuyo valor es un `str` no vacío y no formado solo por espacios en blanco (espacios, tabuladores o saltos de línea).
- **Path_Params**: los seis argumentos de `execute`: `brand_id`, `campaign_id`, `ad_id`, `channel_id`, `variant_id` (enteros, según los conversores `<int:...>` de la ruta) e `image_id` (`str`).
- **Invalid_Param**: un Path_Param que es `None`, cadena vacía, cadena formada solo por espacios en blanco (incluidos espacios, tabuladores y saltos de línea) o el entero `0`. Coincide con la comprobación `if not x` usada por los casos de uso existentes, ampliada a cadenas con solo espacios en blanco. La cadena `"0"` NO es un Invalid_Param.
- **Variant_Image_Response**: el diccionario `{"id": image_id, "url": <Image_Record["url"]>, "prompt": <Image_Record["image_prompt"] o "">}`. Las tres claves son `str`.
- **Success_Envelope**: el cuerpo HTTP 200 `{"ok": True, "data": <Variant_Image_Response>}`, igual que los demás endpoints de `service.py`.
- **Error_Envelope**: el cuerpo HTTP 400 `{"ok": 0, "message": {"code": <code>, "text": <text>}}` que genera el `errorhandler` de `SinergiaException` en `sinergia/app/v2/__init__.py`.
- **ParametersNotFoundException**: excepción de dominio con código `PAR001`, definida en `sinergia/app/exceptions/base.py`.
- **DataNotFoundException**: excepción de dominio con código `DAT001`, definida en `sinergia/app/exceptions/base.py`.
- **ImageLibraryException**: excepción de dominio con código `IMG001`, que lanza el cliente de Image_Library ante fallos de red.
- **StrapiException**: excepción de dominio con código `STRAPI001`, subclase de `SinergiaException`, que lanza `StrapiClient` ante un fallo de red o un timeout de 30 segundos.
- **Unit_Test_Suite**: el archivo `sinergia/tests/v2/unit/use_cases/test_get_ad_variant_image.py`. Se ejecuta con `venv/bin/python -m pytest` desde `sinergia/`, usa `pytest-mock` (declarado como `pytest-mock==3.14.0` en `sinergia/requirements-test.txt`) y no accede a la red, a Strapi ni a Image_Library.

## Requirements

### Requirement 1: Endpoint de servicio

**User Story:** Como Fury, quiero obtener la imagen de una variante de anuncio con una ruta de servicio autenticada, para poder descargar la imagen base y resolver las URL de las variaciones editadas.

#### Acceptance Criteria

1. [Ubicuo] THE Service_Endpoint SHALL estar registrado como una única clase `Resource` en el namespace `service` de `sinergia/app/v2/resources/service.py`, con la ruta `/hiluca/brand/<int:brand_id>/campaign/<int:campaign_id>/ad/<int:ad_id>/channel/<int:channel_id>/variant/<int:variant_id>/image/<string:image_id>` (ruta completa `/api/v2/service/hiluca/...`), y SHALL definir solo el método `get`.
2. [Ubicuo] THE Service_Endpoint SHALL aplicar Service_Auth como decorador del método `get`, de modo que la validación de la cabecera `X-Service-API-Key` ocurra antes de ejecutar el cuerpo del método.
3. [Comportamiento no deseado] IF Service_Auth rechaza la petición (cabecera `X-Service-API-Key` ausente, valor distinto de la clave configurada o clave del servicio no configurada), THEN THE Service_Endpoint SHALL devolver la respuesta de rechazo que genera Service_Auth sin modificarla y sin instanciar GetAdVariantImageUseCase ni invocar `execute`.
4. [Dirigido por evento] WHEN el Service_Endpoint recibe una petición `GET` que Service_Auth acepta, THE Service_Endpoint SHALL instanciar GetAdVariantImageUseCase e invocar `execute(brand_id, campaign_id, ad_id, channel_id, variant_id, image_id)` exactamente una vez, con los Path_Params tal como los entregan los conversores de la ruta (`int` para los cinco primeros, `str` para `image_id`) y en ese orden posicional.
5. [Dirigido por evento] WHEN GetAdVariantImageUseCase devuelve una Variant_Image_Response, THE Service_Endpoint SHALL responder HTTP 200 con el Success_Envelope, cuyo valor `data` es el diccionario devuelto por `execute` sin añadir, eliminar ni modificar claves.
6. [Comportamiento no deseado] IF GetAdVariantImageUseCase lanza ParametersNotFoundException, DataNotFoundException, ImageLibraryException o cualquier otra subclase de `SinergiaException`, THEN THE Service_Endpoint SHALL propagar la excepción original sin capturarla, envolverla ni cambiar su código o texto, de modo que el `errorhandler` de `v2_blueprint` responda HTTP 400 con el Error_Envelope que contiene el código (`PAR001`, `DAT001` o `IMG001`) y el texto de esa excepción.
7. [Comportamiento no deseado] IF alguno de los segmentos `brand_id`, `campaign_id`, `ad_id`, `channel_id` o `variant_id` de la URL no es un entero no negativo representable por el conversor `<int:...>`, THEN THE Service_Endpoint SHALL no resolverse para esa petición y GetAdVariantImageUseCase SHALL no ser instanciado ni invocado.
8. [Ubicuo] THE Service_Endpoint SHALL delegar toda la lógica de validación de Path_Params y de acceso a datos en GetAdVariantImageUseCase, sin llamar directamente a CampaignRepository, AdChannelRepository, ImageLibraryRepository ni `StrapiClient`.

### Requirement 2: Construcción del caso de uso

**User Story:** Como desarrollador de Sinergia, quiero que el caso de uso siga el patrón existente, para poder sustituir sus colaboradores con mocks en las pruebas.

#### Acceptance Criteria

1. [Ubicuo] THE GetAdVariantImageUseCase SHALL estar definido en `sinergia/app/v2/use_cases/image_library.py` como una clase con un único método público (sin prefijo `_`) además de `__init__`: `execute(brand_id: int, campaign_id: int, ad_id: int, channel_id: int, variant_id: int, image_id: str) -> dict`.
2. [Ubicuo] THE GetAdVariantImageUseCase SHALL definir `__init__(self)` sin parámetros adicionales y crear en él exactamente una instancia de cada repositorio, asignada a los atributos `self.campaign_repository` (CampaignRepository), `self.ad_channel_repository` (AdChannelRepository) y `self.image_library_repository` (ImageLibraryRepository), igual que `GetProductImagesUseCase`.
3. [Dirigido por evento] WHEN se invoca `execute`, THE GetAdVariantImageUseCase SHALL acceder a Strapi e Image_Library solo a través de los atributos `self.campaign_repository`, `self.ad_channel_repository` y `self.image_library_repository`, sin crear instancias nuevas de repositorios ni de clientes HTTP dentro de `execute`, de modo que una prueba que sustituya esos tres atributos o sus clases con mocks de `pytest-mock` no genere ninguna llamada de red.
4. [Comportamiento no deseado] IF GetAdVariantImageUseCase está a punto de lanzar ParametersNotFoundException o DataNotFoundException, THEN THE GetAdVariantImageUseCase SHALL llamar exactamente una vez a `logger.error` del `logger` de módulo existente (`logging.getLogger(__name__)` de `image_library.py`) antes de lanzarla, con un mensaje que incluya el texto de la excepción. En el caso de DataNotFoundException, el mensaje SHALL incluir además los identificadores usados en la búsqueda fallida.
5. [Ubicuo] THE GetAdVariantImageUseCase SHALL reutilizar el `logger` de módulo y las importaciones de excepciones ya presentes en `image_library.py`, sin añadir una segunda llamada a `logging.basicConfig` ni un `logger` nuevo, y añadiendo solo las importaciones de CampaignRepository, AdChannelRepository y `from typing import Any, Dict`.
6. [Ubicuo] THE GetAdVariantImageUseCase SHALL usar en `execute` únicamente sintaxis y anotaciones de tipo válidas en Python 3.8 (por ejemplo `typing.Dict` u `Optional` en lugar de `dict[...]`, `list[...]` o `X | None`), de modo que `venv/bin/python -c "import app.v2.use_cases.image_library"` se ejecute sin errores desde `sinergia/`.

### Requirement 3: Validación de parámetros

**User Story:** Como Fury, quiero que una petición con parámetros inválidos se rechace antes de consultar Strapi o Image_Library, para recibir un error claro y no generar tráfico innecesario.

#### Acceptance Criteria

1. [Comportamiento no deseado] IF `brand_id` es un Invalid_Param (`None`, `""`, una cadena formada solo por espacios, tabuladores o saltos de línea, o el entero `0`), THEN THE GetAdVariantImageUseCase SHALL lanzar ParametersNotFoundException con el código `PAR001` y el texto exacto `Brand Id is required`.
2. [Comportamiento no deseado] IF `campaign_id` es un Invalid_Param (`None`, `""`, una cadena formada solo por espacios, tabuladores o saltos de línea, o el entero `0`), THEN THE GetAdVariantImageUseCase SHALL lanzar ParametersNotFoundException con el código `PAR001` y el texto exacto `Campaign Id is required`.
3. [Comportamiento no deseado] IF `ad_id` es un Invalid_Param (`None`, `""`, una cadena formada solo por espacios, tabuladores o saltos de línea, o el entero `0`), THEN THE GetAdVariantImageUseCase SHALL lanzar ParametersNotFoundException con el código `PAR001` y el texto exacto `Ad Id is required`.
4. [Comportamiento no deseado] IF `channel_id` es un Invalid_Param (`None`, `""`, una cadena formada solo por espacios, tabuladores o saltos de línea, o el entero `0`), THEN THE GetAdVariantImageUseCase SHALL lanzar ParametersNotFoundException con el código `PAR001` y el texto exacto `Channel Id is required`.
5. [Comportamiento no deseado] IF `variant_id` es un Invalid_Param (`None`, `""`, una cadena formada solo por espacios, tabuladores o saltos de línea, o el entero `0`), THEN THE GetAdVariantImageUseCase SHALL lanzar ParametersNotFoundException con el código `PAR001` y el texto exacto `Variant Id is required`.
6. [Comportamiento no deseado] IF `image_id` es un Invalid_Param (`None`, `""`, una cadena formada solo por espacios, tabuladores o saltos de línea, o el entero `0`), THEN THE GetAdVariantImageUseCase SHALL lanzar ParametersNotFoundException con el código `PAR001` y el texto exacto `Image Id is required`. La cadena `"0"` no es un Invalid_Param.
7. [Ubicuo] THE GetAdVariantImageUseCase SHALL validar los Path_Params en el orden `brand_id`, `campaign_id`, `ad_id`, `channel_id`, `variant_id`, `image_id` y lanzar una sola ParametersNotFoundException, la que corresponde al primer Invalid_Param de ese orden, aunque haya varios Invalid_Param en la misma llamada.
8. [Comportamiento no deseado] IF algún Path_Param es un Invalid_Param, THEN THE GetAdVariantImageUseCase SHALL lanzar ParametersNotFoundException sin invocar ningún método de CampaignRepository, AdChannelRepository ni ImageLibraryRepository, y sin devolver ningún valor desde `execute`.
9. [Comportamiento no deseado] IF un Path_Param es un Invalid_Param, THEN THE GetAdVariantImageUseCase SHALL registrar exactamente una entrada de error con el `logger` del módulo antes de lanzar ParametersNotFoundException.
10. [Dirigido por evento] WHEN ninguno de los seis Path_Params es un Invalid_Param (incluidos los enteros negativos y la cadena `"0"` en `image_id`), THE GetAdVariantImageUseCase SHALL terminar la validación sin lanzar ParametersNotFoundException y seguir con el Campaign_Lookup.
11. [Dirigido por evento] WHEN `image_id` contiene al menos un carácter que no es espacio en blanco, THE GetAdVariantImageUseCase SHALL usar `image_id` tal como llega, sin recortar los espacios del principio ni del final, tanto al llamar a `ImageLibraryRepository.get_image` como al rellenar `id` en la Variant_Image_Response.

### Requirement 4: Validación de la campaña

**User Story:** Como Fury, quiero que Sinergia compruebe que la campaña pertenece a la marca indicada, para no devolver imágenes de jerarquías incoherentes.

#### Acceptance Criteria

1. [Ubicuo] THE CampaignRepository SHALL ofrecer el Campaign_Lookup como un método nuevo (nombre propuesto: `get_by_id_and_brand(campaign_id, brand_id)`) que, igual que `get_by_id_brand_and_account`, invoca `self.get(self.content_type, params)` una sola vez con exactamente los filtros `filters[id][$eq]=campaign_id` y `filters[brand_ref][id][$eq]=brand_id`, sin añadir filtros por `account_ref` ni otros campos.
2. [Dirigido por evento] WHEN todos los Path_Params son válidos según el Requisito 3, THE GetAdVariantImageUseCase SHALL invocar el Campaign_Lookup exactamente una vez con los argumentos `campaign_id` y `brand_id` recibidos en `execute`, sin transformarlos, y antes de invocar el Variant_Lookup o `ImageLibraryRepository.get_image`.
3. [Comportamiento no deseado] IF el Campaign_Lookup devuelve `None`, THEN THE GetAdVariantImageUseCase SHALL registrar el error con el `logger` de módulo y lanzar DataNotFoundException (código `DAT001`) con el texto `Campaign not found for brand`, de modo que el Service_Endpoint responda HTTP 400 con el Error_Envelope.
4. [Comportamiento no deseado] IF el Campaign_Lookup devuelve `None`, THEN THE GetAdVariantImageUseCase SHALL lanzar DataNotFoundException sin invocar el Variant_Lookup ni `ImageLibraryRepository.get_image` (ambos con cero llamadas).
5. [Comportamiento no deseado] IF la respuesta de Strapi al Campaign_Lookup es `None`, un valor falsy, no contiene la clave `data` o tiene una lista `data` vacía, THEN THE CampaignRepository SHALL devolver `None`; en cualquier otro caso SHALL devolver el primer elemento de `data`.
6. [Dirigido por evento] WHEN el Campaign_Lookup devuelve un valor distinto de `None`, THE GetAdVariantImageUseCase SHALL considerar la campaña válida y continuar con el Requisito 5, sin validar campos adicionales del registro de campaña devuelto.
7. [Comportamiento no deseado] IF el Campaign_Lookup lanza una excepción, THEN THE GetAdVariantImageUseCase SHALL propagarla sin capturarla ni convertirla, y SHALL NOT invocar el Variant_Lookup ni `ImageLibraryRepository.get_image`.

### Requirement 5: Validación de la variante (ad-channel)

**User Story:** Como Fury, quiero que Sinergia compruebe que la variante pertenece al anuncio, a la campaña y al canal indicados, para garantizar la coherencia de la ruta solicitada.

#### Acceptance Criteria

1. [Ubicuo] THE AdChannelRepository SHALL ofrecer el Variant_Lookup como un método nuevo (nombre propuesto: `get_by_id_ad_campaign_and_channel(ad_channel_id, ad_id, campaign_id, channel_id)`) que hereda el cliente de `StrapiClient`, realiza una única petición `GET` al content type `ad-channels` con los cuatro filtros `filters[...][$eq]` definidos en el Glosario aplicados de forma conjunta (todos deben cumplirse) y devuelve el primer elemento de `data` como `dict`.
2. [Dirigido por evento] WHEN el Campaign_Lookup devuelve una campaña distinta de `None`, THE GetAdVariantImageUseCase SHALL invocar el Variant_Lookup exactamente una vez con los argumentos `variant_id`, `ad_id`, `campaign_id` y `channel_id`, en ese orden y con los mismos valores recibidos en `execute`.
3. [Comportamiento no deseado] IF el Variant_Lookup devuelve `None`, THEN THE GetAdVariantImageUseCase SHALL registrar el error con el `logger` de módulo y lanzar DataNotFoundException (código `DAT001`) con el texto `Ad variant not found`.
4. [Comportamiento no deseado] IF el Variant_Lookup devuelve `None`, THEN THE GetAdVariantImageUseCase SHALL lanzar DataNotFoundException sin invocar `ImageLibraryRepository.get_image`.
5. [Comportamiento no deseado] IF la respuesta de Strapi al Variant_Lookup es `None`, no contiene la clave `data`, tiene `data` igual a `None` o tiene una lista `data` vacía, THEN THE AdChannelRepository SHALL devolver `None` sin lanzar excepción.
6. [Comportamiento no deseado] IF existe un ad-channel con id `variant_id` pero no cumple alguno de los filtros `ad_id`, `campaign_id` o `channel_id`, THEN THE AdChannelRepository SHALL devolver `None` en el Variant_Lookup, de modo que THE GetAdVariantImageUseCase lance DataNotFoundException con el texto `Ad variant not found`.
7. [Comportamiento no deseado] IF la petición del Variant_Lookup a Strapi falla por un error de red o supera el timeout de 30 segundos de `StrapiClient`, THEN THE GetAdVariantImageUseCase SHALL propagar sin modificar la `StrapiException` (código `STRAPI001`, subclase de `SinergiaException`) sin invocar `ImageLibraryRepository.get_image`, de modo que el Service_Endpoint responda HTTP 400 con el Error_Envelope.

### Requirement 6: Obtención de la imagen

**User Story:** Como Fury, quiero recibir la URL y el prompt de la imagen solicitada, para poder descargarla y reutilizar su descripción.

#### Acceptance Criteria

1. [Dirigido por evento] WHEN el Variant_Lookup devuelve un ad-channel distinto de `None`, THE GetAdVariantImageUseCase SHALL invocar `ImageLibraryRepository.get_image(image_id)` exactamente una vez por llamada a `execute`, con el `image_id` recibido como único argumento posicional y sin pasar `url_expiry`, de modo que se aplique su valor por defecto (`43200`).
2. [Comportamiento no deseado] IF el Image_Record no es un Existing_Image (es `None`, no es un `dict`, es un `dict` vacío, no contiene la clave `url`, o el valor de `url` no es un `str`, es `""` o está formado solo por espacios, incluido el cuerpo de error JSON que Image_Library devuelve para un `image_id` inexistente), THEN THE GetAdVariantImageUseCase SHALL lanzar DataNotFoundException con el texto `Image not found` y no devolver ninguna Variant_Image_Response.
3. [Comportamiento no deseado] IF `ImageLibraryRepository.get_image` lanza ImageLibraryException, THEN THE GetAdVariantImageUseCase SHALL propagar la misma instancia de ImageLibraryException (mismo código `IMG001` y mismo texto), sin envolverla en DataNotFoundException ni en otra excepción y sin devolver ninguna Variant_Image_Response.
4. [Ubicuo] THE GetAdVariantImageUseCase SHALL validar únicamente la existencia de la imagen según la definición de Existing_Image, sin comprobar ninguna clave del Image_Record que relacione la imagen con la marca, el anuncio o la variante, y sin realizar llamadas adicionales a CampaignRepository, AdChannelRepository ni ImageLibraryRepository después de `get_image`.
5. [Dirigido por evento] WHEN el Image_Record es un Existing_Image, THE GetAdVariantImageUseCase SHALL devolver una Variant_Image_Response con exactamente las claves `id`, `url` y `prompt`, sin incluir ninguna otra clave del Image_Record.
6. [Ubicuo] THE GetAdVariantImageUseCase SHALL asignar a `id` de la Variant_Image_Response el `image_id` recibido como argumento de `execute`, sin modificarlo e independientemente de cualquier clave `id` presente en el Image_Record.
7. [Ubicuo] THE GetAdVariantImageUseCase SHALL asignar a `url` de la Variant_Image_Response el valor de `url` del Image_Record sin modificarlo (sin recortar espacios, codificar ni reescribir la cadena).
8. [Dirigido por evento] WHEN el Image_Record contiene `image_prompt` con un valor de tipo `str` (incluida la cadena vacía), THE GetAdVariantImageUseCase SHALL asignar ese valor sin modificar a `prompt` de la Variant_Image_Response.
9. [Comportamiento no deseado] IF el Image_Record no contiene `image_prompt`, o su valor es `None`, o su valor no es de tipo `str`, THEN THE GetAdVariantImageUseCase SHALL asignar `""` a `prompt` de la Variant_Image_Response y devolver la respuesta sin lanzar ninguna excepción.
10. [Ubicuo] FOR ALL Existing_Image con cualquier conjunto de claves adicionales y con `image_prompt` ausente, `None`, `str` o de otro tipo, THE GetAdVariantImageUseCase SHALL devolver una Variant_Image_Response cuyo conjunto de claves sea exactamente `{"id", "url", "prompt"}` y cuyos tres valores sean `str` (propiedad invariante).

### Requirement 7: Pruebas unitarias

**User Story:** Como desarrollador de Sinergia, quiero pruebas unitarias aisladas del caso de uso, para detectar regresiones sin depender de Strapi ni de Image_Library.

#### Acceptance Criteria

1. [Ubicuo] THE Unit_Test_Suite SHALL estar formado por un único archivo, `sinergia/tests/v2/unit/use_cases/test_get_ad_variant_image.py`, sin crear archivos de prueba, fixtures ni `conftest.py` nuevos fuera de `sinergia/tests/v2/unit/use_cases/`.
2. [Ubicuo] THE Unit_Test_Suite SHALL sustituir CampaignRepository, AdChannelRepository e ImageLibraryRepository por mocks de `pytest-mock` aplicados en el módulo donde los importa el caso de uso (`app.v2.use_cases.image_library.CampaignRepository`, `app.v2.use_cases.image_library.AdChannelRepository` y `app.v2.use_cases.image_library.ImageLibraryRepository`) antes de instanciar GetAdVariantImageUseCase, de forma que ninguna prueba instancie un repositorio real ni realice llamadas HTTP a Strapi o a Image_Library.
3. [Ubicuo] THE Unit_Test_Suite SHALL ejecutarse con `venv/bin/python -m pytest tests/v2/unit/use_cases/test_get_ad_variant_image.py -q` desde `sinergia/` con 0 pruebas fallidas, 0 errores y 0 pruebas omitidas, sin acceso a red y en menos de 60 segundos.
4. [Ubicuo] THE Unit_Test_Suite SHALL anotar cada función de prueba con el tipo de retorno `-> None`.
5. [Ubicuo] THE Unit_Test_Suite SHALL cubrir con al menos una prueba, según la tabla de trazabilidad, cada uno de los criterios 2.2 a 2.4, 3.1 a 3.11, 4.2 a 4.4, 4.6, 4.7, 5.2 a 5.4, 5.7 y 6.1 a 6.10. Los criterios 1.1 a 1.8, 2.1, 2.5, 2.6, 4.1, 4.5, 5.1, 5.5 y 5.6 quedan fuera del Unit_Test_Suite y se verifican por revisión de código o con una prueba de integración opcional; el efecto del criterio 5.6 sobre el caso de uso queda cubierto por las pruebas del criterio 5.3.
6. [Ubicuo] THE Unit_Test_Suite SHALL verificar, en cada prueba de un camino de error, tanto la clase de la excepción lanzada (ParametersNotFoundException, DataNotFoundException, ImageLibraryException o StrapiException) como su texto exacto definido en los Requisitos 3 a 6 cuando el texto lo define esta spec.
7. [Ubicuo] THE Unit_Test_Suite SHALL implementar la prueba de propiedad del criterio 6.10 con `hypothesis` (ya declarado como `hypothesis==6.112.2` en `sinergia/requirements-test.txt`), con `@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])`, igual que las pruebas de propiedad existentes en `sinergia/tests/v2/unit/use_cases/`.

## Trazabilidad requisito → prueba unitaria

Todas las pruebas están en `sinergia/tests/v2/unit/use_cases/test_get_ad_variant_image.py`. Los nombres son propuestas para la fase de diseño.

| Criterio | Patrón EARS | Prueba esperada | Tipo |
|---|---|---|---|
| 2.2 | Ubicuo | `test_init_instantiates_repositories` | Ejemplo |
| 2.3 | Dirigido por evento | `test_execute_uses_injected_repositories_only` (las clases de repositorio parcheadas se instancian una sola vez, en `__init__`, y `execute` solo usa los tres atributos) | Ejemplo |
| 2.4, 3.9 | Comportamiento no deseado | `test_errors_are_logged_once_before_raising` (con `caplog` o `mocker` sobre `logger`; parametrizada por camino de error: parámetro inválido, campaña no encontrada, variante no encontrada, imagen no encontrada), que comprueba una sola llamada a `logger.error` con el texto de la excepción y, en los casos de DataNotFoundException, los identificadores de la búsqueda | Ejemplo parametrizado |
| 3.1 – 3.6 | Comportamiento no deseado | `test_invalid_param_raises_parameters_not_found` (parametrizada por parámetro y por valor: `None`, `""`, `"   "`, `"\t\n"`, `0`), que comprueba el código `PAR001` y el texto exacto de la excepción | Ejemplo parametrizado |
| 3.7 | Ubicuo | `test_validation_reports_first_invalid_param_in_order` | Ejemplo |
| 3.8 | Comportamiento no deseado | `test_invalid_param_does_not_call_repositories` (comprueba `assert_not_called` en los tres repositorios) | Ejemplo parametrizado |
| 3.10 | Dirigido por evento | `test_valid_edge_values_pass_validation` (enteros negativos en los cinco identificadores numéricos e `image_id="0"`), que comprueba que se invoca el Campaign_Lookup | Ejemplo parametrizado |
| 3.11 | Dirigido por evento | `test_image_id_is_not_trimmed` (`image_id` con espacios al principio y al final llega igual a `get_image` y a `id`) | Ejemplo |
| 4.2 | Dirigido por evento | `test_success_calls_campaign_lookup_with_campaign_and_brand` | Ejemplo |
| 4.3, 4.4 | Comportamiento no deseado | `test_campaign_not_found_raises_and_short_circuits` | Ejemplo |
| 4.6 | Dirigido por evento | `test_campaign_found_continues_to_variant_lookup` (cualquier valor distinto de `None`, incluido un `dict` mínimo, continúa al Variant_Lookup) | Ejemplo parametrizado |
| 4.7 | Comportamiento no deseado | `test_campaign_lookup_exception_propagates` (misma instancia propagada; Variant_Lookup y `get_image` sin llamadas) | Ejemplo |
| 5.2 | Dirigido por evento | `test_success_calls_variant_lookup_with_expected_args` | Ejemplo |
| 5.3, 5.4 | Comportamiento no deseado | `test_variant_not_found_raises_and_short_circuits` (cubre también, a nivel de caso de uso, el efecto del criterio 5.6) | Ejemplo |
| 5.7 | Comportamiento no deseado | `test_variant_lookup_strapi_exception_propagates` (misma instancia de StrapiException con código `STRAPI001`; `get_image` sin llamadas) | Ejemplo |
| 6.1, 6.4 | Dirigido por evento / Ubicuo | `test_success_calls_get_image_once` (una sola llamada con `image_id` como único argumento posicional, sin `url_expiry`, y sin llamadas adicionales a los repositorios después de `get_image`) | Ejemplo |
| 6.2 | Comportamiento no deseado | `test_image_not_found_raises_data_not_found` (parametrizada: `None`, valor que no es `dict` (lista, cadena), `{}`, dict sin `url`, `url` que no es `str`, `url` vacía, `url` formada solo por espacios en blanco, cuerpo de error de Image_Library) | Ejemplo parametrizado |
| 6.3 | Comportamiento no deseado | `test_image_library_exception_propagates` | Ejemplo |
| 6.5 – 6.8 | Dirigido por evento / Ubicuo | `test_success_returns_id_url_prompt` | Ejemplo |
| 6.9 | Comportamiento no deseado | `test_missing_or_null_image_prompt_returns_empty_string` (parametrizada: clave ausente, `None`, valor que no es `str` como `int`, `list` o `dict`) | Ejemplo parametrizado |
| 6.10 | Ubicuo (invariante) | `test_property_response_keys_and_types` con `hypothesis`: genera Existing_Image con claves extra arbitrarias e `image_prompt` ausente, `None`, `str` o de cualquier otro tipo | Propiedad |

Quedan fuera del Unit_Test_Suite, por indicación de `structure.md` (las pruebas unitarias cubren casos de uso):

- Los criterios 1.1 a 1.8 del endpoint. Se verifican por revisión de código o con una prueba de integración opcional en `tests/v2/integration/`.
- Los criterios 2.1, 2.5 y 2.6 de estructura del módulo. Se verifican por revisión de código (2.6 también con `venv/bin/python -c "import app.v2.use_cases.image_library"`).
- Los criterios 4.1, 4.5, 5.1, 5.5 y 5.6 de los repositorios. Se verifican por revisión de código. El efecto del criterio 5.6 sobre el caso de uso queda cubierto por `test_variant_not_found_raises_and_short_circuits` (criterio 5.3).
