# Requirements Document

## Introduction

Este documento define los requisitos para una suite de pruebas unitarias con pytest de la clase `FacebookSavePreCheckImagesUseCase`, ubicada en `sinergia/app/v2/use_cases/meta_ads.py` (líneas ~2028-2073), y de su clase padre directa `FacebookSavePreCheckBaseUseCase` (líneas ~1951-2027) en la porción de comportamiento que `FacebookSavePreCheckImagesUseCase` invoca por herencia: el constructor, `_get_ad_channel`, `_get_campaign_setup`, `_set_channel_id` y `_build_response`. `FacebookSavePreCheckBaseUseCase` hereda a su vez de `FacebookGeneratePreCheckCreativeUseCase` (cubierta por su propia suite en el spec `facebook-generate-pre-check-creative-tests`), de la cual `FacebookSavePreCheckImagesUseCase` usa el constructor heredado (que llama al constructor de `FacebookTestCreativeUploadUseCase`), `_get_decoded_access_token` y `_save_creative_to_publish`.

La suite debe caracterizar el comportamiento observable actual, incluida la rama DYNAMIC de validación de imágenes, el no-op de la rama STANDARD, el paso hacia adelante (pass-through) del bloque `try/except Exception as e: raise e`, y las particularidades ya presentes en el código, entre ellas: que `FacebookSavePreCheckBaseUseCase.__init__` siempre invoca al constructor padre con `complete_campaign_data={}` (un diccionario vacío, no `None`), lo que produce `None` silencioso en varios atributos heredados en lugar del `AttributeError` que se produciría con `complete_campaign_data=None`; el default mutable `pre_check_data: PreCheckDataDict = {}` en la firma del constructor; y los distintos comportamientos ante estructuras `creative`/`ads` malformadas (`IndexError`, `AttributeError`, o ejecución sin error según el caso). La implementación de la suite es el entregable de esta fase; no se modifica código productivo.

**Ubicación obligatoria de los artefactos de prueba:** conforme a `sinergia/.kiro/steering/structure.md`, todo archivo de pruebas unitarias de la capa `use_cases` vive en `sinergia/tests/v2/unit/use_cases/`. La suite de esta especificación SHALL residir en `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py`. Todo artefacto de especificación (requirements, design, tasks) y todo artefacto de implementación de esta feature SHALL permanecer dentro del árbol `sinergia/`.

## Glossary

- **Suite_de_Pruebas**: Conjunto de pruebas unitarias pytest para `FacebookSavePreCheckImagesUseCase` definido en `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py`.
- **Caso_de_Uso**: Instancia de `FacebookSavePreCheckImagesUseCase`.
- **Caso_de_Uso_Padre**: `FacebookSavePreCheckBaseUseCase`, superclase directa de la que `FacebookSavePreCheckImagesUseCase` hereda `__init__`, `_get_ad_channel`, `_get_campaign_setup`, `_set_channel_id` y `_build_response`.
- **Caso_de_Uso_Abuelo**: `FacebookGeneratePreCheckCreativeUseCase`, superclase de `FacebookSavePreCheckBaseUseCase`, de la que se hereda transitivamente la instanciación de `ad_channel_repository`/`campaign_publish_repository` y el método `_save_creative_to_publish`.
- **Caso_de_Uso_Bisabuelo**: `FacebookTestCreativeUploadUseCase`, superclase de `FacebookGeneratePreCheckCreativeUseCase`, de la que se hereda transitivamente `_get_decoded_access_token` y la asignación inicial de `ad_account_id`, `page_id`, `objective`, `optimization_goal`, `lead_gen_form_id`, `whatsapp_number_id`, `billing_event` y `channel_id`.
- **Datos_de_Precheck**: Argumento `pre_check_images_data` (tipo `PreCheckDataDict`) recibido por el constructor de `FacebookSavePreCheckImagesUseCase`, reenviado sin modificar como `pre_check_data` al constructor del Caso_de_Uso_Padre.
- **Datos_de_Campaña_Vacíos**: El diccionario literal `{}` que `FacebookSavePreCheckBaseUseCase.__init__` pasa siempre como tercer argumento posicional (`complete_campaign_data`) al invocar `super().__init__(...)`, independientemente del contenido de Datos_de_Precheck.
- **Cliente_Redis**: Objeto `redis_client` importado a nivel de módulo en `app.v2.use_cases.meta_ads`, usado por `_get_decoded_access_token` para leer el token de Facebook.
- **Repositorio_de_Canal**: `AdChannelRepository`, instanciado en el constructor del Caso_de_Uso_Abuelo y usado por `_get_ad_channel` y por `_save_creative_to_publish`.
- **Repositorio_de_Publicación**: `CampaignChannelPublishRepository`, instanciado en el constructor del Caso_de_Uso_Abuelo y usado por `_get_campaign_setup`.
- **Validador_Meta**: `MetaAdsValidator`, clase de utilidades estáticas usada dentro de `_validate_images_dynamic` para validar y contar imágenes.
- **Ad_Channel**: Diccionario retornado por `Repositorio_de_Canal.get_by_campaign_and_ad_channel_id`, con la forma `{"attributes": {"channel_ref": {"data": {"id": ...}}, "channel_creative": {...}}}`.
- **Campaign_Setup**: Diccionario retornado por `Repositorio_de_Publicación.get_by_campaign_id_and_channel_id`, con la forma `{"attributes": {"meta_campaign_mode": "DYNAMIC"|"STANDARD"|...}}`.
- **Creative**: Diccionario `ad_channel['attributes']['channel_creative']`, con la forma `{"name", "id", "daily_budget", "ads": [{"id", "adCreative": {"asset_feed_spec": {...}, "object_story_spec": {...}}}], "proposal_locations"}`.
- **Ad_Creative**: Diccionario `creative['ads'][0]['adCreative']`.
- **Asset_Feed_Spec**: Diccionario `ad_creative['asset_feed_spec']`, mutado in-place por `_validate_images_dynamic`.
- **Object_Story_Spec**: Diccionario `ad_creative['object_story_spec']`, no mutado por esta clase (la rama STANDARD es un no-op).
- **Respuesta_de_Precheck**: Diccionario retornado por `execute()` con la forma completa descrita en `_build_response` (`name`, `adset_id`, `ad_id`, `adchannel_id`, `daily_budget`, `images`, `bodies`, `titles`, `descriptions`, `call_to_action_types`, cinco indicadores `*_valid_amount`, cinco valores `*_max_amount`, `unique_titles`, `unique_bodies`, `unique_descriptions`, `daily_budget_valid`, `min_daily_budget`, `proposal_url`, `proposal_url_valid`, `proposal_locations`, `locations`, `locations_valid`).
- **Doble_de_Prueba**: Sustitución controlada creada con `unittest.mock.MagicMock`/`patch`.
- **Guard_de_Red**: Mecanismo de prueba que impide solicitudes HTTP reales durante la ejecución de la Suite_de_Pruebas.

## Requirements

### Requirement 1: Infraestructura, aislamiento y ubicación de la suite

**User Story:** Como desarrollador, quiero ejecutar la Suite_de_Pruebas de forma aislada y en la ubicación estándar del proyecto, para que los resultados no dependan de Strapi, Redis, la Graph API de Facebook, ni de servicios de red reales.

#### Acceptance Criteria

1. THE Suite_de_Pruebas SHALL residir exclusivamente en el archivo `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py`, conforme a la convención documentada en `sinergia/.kiro/steering/structure.md` para pruebas unitarias de `use_cases`.
2. WHEN una prueba construye un Caso_de_Uso, THE Suite_de_Pruebas SHALL sustituir `AdChannelRepository` y `CampaignChannelPublishRepository` por Dobles_de_Prueba parcheando `app.v2.use_cases.meta_ads.AdChannelRepository` y `app.v2.use_cases.meta_ads.CampaignChannelPublishRepository` antes de invocar el constructor, sin construir ni invocar un `StrapiClient` real.
3. WHEN una prueba ejercita `_get_decoded_access_token`, THE Suite_de_Pruebas SHALL sustituir el Cliente_Redis parcheando `app.v2.use_cases.meta_ads.redis_client`, sin conexiones reales a Redis.
4. WHILE pytest ejecuta la Suite_de_Pruebas, THE Suite_de_Pruebas SHALL realizar cero solicitudes de red reales, incluidas las que `MetaAdsValidator.validate_images_precheck` podría intentar mediante `requests.get`.
5. WHERE un escenario de la rama DYNAMIC requiere ejercitar código de imágenes, THE Suite_de_Pruebas SHALL evitar que se invoque una solicitud HTTP real, ya sea omitiendo `url` en las entradas de imagen del escenario, parcheando `MetaAdsValidator.validate_images_precheck`, o mediante un Guard_de_Red que falle rápido ante cualquier fuga.
6. WHERE una prueba requiere contexto de aplicación Flask, THE Suite_de_Pruebas SHALL primero verificar si dicho contexto es realmente necesario para el código alcanzable (por ejemplo, para que `flask_babel.gettext` resuelva el texto de una `DataNotFoundException`); si no lo es, THE Suite_de_Pruebas SHALL ejecutar la prueba como unidad pura sin crear una aplicación ni un contexto Flask ni un `tests/conftest.py` nuevo.
7. WHILE se implementa la Suite_de_Pruebas, THE Suite_de_Pruebas SHALL mantener sin modificaciones `sinergia/app/v2/use_cases/meta_ads.py`, `sinergia/app/v2/use_cases/facebook_validator_service.py`, `sinergia/app/v2/repository/ad_channel.py`, `sinergia/app/v2/repository/campaign_channel_publish.py`, y cualquier otro archivo de producción.
8. WHEN una prueba necesita fijar una dependencia de test, THE Suite_de_Pruebas SHALL declararla en `sinergia/requirements-test.txt` únicamente si aún no está declarada, sin modificar `sinergia/requirements.txt`.

### Requirement 2: Construcción del Caso de Uso y estado heredado

**User Story:** Como mantenedor, quiero verificar cómo se inicializa el Caso_de_Uso a partir de Datos_de_Precheck, para detectar cambios accidentales en los atributos que consumen el resto de los métodos.

#### Acceptance Criteria

1. WHEN se construye un Caso_de_Uso con Datos_de_Precheck completos, THE Suite_de_Pruebas SHALL verificar que `adset_id`, `ad_id`, `adchannel_id`, `images`, `bodies`, `titles`, `descriptions`, `call_to_action_types` y `locations` quedan asignados exactamente a los valores provistos.
2. WHEN Datos_de_Precheck omite `daily_budget`, THE Suite_de_Pruebas SHALL verificar que `self.daily_budget` queda inicializado en `0`.
3. WHEN Datos_de_Precheck omite `proposal_url`, THE Suite_de_Pruebas SHALL verificar que `self.proposal_url` queda inicializado en `''`.
4. WHEN Datos_de_Precheck omite `images`, `bodies`, `titles`, `descriptions`, `call_to_action_types` o `locations`, THE Suite_de_Pruebas SHALL verificar que el atributo correspondiente queda inicializado en una lista vacía nueva.
5. WHEN se construye un Caso_de_Uso, THE Suite_de_Pruebas SHALL verificar que `campaign_id` queda asignado desde `pre_check_images_data.get('campaign_id')` y que `user_id` queda asignado desde el argumento `user_id`, propagados a través de `FacebookSavePreCheckBaseUseCase.__init__` hacia el Caso_de_Uso_Bisabuelo.
6. WHEN se construye un Caso_de_Uso, THE Suite_de_Pruebas SHALL verificar que `ad_account_id`, `page_id`, `objective`, `optimization_goal`, `lead_gen_form_id`, `whatsapp_number_id`, `billing_event` y `channel_id` quedan todos en `None`, caracterizando que Datos_de_Campaña_Vacíos (`{}`) se propaga siempre hacia el Caso_de_Uso_Bisabuelo sin importar el contenido de Datos_de_Precheck, incluso cuando Datos_de_Precheck incluyera claves como `ad_account_id` o `page_id` (que, de existir, serían ignoradas por el constructor del Caso_de_Uso_Padre).
7. WHEN se construye un Caso_de_Uso, THE Suite_de_Pruebas SHALL verificar que dicha construcción no propaga `AttributeError`, a diferencia del comportamiento caracterizado para `FacebookGeneratePreCheckCreativeUseCase` con `complete_campaign_data=None` documentado en el spec `facebook-generate-pre-check-creative-tests`, dado que aquí siempre se pasa `{}` (un diccionario vacío verdadero para `.get()`, aunque falsy para el operador ternario) en lugar de `None`.
8. WHEN se construye un Caso_de_Uso, THE Suite_de_Pruebas SHALL verificar que el Repositorio_de_Canal parcheado y el Repositorio_de_Publicación parcheado se instancian exactamente una vez cada uno, heredado del Caso_de_Uso_Abuelo.
9. IF se construye un Caso_de_Uso con `pre_check_images_data=None` (en lugar de omitir el argumento), THEN THE Suite_de_Pruebas SHALL verificar que el constructor propaga `AttributeError` al invocar `None.get('campaign_id')`, caracterizando que el default mutable `{}` de la firma solo protege el caso de omisión del argumento, no el paso explícito de `None`.
10. WHERE se invoca el constructor dos veces seguidas sin proveer `pre_check_images_data` en ninguna de las dos invocaciones, THE Suite_de_Pruebas SHALL verificar si el default mutable `pre_check_data: PreCheckDataDict = {}` de la firma de `FacebookSavePreCheckBaseUseCase.__init__` produce o no compartición observable de estado entre ambas instancias (por ejemplo, mutando `images` de la primera instancia y comprobando si la segunda instancia lo refleja), documentando el resultado verificado como comportamiento actual sin proponer una corrección.

### Requirement 3: Obtención del Ad_Channel

**User Story:** Como desarrollador, quiero verificar la búsqueda del Ad_Channel asociado al precheck, para asegurar que un canal inexistente se reporta de forma consistente.

#### Acceptance Criteria

1. WHEN se invoca `_get_ad_channel`, THE Suite_de_Pruebas SHALL verificar que `ad_channel_repository.get_by_campaign_and_ad_channel_id` se invoca exactamente una vez con los argumentos posicionales exactos `(self.campaign_id, self.adset_id, self.ad_id, self.adchannel_id)`, en ese orden.
2. WHEN el Repositorio_de_Canal devuelve un Ad_Channel verdadero, THE Suite_de_Pruebas SHALL verificar que `_get_ad_channel` retorna el mismo objeto por identidad.
3. IF el Repositorio_de_Canal devuelve un valor falsy (`None` o `{}`), THEN THE Suite_de_Pruebas SHALL verificar que `_get_ad_channel` propaga `DataNotFoundException` con el mensaje exacto `"Creative not found!"`.
4. WHEN `execute()` obtiene un Ad_Channel ausente, THE Suite_de_Pruebas SHALL verificar que la excepción se propaga sin invocar `_set_channel_id`, `campaign_publish_repository.get_by_campaign_id_and_channel_id`, ni `ad_channel_repository.update`.

### Requirement 4: Obtención del Campaign_Setup

**User Story:** Como desarrollador, quiero verificar la búsqueda de la configuración de campaña asociada al canal, para asegurar que una configuración inexistente se reporta con un mensaje diagnosticable.

#### Acceptance Criteria

1. WHEN se invoca `_get_campaign_setup`, THE Suite_de_Pruebas SHALL verificar que `campaign_publish_repository.get_by_campaign_id_and_channel_id` se invoca exactamente una vez con los argumentos posicionales exactos `(self.campaign_id, self.channel_id)`, en ese orden.
2. WHEN el Repositorio_de_Publicación devuelve un Campaign_Setup verdadero, THE Suite_de_Pruebas SHALL verificar que `_get_campaign_setup` retorna el mismo objeto por identidad.
3. IF el Repositorio_de_Publicación devuelve un valor falsy, THEN THE Suite_de_Pruebas SHALL verificar que `_get_campaign_setup` propaga `DataNotFoundException` con un mensaje que contiene exactamente `self.campaign_id` y `self.channel_id` en el formato `f"Campaign Setup not found for campaign_id: {self.campaign_id} and channel_id: {self.channel_id}"`.
4. WHEN `execute()` obtiene un Campaign_Setup ausente, THE Suite_de_Pruebas SHALL verificar que la excepción se propaga sin invocar `MetaAdsValidator.validate_images_precheck`, `MetaAdsValidator.is_valid_images_amount`, ni `ad_channel_repository.update` (vía `_save_creative_to_publish`), pero después de que `_get_ad_channel` y `_set_channel_id` ya se ejecutaron.

### Requirement 5: Asignación del channel_id

**User Story:** Como mantenedor, quiero verificar la extracción anidada del identificador de canal, para asegurar que los valores ausentes en cualquier nivel producen un default seguro.

#### Acceptance Criteria

1. WHEN `ad_channel['attributes']['channel_ref']['data']['id']` está presente con un valor verdadero, THE Suite_de_Pruebas SHALL verificar que `_set_channel_id` asigna exactamente ese valor a `self.channel_id`.
2. IF cualquiera de las claves `attributes`, `channel_ref`, `data` o `id` está ausente en el Ad_Channel, THEN THE Suite_de_Pruebas SHALL verificar que `_set_channel_id` asigna `0` a `self.channel_id`, sin propagar ninguna excepción, para cada nivel de ausencia probado por separado.
3. WHEN `_set_channel_id` se invoca dentro de `execute()`, THE Suite_de_Pruebas SHALL verificar que ocurre después de `_get_ad_channel` y antes de `_get_campaign_setup`, de forma que el `channel_id` usado por `_get_campaign_setup` sea el recién asignado y no el valor inicial `None` heredado del constructor.

### Requirement 6: Orquestación de execute() y cortocircuito ante fallos

**User Story:** Como responsable de calidad, quiero verificar el orden exacto de operaciones de `execute()`, para asegurar que un fallo temprano impide efectos secundarios posteriores.

#### Acceptance Criteria

1. WHEN `execute()` se ejecuta sin fallos, THE Suite_de_Pruebas SHALL verificar que las operaciones ocurren en el orden: `_get_decoded_access_token`, `_get_ad_channel`, `_set_channel_id`, extracción de `creative` desde `ad_channel`, `_get_campaign_setup`, bloque de validación condicional, `_save_creative_to_publish`, `_build_response`.
2. WHEN el Cliente_Redis devuelve un valor falsy, THE Suite_de_Pruebas SHALL verificar que `execute()` propaga `NotAccessException` sin invocar `_get_ad_channel`, `_get_campaign_setup`, ninguna validación de imágenes, ni `_save_creative_to_publish`.
3. WHEN `_get_ad_channel` propaga `DataNotFoundException`, THE Suite_de_Pruebas SHALL verificar que `execute()` no invoca `_save_creative_to_publish` ni `_build_response`.
4. WHEN `_get_campaign_setup` propaga `DataNotFoundException`, THE Suite_de_Pruebas SHALL verificar que `execute()` no invoca `_save_creative_to_publish` ni `_build_response`, pero que la extracción de `creative` y de `asset_feed`/`story_spec` sí ocurrió antes del fallo, dado que estas extracciones preceden a la llamada de `_get_campaign_setup` en el cuerpo de `execute()`.
5. WHEN el bloque de validación (DYNAMIC o STANDARD) completa sin excepción, THE Suite_de_Pruebas SHALL verificar que `execute()` invoca `_save_creative_to_publish` exactamente una vez con el mismo objeto `creative` por identidad, y a continuación `_build_response` exactamente una vez con ese mismo objeto `creative` por identidad.
6. WHEN `execute()` completa sin excepción, THE Suite_de_Pruebas SHALL verificar que retorna exactamente el diccionario producido por `_build_response`, por identidad.

### Requirement 7: Rama DYNAMIC — validación de imágenes

**User Story:** Como responsable de campañas, quiero verificar que el precheck de imágenes DYNAMIC invoca los validadores correctos y sobreescribe el Asset_Feed_Spec con los datos propios del Caso_de_Uso.

#### Acceptance Criteria

1. WHEN `campaign_setup['attributes']['meta_campaign_mode']` es `"DYNAMIC"` y `asset_feed` (`ad_creative['asset_feed_spec']`) es un diccionario verdadero, THE Suite_de_Pruebas SHALL verificar que `_validate_images_dynamic` es invocado con ese `asset_feed` por identidad.
2. WHEN se invoca `_validate_images_dynamic`, THE Suite_de_Pruebas SHALL verificar que `MetaAdsValidator.validate_images_precheck` se invoca exactamente una vez con `self.images` como único argumento, comparado por identidad de lista (no por igualdad de contenido), sin que la Suite_de_Pruebas permita una solicitud HTTP real.
3. WHEN `MetaAdsValidator.validate_images_precheck` retorna (sin lanzar excepción, comportamiento real de dicho método), THE Suite_de_Pruebas SHALL verificar que `asset_feed['images']` queda sobreescrito exactamente con `self.images` por identidad, incluso si `asset_feed['images']` tenía previamente un valor distinto (por ejemplo una lista vacía o una lista con otras entradas), caracterizando que el contenido original de `asset_feed['images']` se descarta sin combinarse con `self.images`.
4. WHEN se invoca `_validate_images_dynamic`, THE Suite_de_Pruebas SHALL verificar que `MetaAdsValidator.is_valid_images_amount` se invoca exactamente una vez con `self.images` como único argumento, y que `asset_feed['images_valid_amount']` queda asignado exactamente con el valor booleano retornado.
5. WHEN `self.images` es una lista vacía, THE Suite_de_Pruebas SHALL verificar, usando el comportamiento real (no simulado) de `MetaAdsValidator.is_valid_images_amount`, que `asset_feed['images_valid_amount']` queda en `False`.
6. WHEN `self.images` contiene exactamente 10 entradas, THE Suite_de_Pruebas SHALL verificar, usando el comportamiento real de `MetaAdsValidator.is_valid_images_amount`, que `asset_feed['images_valid_amount']` queda en `True`.
7. WHEN `self.images` contiene exactamente 11 entradas, THE Suite_de_Pruebas SHALL verificar, usando el comportamiento real de `MetaAdsValidator.is_valid_images_amount`, que `asset_feed['images_valid_amount']` queda en `False`.
8. WHEN una entrada de `self.images` tiene `url` ausente o falsy, THE Suite_de_Pruebas SHALL verificar, usando el comportamiento real de `MetaAdsValidator.validate_images_precheck`, que dicha entrada no provoca una solicitud HTTP y que el bucle continúa sin agregarle las claves `valid`/`error`, mientras que las entradas restantes con `url` ausente reciben el mismo tratamiento.
9. WHEN una entrada de `self.images` tiene `url` verdadero y la Suite_de_Pruebas parchea la solicitud HTTP subyacente para simular un fallo de red, THE Suite_de_Pruebas SHALL verificar, usando el comportamiento real de `MetaAdsValidator.validate_images_precheck`, que dicha entrada queda mutada in-place con `valid=False` y `error="Could not fetch image"`, sin que `_validate_images_dynamic` ni `execute()` propaguen ninguna excepción, caracterizando que `validate_images_precheck` nunca lanza excepción por sí misma.
10. WHEN `_validate_images_dynamic` completa exitosamente, THE Suite_de_Pruebas SHALL verificar que `execute()` continúa hacia `_save_creative_to_publish` y `_build_response` sin interrupción, y que la Respuesta_de_Precheck resultante se construye a partir del `asset_feed` ya mutado.

### Requirement 8: Rama DYNAMIC con Asset_Feed_Spec ausente o vacío

**User Story:** Como responsable de calidad, quiero verificar que un creativo DYNAMIC sin Asset_Feed_Spec no dispara ninguna validación de imágenes.

#### Acceptance Criteria

1. IF `campaign_setup['attributes']['meta_campaign_mode']` es `"DYNAMIC"` y `asset_feed` es `None`, THEN THE Suite_de_Pruebas SHALL verificar que `_validate_images_dynamic` no se invoca, que `MetaAdsValidator.validate_images_precheck` y `MetaAdsValidator.is_valid_images_amount` no se invocan, y que `execute()` continúa sin error hacia `_save_creative_to_publish` y `_build_response`.
2. IF `asset_feed` es un diccionario vacío (`{}`), THEN THE Suite_de_Pruebas SHALL verificar el mismo resultado que en 8.1, dado que `{}` es falsy en la condición `and asset_feed` de `execute()`.
3. IF la clave `asset_feed_spec` está completamente ausente en `ad_creative` (a diferencia de estar presente con valor `None` o `{}`), THEN THE Suite_de_Pruebas SHALL verificar que `asset_feed` queda en `None` (por el default `{}` de `.get('asset_feed_spec')`... **nota de precisión:** el código productivo invoca `ad_creative.get('asset_feed_spec')` sin segundo argumento de default, por lo que la ausencia de la clave produce `None`, igual que el caso 8.1) y que el resultado observable es idéntico al de 8.1.

### Requirement 9: Rama STANDARD — no-op de validación de imágenes

**User Story:** Como responsable de campañas, quiero verificar que el precheck de imágenes STANDARD no realiza ninguna validación, para caracterizar explícitamente que esta clase solo valida imágenes en modo DYNAMIC.

#### Acceptance Criteria

1. WHEN `campaign_setup['attributes']['meta_campaign_mode']` es `"STANDARD"` y `story_spec` (`ad_creative['object_story_spec']`) es un diccionario verdadero, THE Suite_de_Pruebas SHALL verificar que `_validate_images_standard` es invocado con ese `story_spec` por identidad.
2. WHEN se invoca `_validate_images_standard`, THE Suite_de_Pruebas SHALL verificar que no se invoca `MetaAdsValidator.validate_images_precheck` ni `MetaAdsValidator.is_valid_images_amount`, y que el objeto `story_spec` permanece sin ninguna clave nueva añadida tras la ejecución.
3. WHEN el bloque STANDARD completa, THE Suite_de_Pruebas SHALL verificar que `execute()` continúa sin error hacia `_save_creative_to_publish` y `_build_response`, y que la Respuesta_de_Precheck resultante no refleja ninguna validación de imágenes aplicada (los campos `images`, `images_valid_amount` de la Respuesta_de_Precheck provienen íntegramente de los valores ya presentes en `asset_feed_spec` antes de `execute()`, sin mutación).
4. IF `campaign_setup['attributes']['meta_campaign_mode']` es `"STANDARD"` y `story_spec` es falsy (`None` o `{}`), THEN THE Suite_de_Pruebas SHALL verificar que `_validate_images_standard` no se invoca y que `execute()` continúa sin error hacia `_save_creative_to_publish` y `_build_response`.

### Requirement 10: meta_campaign_mode desconocido

**User Story:** Como responsable de calidad, quiero verificar que un modo de campaña distinto de DYNAMIC/STANDARD no dispara ninguna validación.

#### Acceptance Criteria

1. WHEN `campaign_setup['attributes']['meta_campaign_mode']` no es `"DYNAMIC"` ni `"STANDARD"` (incluida cadena vacía, `None`, o la clave `meta_campaign_mode` completamente ausente), THE Suite_de_Pruebas SHALL verificar que ni `_validate_images_dynamic` ni `_validate_images_standard` se invocan, independientemente de si `asset_feed`/`story_spec` son verdaderos o falsy.
2. WHEN se da la condición de 10.1, THE Suite_de_Pruebas SHALL verificar que `execute()` continúa directamente hacia `_save_creative_to_publish` y `_build_response` sin ninguna mutación de `asset_feed_spec`/`object_story_spec`.

### Requirement 11: Estructuras de creative/ads malformadas

**User Story:** Como mantenedor, quiero caracterizar el comportamiento exacto ante estructuras `creative`/`ads`/`adCreative` incompletas dentro del bloque de validación, para detectar cambios accidentales en esos casos límite.

#### Acceptance Criteria

1. IF `creative` no tiene la clave `ads` o `creative['ads']` es una lista vacía, THEN THE Suite_de_Pruebas SHALL verificar que `execute()` propaga `IndexError` al evaluar `creative.get('ads', [])[0]`, y que ni `_get_campaign_setup` ni `_save_creative_to_publish` fueron invocados antes de la excepción (dado que esta extracción ocurre dentro del bloque `try` que antecede a `_save_creative_to_publish`, pero después de `_get_campaign_setup` en el orden de líneas del método), verificando el orden exacto observado en el código bajo prueba en lugar de asumirlo.
2. IF `creative['ads'][0]['adCreative']` está presente con valor `None` explícito, THEN THE Suite_de_Pruebas SHALL verificar que `execute()` propaga `AttributeError` al invocar `.get('asset_feed_spec')`/`.get('object_story_spec')` sobre `None`, caracterizando que `.get('adCreative', {})` no aplica su valor de default cuando la clave existe con valor `None` (el default de `dict.get` solo se usa cuando la clave está ausente, no cuando su valor es `None`), y que dicha excepción ocurre antes de `_save_creative_to_publish`.
3. IF `creative['ads'][0]['adCreative']` está presente con valor `{}` (diccionario vacío), THEN THE Suite_de_Pruebas SHALL verificar que `execute()` NO propaga ninguna excepción en este punto: `asset_feed` y `story_spec` quedan ambos en `None` (vía `{}.get('asset_feed_spec')`/`{}.get('object_story_spec')`, ambos sin segundo argumento de default en el código productivo), ninguna rama de validación se ejecuta, y `execute()` continúa hacia `_save_creative_to_publish` y `_build_response`.
4. IF la clave `adCreative` está completamente ausente en `creative['ads'][0]` (a diferencia de estar presente con valor `None` o `{}`), THEN THE Suite_de_Pruebas SHALL verificar que, dentro del bloque de validación, `ad_creative.get('asset_feed_spec')`/`ad_creative.get('object_story_spec')` se evalúan sobre el diccionario vacío de default `{}` que sí aplica `.get('adCreative', {})` en este punto del código (a diferencia del caso 11.2), por lo que `asset_feed`/`story_spec` quedan en `None` sin excepción, resultando en el mismo comportamiento observable que 11.3.

### Requirement 12: Pass-through del bloque try/except

**User Story:** Como mantenedor, quiero verificar que el bloque `try/except Exception as e: raise e` no altera el tipo ni el mensaje de las excepciones que atraviesa, para confirmar que es funcionalmente transparente.

#### Acceptance Criteria

1. WHEN una excepción de cualquier tipo se origina dentro del bloque `try` de `execute()` (por ejemplo el `AttributeError` caracterizado en Requirement 11.2), THE Suite_de_Pruebas SHALL verificar que el tipo de excepción observado desde `execute()` es idéntico al tipo de la excepción original, y que el mensaje (`str(exception)`) observado es idéntico al mensaje de la excepción originada dentro del bloque `try`, sin ningún prefijo, sufijo, ni envoltura adicional.
2. WHEN se compara el resultado de 12.1 con el comportamiento que se observaría si el bloque `try/except Exception as e: raise e` no existiera en absoluto, THE Suite_de_Pruebas SHALL documentar mediante el docstring o comentario de la prueba que ambos comportamientos son equivalentes, dado que `raise e` sin transformación reproduce exactamente la excepción original (a diferencia de un patrón de envoltura como `raise NuevaExcepcion(str(e))`, que sí alteraría el tipo).

### Requirement 13: Persistencia vía _save_creative_to_publish

**User Story:** Como mantenedor, quiero verificar la llamada exacta al repositorio de canal al persistir el creativo validado, para detectar regresiones en la actualización de Strapi.

#### Acceptance Criteria

1. WHEN `execute()` invoca `_save_creative_to_publish(creative)`, THE Suite_de_Pruebas SHALL verificar que `ad_channel_repository.update` se invoca exactamente una vez con los argumentos exactos `(ad_channel_id, {'channel_creative': creative})`, donde `creative` es el mismo objeto por identidad y `ad_channel_id` se extrae de `creative.get('ads')[0].get('adCreative', {}).get('asset_feed_spec', {}).get('ad_channel_id', 0)`.
2. WHEN `asset_feed_spec['ad_channel_id']` está presente con un valor verdadero, THE Suite_de_Pruebas SHALL verificar que ese valor exacto se usa como primer argumento de `ad_channel_repository.update`.
3. IF la ruta `creative['ads'][0]['adCreative']['asset_feed_spec']['ad_channel_id']` está ausente en cualquiera de sus niveles intermedios (`adCreative` ausente de forma tolerada por el default `{}`, o `asset_feed_spec` ausente, o `ad_channel_id` ausente), THEN THE Suite_de_Pruebas SHALL verificar que se usa el default `0` como primer argumento de `ad_channel_repository.update`, para cada nivel de ausencia probado por separado, siempre que `creative['ads']` no esté vacía (condición ya garantizada por el momento en que `_save_creative_to_publish` es alcanzable, ver 13.4).
4. THE Suite_de_Pruebas SHALL verificar y documentar explícitamente que `_save_creative_to_publish` usa `creative.get('ads')` **sin** segundo argumento de default (a diferencia del `creative.get('ads', [])` usado en el bloque de validación de `execute()`), y que esta línea solo es alcanzable después de que el bloque de validación ya evaluó exitosamente `creative.get('ads', [])[0]` sin lanzar `IndexError` (Requirement 11.1); por lo tanto, en todo escenario donde se llega a invocar `_save_creative_to_publish` dentro de `execute()`, `creative['ads']` ya es una lista no vacía, y la ausencia de default en esta línea no introduce ningún riesgo adicional de `TypeError`/`IndexError` no cubierto por el Requirement 11. La Suite_de_Pruebas SHALL además incluir una prueba que invoque `_save_creative_to_publish` de forma directa y aislada (sin pasar por `execute()`) con un `creative` cuya clave `ads` está ausente, verificando que en esa invocación directa sí se propaga `TypeError` (porque `creative.get('ads')` devuelve `None` y `None[0]` no es válido), para dejar constancia de que la protección descrita depende del orden de `execute()` y no es una garantía intrínseca del método `_save_creative_to_publish` en sí mismo.

### Requirement 14: Construcción de la Respuesta_de_Precheck

**User Story:** Como consumidor de la API, quiero verificar que `_build_response` construye el diccionario de salida completo con los valores y defaults documentados, incluyendo los valores ya mutados por la validación DYNAMIC.

#### Acceptance Criteria

1. WHEN `_build_response` se invoca con un `creative` completo, THE Suite_de_Pruebas SHALL verificar que la Respuesta_de_Precheck contiene exactamente las claves `name`, `adset_id`, `ad_id`, `adchannel_id`, `daily_budget`, `images`, `bodies`, `titles`, `descriptions`, `call_to_action_types`, `images_valid_amount`, `titles_valid_amount`, `bodies_valid_amount`, `descriptions_valid_amount`, `call_to_action_types_valid_amount`, `images_max_amount`, `titles_max_amount`, `bodies_max_amount`, `descriptions_max_amount`, `call_to_action_types_max_amount`, `unique_titles`, `unique_bodies`, `unique_descriptions`, `daily_budget_valid`, `min_daily_budget`, `proposal_url`, `proposal_url_valid`, `proposal_locations`, `locations`, `locations_valid`, sin claves adicionales ni faltantes.
2. WHEN `asset_feed_spec` provee valores explícitos para cada campo listado en 14.1, THE Suite_de_Pruebas SHALL verificar que la Respuesta_de_Precheck refleja exactamente esos valores, incluida la proyección de `images` a `[{'url', 'valid', 'error'}]` por cada entrada.
3. WHEN `asset_feed_spec` omite alguno de los campos listados en 14.1 (excepto `images`, `bodies`, `titles`, `descriptions`, `call_to_action_types`, que tienen su propio default de lista vacía), THE Suite_de_Pruebas SHALL verificar los defaults exactos: `False` para los cinco indicadores `*_valid_amount`, `0` para los cinco valores `*_max_amount`, `False` para `unique_titles`/`unique_bodies`/`unique_descriptions`/`daily_budget_valid`/`proposal_url_valid`/`locations_valid`, `0` para `min_daily_budget`, y lista vacía para `locations`.
4. WHEN `asset_feed_spec['link_urls']` contiene entradas con `website_url`, THE Suite_de_Pruebas SHALL verificar que `proposal_url` en la Respuesta_de_Precheck es la unión por comas (`','.join(...)`) de esos valores, en el mismo orden.
5. WHEN `creative` omite la clave `proposal_locations`, THE Suite_de_Pruebas SHALL verificar que `proposal_locations` en la Respuesta_de_Precheck es una lista vacía.
6. WHEN se ejecuta un escenario completo de `execute()` en rama DYNAMIC donde `_validate_images_dynamic` mutó `asset_feed['images']` con entradas que ahora tienen `valid`/`error` asignados por el comportamiento real de `MetaAdsValidator.validate_images_precheck`, THE Suite_de_Pruebas SHALL verificar que la Respuesta_de_Precheck final refleja esos mismos valores `valid`/`error` mutados en su proyección de `images`, demostrando que `_build_response` lee el `asset_feed_spec` después de la mutación de la validación, no una copia previa.
7. IF `creative['ads'][0]['adCreative']` es un valor falsy explícito distinto de estar completamente ausente (por ejemplo `None`) en el momento de invocar `_build_response` de forma aislada (fuera del flujo de `execute()`, donde el Requirement 11.2 ya caracteriza que esa situación produce una excepción previa dentro de `execute()`), THEN THE Suite_de_Pruebas SHALL verificar que `_build_response` propaga `AttributeError` al invocar `.get('asset_feed_spec', {})` sobre `None`, dado que `ad_creative = ads_to_publish.get('adCreative')` no usa segundo argumento de default en `_build_response`.
8. IF la clave `adCreative` está completamente ausente en `ads_to_publish` al invocar `_build_response` de forma aislada, THEN THE Suite_de_Pruebas SHALL verificar que `_build_response` propaga `AttributeError` al invocar `.get('asset_feed_spec', {})` sobre el valor `None` resultante de `ads_to_publish.get('adCreative')` sin default, caracterizando que este escenario —distinto del Requirement 11.4, donde el bloque de validación de `execute()` sí tolera la ausencia de `adCreative` gracias a su propio uso de `.get('adCreative', {})` con default— hace que `_build_response` sea, en la práctica, menos tolerante que el bloque de validación que la precede dentro de `execute()`; por esta razón, dentro del flujo completo de `execute()`, este escenario solo es observable si `creative` es compartido por referencia y mutado entre la extracción del bloque de validación y la llamada a `_build_response` de forma que `adCreative` desaparezca entretanto (escenario no alcanzable con los Dobles_de_Prueba usuales), por lo que la Suite_de_Pruebas SHALL verificar este criterio invocando `_build_response` directamente sobre una instancia del Caso_de_Uso, sin pasar por `execute()`, dejando constancia en el comentario de la prueba de por qué este camino no es alcanzable de forma natural desde `execute()` con un `creative` construido consistentemente.

### Requirement 15: Calidad y mantenibilidad de la suite

**User Story:** Como equipo de desarrollo, quiero una suite determinista y legible, para facilitar el diagnóstico de regresiones.

#### Acceptance Criteria

1. THE Suite_de_Pruebas SHALL definir nombres de función únicos con el prefijo `test_` que identifiquen la condición ejercitada y el resultado esperado.
2. THE Suite_de_Pruebas SHALL usar en cada escenario datos mínimos que incluyan únicamente los campos necesarios para alcanzar la rama y observar el resultado especificado.
3. WHEN varios escenarios reutilizan una función constructora (builder) o fixture, THE Suite_de_Pruebas SHALL recibir una instancia nueva de cada lista y diccionario mutable en cada invocación, sin defaults mutables compartidos entre pruebas (distinto del default mutable de producción caracterizado en Requirement 2.10, que sí se ejercita deliberadamente en esa prueba puntual).
4. WHEN una prueba verifica una llamada a un Doble_de_Prueba, THE Suite_de_Pruebas SHALL comprobar exactamente los argumentos posicionales y nombrados relevantes, no solo que la llamada ocurrió.
5. WHEN una prueba verifica una excepción, THE Suite_de_Pruebas SHALL comprobar exactamente el tipo de excepción y su mensaje.
6. WHEN pytest ejecuta repetidamente el archivo de pruebas con las mismas entradas y distintos órdenes de ejecución, THE Suite_de_Pruebas SHALL producir los mismos resultados sin depender de estado mutable compartido entre pruebas ni del orden de las pruebas.
7. WHEN pytest ejecuta `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py`, THE Suite_de_Pruebas SHALL finalizar con exactamente cero pruebas `failed`, cero pruebas `skipped` y cero errores de recopilación o ejecución.

## Testing Strategy

### Unit Tests
- Construcción del Caso_de_Uso y estado heredado, incluida la peculiaridad de Datos_de_Campaña_Vacíos y el default mutable de la firma (Requirement 2).
- Métodos propios heredados de `FacebookSavePreCheckBaseUseCase`: `_get_ad_channel`, `_get_campaign_setup`, `_set_channel_id`, `_build_response` (Requirements 3-5, 14).
- Orquestación completa de `execute()`: orden de llamadas, cortocircuito, ramas DYNAMIC/STANDARD/desconocida, estructuras malformadas, pass-through de excepciones, persistencia (Requirements 6-13).

### Integration Tests
Fuera de alcance de esta especificación. La suite descrita es exclusivamente unitaria con dependencias externas sustituidas por Dobles_de_Prueba.

### Property-Based Tests
No se exige un conjunto de propiedades con Hypothesis para esta suite: el comportamiento de `FacebookSavePreCheckImagesUseCase` es principalmente de orquestación con efectos secundarios verificables por ejemplo concreto y por matrices parametrizadas (por ejemplo los límites de `is_valid_images_amount` en 0/10/11 imágenes). Si durante la implementación se identifica una invariante pura de amplio dominio, puede añadirse como prueba basada en propiedades adicional sin que sea un requisito obligatorio de esta especificación.
