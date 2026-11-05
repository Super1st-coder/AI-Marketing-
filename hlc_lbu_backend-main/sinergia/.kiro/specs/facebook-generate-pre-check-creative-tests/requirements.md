# Requirements Document

## Introduction

Este documento define los requisitos para una suite de pruebas unitarias con pytest de la clase `FacebookGeneratePreCheckCreativeUseCase`, ubicada en `app/v2/use_cases/meta_ads.py` (líneas 1215-1584), y de su clase padre `FacebookTestCreativeUploadUseCase` (líneas 920-1214) en la porción de comportamiento heredado que `FacebookGeneratePreCheckCreativeUseCase` invoca. La suite debe caracterizar el comportamiento observable actual, incluidas sus ramas DYNAMIC y STANDARD, los efectos secundarios sobre los repositorios de Strapi, la propagación de excepciones y las particularidades ya existentes en el código (por ejemplo la reutilización del slug `assets-budget-error` para errores de URL, o la ausencia total de errores cuando un creativo STANDARD carece de `link_data`). La implementación de la suite es el entregable de esta fase; no se modifica código productivo.

**Ubicación obligatoria de los artefactos de prueba:** conforme a `sinergia/.kiro/steering/structure.md`, todo archivo de pruebas unitarias de la capa `use_cases` vive en `tests/v2/unit/use_cases/`. La suite de esta especificación SHALL residir en `tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py`, dentro del proyecto `sinergia`. Todo artefacto de especificación (requirements, design, tasks) y todo artefacto de implementación de esta feature SHALL permanecer dentro del árbol `sinergia/`.

## Glossary

- **Suite_de_Pruebas**: Conjunto de pruebas unitarias pytest para `FacebookGeneratePreCheckCreativeUseCase` definido en `tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py`.
- **Caso_de_Uso**: Instancia de `FacebookGeneratePreCheckCreativeUseCase`.
- **Caso_de_Uso_Padre**: `FacebookTestCreativeUploadUseCase`, superclase de la que `FacebookGeneratePreCheckCreativeUseCase` hereda `__init__`, `_get_decoded_access_token` y `_build_meta_payload`.
- **Datos_de_Campaña**: Argumento `complete_campaign_data` (tipo `CampaignDataDict`) recibido por el constructor.
- **Cliente_Redis**: Objeto `redis_client` importado a nivel de módulo en `app.v2.use_cases.meta_ads`, usado por `_get_decoded_access_token` para leer el token de Facebook.
- **Constructor_de_Payload**: `MetaAdsPayloadBuilder`, instanciado dentro de `_build_meta_payload` para construir el payload de Meta desde Strapi.
- **Caso_de_Cuenta**: `FacebookGetAdAccountDetailsUseCase`, dependencia instanciada dentro de `_get_account_details`.
- **Caso_de_Presupuesto_Mínimo**: `FacebookMinimumBudgetUseCase`, dependencia instanciada dentro de `_get_minimum_budget`.
- **Repositorio_de_Canal**: `AdChannelRepository`, instanciado en el constructor del Caso_de_Uso y usado por `_save_creative_to_publish`.
- **Repositorio_de_Publicación**: `CampaignChannelPublishRepository`, instanciado en el constructor del Caso_de_Uso y usado por `_save_campaign_channel_publish`.
- **Validador_Meta**: `MetaAdsValidator`, clase de utilidades estáticas/de clase usada dentro de `execute()` para validar textos, CTAs, imágenes, cantidades de assets, presupuesto y URLs.
- **Ad_Set**, **Ad**, **Ad_Creative**, **Asset_Feed_Spec**, **Object_Story_Spec**: Estructuras de diccionario anidadas dentro del payload de Meta (`meta_payload['campaign']['ad_sets'][i]['ads'][j]['adCreative']`).
- **Resultado_de_Ad**: Diccionario `{"ad_name": ..., "status": "Created"|"Failed", "errors": [...] }` (sin `errors` cuando `status="Created"`) agregado a la lista local `results` dentro de `execute()`.
- **Respuesta_Final**: Tupla `(dict, 200)` retornada por `execute()`, donde el `dict` tiene la forma `{"ok": 0|1, "data": {"campaign", "creatives", "valid_ctas", "account_config"}}`.
- **Doble_de_Prueba**: Sustitución controlada creada con `unittest.mock.MagicMock`/`patch`.
- **Guard_de_Red**: Mecanismo de prueba que impide solicitudes HTTP reales durante la ejecución de la Suite_de_Pruebas.

## Requirements

### Requirement 1: Infraestructura, aislamiento y ubicación de la suite

**User Story:** Como desarrollador, quiero ejecutar la Suite_de_Pruebas de forma aislada y en la ubicación estándar del proyecto, para que los resultados no dependan de Strapi, Redis, la Graph API de Facebook, ni de servicios de red reales.

#### Acceptance Criteria

1. THE Suite_de_Pruebas SHALL residir exclusivamente en el archivo `tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` dentro del proyecto `sinergia`, conforme a la convención documentada en `sinergia/.kiro/steering/structure.md` para pruebas unitarias de `use_cases`.
2. WHEN una prueba construye un Caso_de_Uso, THE Suite_de_Pruebas SHALL sustituir `AdChannelRepository` y `CampaignChannelPublishRepository` por Dobles_de_Prueba parcheando `app.v2.use_cases.meta_ads.AdChannelRepository` y `app.v2.use_cases.meta_ads.CampaignChannelPublishRepository` antes de invocar el constructor, sin construir ni invocar un `StrapiClient` real.
3. WHEN una prueba ejercita `_get_account_details` o `_get_minimum_budget`, THE Suite_de_Pruebas SHALL sustituir `FacebookGetAdAccountDetailsUseCase` y `FacebookMinimumBudgetUseCase` por Dobles_de_Prueba parcheando sus símbolos en `app.v2.use_cases.meta_ads`, sin realizar solicitudes HTTP reales a la Graph API de Facebook.
4. WHEN una prueba ejercita `_get_decoded_access_token` o `_build_meta_payload`, THE Suite_de_Pruebas SHALL sustituir el Cliente_Redis parcheando `app.v2.use_cases.meta_ads.redis_client` y sustituir el Constructor_de_Payload parcheando `app.v2.use_cases.meta_ads.MetaAdsPayloadBuilder`, sin conexiones reales a Redis ni a Strapi.
5. WHILE pytest ejecuta la Suite_de_Pruebas, THE Suite_de_Pruebas SHALL realizar cero solicitudes de red reales, incluidas las que `MetaAdsValidator.validate_images_precheck` y `MetaAdsValidator.validate_images` podrían intentar mediante `requests.get`.
6. WHERE un escenario de la rama DYNAMIC o STANDARD requiere ejercitar código de imágenes, THE Suite_de_Pruebas SHALL evitar que se invoque una solicitud HTTP real, ya sea omitiendo URLs de imagen en el escenario, parcheando `MetaAdsValidator.validate_images_precheck`/`validate_images`, o mediante un Guard_de_Red que falle rápido ante cualquier fuga.
7. WHERE una prueba requiere contexto de aplicación Flask, THE Suite_de_Pruebas SHALL primero verificar si dicho contexto es realmente necesario para el código alcanzable (por ejemplo, para que `flask_babel.gettext` resuelva el texto de una `SinergiaException`); si no lo es, THE Suite_de_Pruebas SHALL ejecutar la prueba como unidad pura sin crear una aplicación ni un contexto Flask ni un `tests/conftest.py` nuevo.
8. WHILE se implementa la Suite_de_Pruebas, THE Suite_de_Pruebas SHALL mantener sin modificaciones `app/v2/use_cases/meta_ads.py`, `app/v2/use_cases/facebook_validator_service.py`, `app/v2/repository/ad_channel.py`, `app/v2/repository/campaign_channel_publish.py`, y cualquier otro archivo de producción.
9. WHEN una prueba necesita fijar una dependencia de test (por ejemplo Hypothesis, si se usa), THE Suite_de_Pruebas SHALL declararla en `requirements-test.txt` únicamente si aún no está declarada, sin modificar `requirements.txt`.

### Requirement 2: Construcción del Caso de Uso y estado heredado

**User Story:** Como mantenedor, quiero verificar cómo se inicializa el Caso_de_Uso a partir de los Datos_de_Campaña, para detectar cambios accidentales en los atributos que consumen el resto de los métodos.

#### Acceptance Criteria

1. WHEN se construye un Caso_de_Uso con Datos_de_Campaña completos, THE Suite_de_Pruebas SHALL verificar que `ad_account_id`, `page_id`, `objective`, `optimization_goal`, `lead_gen_form_id`, `whatsapp_number_id` y `creative_type` quedan asignados exactamente a los valores provistos.
2. WHEN se construye un Caso_de_Uso, THE Suite_de_Pruebas SHALL verificar que `billing_event` y `channel_id` quedan inicializados en `None`.
3. WHEN se construye un Caso_de_Uso, THE Suite_de_Pruebas SHALL verificar que el Repositorio_de_Canal parcheado y el Repositorio_de_Publicación parcheado se instancian exactamente una vez cada uno.
4. WHEN Datos_de_Campaña omite `lead_gen_form_id` o `whatsapp_number_id`, THE Suite_de_Pruebas SHALL verificar que el atributo correspondiente queda en `None`.
5. IF se construye un Caso_de_Uso con `complete_campaign_data=None` (el valor por defecto), THEN THE Suite_de_Pruebas SHALL verificar que el constructor propaga `AttributeError`, caracterizando el comportamiento actual en el que solo `lead_gen_form_id` y `whatsapp_number_id` están protegidos contra `complete_campaign_data` ausente.

### Requirement 3: Obtención del token de acceso decodificado

**User Story:** Como desarrollador, quiero verificar la lectura del token de Facebook desde Redis, para asegurar que la autenticación fallida se reporta de forma consistente.

#### Acceptance Criteria

1. WHEN el Cliente_Redis devuelve un valor verdadero para la clave `facebook_access_token:{user_id}`, THE Suite_de_Pruebas SHALL verificar que `_get_decoded_access_token` devuelve el resultado de decodificar ese valor con `utf-8` y que `get` fue llamado exactamente una vez con esa clave exacta.
2. IF el Cliente_Redis devuelve un valor falsy (`None` o cadena vacía tras decodificar previamente el mock), THEN THE Suite_de_Pruebas SHALL verificar que `_get_decoded_access_token` propaga `NotAccessException` con el mensaje exacto `"No access token found in Redis. Please re-authenticate."`.
3. WHEN `execute()` obtiene un token ausente en el primer paso, THE Suite_de_Pruebas SHALL verificar que la excepción se propaga sin llamar al Constructor_de_Payload, al Caso_de_Cuenta ni al Caso_de_Presupuesto_Mínimo.

### Requirement 4: Construcción del payload de Meta

**User Story:** Como mantenedor, quiero verificar la orquestación de `_build_meta_payload`, para asegurar que los errores de Strapi se envuelven de forma consistente.

#### Acceptance Criteria

1. WHEN `ad_account_id` y `page_id` son valores verdaderos, THE Suite_de_Pruebas SHALL verificar que el Constructor_de_Payload se instancia con `(campaign_id, objective, optimization_goal, creative_type)` y que `select_ad_account(ad_account_id)` y `select_page(page_id)` se llaman exactamente una vez cada uno antes de `build_meta_payload()`.
2. WHEN `ad_account_id` o `page_id` son falsy, THE Suite_de_Pruebas SHALL verificar que `select_ad_account`/`select_page` no se invocan para el valor falsy correspondiente.
3. WHEN `build_meta_payload()` del Doble_de_Prueba retorna un payload, THE Suite_de_Pruebas SHALL verificar que `_build_meta_payload` asigna `self.billing_event` desde `get_billing_event()`, asigna `self.channel_id` desde `get_channel_id()` y retorna el mismo objeto de payload por identidad.
4. IF `build_meta_payload()` lanza una excepción, THEN THE Suite_de_Pruebas SHALL verificar que `_build_meta_payload` propaga `StrapiException` con un mensaje que contiene el texto de la excepción original, y no la excepción original directamente.

### Requirement 5: Obtención de detalles de la cuenta publicitaria

**User Story:** Como desarrollador, quiero verificar el mapeo de errores de la Graph API al obtener detalles de cuenta, para que cada código de error produzca la excepción de negocio correcta.

#### Acceptance Criteria

1. WHEN el Caso_de_Cuenta devuelve estado `200`, THE Suite_de_Pruebas SHALL verificar que `_get_account_details` retorna el mismo diccionario por identidad y que `execute` fue invocado exactamente una vez con `(self.user_id, self.ad_account_id)`.
2. IF el Caso_de_Cuenta devuelve estado distinto de `200` con `error.code=190`, THEN THE Suite_de_Pruebas SHALL verificar que se propaga `NotAccessException` con el mensaje exacto `"Access token is invalid or expired. Please re-authenticate."`.
3. IF el Caso_de_Cuenta devuelve estado distinto de `200` con `error.code=200`, THEN THE Suite_de_Pruebas SHALL verificar que se propaga `PermissionDeniedException` con el mensaje exacto `"Insufficient permissions to access ad account details. Please check your Facebook app permissions."`.
4. IF el Caso_de_Cuenta devuelve estado distinto de `200` con `error.code=100`, THEN THE Suite_de_Pruebas SHALL verificar que se propaga `ParametersNotFoundException` con el mensaje exacto `"Invalid parameters provided for fetching ad account details. Please check the ad account ID and try again."`.
5. IF el Caso_de_Cuenta devuelve estado distinto de `200` con `error.code=613`, THEN THE Suite_de_Pruebas SHALL verificar que se propaga `RateLimitExceededException` con el mensaje exacto `"Facebook API rate limit exceeded. Please try again later."`.
6. IF el Caso_de_Cuenta devuelve estado distinto de `200` con un `error.code` no mapeado o ausente, THEN THE Suite_de_Pruebas SHALL verificar que se propaga `RESTClientException` con un mensaje que incluye `error.message` cuando existe, y el texto `"Unknown error"` cuando `error.message` está ausente.

### Requirement 6: Obtención del presupuesto mínimo

**User Story:** Como desarrollador, quiero verificar el cálculo del presupuesto mínimo por moneda, para asegurar conversiones y errores correctos.

#### Acceptance Criteria

1. IF el Caso_de_Presupuesto_Mínimo devuelve estado distinto de `200`, THEN THE Suite_de_Pruebas SHALL verificar que `_get_minimum_budget` propaga `PermissionDeniedException` con el mensaje exacto `"Insufficient permissions to access minimum budget details. Please check your Facebook app permissions."`.
2. WHEN el Caso_de_Presupuesto_Mínimo devuelve estado `200` con al menos un elemento en `data` cuya `currency` coincide con `ad_account_info.currency`, THE Suite_de_Pruebas SHALL verificar que `_get_minimum_budget` retorna `min_daily_budget_imp / 100` para el primer elemento coincidente en orden de aparición.
3. IF el Caso_de_Presupuesto_Mínimo devuelve estado `200` sin ningún elemento cuya `currency` coincida, THEN THE Suite_de_Pruebas SHALL verificar que se propaga `DataNotFoundException` con el mensaje exacto `"Minimum budget not found for account currency"`.
4. WHEN un elemento coincidente omite `min_daily_budget_imp`, THE Suite_de_Pruebas SHALL verificar que `_get_minimum_budget` retorna `0` dividido entre `100`.

### Requirement 7: Ads sin creativo

**User Story:** Como responsable de calidad, quiero verificar que un ad sin `adCreative` se reporta como fallo sin ejecutar validaciones adicionales.

#### Acceptance Criteria

1. WHEN un ad tiene `adCreative` ausente, `None`, o cualquier valor falsy, THE Suite_de_Pruebas SHALL verificar que, para un escenario donde ese es el único ad de la ejecución, la Respuesta_Final contiene `ok=0` (derivado de `has_errors=True`), caracterizando que este fallo se agrega a la lista interna `results` aunque `results` no forme parte de la Respuesta_Final observable.
2. WHEN se detecta un ad sin creativo, THE Suite_de_Pruebas SHALL verificar que el Validador_Meta no es invocado para ese ad y que la iteración continúa con el siguiente ad sin interrumpir el resto del `ad_set` ni de la campaña, comprobando que los ads/ad_sets restantes se procesan normalmente (por ejemplo, produciendo `ok=1` cuando el resto de la ejecución es válida).
3. IF el ad sin creativo tiene `adCreative` ausente o `None` (no `{}`, ver nota) y es `ads[0]` de su `ad_set`, THEN THE Suite_de_Pruebas SHALL verificar que `execute()` propaga `AttributeError` al construir `creatives`, dado que ese bucle ejecuta `ad_creative.get('asset_feed_spec', {})` sobre un `adCreative` cuyo valor es `None`, y `None.get(...)` lanza `AttributeError`; la prueba SHALL verificar que la excepción ocurre después de que `campaign_publish_repository.save_or_update` ya se invocó una vez, caracterizando este comportamiento como actual y no como una corrección pendiente. **Nota de precisión:** cuando `adCreative={}}` (diccionario vacío, en lugar de ausente/`None`), `ad_creative.get('asset_feed_spec', {})` es una llamada válida sobre un diccionario real y NO lanza `AttributeError`; ese caso, al ser `ads[0]`, completa la construcción de `creatives` con valores default y la ejecución continúa hasta el final con `ok=0` (por el fallo `missing-creative-error` registrado en `results`), sin excepción. THE Suite_de_Pruebas SHALL verificar ambos subcasos por separado: `AttributeError` para `adCreative` ausente/`None` como `ads[0]`, y `ok=0` sin excepción para `adCreative={}}` como `ads[0]`.

### Requirement 8: Rama DYNAMIC — validaciones que anotan sin interrumpir

**User Story:** Como responsable de campañas, quiero verificar cada validación DYNAMIC y su comportamiento de no interrupción, para que el precheck refleje fielmente el estado real de cada asset.

#### Acceptance Criteria

1. WHEN `creative_type="DYNAMIC"` y `asset_feed_spec` está presente, THE Suite_de_Pruebas SHALL verificar que `MetaAdsValidator.is_unique_texts` se invoca con los textos de `titles`, `bodies` y `descriptions` respectivamente, y que `asset_feed['unique_titles']`, `asset_feed['unique_bodies']` y `asset_feed['unique_descriptions']` quedan asignados con el valor retornado por cada llamada.
2. WHEN se procesan `titles`, `bodies` y `descriptions`, THE Suite_de_Pruebas SHALL verificar que `MetaAdsValidator.is_valid_length` se invoca exactamente una vez por colección con el tipo (`'titles'`, `'bodies'`, `'descriptions'`) y la lista correspondiente.
3. WHEN un doble sustituye `is_unique_texts` o `is_valid_length` y lanza `ValueError` para `titles`, `bodies` o `descriptions` respectivamente, THE Suite_de_Pruebas SHALL verificar que la asignación de éxito correspondiente (`asset_feed['unique_titles']`, `asset_feed['unique_bodies']` o `asset_feed['unique_descriptions']`) está ausente del objeto `asset_feed` propio de la prueba tras la ejecución, y que la Respuesta_Final contiene `ok=0` para una ejecución donde ese es el único ad, caracterizando la ruta de manejo de errores aunque el comportamiento actual de esos validadores nunca la alcance con datos válidos.
4. WHEN `asset_feed['call_to_action_types']` contiene una o más entradas, THE Suite_de_Pruebas SHALL verificar que `MetaAdsValidator.validate_cta` se invoca por cada entrada con `(cta.get('value'), self.objective, False)` y que `cta['valid']` queda asignado con el valor booleano retornado.
5. IF `self.objective` no es una clave de `META_ODAX_CTA_MAPPING` (por ejemplo un objetivo desconocido) mientras hay al menos una entrada en `call_to_action_types`, THEN THE Suite_de_Pruebas SHALL verificar que ninguna entrada de `call_to_action_types` recibe la clave `valid` (dado que `validate_cta` lanza siempre para objetivo no soportado, sin importar `throw=False`, y la asignación de éxito nunca se alcanza), que la Respuesta_Final contiene `ok=0` para una ejecución donde ese es el único ad, y que la iteración continúa evaluando las entradas de CTA restantes (verificable porque `MetaAdsValidator.validate_cta` es invocado una vez por cada entrada, no solo por la primera).
6. WHEN `asset_feed['images']` contiene entradas con `url`, THE Suite_de_Pruebas SHALL verificar que `MetaAdsValidator.validate_images_precheck` se invoca exactamente una vez con la lista completa de imágenes, sin que la Suite_de_Pruebas permita una solicitud HTTP real.
7. WHEN un doble sustituye `validate_images_precheck` y lanza `ValueError`, THE Suite_de_Pruebas SHALL verificar que la Respuesta_Final contiene `ok=0` para una ejecución donde ese es el único ad, caracterizando que no existe ninguna asignación de éxito asociada a esta validación (ni siquiera en la ruta sin error) por lo que `ok` y la aserción de argumentos de llamada de 8.6 son la única señal observable disponible.
8. WHEN se procesa `asset_feed`, THE Suite_de_Pruebas SHALL verificar que `MetaAdsValidator.is_valid_amount` se invoca exactamente una vez con `(asset_feed, self.creative_type, None)`.
9. WHEN un doble sustituye `is_valid_amount` y lanza `ValueError`, THE Suite_de_Pruebas SHALL verificar que la Respuesta_Final contiene `ok=0` para una ejecución donde ese es el único ad, caracterizando que `is_valid_amount` no asigna ningún valor de retorno ni en éxito ni en fallo, por lo que `ok` junto con la aserción de argumentos de llamada de 8.8 son la única señal observable disponible.
10. WHEN `ad_set.get('daily_budget', 0)` es comparable con `min_budget`, THE Suite_de_Pruebas SHALL verificar que `asset_feed['min_daily_budget']` queda asignado al valor de `min_budget` y `asset_feed['daily_budget_valid']` queda asignado a `True` o `False` según la comparación `>=`.
11. IF `ad_set['daily_budget']` es un valor explícito no comparable con `min_budget` (por ejemplo `None`), THEN THE Suite_de_Pruebas SHALL verificar que `asset_feed['min_daily_budget']` queda asignado igualmente (esa asignación ocurre antes de la comparación que lanza la excepción), que `asset_feed['daily_budget_valid']` está ausente del objeto `asset_feed` propio de la prueba, y que la Respuesta_Final contiene `ok=0` para una ejecución donde ese es el único ad.
12. WHEN `asset_feed['link_urls']` contiene entradas válidas con `website_url`, THE Suite_de_Pruebas SHALL verificar que `MetaAdsValidator.is_valid_link_url` se invoca con la unión por comas de esas URLs y que `asset_feed['link_url_valid']` queda asignado al valor retornado.
13. IF una entrada de `asset_feed['link_urls']` no admite `.get` (por ejemplo `None` dentro de la lista), THEN THE Suite_de_Pruebas SHALL verificar que se captura la excepción, que `asset_feed['link_url_valid']` está ausente del objeto `asset_feed` propio de la prueba mientras que `asset_feed['daily_budget_valid']` sí está presente (en un escenario donde el presupuesto es válido), y que la Respuesta_Final contiene `ok=0` para una ejecución donde ese es el único ad; dado que este fallo captura la misma excepción genérica y reutiliza el mismo `slug="assets-budget-error"` que 8.11 dentro del código productivo, la ausencia de `link_url_valid` combinada con la presencia de `daily_budget_valid` es la única forma de distinguir observablemente cuál de las dos validaciones falló, caracterizando explícitamente esta reutilización de slug como comportamiento actual, no como defecto de la prueba.
14. WHEN un ad DYNAMIC satisface todas las validaciones anteriores sin que ningún doble fuerce una excepción, THE Suite_de_Pruebas SHALL verificar, para una ejecución con ese único ad, que la Respuesta_Final contiene `ok=1` y que `asset_feed['unique_titles']`, `asset_feed['unique_bodies']`, `asset_feed['unique_descriptions']`, `cta['valid']` en cada entrada de CTA, `asset_feed['daily_budget_valid']` y `asset_feed['link_url_valid']` quedan todos presentes simultáneamente en los objetos propios de la prueba, como prueba indirecta de que ningún error fue registrado para ese ad y de que el procesamiento continuó hacia el bloque de creación.

### Requirement 9: Rama STANDARD — validaciones que interrumpen por excepción

**User Story:** Como responsable de campañas, quiero verificar cada validación STANDARD, incluyendo el caso donde `link_data` está ausente y no se agrega ningún error.

#### Acceptance Criteria

1. IF `creative_type="STANDARD"` y `object_story_spec` está presente pero `object_story_spec.get('link_data')` es falsy, THEN THE Suite_de_Pruebas SHALL verificar que no se agrega ningún error de esta rama y que ninguno de `validate_cta`, `validate_images` ni `validate_assets_amount` es invocado, caracterizando que un creativo STANDARD sin `link_data` pasa sin errores hacia el bloque de creación.
2. WHEN `link_data.call_to_action` es un diccionario verdadero, THE Suite_de_Pruebas SHALL verificar que `MetaAdsValidator.validate_cta` se invoca con `(call_to_action.get('type'), self.objective)` sin el argumento `throw`.
3. IF `validate_cta` lanza `ValueError` en la rama STANDARD, THEN THE Suite_de_Pruebas SHALL verificar que la Respuesta_Final contiene `ok=0` para una ejecución donde ese es el único ad, y que la evaluación continúa con la validación de `image_url` (verificable porque `MetaAdsValidator.validate_images` o la rama de `image_url` ausente sigue ejecutándose después del fallo de `validate_cta`, ya que STANDARD no asigna ningún valor observable en éxito para CTA que permita detectar la ausencia de la asignación).
4. WHEN `link_data.image_url` es un valor verdadero, THE Suite_de_Pruebas SHALL verificar que `MetaAdsValidator.validate_images` se invoca exactamente una vez con ese valor como argumento único (no como lista), sin que la Suite_de_Pruebas permita una solicitud HTTP real.
5. IF `validate_images` lanza `ValueError`, THEN THE Suite_de_Pruebas SHALL verificar que la Respuesta_Final contiene `ok=0` para una ejecución donde ese es el único ad, y que `validate_assets_amount` sigue siendo invocado a continuación (STANDARD no asigna ningún valor observable en éxito para la validación de imagen, por lo que `ok` combinado con la aserción de continuación de llamadas es la única señal disponible).
6. IF `link_data.image_url` está ausente o es falsy, THEN THE Suite_de_Pruebas SHALL verificar que la Respuesta_Final contiene `ok=0` para una ejecución donde ese es el único ad, sin invocar `validate_images`, y que `validate_assets_amount` sigue siendo invocado a continuación.
7. WHEN `link_data` es verdadero, THE Suite_de_Pruebas SHALL verificar que `MetaAdsValidator.validate_assets_amount` se invoca exactamente una vez con `(None, self.creative_type, story_spec=story_spec)`, independientemente del resultado de las validaciones de CTA e imagen.
8. IF `validate_assets_amount` lanza `ValueError`, THEN THE Suite_de_Pruebas SHALL verificar que la Respuesta_Final contiene `ok=0` para una ejecución donde ese es el único ad, caracterizando que STANDARD no ofrece ninguna señal de mutación observable y que `ok` es la única evidencia de fallo disponible tras confirmar la llamada de 9.7.
9. WHEN un ad STANDARD con `link_data` satisface todas las validaciones sin excepciones forzadas, THE Suite_de_Pruebas SHALL verificar, para una ejecución con ese único ad, que la Respuesta_Final contiene `ok=1`, dado que STANDARD no expone ninguna mutación observable que sirva como prueba positiva adicional.

Nota general para Requirement 10: dado que `creatives` se construye leyendo incondicionalmente `ad_sets[i]['ads'][0]`, un ad `Failed` que sea `ads[0]` de su `ad_set` sigue contribuyendo campos a `creatives` (por ejemplo, `asset_feed_spec` parcialmente poblado hasta el punto del fallo); la Suite_de_Pruebas SHALL tener esto en cuenta al construir escenarios combinados que mezclen ads `Failed` y `Created` dentro del mismo `ad_set`.

### Requirement 10: Bloque de creación simulada (dry-run)

**User Story:** Como mantenedor, quiero verificar que el bloque de "creación" no realiza llamadas reales a Meta y produce el resultado correcto, incluida su única condición de fallo alcanzable.

#### Acceptance Criteria

1. WHEN un ad sin errores de validación tiene `page_id` verdadero en el Caso_de_Uso y `ad_creative.object_story_spec` es un diccionario verdadero, THE Suite_de_Pruebas SHALL verificar que `object_story_spec['page_id']` queda mutado con el valor de `self.page_id`.
2. WHEN `self.page_id` es falsy o `ad_creative.object_story_spec` está ausente, THE Suite_de_Pruebas SHALL verificar que no se intenta ninguna mutación de `page_id` y que no se agrega ningún error por ese motivo.
3. WHEN un ad sin errores de validación completa el bloque de creación sin excepciones, THE Suite_de_Pruebas SHALL verificar, para una ejecución donde ese es el único ad, que la Respuesta_Final contiene `ok=1`, dado que el contenido detallado del Resultado_de_Ad (`{"ad_name": ..., "status": "Created"}`, sin `creative_id`/`meta_response`/`errors`) forma parte de `results`, que no se retorna desde `execute()` y por tanto no es observable directamente desde la Respuesta_Final.
4. IF `ad_creative.object_story_spec` es un valor verdadero que no admite asignación de clave (por ejemplo una cadena de texto), THEN THE Suite_de_Pruebas SHALL verificar, para una ejecución donde ese es el único ad, que la Respuesta_Final contiene `ok=0`, caracterizando que la excepción se captura dentro del bloque de creación (`slug="execution-error"`) sin propagarse fuera de `execute()`; dado que ese Resultado_de_Ad tampoco es observable en la Respuesta_Final, `ok=0` es la única señal disponible para este escenario. Nota: dado que este ad tiene `adCreative` presente (solo `object_story_spec` es inválido), no está sujeto al `AttributeError` de construcción de `creatives` caracterizado en Requirement 7.3, que solo se dispara cuando `adCreative` mismo es falsy.
5. WHEN un `creative_type` distinto de `"DYNAMIC"` y de `"STANDARD"` (incluida cadena vacía) se combina con un ad que tiene `adCreative` presente, THE Suite_de_Pruebas SHALL verificar que ninguna validación de las Requirement 8 o 9 se ejecuta, que `current_ad_errors` permanece vacío, y que el ad avanza directamente al bloque de creación.

### Requirement 11: Agregación de resultados y código de estado final

**User Story:** Como consumidor de la API, quiero verificar cómo se determina `ok` y el código HTTP final, para interpretar correctamente la respuesta.

#### Acceptance Criteria

1. WHEN todos los Resultado_de_Ad de la ejecución tienen `status="Created"`, THE Suite_de_Pruebas SHALL verificar que la Respuesta_Final contiene `ok=1`.
2. WHEN al menos un Resultado_de_Ad tiene `status="Failed"`, THE Suite_de_Pruebas SHALL verificar que la Respuesta_Final contiene `ok=0`, incluso si otros ads de la misma ejecución fueron `"Created"`.
3. WHEN `execute()` retorna una Respuesta_Final exitosa (sin excepción no controlada), THE Suite_de_Pruebas SHALL verificar que el código de estado HTTP es exactamente `200`, tanto cuando `ok=1` como cuando `ok=0`.

### Requirement 12: Efectos secundarios de persistencia

**User Story:** Como mantenedor, quiero verificar las llamadas exactas a los repositorios de Strapi, para detectar regresiones en la persistencia del precheck.

#### Acceptance Criteria

1. WHEN `execute()` completa el procesamiento de ads, THE Suite_de_Pruebas SHALL verificar que `campaign_publish_repository.save_or_update` se invoca exactamente una vez con `filter_data={'campaign_id': self.campaign_id, 'channel_id': self.channel_id}` y un segundo argumento que contiene exactamente `meta_campaign_objective`, `meta_optimization_goal`, `meta_billing_event`, `meta_campaign_mode` y `meta_account_id`, más `meta_page_id`.
2. WHEN el Caso_de_Uso tiene `lead_gen_form_id` o `whatsapp_number_id` con valor verdadero, THE Suite_de_Pruebas SHALL verificar que el diccionario pasado a `save_or_update` incluye adicionalmente `meta_lead_form_id` y/o `meta_whatsapp_id` respectivamente; en su ausencia, THE Suite_de_Pruebas SHALL verificar que dichas claves no aparecen en el diccionario.
3. WHEN `meta_payload['campaign']['ad_sets']` contiene una lista no vacía, THE Suite_de_Pruebas SHALL verificar que `ad_channel_repository.update` se invoca exactamente una vez por cada ad set, en el mismo orden, con el `ad_channel_id` extraído de `ads[0].adCreative.asset_feed_spec.ad_channel_id` (o `0` cuando esa ruta está ausente) y `data={'channel_creative': <ad_set correspondiente>}`.
4. IF la clave `ad_sets` está completamente ausente en `meta_payload['campaign']` (a diferencia de estar presente como lista vacía), THEN THE Suite_de_Pruebas SHALL verificar que `execute()` propaga `TypeError` en la segunda iteración sobre `campaign_data.get('ad_sets')` (sin valor por defecto), después de que `save_or_update` ya haya sido invocado una vez, caracterizando esta inconsistencia actual entre la primera iteración (con default `[]`) y la segunda (sin default).
5. WHEN `lead_gen_form_id` o `whatsapp_number_id` están presentes en el Caso_de_Uso, THE Suite_de_Pruebas SHALL verificar que se inyectan respectivamente como `lead_gen_form_id`/`whatsapp_number_id` dentro de cada ad set antes de invocar `_save_creative_to_publish`.
6. WHEN se construye cada entrada de `creatives`, THE Suite_de_Pruebas SHALL verificar los campos `idx`, `name`, `adset_id`, `ad_id`, `adchannel_id`, `daily_budget`, `images` (proyección de `url`/`valid`/`error`), `bodies`, `titles`, `descriptions`, `call_to_action_types`, los cinco indicadores `*_valid_amount`, los cinco valores `*_max_amount` (por defecto `0` cuando `asset_feed_spec` no los define), `unique_titles`, `unique_bodies`, `unique_descriptions`, `daily_budget_valid`, `min_daily_budget`, `proposal_url` (unión por comas de `website_url`), `proposal_url_valid`, `proposal_locations`, `locations` y `locations_valid`.
7. WHEN se construye la sección `campaign` de la Respuesta_Final, THE Suite_de_Pruebas SHALL verificar exactamente `name`, `channel_name="Meta"`, `creatives_no=len(creatives)`, `objective`, `optimization_goal` y `mode=self.creative_type`.
8. WHEN `self.objective` es una clave válida de `META_ODAX_CTA_MAPPING`, THE Suite_de_Pruebas SHALL verificar que `valid_ctas` contiene exactamente el mismo conjunto de valores que `META_ODAX_CTA_MAPPING[self.objective]["recommended_ctas"]`, comparando por conjunto y no por orden de lista.
9. IF `self.objective` no es una clave de `META_ODAX_CTA_MAPPING`, THEN THE Suite_de_Pruebas SHALL verificar que `execute()` propaga `TypeError` al calcular `valid_ctas`, después de que `save_or_update` y todas las llamadas a `ad_channel_repository.update` ya se hayan ejecutado, caracterizando que el fallo ocurre al final de la ejecución pese a que los efectos de persistencia ya se completaron.

### Requirement 13: Escenarios combinados y orden de evaluación

**User Story:** Como responsable de calidad, quiero verificar que múltiples ad sets y ads se procesan de forma independiente y en orden, para confiar en el precheck sobre campañas reales.

#### Acceptance Criteria

1. WHEN `meta_payload['campaign']['ad_sets']` está presente como una lista vacía, THE Suite_de_Pruebas SHALL verificar que la primera iteración de validación no produce ningún Resultado_de_Ad, que `has_errors` es `False`, y que `ok=1`. **Nota de precisión:** cuando la clave `ad_sets` está completamente ausente (no como lista vacía), esta condición NO produce `ok=1`: por la misma inconsistencia de default entre la primera iteración (`campaign_data.get('ad_sets', [])`, con default `[]`) y la segunda iteración de construcción de `creatives` (`campaign_data.get('ad_sets')`, sin default) caracterizada en el Requirement 12.9, `enumerate(None)` lanza `TypeError` antes de que `execute()` pueda retornar una Respuesta_Final. THE Suite_de_Pruebas SHALL verificar ambos subcasos por separado: `ok=1` para `ad_sets=[]`, y `TypeError` (después de que `save_or_update` ya se invocó una vez) para la clave `ad_sets` completamente ausente.
2. WHEN existen múltiples ad sets con una combinación de ads válidos e inválidos, THE Suite_de_Pruebas SHALL verificar que la Respuesta_Final contiene `ok=0` (por la presencia de al menos un ad inválido) y que cada ad se procesa de forma independiente sin mezclar sus resultados, mediante aserciones de argumentos de llamada sobre los dobles de `MetaAdsValidator` que demuestren que cada ad inválido dispara únicamente las llamadas correspondientes a su propio defecto (por ejemplo, un doble configurado con `side_effect` distinto por ad, verificando que cada llamada recibió los datos de su propio ad y no los de otro), dado que `results` no forma parte de la Respuesta_Final y su contenido detallado por ad no es observable directamente.
3. WHEN existen múltiples ad sets válidos, THE Suite_de_Pruebas SHALL verificar que `creatives` contiene una entrada por ad set con `idx` secuencial comenzando en `0`, en el mismo orden que `meta_payload['campaign']['ad_sets']`.

### Requirement 14: Calidad y mantenibilidad de la suite

**User Story:** Como equipo de desarrollo, quiero una suite determinista y legible, para facilitar el diagnóstico de regresiones.

#### Acceptance Criteria

1. THE Suite_de_Pruebas SHALL definir nombres de función únicos con el prefijo `test_` que identifiquen la condición ejercitada y el resultado esperado.
2. THE Suite_de_Pruebas SHALL usar en cada escenario datos mínimos que incluyan únicamente los campos necesarios para alcanzar la rama y observar el resultado especificado.
3. WHEN varios escenarios reutilizan una función constructora (builder) o fixture, THE Suite_de_Pruebas SHALL recibir una instancia nueva de cada lista y diccionario mutable en cada invocación, sin defaults mutables compartidos.
4. WHEN una prueba verifica una llamada a un Doble_de_Prueba, THE Suite_de_Pruebas SHALL comprobar exactamente los argumentos posicionales y nombrados relevantes, no solo que la llamada ocurrió.
5. WHEN una prueba verifica un error dentro de `errors`, THE Suite_de_Pruebas SHALL comprobar exactamente la cantidad de errores, el `slug` y el contenido relevante del `message`.
6. WHEN una prueba verifica una excepción, THE Suite_de_Pruebas SHALL comprobar exactamente el tipo de excepción y su mensaje o la ausencia de una Respuesta_Final exitosa.
7. WHEN pytest ejecuta repetidamente el archivo de pruebas con las mismas entradas y distintos órdenes de ejecución, THE Suite_de_Pruebas SHALL producir los mismos resultados sin depender de estado mutable compartido ni del orden de las pruebas.
8. WHEN pytest ejecuta `tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py`, THE Suite_de_Pruebas SHALL finalizar con exactamente cero pruebas `failed`, cero pruebas `skipped` y cero errores de recopilación o ejecución.

## Testing Strategy

### Unit Tests
- Construcción del Caso_de_Uso y estado heredado (Requirement 2).
- Métodos auxiliares heredados: `_get_decoded_access_token`, `_build_meta_payload` (Requirements 3-4).
- Métodos propios: `_get_account_details`, `_get_minimum_budget`, `_save_creative_to_publish`, `_save_campaign_channel_publish` (Requirements 5-6, 12).
- Orquestación completa de `execute()`: ramas DYNAMIC, STANDARD, tipo desconocido, bloque de creación, agregación y respuesta final (Requirements 7-13).

### Integration Tests
Fuera de alcance de esta especificación. La suite descrita es exclusivamente unitaria con dependencias externas sustituidas por Dobles_de_Prueba.

### Property-Based Tests
No se exige un conjunto de propiedades con Hypothesis para esta suite: el comportamiento de `FacebookGeneratePreCheckCreativeUseCase` es principalmente de orquestación con efectos secundarios verificables por ejemplo concreto y por matrices parametrizadas. Si durante la implementación se identifica una invariante pura de amplio dominio (por ejemplo la fórmula de `has_errors` sobre una lista arbitraria de resultados), puede añadirse como prueba basada en propiedades adicional sin que sea un requisito obligatorio de esta especificación.
