# Requirements Document

## Introduction

Sinergia necesita un punto de entrada para el pipeline de edición de imágenes de variantes de anuncio de Fury (`fury/.kiro/specs/ad-variant-image-edit-pipeline`). El usuario de HiLuca elige una imagen de una variante (ad-channel), indica una instrucción libre (`custom_prompt`), una opción de expansión/zoom (`expand_zoom_option`) o ambas, y el número de variaciones. Sinergia valida la petición y la pertenencia de la campaña, la variante y la imagen a la cuenta del usuario, encola el job en Fury con `POST /api/v2/variants/image/edit` y devuelve el identificador del job.

Esta spec añade en Sinergia:

- El caso de uso `EditAdVariantImageUseCase` en `sinergia/app/v2/use_cases/ad.py`.
- El endpoint `POST /hiluca/brand/campaign/ad/channel/media/image/edit` en `sinergia/app/v2/resources/ad.py`, con su modelo de documentación Swagger.
- Pruebas unitarias en `sinergia/tests/v2/unit/use_cases/test_edit_ad_variant_image_use_case.py`.

No se crean repositorios ni métodos de repositorio nuevos, y no se modifican `FuryClient` ni las excepciones existentes.

Decisiones confirmadas por el usuario:

1. El `image_id` de la petición se envía a Fury como `id_base_image`. El resto de campos conservan su nombre.
2. La cuenta se obtiene con `AccountRepository.get_by_email(user_id)`. La Parent_Account es el id de `attributes.parent_account.data` o, si no existe, el id de la cuenta (patrón existente).
3. No se valida la marca por separado: el Campaign_Lookup ya filtra por campaña, marca y cuenta. No se usan `AdRepository` ni `BrandRepository`.
4. Sinergia replica las validaciones del esquema `AdVariantImageEditCreate` de Fury (`fury/app/schemas/pipeline_schemas.py`): IDs enteros ≥ 1; `image_name` e `image_id` recortados y de 1 a 255 caracteres; `n_variations` entero de 1 a 10; `custom_prompt` recortado, vacío o solo espacios equivale a ausente, máximo 2000 caracteres; `expand_zoom_option` enum sensible a mayúsculas.
5. Un parámetro obligatorio ausente o vacío lanza ParametersNotFoundException. Un valor inválido (tipo, rango, enum, longitud, o falta de `custom_prompt` y `expand_zoom_option`) lanza IncorrectValidationException.
6. La FuryException que lanza `FuryClient` se propaga. Si la respuesta de Fury no contiene `data.edit_job_id`, se lanza FuryException.
7. Los IDs y `n_variations` deben llegar como `int` JSON. Un `bool`, un `float` o una cadena numérica (p. ej. `"5"`) se rechazan con IncorrectValidationException.
8. `expand_zoom_option` ausente o `null` equivale a "sin opción". Cualquier otro valor, incluida la cadena vacía, debe coincidir exactamente con uno de los 7 valores; si no, se rechaza.
9. La comparación del `image_id` con los elementos de `media_images_banner` es una igualdad exacta `==` entre el `image_id` recortado y el valor `image_id` del elemento, sin conversión de tipos.

Hechos del código inspeccionado que fijan el comportamiento:

- `SinergiaException` y sus subclases se convierten en HTTP 400 con cuerpo `{"ok": 0, "message": {"code": <code>, "text": <text>}}` mediante el `errorhandler` de `sinergia/app/v2/__init__.py`.
- Códigos de `sinergia/app/exceptions/base.py`: ParametersNotFoundException `PAR001`, IncorrectValidationException `SYSVAL001`, DataNotFoundException `DAT001`, FuryException `FURY001`.
- `FuryClient.post(endpoint, data)` (`sinergia/app/tools/fury.py`) envía JSON con timeout de 30 segundos, llama a `raise_for_status()` y convierte cualquier `requests.exceptions.RequestException` en `FuryException("Failed to POST <endpoint>")`. Ante éxito devuelve `response.json()`.
- Fury responde HTTP 201 con `{"ok": 1, "data": {"edit_job_id": <str>, "status": "RUNNING", "poll_url": "/api/v2/jobs/<id>"}}` (`AdVariantImageEditJobResponse`).
- Los casos de uso de `ad.py` (p. ej. `GenerateAnAdVariantUseCase`) reciben el email de la cuenta en el constructor, instancian repositorios y `FuryClient` en `__init__` y los endpoints devuelven `{'ok': 1, 'data': data}, 200`.
- Cada elemento de `attributes.media_images_banner` de un ad-channel es un diccionario que puede contener `image_id` (ver `UpdateAdChannelGenerationFuryUseCase`).

## Glossary

- **Sinergia**: servicio Flask (`flask_restplus`, Python 3.8, Flask 1.1.2) ubicado en `sinergia/`.
- **Fury**: servicio interno que ejecuta el pipeline de edición de imágenes.
- **Edit_Endpoint**: el recurso `POST /hiluca/brand/campaign/ad/channel/media/image/edit` del namespace `ad_ns` en `sinergia/app/v2/resources/ad.py`.
- **EditAdVariantImageUseCase**: el caso de uso nuevo en `sinergia/app/v2/use_cases/ad.py`, con constructor `__init__(self, user_id: str)` y método público `execute(payload: Dict[str, Any]) -> Dict[str, str]`.
- **Edit_Payload**: el cuerpo JSON de la petición (`request.json`) que recibe `execute`, con las claves `brand_id`, `campaign_id`, `ad_id`, `channel_id`, `variant_id`, `image_name`, `image_id`, `n_variations`, `custom_prompt` y `expand_zoom_option`.
- **Required_Fields**: las 8 claves obligatorias del Edit_Payload, en este orden: `brand_id`, `campaign_id`, `ad_id`, `channel_id`, `variant_id`, `image_name`, `image_id`, `n_variations`.
- **ID_Fields**: `brand_id`, `campaign_id`, `ad_id`, `channel_id` y `variant_id`.
- **Missing_Value**: el valor de una clave ausente del Edit_Payload, `None`, o un `str` para el que `valor.strip() == ""`.
- **Valid_Integer**: un valor de tipo `int` que no es `bool`.
- **ExpandZoomOption_Values**: las 7 cadenas `TOP`, `BOTTOM`, `LEFT`, `RIGHT`, `ZOOM_2X`, `ZOOM_1_5X` y `ZOOM_1_25X`, comparadas sensibles a mayúsculas y sin recortar espacios.
- **Normalized_Custom_Prompt**: `custom_prompt` recortado de espacios iniciales y finales, o `None` si el valor es ausente, `None` o queda vacío tras el recorte.
- **AccountRepository**: repositorio de `sinergia/app/v2/repository/account.py`, con el método `get_by_email(email)`.
- **CampaignRepository**: repositorio de `sinergia/app/v2/repository/campaign.py`, con el método `get_by_id_brand_and_account(campaign_id, brand_id, account_id)` (Campaign_Lookup).
- **AdChannelRepository**: repositorio de `sinergia/app/v2/repository/ad_channel.py`, con el método `get_by_id_ad_campaign_and_channel(ad_channel_id, ad_id, campaign_id, channel_id)` (Variant_Lookup).
- **Parent_Account**: `account['attributes']['parent_account']['data']['id']` si ese `data` existe y no es falsy; en otro caso, `account['id']`.
- **Ad_Variant**: el ad-channel devuelto por el Variant_Lookup.
- **Banner_Images**: la lista `Ad_Variant['attributes']['media_images_banner']`; se considera una lista vacía si falta, es `None` o no es una lista.
- **FuryClient**: cliente HTTP de `sinergia/app/tools/fury.py`.
- **Fury_Edit_Payload**: el diccionario enviado a Fury, con exactamente las 10 claves de `AdVariantImageEditCreate`: `brand_id`, `campaign_id`, `ad_id`, `channel_id`, `variant_id`, `image_name`, `id_base_image`, `n_variations`, `custom_prompt` y `expand_zoom_option`.
- **Fury_Response**: el valor devuelto por `FuryClient.post`.
- **Edit_Job_Id**: el valor `Fury_Response['data']['edit_job_id']`.
- **Success_Envelope**: el cuerpo HTTP 200 `{"ok": 1, "data": {"job_id": <Edit_Job_Id>}}`.
- **Error_Envelope**: el cuerpo HTTP 400 `{"ok": 0, "message": {"code": <code>, "text": <text>}}` que genera el `errorhandler` de `SinergiaException`.
- **Unit_Test_Suite**: el archivo `sinergia/tests/v2/unit/use_cases/test_edit_ad_variant_image_use_case.py`, ejecutado con `venv/bin/python -m pytest` desde `sinergia/`.

## Requirements

### Requirement 1: Endpoint de edición

**User Story:** Como usuario administrador de HiLuca, quiero solicitar la edición de una imagen de una variante de anuncio, para obtener variaciones editadas sin esperar a que terminen.

#### Acceptance Criteria

1. [Ubicuo] THE Edit_Endpoint SHALL estar definido como una clase que hereda de `ProxySecureResource` (importada de `app.v1.resources.base`, que a su vez hereda de `Resource`), con un nombre de clase que no exista ya en `sinergia/app/v2/resources/ad.py`, decorada a nivel de clase con `@ad_ns.route('/hiluca/brand/campaign/ad/channel/media/image/edit')` y `@v2_api.expect(secureHeader)`, y con `post` como único método HTTP.
2. [Ubicuo] THE Edit_Endpoint SHALL aplicar al método `post` los decoradores en este orden, de arriba abajo: `@ad_ns.doc(...)`, `@v2_api.expect(<modelo del Edit_Payload>)`, `@jwt_required` y `@check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)`, igual que `HilucaResourceAdChannelVariantGenerate` en `ad.py`.
3. [Comportamiento no deseado] IF `@jwt_required` o `@check_access` rechazan la petición, THEN THE Edit_Endpoint SHALL devolver la respuesta de rechazo del decorador sin instanciar EditAdVariantImageUseCase.
4. [Ubicuo] THE Edit_Endpoint SHALL definir en `ad.py` un modelo `v2_api.model` con `fields` de `flask_restplus` que documente las 10 claves del Edit_Payload (`fields.Integer` para los ID_Fields y `n_variations`; `fields.String` para `image_name`, `image_id`, `custom_prompt` y `expand_zoom_option`), con un nombre de modelo que no exista ya en `ad.py`, y usarlo en el `@v2_api.expect` del método `post` del criterio 2.
5. [Dirigido por evento] WHEN el Edit_Endpoint recibe una petición autorizada, THE Edit_Endpoint SHALL obtener `user_id = self.checkCredentials()['username']`, instanciar `EditAdVariantImageUseCase(user_id)` e invocar `execute(request.json)` exactamente una vez, pasando `request.json` sin modificar (incluido `None` si no hay cuerpo JSON).
6. [Dirigido por evento] WHEN `execute` devuelve un resultado, THE Edit_Endpoint SHALL responder HTTP 200 con `{"ok": 1, "data": <resultado>}`, sin modificar el resultado.
7. [Comportamiento no deseado] IF EditAdVariantImageUseCase lanza una subclase de `SinergiaException`, THEN THE Edit_Endpoint SHALL propagarla sin capturarla, de modo que el `errorhandler` de `v2_blueprint` responda HTTP 400 con el Error_Envelope.
8. [Ubicuo] THE Edit_Endpoint SHALL delegar toda la validación, el acceso a datos y la llamada a Fury en EditAdVariantImageUseCase, sin llamar directamente a repositorios ni a FuryClient, y sin bloques `try/except` en el método `post`.

### Requirement 2: Construcción del caso de uso

**User Story:** Como desarrollador de Sinergia, quiero que el caso de uso siga el patrón de `ad.py`, para poder sustituir sus colaboradores con mocks en las pruebas.

#### Acceptance Criteria

1. [Ubicuo] THE EditAdVariantImageUseCase SHALL estar definido en `sinergia/app/v2/use_cases/ad.py` con un constructor `__init__(self, user_id: str)` y un único método público `execute(self, payload: Dict[str, Any]) -> Dict[str, str]`; los métodos auxiliares SHALL tener nombres que empiecen por `_`.
2. [Ubicuo] THE EditAdVariantImageUseCase SHALL guardar `user_id` en `self.user_id` y crear en `__init__` exactamente una instancia de cada colaborador, usando los nombres ya importados en `ad.py`: `self.account_repo = AccountRepository()`, `self.campaign_repo = CampaignRepository()`, `self.ad_channel_repo = AdChannelRepository()` y `self.fury_client = FuryClient()`.
3. [Ubicuo] THE EditAdVariantImageUseCase SHALL acceder a Strapi y a Fury únicamente a través de los cuatro atributos del criterio 2, sin instanciar AdRepository, BrandRepository ni otros repositorios o clientes, ni en `__init__` ni en `execute`.
4. [Ubicuo] THE EditAdVariantImageUseCase SHALL usar el `logger` de módulo existente de `ad.py` (`logging.getLogger(__name__)`) y llamar a `logger.error` exactamente una vez antes de lanzar cada ParametersNotFoundException, IncorrectValidationException, DataNotFoundException o FuryException creada por el propio caso de uso, con un mensaje que incluya el texto de la excepción; las excepciones propagadas sin envolver (Requisitos 5.4, 6.4, 7.3 y 9.5) no requieren esa llamada.
5. [Ubicuo] THE EditAdVariantImageUseCase SHALL importar IncorrectValidationException y FuryException desde `app.exceptions.base` y usar solo sintaxis y anotaciones válidas en Python 3.8 (`typing.Dict`, `Any`, `Optional`, `List`; sin `dict[...]`/`list[...]` ni uniones con `|`), de modo que `venv/bin/python -c "import app.v2.use_cases.ad"` termine con código de salida 0 desde `sinergia/`.
6. [Ubicuo] THE EditAdVariantImageUseCase SHALL definir los ExpandZoomOption_Values, el rango de `n_variations` (1 a 10) y las longitudes máximas (255 y 2000) como constantes de módulo o de clase en `ad.py`, sin repetir esos literales dentro de `execute` ni de sus métodos auxiliares.

### Requirement 3: Presencia de parámetros obligatorios

**User Story:** Como usuario de HiLuca, quiero que una petición incompleta se rechace antes de consultar Strapi o Fury, para recibir un error claro.

#### Acceptance Criteria

1. [Comportamiento no deseado] IF `payload` no es un `dict` (incluido `None`), THEN THE EditAdVariantImageUseCase SHALL lanzar ParametersNotFoundException (`PAR001`) con el texto exacto `Payload is required`.
2. [Comportamiento no deseado] IF alguna de las Required_Fields tiene un Missing_Value, THEN THE EditAdVariantImageUseCase SHALL lanzar ParametersNotFoundException (`PAR001`) con el texto exacto `<campo> is required`, donde `<campo>` es el nombre de la clave (p. ej. `brand_id is required`). Esto aplica a todas las Required_Fields por igual, incluidos los ID_Fields y `n_variations` (p. ej. `brand_id = "   "` o `n_variations = ""` lanzan `PAR001`).
3. [Ubicuo] THE EditAdVariantImageUseCase SHALL determinar si un `str` está vacío o formado solo por espacios en blanco con `valor.strip() == ""` (`str.strip()` sin argumentos), y SHALL tratar como valores presentes (no Missing_Value) todos los demás, incluidos `0`, `False`, `[]`, `{}` y cualquier `str` con al menos un carácter tras el recorte (p. ej. `"5"` o `"abc"`), que pasan a validarse en el Requisito 4.
4. [Ubicuo] THE EditAdVariantImageUseCase SHALL comprobar la presencia de las Required_Fields en el orden del Glosario y lanzar solo la ParametersNotFoundException del primer campo con Missing_Value.
5. [Ubicuo] THE EditAdVariantImageUseCase SHALL completar las comprobaciones de presencia del Requisito 3 antes de cualquier comprobación de valor del Requisito 4, de modo que una petición con un campo ausente y otro inválido lance ParametersNotFoundException, aunque el campo inválido aparezca antes en el orden del Glosario.
6. [Ubicuo] THE EditAdVariantImageUseCase SHALL tratar `custom_prompt` y `expand_zoom_option` como opcionales, sin lanzar ParametersNotFoundException por su ausencia ni por ningún valor que tengan.

### Requirement 4: Validación de valores

**User Story:** Como usuario de HiLuca, quiero que Sinergia aplique las mismas reglas que Fury, para recibir el error en Sinergia y no un fallo de Fury.

#### Acceptance Criteria

1. [Comportamiento no deseado] IF algún ID_Field no es un Valid_Integer (p. ej. `True`, `5.0`, `"5"`, `"abc"`, `[]`) o es menor que 1, THEN THE EditAdVariantImageUseCase SHALL lanzar IncorrectValidationException (`SYSVAL001`) con el texto exacto `<campo> must be an integer greater than or equal to 1`.
2. [Comportamiento no deseado] IF `n_variations` no es un Valid_Integer, o es menor que 1 o mayor que 10 (rango válido de 1 a 10, ambos incluidos), THEN THE EditAdVariantImageUseCase SHALL lanzar IncorrectValidationException con el texto exacto `n_variations must be an integer between 1 and 10`.
3. [Comportamiento no deseado] IF `image_name` o `image_id` no es un `str`, o su longitud tras `str.strip()` supera 255 caracteres, THEN THE EditAdVariantImageUseCase SHALL lanzar IncorrectValidationException con el texto exacto `<campo> must be a string of at most 255 characters`. La longitud mínima de 1 carácter tras el recorte la garantiza el Requisito 3, por lo que este criterio no comprueba un mínimo, y los espacios iniciales y finales no cuentan para el máximo (p. ej. `"  " + "a"*255 + "  "` es válido).
4. [Comportamiento no deseado] IF `custom_prompt` está presente y no es `None` ni un `str`, o su Normalized_Custom_Prompt supera 2000 caracteres, THEN THE EditAdVariantImageUseCase SHALL lanzar IncorrectValidationException con el texto exacto `custom_prompt must be a string of at most 2000 characters`. Un `custom_prompt` igual a `""` o solo con espacios no es un error de este criterio (su Normalized_Custom_Prompt es `None`).
5. [Comportamiento no deseado] IF `expand_zoom_option` está presente y no es `None`, y no es un `str` idéntico a uno de los ExpandZoomOption_Values (p. ej. `"top"`, `"ZOOM_3X"`, `" TOP"` o `""`), THEN THE EditAdVariantImageUseCase SHALL lanzar IncorrectValidationException con el texto exacto `expand_zoom_option must be one of: TOP, BOTTOM, LEFT, RIGHT, ZOOM_2X, ZOOM_1_5X, ZOOM_1_25X`.
6. [Comportamiento no deseado] IF el Normalized_Custom_Prompt es `None` y `expand_zoom_option` es ausente o `None`, THEN THE EditAdVariantImageUseCase SHALL lanzar IncorrectValidationException con el texto exacto `custom_prompt or expand_zoom_option is required`.
7. [Ubicuo] THE EditAdVariantImageUseCase SHALL aplicar los criterios 1 a 6 en el orden `brand_id`, `campaign_id`, `ad_id`, `channel_id`, `variant_id`, `image_name`, `image_id`, `n_variations`, `custom_prompt`, `expand_zoom_option` y, por último, el criterio 6, lanzando solo la excepción del primer incumplimiento.
8. [Comportamiento no deseado] IF el Requisito 3 o el Requisito 4 lanzan una excepción, THEN THE EditAdVariantImageUseCase SHALL lanzarla con cero invocaciones de AccountRepository, CampaignRepository, AdChannelRepository y FuryClient.
9. [Dirigido por evento] WHEN el Edit_Payload supera los Requisitos 3 y 4, THE EditAdVariantImageUseCase SHALL usar en los pasos siguientes `image_name` e `image_id` recortados con `str.strip()` y `custom_prompt` igual al Normalized_Custom_Prompt.

### Requirement 5: Validación de la cuenta

**User Story:** Como Sinergia, quiero identificar la cuenta del usuario autenticado, para limitar la edición a sus propias campañas.

#### Acceptance Criteria

1. [Dirigido por evento] WHEN el Edit_Payload supera los Requisitos 3 y 4, THE EditAdVariantImageUseCase SHALL invocar `AccountRepository.get_by_email(self.user_id)` exactamente una vez.
2. [Comportamiento no deseado] IF `get_by_email` devuelve un valor falsy (`None`, `{}` u otro valor falsy), THEN THE EditAdVariantImageUseCase SHALL lanzar DataNotFoundException (`DAT001`) con el texto exacto `Account not found`, con cero invocaciones de CampaignRepository, AdChannelRepository y FuryClient.
3. [Dirigido por evento] WHEN `get_by_email` devuelve una cuenta, THE EditAdVariantImageUseCase SHALL usar como Parent_Account `account['attributes']['parent_account']['data']['id']` solo si `attributes`, `parent_account` y `data` son `dict` no vacíos y `data` contiene `id`; en cualquier otro caso (`attributes`, `parent_account` o `data` ausentes, `None`, vacíos o que no son `dict`, o `data` sin `id`) SHALL usar `account['id']`, sin lanzar excepción.
4. [Comportamiento no deseado] IF `get_by_email` lanza una excepción, THEN THE EditAdVariantImageUseCase SHALL propagar la misma instancia sin envolverla, con cero invocaciones de CampaignRepository, AdChannelRepository y FuryClient.

### Requirement 6: Validación de la campaña

**User Story:** Como Sinergia, quiero comprobar que la campaña pertenece a la marca y a la cuenta del usuario, para no editar imágenes de otras cuentas.

#### Acceptance Criteria

1. [Dirigido por evento] WHEN se ha calculado la Parent_Account, THE EditAdVariantImageUseCase SHALL invocar `CampaignRepository.get_by_id_brand_and_account(campaign_id, brand_id, parent_account)` exactamente una vez, con esos argumentos en ese orden y con `campaign_id` y `brand_id` del Edit_Payload sin transformar.
2. [Comportamiento no deseado] IF el Campaign_Lookup devuelve un valor falsy (`None`, `{}` u otro valor falsy), THEN THE EditAdVariantImageUseCase SHALL lanzar DataNotFoundException (`DAT001`) con el texto exacto `Campaign not found or does not belong to account`, con cero invocaciones de AdChannelRepository y FuryClient.
3. [Ubicuo] THE EditAdVariantImageUseCase SHALL validar la marca únicamente a través del Campaign_Lookup, sin consultas adicionales de marca.
4. [Comportamiento no deseado] IF el Campaign_Lookup lanza una excepción, THEN THE EditAdVariantImageUseCase SHALL propagar la misma instancia sin envolverla, con cero invocaciones de AdChannelRepository y FuryClient.

### Requirement 7: Validación de la variante

**User Story:** Como Sinergia, quiero comprobar que la variante pertenece al anuncio, a la campaña y al canal indicados, para garantizar la coherencia de la petición.

#### Acceptance Criteria

1. [Dirigido por evento] WHEN el Campaign_Lookup devuelve una campaña no falsy, THE EditAdVariantImageUseCase SHALL invocar `AdChannelRepository.get_by_id_ad_campaign_and_channel(variant_id, ad_id, campaign_id, channel_id)` exactamente una vez, con esos argumentos en ese orden y los valores del Edit_Payload sin transformar.
2. [Comportamiento no deseado] IF el Variant_Lookup devuelve un valor falsy (`None`, `{}` u otro valor falsy), THEN THE EditAdVariantImageUseCase SHALL lanzar DataNotFoundException (`DAT001`) con el texto exacto `Ad variant not found`, con cero invocaciones de FuryClient.
3. [Comportamiento no deseado] IF el Variant_Lookup lanza una excepción, THEN THE EditAdVariantImageUseCase SHALL propagar la misma instancia sin envolverla, con cero invocaciones de FuryClient.

### Requirement 8: Validación de la imagen

**User Story:** Como Sinergia, quiero comprobar que la imagen pertenece a la variante, para que Fury edite solo imágenes de esa variante.

#### Acceptance Criteria

1. [Dirigido por evento] WHEN el Variant_Lookup devuelve un Ad_Variant no falsy, THE EditAdVariantImageUseCase SHALL considerar válida la imagen si al menos un elemento de las Banner_Images es un `dict` cuyo valor `image_id` es igual (`==`, sin conversión de tipos ni recorte del valor almacenado) al `image_id` recortado del Edit_Payload; por ejemplo, un elemento con `image_id` `5` (int) no coincide con un `image_id` `"5"` en el Edit_Payload.
2. [Comportamiento no deseado] IF ningún elemento de las Banner_Images cumple el criterio 1 (incluidos los casos en que `Ad_Variant['attributes']` falta, es `None` o no es `dict`, y los casos de `media_images_banner` vacío, ausente, `None` o que no es una lista), THEN THE EditAdVariantImageUseCase SHALL lanzar DataNotFoundException (`DAT001`) con el texto exacto `Image not found in ad variant`, sin lanzar `KeyError` ni `TypeError`, con cero invocaciones de FuryClient.
3. [Ubicuo] THE EditAdVariantImageUseCase SHALL omitir los elementos de las Banner_Images que no son `dict` o no contienen la clave `image_id`, sin lanzar excepción por ellos.
4. [Ubicuo] THE EditAdVariantImageUseCase SHALL validar la imagen solo con los datos del Ad_Variant, sin llamadas adicionales a repositorios ni a Image_Library.

### Requirement 9: Encolado del job en Fury

**User Story:** Como usuario de HiLuca, quiero que Sinergia encole la edición en Fury y me devuelva el identificador del job, para consultar su progreso.

#### Acceptance Criteria

1. [Dirigido por evento] WHEN la imagen se valida según el Requisito 8, THE EditAdVariantImageUseCase SHALL invocar `self.fury_client.post('/api/v2/variants/image/edit', fury_edit_payload)` exactamente una vez, con esos dos argumentos posicionales.
2. [Ubicuo] THE EditAdVariantImageUseCase SHALL construir el Fury_Edit_Payload con exactamente sus 10 claves: los ID_Fields y `n_variations` como `int` sin transformar; `image_name` recortado; `id_base_image` igual al `image_id` recortado del Edit_Payload; `custom_prompt` igual al Normalized_Custom_Prompt (`None` si no hay); `expand_zoom_option` igual al valor recibido o `None` si es ausente o `None`.
3. [Ubicuo] THE EditAdVariantImageUseCase SHALL excluir del Fury_Edit_Payload la clave `image_id` y cualquier clave del Edit_Payload distinta de las 10 claves del Fury_Edit_Payload.
4. [Dirigido por evento] WHEN `FuryClient.post` devuelve un `dict` cuyo `data` es un `dict` con `edit_job_id` de tipo `str` no vacío tras recortar espacios, THE EditAdVariantImageUseCase SHALL devolver exactamente `{"job_id": <Edit_Job_Id>}`, con el valor original sin recortar ni modificar (p. ej. `" abc "` se devuelve como `" abc "`), sin comprobar `ok`, `status` ni `poll_url`.
5. [Comportamiento no deseado] IF `FuryClient.post` lanza FuryException o cualquier otra subclase de `SinergiaException`, THEN THE EditAdVariantImageUseCase SHALL propagar la misma instancia (mismo tipo, código y texto), sin envolverla ni convertirla en FuryException.
6. [Comportamiento no deseado] IF `FuryClient.post` lanza una excepción que no es subclase de `SinergiaException`, THEN THE EditAdVariantImageUseCase SHALL lanzar FuryException (`FURY001`) con el texto exacto `Failed to enqueue image edit job in Fury`.
7. [Comportamiento no deseado] IF el Fury_Response no es un `dict`, no contiene `data`, `data` no es un `dict`, o `edit_job_id` falta, es `None`, no es `str` o está vacío tras recortar espacios, THEN THE EditAdVariantImageUseCase SHALL lanzar FuryException (`FURY001`) con el texto exacto `Fury response does not contain edit_job_id`.
8. [Dirigido por evento] WHEN la imagen se valida según el Requisito 8 y antes de invocar `FuryClient.post`, THE EditAdVariantImageUseCase SHALL llamar a `logger.info` exactamente una vez con un mensaje que incluya `variant_id`, el `image_id` recortado, `n_variations`, `expand_zoom_option` y la longitud en caracteres del Normalized_Custom_Prompt (`0` si es `None`), sin incluir el texto de `custom_prompt`.

### Requirement 10: Pruebas unitarias

**User Story:** Como desarrollador de Sinergia, quiero pruebas unitarias aisladas del caso de uso, para detectar regresiones sin depender de Strapi ni de Fury.

#### Acceptance Criteria

1. [Ubicuo] THE Unit_Test_Suite SHALL estar formado por el único archivo `sinergia/tests/v2/unit/use_cases/test_edit_ad_variant_image_use_case.py`, sin crear `conftest.py` ni fixtures fuera de ese archivo, y sin añadir dependencias distintas de las ya fijadas en `sinergia/requirements-test.txt` (`pytest-mock==3.14.0`, `hypothesis==6.112.2`).
2. [Ubicuo] THE Unit_Test_Suite SHALL sustituir AccountRepository, CampaignRepository, AdChannelRepository y FuryClient con `mocker.patch('app.v2.use_cases.ad.<Clase>')` de `pytest-mock` antes de instanciar EditAdVariantImageUseCase, de modo que ninguna prueba realice llamadas HTTP a Strapi ni a Fury.
3. [Ubicuo] THE Unit_Test_Suite SHALL ejecutarse con `venv/bin/python -m pytest tests/v2/unit/use_cases/test_edit_ad_variant_image_use_case.py -q` desde `sinergia/`, con las dependencias de `requirements-test.txt` instaladas en `venv`, con 0 pruebas fallidas, 0 errores y 0 omitidas, en menos de 60 segundos.
4. [Ubicuo] THE Unit_Test_Suite SHALL anotar cada función de prueba con `-> None`.
5. [Dirigido por evento] WHEN la prueba del camino feliz ejecuta `execute` con un Edit_Payload válido, THE Unit_Test_Suite SHALL verificar que el resultado es exactamente `{"job_id": <edit_job_id del mock>}` y que `FuryClient.post` se invoca una vez con `'/api/v2/variants/image/edit'` y un Fury_Edit_Payload igual (`==`) al diccionario esperado, incluido `id_base_image` igual al `image_id` y la ausencia de la clave `image_id`.
6. [Comportamiento no deseado] IF la prueba envía, para cada una de las 8 Required_Fields, un Edit_Payload con cada Missing_Value (`None`, `""`, `"   "` y clave ausente), o un `payload` que no es `dict` (`None`, una lista y una cadena), THEN THE Unit_Test_Suite SHALL verificar ParametersNotFoundException con el código `PAR001` y el texto exacto del Requisito 3.
7. [Comportamiento no deseado] IF la prueba envía valores inválidos (para cada uno de los 5 ID_Fields: `0`, `-1`, `True`, `1.0` y `"5"`; `n_variations` igual a `0`, `11`, `True` y `"5"`; `image_name` e `image_id` de 256 caracteres tras recortar y de tipo no `str` como `123`; `custom_prompt` de 2001 caracteres tras recortar o de tipo no `str` como `123`; `expand_zoom_option` igual a `"top"`, `"ZOOM_3X"`, `" TOP"` y `""`; ni `custom_prompt` ni `expand_zoom_option`, con `custom_prompt` `None`, `""` y `"   "`), THEN THE Unit_Test_Suite SHALL verificar IncorrectValidationException con el código `SYSVAL001` y el texto exacto del Requisito 4.
8. [Dirigido por evento] WHEN la prueba envía valores límite válidos (IDs igual a `1`, `n_variations` igual a `1` y `10`, `image_name` e `image_id` de 255 caracteres tras recortar, `custom_prompt` de 2000 caracteres tras recortar, cada uno de los 7 ExpandZoomOption_Values), THE Unit_Test_Suite SHALL verificar que `execute` devuelve el `job_id` sin excepción.
9. [Comportamiento no deseado] IF la prueba simula que AccountRepository, CampaignRepository o AdChannelRepository devuelven `None` o lanzan una excepción, o que las Banner_Images están vacías, ausentes, son `None`, no son una lista o no contienen ningún `dict` con `image_id` coincidente, THEN THE Unit_Test_Suite SHALL verificar DataNotFoundException con el texto exacto de los Requisitos 5 a 8, o la misma instancia propagada (`is`) en el caso de excepción.
10. [Ubicuo] THE Unit_Test_Suite SHALL verificar, en cada camino de error de los Requisitos 3 a 8, que los colaboradores de los pasos posteriores al paso fallido tienen cero invocaciones (`assert_not_called`).
11. [Dirigido por evento] WHEN la prueba simula una cuenta con y sin `parent_account.data`, THE Unit_Test_Suite SHALL verificar que el Campaign_Lookup recibe el id de la cuenta padre y el id de la cuenta, respectivamente.
12. [Comportamiento no deseado] IF la prueba simula que `FuryClient.post` lanza FuryException, lanza una excepción que no es `SinergiaException` (p. ej. `RuntimeError`), o devuelve una respuesta que no es `dict`, sin `data`, sin `edit_job_id`, con `edit_job_id` `None`, no `str` o `"   "`, THEN THE Unit_Test_Suite SHALL verificar, respectivamente, la misma instancia de FuryException propagada (`is`), una FuryException con el texto exacto `Failed to enqueue image edit job in Fury`, o una FuryException con el texto exacto `Fury response does not contain edit_job_id`.
13. [Ubicuo] THE Unit_Test_Suite SHALL incluir una prueba de propiedad con `hypothesis` (`@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])`) que verifique, para cualquier Edit_Payload válido generado, que el Fury_Edit_Payload tiene exactamente las 10 claves, que `id_base_image` es igual al `image_id` recortado y que `custom_prompt` es igual al Normalized_Custom_Prompt (invariante de mapeo).
14. [Ubicuo] THE Unit_Test_Suite SHALL incluir una prueba que verifique que el constructor guarda `user_id` en `self.user_id` e instancia una vez cada uno de los 4 colaboradores parcheados (Requisitos 2.2 y 2.3), y que `get_by_email` se invoca exactamente una vez con ese `user_id`.
15. [Ubicuo] THE Unit_Test_Suite SHALL parchear `app.v2.use_cases.ad.logger` y verificar que cada excepción creada por el caso de uso va precedida de exactamente una llamada a `logger.error` cuyo mensaje contiene el texto de la excepción (Requisito 2.4), y que en el camino feliz ningún argumento de `logger.info` contiene el texto completo de un `custom_prompt` de al menos 20 caracteres (Requisito 9.8).

## Trazabilidad

Quedan fuera del Unit_Test_Suite y se verifican por revisión de código: los criterios 1.1 a 1.8 del endpoint (prueba de integración opcional en `tests/v2/integration/`) y los criterios 2.1, 2.5 y 2.6 de estructura del módulo (2.5 también con `venv/bin/python -c "import app.v2.use_cases.ad"`).

El resto de criterios se cubren con los criterios 10.5 a 10.15:

- 2.2 y 2.3 (constructor y colaboradores): 10.14.
- 2.4 (`logger.error` antes de cada excepción propia) y 9.8 (`logger.info` sin el texto de `custom_prompt`): 10.15.
- 3.1, 3.2, 3.4, 3.5 y 3.6 (presencia y orden): 10.6 y 10.10.
- 3.3 (`valor.strip() == ""` y valores presentes no vacíos): 10.6 (casos `""` y `"   "`) y 10.7 (caso cadena `"5"` en los ID_Fields y `n_variations`, que pasa el Requisito 3 y falla en el Requisito 4).
- 4.1 a 4.9 (validación de valores): 10.7, 10.8, 10.10 y 10.13.
- 5.1 a 5.4, 6.1 a 6.4, 7.1 a 7.3 y 8.1 a 8.4 (cuenta, campaña, variante e imagen): 10.9, 10.10 y 10.11.
- 9.1 a 9.7 (encolado en Fury): 10.5, 10.12 y 10.13.
