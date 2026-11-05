# Requirements Document

## Introduction

Este documento reside en `sinergia/.kiro/specs/meta-ads-leads-offsite-conversions/requirements.md` y describe cambios exclusivamente dentro del árbol `sinergia/` (aplicación Flask independiente dentro del monorepo `docker-deploy`, con virtualenv en `sinergia/venv`).

La funcionalidad habilita la validación (PreCheck), construcción y publicación (Launch) de campañas Meta Ads con la combinación **Objetivo `OUTCOME_LEADS` + Optimización `OFFSITE_CONVERSIONS`**, tanto para la rama `DYNAMIC` como para la rama `STANDARD`. La combinación exige un píxel de Meta (`pixel_id`) y un evento de conversión (`conversion_event`) que se transmiten a Meta como `promoted_object` del ad set, además de `destination_type = WEBSITE` en el ad set y `tracking_specs` en el ad.

Código productivo afectado (rutas relativas a `sinergia/`):

- `app/v2/use_cases/facebook_validator_service.py`: constantes y enumeraciones de soporte.
- `app/v2/use_cases/meta_ads.py`: `CampaignDataDict`, `FacebookTestCreativeUploadUseCase.__init__` (solo lectura del nuevo campo), `FacebookGetCampaignObjectiveUseCase`, `FacebookGeneratePreCheckCreativeUseCase`, `FacebookSavePreCheck*UseCase` y `FacebookLaunchCampaignUseCase`; además, como seguimiento (Requirement 16), una guarda mínima en `FacebookGetLaunchCampaignCreativesUseCase._build_standard_creative_published` y el cálculo de `proposal_url` en `FacebookGeneratePreCheckCreativeUseCase._build_dynamic_creative_entry`.
- `app/v2/resources/external.py`: modelo Swagger y construcción de `complete_campaign_data` del endpoint de PreCheck.

Decisiones confirmadas por el usuario durante la revisión del código:

1. La fuente única de `pixel_id` en el PreCheck es el campo plano del body (`payload.pixel_id` → `complete_campaign_data['pixel_id']` → `self.pixel_id`), igual para DYNAMIC y STANDARD. El `promoted_object` se construye recién en el Launch.
2. `conversion_event` es un campo plano nuevo del body del PreCheck, junto a `pixel_id`.
3. El campo `meta_conversion_event` del content-type Strapi `campaign-channel-publishes` se crea manualmente en Strapi (fuera de alcance); esta especificación asume que ya existe.
4. Los errores de parámetros obligatorios del PreCheck se lanzan como `MetaException` antes de recorrer los ads (códigos `META012`, `META013`, `META014`).
5. `promoted_object_valid` refleja la validez de `pixel_id` + `conversion_event` en ambas ramas para esta combinación.
6. En DYNAMIC, para esta combinación, una `proposal_url` ausente o inválida agrega un error por-ad `url-error` (paridad con STANDARD).
7. El Launch obtiene `pixel_id` y `conversion_event` del Campaign_Setup (`meta_pixel_id`, `meta_conversion_event`); `tracking_specs` se agrega solo para esta combinación.
8. Un `conversion_event` enviado con cualquier otra combinación se ignora (no se valida ni se persiste).
9. El Launch re-valida `meta_conversion_event` del Campaign_Setup contra Eventos_Conversion_Leads antes de publicar el ad set (Requirement 11, criterio 9), como defensa ante ediciones del Campaign_Setup posteriores al PreCheck.
10. Se corrige de forma global (todas las combinaciones de `_STANDARD_SUPPORTED_COMBINATIONS`, no solo Combinación_Leads_Offsite) la inconsistencia de anotación del CTA en Rama_STANDARD de Caso_PreCheck: hoy `_validate_standard_cta` escribe el resultado en `call_to_action['valid']` (raíz), mientras que `_build_standard_creative_entry`, los demás constructores de elementos STANDARD de `meta_ads.py` y `Caso_Launch._is_campaign_valid` leen `call_to_action['type']['valid']`. En consecuencia, `call_to_action_types_valid_amount` y la compuerta del Launch heredan el `type.valid` enviado por el cliente: un CTA no permitido con `type.valid = True` pasa, y un CTA permitido sin `type.valid` bloquea el Launch hasta que se ejecuta `FacebookSavePreCheckCTAsUseCase`. La corrección (Requirement 15) hace que Caso_PreCheck escriba el resultado real en `call_to_action['type']['valid']`; es el único cambio de comportamiento intencional para Otras_Combinaciones (Requirement 13). Los lectores no cambian su lógica de lectura; la única excepción es una guarda mínima en `_build_standard_creative_entry` y en los constructores STANDARD análogos que trata un `call_to_action` truthy no-diccionario como `{}`, porque hoy `call_to_action.get('type', ...)` lanza `AttributeError` tras el `cta-error` del criterio 15.5 y `execute()` no retorna Respuesta_PreCheck (Requirement 15, criterios 8 y 11).
11. Seguimiento detectado durante la implementación (Requirement 16), aplicado a todas las combinaciones: (a) `FacebookGetLaunchCampaignCreativesUseCase._build_standard_creative_published` recibe la misma guarda mínima de `call_to_action` no-diccionario que el Requirement 15 criterio 8, extendida a `call_to_action.type` no-diccionario, porque hoy lanza `AttributeError`; (b) `_build_dynamic_creative_entry` calcula `proposal_url` omitiendo los `website_url` con valor `None`, porque hoy `','.join(...)` lanza `TypeError` y `execute()` falla para Otras_Combinaciones en Rama_DYNAMIC con `website_url = None`. El caso (b) es una excepción explícita al Requirement 13 criterio 1; el bloque de URL existente y su slug `assets-budget-error` para Otras_Combinaciones no cambian.

## Out of Scope

- Creación del campo `meta_conversion_event` en el schema de Strapi.
- Cualquier cambio de comportamiento para combinaciones distintas de `OUTCOME_LEADS` + `OFFSITE_CONVERSIONS`, incluida `OUTCOME_SALES` + `OFFSITE_CONVERSIONS`, con la única excepción de la corrección global de la anotación del CTA en Rama_STANDARD de Caso_PreCheck (decisión 10, Requirement 15) y de las correcciones de robustez del seguimiento (decisión 11, Requirement 16).
- Modificación de los lectores de `call_to_action['type']['valid']` (`_build_standard_creative_entry`, constructores análogos de elementos STANDARD y `Caso_Launch._is_campaign_valid`) y de `FacebookSavePreCheckCTAsUseCase._validate_ctas_standard`, con la única excepción de la guarda mínima de `call_to_action` no-diccionario en `_build_standard_creative_entry` y en los constructores STANDARD análogos que usan `call_to_action.get('type', ...)` (Requirement 15, criterios 8 y 11) y en `Caso_Consulta_Launch._build_standard_creative_published` (Requirement 16, criterios 1–3). `_is_campaign_valid` y `_validate_ctas_standard` no se modifican.
- `_build_dynamic_creative_entry`, salvo el cálculo de `proposal_url` sin valores `None` (Requirement 16, criterios 4–5).
- `FacebookTestCreativeUploadUseCase.execute()`, `FacebookPublishCampaignUseCase` y `MetaAdsValidator.validate_promoted_object` (lógica exclusiva de SALES).
- Validación de elegibilidad del píxel (volumen de eventos) para esta combinación.
- `FacebookSavePreCheckBaseUseCase._build_response` (no se modifica).

## Glossary

- **Combinación_Leads_Offsite**: el par (`objective == "OUTCOME_LEADS"`, `optimization_goal == "OFFSITE_CONVERSIONS"`).
- **Otras_Combinaciones**: cualquier par (objective, optimization_goal) distinto de Combinación_Leads_Offsite.
- **Servicio_Validador**: módulo `app/v2/use_cases/facebook_validator_service.py`, incluida la clase `MetaAdsValidator`.
- **Enum_Leads**: enumeración `LeadsOptimizationGoal` del Servicio_Validador.
- **Eventos_Conversion_Leads**: nueva constante del Servicio_Validador con el conjunto exacto `{COMPLETE_REGISTRATION, LEAD, CONTACT, SUBMIT_APPLICATION, SCHEDULE, SUBSCRIBE, START_TRIAL}`.
- **CTAs_Leads_Offsite**: conjunto exacto de CTAs permitidos para Combinación_Leads_Offsite: `{LEARN_MORE, SIGN_UP, SUBSCRIBE, ORDER_NOW, SHOP_NOW, APPLY_NOW, BOOK_NOW, CONTACT_US, GET_OFFER, GET_QUOTE, DOWNLOAD, SEE_MENU, SEE_DETAILS, GET_SHOWTIMES, REQUEST_TIME, BUY_TICKETS, LISTEN_NOW, PLAY_GAME, WATCH_MORE, NO_BUTTON}`, registrado como entrada `OFFSITE_CONVERSIONS` de `LEADS_GOAL_ALLOWED_CTAS`.
- **Caso_Objetivos**: `FacebookGetCampaignObjectiveUseCase`.
- **Caso_PreCheck**: `FacebookGeneratePreCheckCreativeUseCase`.
- **Casos_Save_PreCheck**: `FacebookSavePreCheckImagesUseCase`, `FacebookSavePreCheckTextsUseCase`, `FacebookSavePreCheckCTAsUseCase`, `FacebookSavePreCheckBudgetUseCase`, `FacebookSavePreCheckProposalURLUseCase` y `FacebookSavePreCheckLocationsUseCase`.
- **Caso_Launch**: `FacebookLaunchCampaignUseCase`.
- **Caso_Consulta_Launch**: `FacebookGetLaunchCampaignCreativesUseCase` (consulta de solo lectura de los creativos ya publicados de una campaña Meta Ads).
- **Recurso_PreCheck**: endpoint Flask de `app/v2/resources/external.py` que construye `complete_campaign_data` e invoca a Caso_PreCheck.
- **Pixel_Id**: valor `self.pixel_id` de Caso_PreCheck, proveniente del campo plano `pixel_id` del body.
- **Conversion_Event**: valor `self.conversion_event` de Caso_PreCheck, proveniente del campo plano `conversion_event` del body, normalizado con `strip()` y `upper()` cuando es un string no vacío.
- **Campaign_Setup**: registro del content-type Strapi `campaign-channel-publishes`, accedido mediante `CampaignChannelPublishRepository`.
- **Rama_DYNAMIC** / **Rama_STANDARD**: flujos de procesamiento cuando `creative_type` (o `meta_campaign_mode`) es `DYNAMIC` / `STANDARD`.
- **Respuesta_PreCheck**: diccionario `data` retornado por Caso_PreCheck con las claves `campaign`, `creatives`, `valid_ctas` y `account_config`.
- **Payload_AdSet**: diccionario enviado a `POST /act_{ad_account_id}/adsets` por `Caso_Launch._publish_adset`.
- **Payload_Ad**: diccionario enviado a `POST /act_{ad_account_id}/ads` por `Caso_Launch._publish_ad`.
- **Suite_de_Pruebas**: conjunto de pruebas unitarias bajo `sinergia/tests/v2/unit/use_cases/`.

## Requirements

### Requirement 1: Constantes de soporte en el Servicio_Validador

**User Story:** Como desarrollador, quiero que el Servicio_Validador conozca la nueva optimización, sus eventos de conversión y sus CTAs, para que todas las validaciones usen una única fuente de verdad.

#### Acceptance Criteria

1. THE Enum_Leads SHALL contener exactamente cuatro miembros: `LEAD_GENERATION`, `QUALITY_LEAD`, `CONVERSATIONS` y `OFFSITE_CONVERSIONS`, donde cada miembro tiene como valor el string idéntico a su nombre (`OFFSITE_CONVERSIONS` con valor `"OFFSITE_CONVERSIONS"`) y los tres miembros preexistentes conservan sus valores actuales.
2. THE Servicio_Validador SHALL definir la constante Eventos_Conversion_Leads como un `Set[str]` de exactamente siete elementos, iguales en mayúsculas a `COMPLETE_REGISTRATION`, `LEAD`, `CONTACT`, `SUBMIT_APPLICATION`, `SCHEDULE`, `SUBSCRIBE` y `START_TRIAL`, sin modificar el contenido de `SALES_ALLOWED_CUSTOM_EVENTS`.
3. THE Servicio_Validador SHALL registrar en `LEADS_GOAL_ALLOWED_CTAS`, bajo la clave `LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value`, un conjunto igual a CTAs_Leads_Offsite (exactamente los veinte valores del Glossary), conservando con su contenido actual las entradas `LEAD_GENERATION`, `QUALITY_LEAD` y `CONVERSATIONS`.
4. WHEN `MetaAdsValidator.validate_optimization_goal_for_objective` es invocado con `goal = "OFFSITE_CONVERSIONS"` y `objective = "OUTCOME_LEADS"`, con `throw = True` o `throw = False`, THE Servicio_Validador SHALL retornar `True` sin lanzar excepción.
5. WHEN `MetaAdsValidator.validate_cta_for_goal(c, "OUTCOME_LEADS", "OFFSITE_CONVERSIONS", throw=False)` es invocado con un `c` de tipo `str` cuyo valor normalizado por `MetaAdsValidator._normalize_cta` (`strip()`, `upper()` y espacios reemplazados por `_`) pertenece a CTAs_Leads_Offsite, incluidas variantes como `"learn more"` o `" SEE_MENU "`, THE Servicio_Validador SHALL retornar `True`.
6. IF `MetaAdsValidator.validate_cta_for_goal` es invocado con `objective = "OUTCOME_LEADS"`, `goal = "OFFSITE_CONVERSIONS"` y un `c` de tipo `str` no vacío cuyo valor normalizado no pertenece a CTAs_Leads_Offsite (por ejemplo `WHATSAPP_MESSAGE` o `CALL_NOW`), THEN THE Servicio_Validador SHALL retornar `False` cuando `throw = False` y lanzar `ValueError` con el mensaje `"CTA '<cta_normalizado>' not allowed for objective 'OUTCOME_LEADS' and goal 'OFFSITE_CONVERSIONS'"` cuando `throw = True`.
7. IF `MetaAdsValidator.validate_cta_for_goal` es invocado con `objective = "OUTCOME_LEADS"`, `goal = "OFFSITE_CONVERSIONS"` y un `c` que es `None`, `""` o solo espacios en blanco, THEN THE Servicio_Validador SHALL retornar `False` cuando `throw = False` y lanzar `ValueError` con el mensaje `"CTA is required but was empty"` cuando `throw = True`.
8. THE Servicio_Validador SHALL incluir `SEE_MENU` y `SEE_DETAILS` en `MetaAdsValidator.VALID_CTA_VALUES`, conservando todos los valores existentes, de modo que cada elemento de CTAs_Leads_Offsite pertenezca a `MetaAdsValidator.VALID_CTA_VALUES`.
9. THE Servicio_Validador SHALL conservar sin cambios `SALES_GOAL_ALLOWED_CTAS`, `AWARENESS_GOAL_ALLOWED_CTAS`, `SALES_ALLOWED_CUSTOM_EVENTS`, `META_ODAX_CTA_MAPPING` y el comportamiento de `validate_promoted_object`, de modo que para Otras_Combinaciones `validate_optimization_goal_for_objective`, `get_allowed_ctas_for_goal` y `validate_cta_for_goal` retornen los mismos resultados que antes del cambio (por ejemplo, `validate_optimization_goal_for_objective("OFFSITE_CONVERSIONS", "OUTCOME_AWARENESS", throw=False)` sigue retornando `False`).

### Requirement 2: Catálogo de objetivos (Caso_Objetivos)

**User Story:** Como usuario de la plataforma, quiero ver `OFFSITE_CONVERSIONS` entre las optimizaciones de `OUTCOME_LEADS`, para poder seleccionarla al configurar la campaña.

#### Acceptance Criteria

1. WHEN Caso_Objetivos es ejecutado con cualquier valor de `user_id`, THE Caso_Objetivos SHALL retornar, para el objetivo `OUTCOME_LEADS`, una lista `goals` de exactamente 3 elementos cuyo tercer elemento (índice 2) es exactamente `{'id': 'OFFSITE_CONVERSIONS', 'billing_event': 'IMPRESSIONS'}`, con el valor `'OFFSITE_CONVERSIONS'` obtenido del miembro `OFFSITE_CONVERSIONS` de Enum_Leads.
2. WHEN Caso_Objetivos es ejecutado, THE Caso_Objetivos SHALL retornar en la lista `goals` de `OUTCOME_LEADS` el elemento `{'id': 'LEAD_GENERATION', 'billing_event': 'IMPRESSIONS'}` en el índice 0 y el elemento `{'id': 'CONVERSATIONS', 'billing_event': 'IMPRESSIONS'}` en el índice 1, sin incluir ningún elemento con `id` `QUALITY_LEAD`.
3. WHEN Caso_Objetivos es ejecutado, THE Caso_Objetivos SHALL retornar el objetivo `OUTCOME_LEADS` con `'active': True`.
4. WHEN Caso_Objetivos es ejecutado, THE Caso_Objetivos SHALL retornar una lista de exactamente 4 objetivos en el orden `[OUTCOME_AWARENESS, OUTCOME_TRAFFIC, OUTCOME_SALES, OUTCOME_LEADS]`, donde `OUTCOME_AWARENESS`, `OUTCOME_TRAFFIC` y `OUTCOME_SALES` tienen valores de `id`, `active` y `goals` (contenido y orden de elementos) idénticos a los retornados antes de este cambio.
5. WHEN Caso_Objetivos es ejecutado, THE Caso_Objetivos SHALL retornar el catálogo sin realizar llamadas a la Graph API de Meta ni accesos a Redis o Strapi, produciendo el mismo resultado para cualquier valor de `user_id`.

### Requirement 3: Recepción del parámetro `conversion_event`

**User Story:** Como cliente del API, quiero enviar el evento de conversión en el body del PreCheck, para que la campaña optimice hacia ese evento.

#### Acceptance Criteria

1. THE Recurso_PreCheck SHALL declarar `conversion_event` como campo `String` opcional (no requerido) en su modelo Swagger de entrada, al mismo nivel que el campo plano `pixel_id`.
2. WHEN el Recurso_PreCheck recibe una petición de PreCheck, THE Recurso_PreCheck SHALL incluir la clave `conversion_event` en `complete_campaign_data` con el valor `payload.get('conversion_event')` sin transformarlo, de modo que la clave exista con valor `None` cuando el body no contiene `conversion_event`.
3. WHEN el Recurso_PreCheck recibe una petición de PreCheck, THE Recurso_PreCheck SHALL conservar sin cambios los valores de las demás claves de `complete_campaign_data`, incluida `pixel_id`.
4. THE `CampaignDataDict` SHALL declarar la clave `conversion_event: Optional[str]`.
5. WHEN Caso_PreCheck es construido con un `complete_campaign_data` cuyo `conversion_event` es un string que contiene al menos un carácter distinto de espacio en blanco, THE Caso_PreCheck SHALL asignar a Conversion_Event el resultado de aplicar `strip()` y luego `upper()` a dicho valor (por ejemplo, `"  lead "` produce `"LEAD"`).
6. IF el `conversion_event` de `complete_campaign_data` está ausente, es `None`, no es de tipo `str` o es un string vacío tras `strip()`, THEN THE Caso_PreCheck SHALL asignar `None` a Conversion_Event.
7. WHEN Caso_PreCheck es construido, THE Caso_PreCheck SHALL asignar Conversion_Event sin lanzar excepciones ni validar el valor contra Eventos_Conversion_Leads, independientemente del par (objective, optimization_goal), dejando la validación y el descarte para Otras_Combinaciones a los Requirements 4, 9 y 13.

### Requirement 4: Validaciones obligatorias previas en Caso_PreCheck

**User Story:** Como usuario, quiero que el PreCheck rechace de inmediato una campaña Combinación_Leads_Offsite sin píxel o sin evento válido, para no construir creativos que Meta rechazará.

#### Acceptance Criteria

1. IF Caso_PreCheck procesa Combinación_Leads_Offsite y Pixel_Id está ausente, es `None` o es un string vacío o compuesto solo por espacios tras `strip()`, THEN THE Caso_PreCheck SHALL lanzar `MetaException("META012", ...)` con un mensaje que indique que `pixel_id` es obligatorio para `OUTCOME_LEADS`/`OFFSITE_CONVERSIONS`.
2. IF Caso_PreCheck procesa Combinación_Leads_Offsite, Pixel_Id es válido y Conversion_Event es `None`, THEN THE Caso_PreCheck SHALL lanzar `MetaException("META013", ...)` con un mensaje que indique que `conversion_event` es obligatorio para `OUTCOME_LEADS`/`OFFSITE_CONVERSIONS`.
3. IF Caso_PreCheck procesa Combinación_Leads_Offsite, Pixel_Id es válido, Conversion_Event no es `None` y Conversion_Event no pertenece a Eventos_Conversion_Leads, THEN THE Caso_PreCheck SHALL lanzar `MetaException("META014", ...)` con un mensaje que incluya el valor recibido y los 7 valores de Eventos_Conversion_Leads.
4. WHEN Caso_PreCheck procesa Combinación_Leads_Offsite, THE Caso_PreCheck SHALL evaluar los criterios 1, 2 y 3 en ese orden, lanzar únicamente la excepción de la primera validación que falle, y hacerlo antes de recorrer los ad sets y los ads y antes de invocar `_save_campaign_channel_publish`, tanto en Rama_DYNAMIC como en Rama_STANDARD.
5. IF Caso_PreCheck lanza `META012`, `META013` o `META014`, THEN THE Caso_PreCheck SHALL propagar la `MetaException` sin retornar Respuesta_PreCheck y omitir toda escritura en Campaign_Setup y en `ad-channels`, dejando ambos sin cambios respecto de su estado previo a la invocación.
6. WHEN Caso_PreCheck procesa Combinación_Leads_Offsite con Pixel_Id válido y un Conversion_Event cuyo valor tras `strip()` + `upper()` pertenece a Eventos_Conversion_Leads (independientemente de mayúsculas/minúsculas y de espacios en los extremos del valor original), THE Caso_PreCheck SHALL completar la ejecución sin lanzar `META012`, `META013` ni `META014` y SHALL usar el valor normalizado como Conversion_Event en el resto del procesamiento.
7. WHILE Caso_PreCheck procesa Otras_Combinaciones, THE Caso_PreCheck SHALL omitir la evaluación de los criterios 1, 2 y 3 y completar la ejecución sin lanzar `META012`, `META013` ni `META014`, aunque Pixel_Id o Conversion_Event estén ausentes, vacíos o fuera de Eventos_Conversion_Leads.

### Requirement 5: Soporte de la combinación en Rama_STANDARD de Caso_PreCheck

**User Story:** Como usuario, quiero usar creativos STANDARD con Combinación_Leads_Offsite, para publicar anuncios de imagen única orientados a conversiones web.

#### Acceptance Criteria

1. THE Caso_PreCheck SHALL definir `_STANDARD_SUPPORTED_COMBINATIONS` con exactamente cinco tuplas: (`OUTCOME_AWARENESS`, `REACH`), (`OUTCOME_LEADS`, `LEAD_GENERATION`), (`OUTCOME_LEADS`, `CONVERSATIONS`), (`OUTCOME_SALES`, `OFFSITE_CONVERSIONS`) y la nueva (`OUTCOME_LEADS`, `OFFSITE_CONVERSIONS`).
2. WHEN Caso_PreCheck procesa Combinación_Leads_Offsite en Rama_STANDARD con Pixel_Id válido y Conversion_Event perteneciente a Eventos_Conversion_Leads, THE Caso_PreCheck SHALL completar la ejecución sin lanzar `MetaException("META011", ...)` ni `MetaException("META002", ...)`.
3. WHEN Caso_PreCheck completa la ejecución para Combinación_Leads_Offsite en Rama_STANDARD, THE Caso_PreCheck SHALL retornar una Respuesta_PreCheck con las claves `campaign`, `creatives`, `valid_ctas` y `account_config`, y con un elemento en `creatives` por cada ad recibido en `ad_sets[].ads[]`.
4. IF Caso_PreCheck procesa en Rama_STANDARD un par (objective, optimization_goal) que no pertenece a `_STANDARD_SUPPORTED_COMBINATIONS`, THEN THE Caso_PreCheck SHALL lanzar `MetaException("META011", ...)` antes de recorrer los ad sets y sin invocar `_save_campaign_channel_publish`, igual que la implementación actual.
5. WHILE Caso_PreCheck procesa Rama_DYNAMIC, THE Caso_PreCheck SHALL omitir la verificación contra `_STANDARD_SUPPORTED_COMBINATIONS`.

### Requirement 6: Validación de CTAs en Caso_PreCheck

**User Story:** Como usuario, quiero que el PreCheck marque como válidos únicamente los CTAs aceptados por Meta para esta combinación, para corregirlos antes de publicar.

#### Acceptance Criteria

1. WHEN Caso_PreCheck procesa un ad de Combinación_Leads_Offsite en Rama_DYNAMIC, THE Caso_PreCheck SHALL anotar `valid = True` en cada elemento de `call_to_action_types` cuyo campo `value`, normalizado por `MetaAdsValidator._normalize_cta`, pertenece a CTAs_Leads_Offsite, y `valid = False` en cada uno de los demás elementos, sin modificar el campo `value` original.
2. IF un elemento de `call_to_action_types` de un ad de Combinación_Leads_Offsite en Rama_DYNAMIC tiene `value` ausente, `None` o un string vacío tras la normalización, THEN THE Caso_PreCheck SHALL anotar `valid = False` en ese elemento y continuar procesando los elementos restantes del mismo ad y los ads siguientes sin lanzar excepción.
3. WHEN Caso_PreCheck procesa un ad de Combinación_Leads_Offsite en Rama_STANDARD cuyo `call_to_action` es un diccionario, THE Caso_PreCheck SHALL aplicar `_validate_standard_cta` con la corrección del Requirement 15, anotando el mismo valor booleano en `call_to_action.type.valid` y en `call_to_action.valid` (raíz): `True` si `call_to_action.type.value`, normalizado según el criterio 1, pertenece a CTAs_Leads_Offsite, y `False` en caso contrario (incluido `value` ausente, `None` o vacío).
4. IF Caso_PreCheck anota `call_to_action.type.valid = False` (y por tanto `call_to_action.valid = False`, según el Requirement 15) en un ad de Combinación_Leads_Offsite en Rama_STANDARD, THEN THE Caso_PreCheck SHALL registrar exactamente un error por-ad con slug `cta-error` y un mensaje que indique el CTA rechazado, y continuar procesando los ads siguientes sin lanzar excepción.
5. IF un ad de Combinación_Leads_Offsite en Rama_STANDARD tiene `call_to_action` presente pero no es un diccionario, THEN THE Caso_PreCheck SHALL registrar exactamente un error por-ad con slug `cta-error` que indique que `call_to_action` tiene un formato inválido, sin anotar `valid`.
6. IF un ad de Combinación_Leads_Offsite en Rama_STANDARD no tiene `call_to_action` (ausente, `None` o vacío), THEN THE Caso_PreCheck SHALL omitir la validación de CTA de ese ad sin registrar error `cta-error` ni anotar `valid`.
7. WHEN Caso_PreCheck procesa Combinación_Leads_Offsite en Rama_DYNAMIC o en Rama_STANDARD, THE Caso_PreCheck SHALL retornar en `valid_ctas` de la Respuesta_PreCheck una lista de 20 elementos sin duplicados cuyo conjunto es exactamente igual a CTAs_Leads_Offsite, sin que el orden de los elementos sea significativo.

### Requirement 7: Validación de `proposal_url` en Caso_PreCheck

**User Story:** Como usuario, quiero que el PreCheck exija una URL de destino válida, porque una conversión offsite requiere un sitio web donde se dispare el píxel.

#### Acceptance Criteria

1. WHEN Caso_PreCheck procesa un ad de Combinación_Leads_Offsite en Rama_DYNAMIC con al menos una entrada de `asset_feed_spec.link_urls` que tenga `website_url` no vacío, THE Caso_PreCheck SHALL asignar a `asset_feed_spec.link_url_valid` el valor booleano retornado por `MetaAdsValidator.is_valid_link_url` invocado con los valores `website_url` de las entradas de `asset_feed_spec.link_urls` unidos por coma (`,`), de modo que `link_url_valid` sea `True` únicamente cuando exista exactamente 1 URL y esta cumpla `URL_PATTERN`.
2. IF Caso_PreCheck procesa un ad de Combinación_Leads_Offsite en Rama_DYNAMIC y `asset_feed_spec.link_urls` está ausente, es una lista vacía o todas sus entradas tienen `website_url` ausente, `None` o string vacío, THEN THE Caso_PreCheck SHALL asignar `asset_feed_spec.link_url_valid = False` sin invocar `MetaAdsValidator.is_valid_link_url` y SHALL registrar para ese ad exactamente 1 error con `slug` igual a `url-error` y un `message` que indique que la URL de destino está ausente.
3. IF Caso_PreCheck procesa un ad de Combinación_Leads_Offsite en Rama_DYNAMIC y `asset_feed_spec.link_url_valid` resulta `False` según el criterio 1 (más de 1 URL o URL que no cumple `URL_PATTERN`), THEN THE Caso_PreCheck SHALL registrar para ese ad exactamente 1 error con `slug` igual a `url-error` y un `message` que incluya el valor de URL evaluado e indique que su formato no es válido.
4. IF Caso_PreCheck registra un error `url-error` para un ad de Combinación_Leads_Offsite, THEN THE Caso_PreCheck SHALL agregar ese ad a la lista interna de resultados (`results`, no expuesta en Respuesta_PreCheck) con `status` igual a `Failed`, SHALL continuar procesando los ads restantes sin lanzar `MetaException` y SHALL conservar sin modificar las demás anotaciones de validación (`*_valid`) ya calculadas para ese ad.
5. WHEN Caso_PreCheck procesa un ad de Combinación_Leads_Offsite en Rama_STANDARD, THE Caso_PreCheck SHALL aplicar la validación existente `_validate_standard_url`, que asigna `link_data.link_url_valid` con el resultado de `MetaAdsValidator.is_valid_link_url` sobre `link_data.link` y registra exactamente 1 error `url-error` para el ad cuando `link_data.link` está ausente o vacío o cuando `link_url_valid` es `False`.
6. WHILE Caso_PreCheck procesa un ad de Otras_Combinaciones en Rama_DYNAMIC, THE Caso_PreCheck SHALL asignar `asset_feed_spec.link_url_valid` según el comportamiento actual (resultado de `MetaAdsValidator.is_valid_link_url` sobre las URLs unidas por coma) y SHALL omitir el registro de errores con `slug` igual a `url-error` para ese ad, independientemente del valor de `link_url_valid`.

### Requirement 8: Indicador `promoted_object_valid`

**User Story:** Como usuario, quiero ver en la respuesta si la configuración de píxel y evento es válida, para saber si el ad set podrá optimizar hacia conversiones.

#### Acceptance Criteria

1. WHEN Caso_PreCheck completa la ejecución para Combinación_Leads_Offsite en Rama_DYNAMIC sin lanzar `META012`, `META013` ni `META014`, THE Caso_PreCheck SHALL retornar la clave `promoted_object_valid` con el valor booleano `True` (tipo `bool`) en cada uno de los elementos de `creatives` de la Respuesta_PreCheck.
2. WHEN Caso_PreCheck completa la ejecución para Combinación_Leads_Offsite en Rama_STANDARD sin lanzar `META012`, `META013` ni `META014`, THE Caso_PreCheck SHALL retornar la clave `promoted_object_valid` con el valor booleano `True` (tipo `bool`) en cada uno de los elementos de `creatives` de la Respuesta_PreCheck.
3. WHILE Caso_PreCheck procesa Combinación_Leads_Offsite, THE Caso_PreCheck SHALL determinar `promoted_object_valid` exclusivamente a partir de la validez de Pixel_Id y Conversion_Event, de modo que el elemento de `creatives` de un ad con errores por-ad registrados (incluido `url-error` o `cta-error`) conserve `promoted_object_valid = True`.
4. WHILE Caso_PreCheck procesa Combinación_Leads_Offsite, THE Caso_PreCheck SHALL omitir la invocación de `MetaAdsValidator.validate_promoted_object` para calcular `promoted_object_valid`, tanto en Rama_DYNAMIC como en Rama_STANDARD.
5. IF Caso_PreCheck lanza `META012`, `META013` o `META014` para Combinación_Leads_Offsite, THEN THE Caso_PreCheck SHALL propagar la `MetaException` sin retornar Respuesta_PreCheck, por lo que ningún valor de `promoted_object_valid` se emite.
6. WHILE Caso_PreCheck procesa Otras_Combinaciones, THE Caso_PreCheck SHALL retornar `promoted_object_valid` con el mismo valor que produce la implementación actual para los mismos datos de entrada (Rama_DYNAMIC: `True` salvo que la validación SALES existente con `MetaAdsValidator.validate_promoted_object` falle; Rama_STANDARD: `False`), con independencia de que el body incluya o no `conversion_event`.

### Requirement 9: Persistencia en Campaign_Setup

**User Story:** Como sistema, quiero guardar el píxel y el evento de conversión en el Campaign_Setup, para que el Launch los use sin volver a pedirlos.

#### Acceptance Criteria

1. WHEN Caso_PreCheck termina de recorrer todos los ads para Combinación_Leads_Offsite, THE Caso_PreCheck SHALL invocar `CampaignChannelPublishRepository.save_or_update` exactamente una vez con el filtro (`campaign_id`, `channel_id`) de la ejecución e incluir en los datos la clave `meta_conversion_event` con el valor exacto de Conversion_Event (ya normalizado con `strip()` y `upper()`), tanto en Rama_DYNAMIC como en Rama_STANDARD e independientemente de que uno o más ads tengan `status = "Failed"` en la lista interna de resultados.
2. WHEN Caso_PreCheck termina de recorrer todos los ads para Combinación_Leads_Offsite, THE Caso_PreCheck SHALL incluir en los datos enviados a `CampaignChannelPublishRepository.save_or_update` la clave `meta_pixel_id` con el valor exacto de Pixel_Id, sin transformación, tanto en Rama_DYNAMIC como en Rama_STANDARD.
3. WHILE Caso_PreCheck procesa Otras_Combinaciones, THE Caso_PreCheck SHALL omitir la clave `meta_conversion_event` de los datos enviados a `CampaignChannelPublishRepository.save_or_update`, aun cuando el body incluya un `conversion_event` no vacío.
4. THE Caso_PreCheck SHALL enviar a `CampaignChannelPublishRepository.save_or_update` las claves `meta_campaign_objective`, `meta_optimization_goal`, `meta_billing_event`, `meta_campaign_mode`, `meta_account_id` y `meta_page_id` con los mismos valores que produce el comportamiento previo a esta funcionalidad, e incluir las claves opcionales `meta_lead_form_id`, `meta_whatsapp_id` y `meta_pixel_id` solo cuando el valor de origen correspondiente es truthy, para todas las combinaciones.
5. WHEN Caso_PreCheck termina de recorrer todos los ads para Combinación_Leads_Offsite, THE Caso_PreCheck SHALL enviar `meta_billing_event = "IMPRESSIONS"` en los datos pasados a `CampaignChannelPublishRepository.save_or_update`.
6. IF Caso_PreCheck lanza una `MetaException` con código `META012`, `META013` o `META014` para Combinación_Leads_Offsite, THEN THE Caso_PreCheck SHALL omitir la invocación de `CampaignChannelPublishRepository.save_or_update`, dejando el Campaign_Setup existente sin modificaciones.

### Requirement 10: Soporte en Casos_Save_PreCheck

**User Story:** Como usuario, quiero editar imágenes, textos, CTAs, presupuesto, URL y ubicaciones de una campaña Combinación_Leads_Offsite, para ajustar los creativos después del PreCheck inicial.

#### Acceptance Criteria

1. WHILE el Campaign_Setup registra `meta_campaign_objective = "OUTCOME_LEADS"` y `meta_optimization_goal = "OFFSITE_CONVERSIONS"`, WHEN `FacebookSavePreCheckCTAsUseCase` procesa en Rama_DYNAMIC una lista de 0 a N CTAs, THE `FacebookSavePreCheckCTAsUseCase` SHALL anotar `valid = True` en cada CTA cuyo `value` normalizado pertenece a CTAs_Leads_Offsite y `valid = False` en cada CTA cuyo `value` no pertenece a CTAs_Leads_Offsite, está ausente o provoca una excepción en la validación, sin eliminar ni reordenar ningún CTA de la lista.
2. WHILE el Campaign_Setup registra Combinación_Leads_Offsite, WHEN `FacebookSavePreCheckCTAsUseCase` termina de anotar los CTAs en Rama_DYNAMIC, THE `FacebookSavePreCheckCTAsUseCase` SHALL asignar la lista anotada a `asset_feed_spec.call_to_action_types` y el resultado de `MetaAdsValidator.is_valid_ctas_amount` sobre esa lista a `asset_feed_spec.call_to_action_types_valid_amount` (`False` con 0 CTAs o con más CTAs que `ASSET_MAX_AMOUNTS['call_to_action_types']`), con el mismo criterio que aplica a `OUTCOME_LEADS` + `LEAD_GENERATION`.
3. WHILE el Campaign_Setup registra Combinación_Leads_Offsite, WHEN `FacebookSavePreCheckCTAsUseCase` procesa exactamente un CTA en Rama_STANDARD, THE `FacebookSavePreCheckCTAsUseCase` SHALL asignar `link_data.call_to_action = {'type': {'value': <cta>, 'valid': <pertenece a CTAs_Leads_Offsite>}}`, donde `valid` es `True` si y solo si `<cta>` normalizado pertenece a CTAs_Leads_Offsite.
4. WHILE el Campaign_Setup registra Combinación_Leads_Offsite, WHEN `FacebookSavePreCheckCTAsUseCase` procesa en Rama_STANDARD cero CTAs o más de un CTA, THE `FacebookSavePreCheckCTAsUseCase` SHALL aplicar el mismo tratamiento que aplica hoy a `OUTCOME_LEADS` + `LEAD_GENERATION` (eliminar `link_data.call_to_action` con cero CTAs; dejar `link_data.call_to_action` sin modificar con más de un CTA).
5. WHILE el Campaign_Setup registra Combinación_Leads_Offsite, WHEN `FacebookSavePreCheckImagesUseCase`, `FacebookSavePreCheckTextsUseCase`, `FacebookSavePreCheckBudgetUseCase`, `FacebookSavePreCheckProposalURLUseCase` o `FacebookSavePreCheckLocationsUseCase` es ejecutado con los mismos datos de entrada y el mismo `channel_creative` inicial, THE caso de uso correspondiente SHALL producir anotaciones, persistencia en `ad-channels` y respuesta idénticas, campo por campo, a las que produce para `OUTCOME_LEADS` + `LEAD_GENERATION`, tanto en Rama_DYNAMIC como en Rama_STANDARD.
6. WHILE el Campaign_Setup registra Combinación_Leads_Offsite, WHEN cualquiera de los Casos_Save_PreCheck es ejecutado, THE caso de uso correspondiente SHALL completar la ejecución sin lanzar ninguna excepción cuya causa sea el valor de `meta_campaign_objective` o de `meta_optimization_goal`, y SHALL invocar `_save_creative_to_publish` exactamente una vez con el `channel_creative` actualizado.
7. WHILE el Campaign_Setup registra Combinación_Leads_Offsite, WHEN cualquiera de los Casos_Save_PreCheck persiste el `channel_creative` en Rama_DYNAMIC, THE caso de uso correspondiente SHALL conservar sin cambios el valor de `asset_feed_spec.promoted_object_valid` persistido por Caso_PreCheck.
8. WHILE el Campaign_Setup registra Otras_Combinaciones, THE Casos_Save_PreCheck SHALL producir anotaciones, persistencia en `ad-channels` y respuesta idénticas a las que producían antes de este cambio para los mismos datos de entrada, verificado por la Suite_de_Pruebas con al menos un caso de `OUTCOME_LEADS` + `LEAD_GENERATION` y un caso de `OUTCOME_SALES` + `OFFSITE_CONVERSIONS`.

### Requirement 11: Payload del ad set en Caso_Launch

**User Story:** Como usuario, quiero que el ad set publicado en Meta quede configurado para conversiones en mi sitio web, para que Meta optimice hacia el evento elegido.

#### Acceptance Criteria

1. WHEN Caso_Launch lee el Campaign_Setup, THE Caso_Launch SHALL obtener `meta_pixel_id` y `meta_conversion_event` del diccionario `attributes` del Campaign_Setup, tratando como vacío un valor `None`, un string de longitud 0 o un string compuesto solo por espacios en blanco.
2. WHEN Caso_Launch publica un ad set para Combinación_Leads_Offsite, THE Caso_Launch SHALL incluir en Payload_AdSet la clave `"destination_type"` con el valor exacto `"WEBSITE"`.
3. WHEN Caso_Launch publica un ad set para Combinación_Leads_Offsite, THE Caso_Launch SHALL incluir en Payload_AdSet `"promoted_object": {"pixel_id": <meta_pixel_id>, "custom_event_type": <meta_conversion_event>}`, con exactamente esas dos claves, con valores tomados exclusivamente del Campaign_Setup (ignorando cualquier `promoted_object` presente en el `channel_creative` del ad set) y sin la clave `page_id`.
4. WHEN Caso_Launch publica un ad set para Combinación_Leads_Offsite, THE Caso_Launch SHALL incluir en Payload_AdSet `"optimization_goal": "OFFSITE_CONVERSIONS"` y `"billing_event": "IMPRESSIONS"`.
5. IF Caso_Launch publica un ad set para Combinación_Leads_Offsite y `meta_pixel_id` o `meta_conversion_event` está vacío (según el criterio 1) o ausente en el Campaign_Setup, THEN THE Caso_Launch SHALL lanzar `ParametersNotFoundException` con un mensaje que identifique el campo faltante, antes de enviar la petición `POST` de Payload_AdSet a Meta.
6. IF Caso_Launch lanza una excepción de los criterios 5 o 9 después de haber creado la campaña en Meta, THEN THE Caso_Launch SHALL ejecutar el rollback existente (`_rollback_publish`) sobre la campaña y los ad creatives ya creados, y SHALL propagar la excepción original al llamador tras completar el rollback.
7. THE Caso_Launch SHALL aplicar los criterios 2, 3, 4, 5 y 9 tanto en Rama_DYNAMIC como en Rama_STANDARD.
8. WHEN Caso_Launch publica un ad set con `objective == "OUTCOME_LEADS"` y `optimization_goal == "LEAD_GENERATION"`, THE Caso_Launch SHALL construir Payload_AdSet con `promoted_object = {"page_id": <page_id>}` (con `page_id` tomado del `promoted_object` del ad set o, en su defecto, de `meta_page_id` del Campaign_Setup) y `"destination_type": "ON_AD"`, sin incluir `pixel_id` ni `custom_event_type`.
9. IF Caso_Launch publica un ad set para Combinación_Leads_Offsite y el valor de `meta_conversion_event` no pertenece a Eventos_Conversion_Leads, THEN THE Caso_Launch SHALL lanzar `ParametersNotFoundException` con un mensaje que indique que el evento de conversión no es válido, antes de enviar la petición `POST` de Payload_AdSet a Meta.
10. WHEN Caso_Launch publica un ad set con `objective == "OUTCOME_LEADS"` y `optimization_goal == "CONVERSATIONS"`, THE Caso_Launch SHALL construir Payload_AdSet con `promoted_object = {"page_id": <page_id>}` (misma fuente que el criterio 8), `"destination_type": "WHATSAPP"` y el mismo ajuste de `targeting` que aplica actualmente (`targeting_automation.advantage_audience = 1` y eliminación de `age_max` cuando tiene valor), sin incluir `pixel_id` ni `custom_event_type`.
11. WHEN Caso_Launch publica un ad set con `objective == "OUTCOME_SALES"`, THE Caso_Launch SHALL construir Payload_AdSet con el mismo `promoted_object`, `destination_type` (ausente), `optimization_goal` y `billing_event` que produce el código previo a este cambio.

### Requirement 12: Payload del ad en Caso_Launch

**User Story:** Como usuario, quiero que cada anuncio publicado registre las conversiones offsite del píxel, para medir los resultados de la campaña.

#### Acceptance Criteria

1. WHEN Caso_Launch publica cada ad para Combinación_Leads_Offsite, THE Caso_Launch SHALL incluir en Payload_Ad la clave `"tracking_specs": [{"action.type": ["offsite_conversion"], "dataset": [<meta_pixel_id>]}]`, con una lista de exactamente un elemento cuyo `dataset` contiene exactamente un valor igual al `meta_pixel_id` leído del Campaign_Setup (el mismo valor usado en `promoted_object.pixel_id` de Payload_AdSet).
2. WHEN Caso_Launch publica cada ad para Combinación_Leads_Offsite, THE Caso_Launch SHALL conservar en Payload_Ad las claves existentes `name`, `adset_id`, `creative`, `status` y `access_token` con los mismos valores que produce la implementación previa a esta especificación.
3. THE Caso_Launch SHALL aplicar los criterios 1 y 2 a todos los ads publicados, tanto en Rama_DYNAMIC como en Rama_STANDARD.
4. WHEN Caso_Launch publica un ad para Otras_Combinaciones, THE Caso_Launch SHALL construir Payload_Ad sin la clave `tracking_specs`.
5. WHEN Caso_Launch construye el creativo para Combinación_Leads_Offsite, THE Caso_Launch SHALL conservar el `link` de destino y el tipo de CTA del creativo con los mismos valores que produce la implementación previa a esta especificación, sin agregar `lead_gen_form_id` al `call_to_action` de `link_data`, sin agregar `call_to_actions` al `asset_feed_spec` y sin agregar `app_destination`, aun cuando el ad o el ad set contengan `lead_gen_form_id`.
6. IF `meta_pixel_id` está ausente o vacío en el Campaign_Setup para Combinación_Leads_Offsite, THEN THE Caso_Launch SHALL omitir el envío de todo Payload_Ad a Meta, dado que la `ParametersNotFoundException` del Requirement 11 criterio 5 se lanza antes de publicar el ad set.

### Requirement 13: Compatibilidad hacia atrás

**User Story:** Como responsable del producto, quiero que ningún flujo existente cambie, para no afectar campañas que hoy funcionan.

#### Acceptance Criteria

1. WHILE Caso_PreCheck, Casos_Save_PreCheck o Caso_Launch procesan una campaña con Otras_Combinaciones, THE caso de uso correspondiente SHALL producir, para la misma entrada, las mismas excepciones (tipo y código), las mismas anotaciones por-ad, los mismos datos persistidos en Campaign_Setup, el mismo Payload_AdSet, el mismo Payload_Ad y la misma Respuesta_PreCheck que produce la implementación previa a esta especificación, tanto en Rama_DYNAMIC como en Rama_STANDARD, con las únicas excepciones documentadas en el criterio 7 y en el Requirement 16 criterios 4 y 5 (`proposal_url` sin `None` en Rama_DYNAMIC, que reemplaza el `TypeError` previo).
2. WHILE Caso_Launch publica una campaña con `objective == "OUTCOME_SALES"` y `optimization_goal == "OFFSITE_CONVERSIONS"`, THE Caso_Launch SHALL construir el `promoted_object` de Payload_AdSet validado mediante `MetaAdsValidator.validate_promoted_object`, con `custom_event_type` igual a `PURCHASE` cuando el `promoted_object` del ad set no provee otro evento, SHALL omitir la clave `destination_type` en Payload_AdSet y SHALL omitir la clave `tracking_specs` en Payload_Ad.
3. WHEN se ejecuta la Suite_de_Pruebas tras implementar esta especificación, THE Suite_de_Pruebas SHALL finalizar con 0 fallos y 0 errores en todas las pruebas que existían en `sinergia/tests/v2/unit/use_cases/` antes de esta especificación, sin que dichas pruebas hayan sido eliminadas, marcadas como omitidas o esperadas como fallidas, ni sus aserciones modificadas, salvo la excepción del criterio 8.
4. IF el body del PreCheck incluye `conversion_event` y la campaña corresponde a Otras_Combinaciones, THEN THE Caso_PreCheck SHALL ignorar el campo sin lanzar `MetaException`, sin agregar anotaciones por-ad, sin persistir `meta_conversion_event` en Campaign_Setup y retornando una Respuesta_PreCheck idéntica a la que produce el mismo body sin `conversion_event`.
5. WHEN Recurso_PreCheck recibe, para Otras_Combinaciones, un body que no incluye el campo `conversion_event`, THE Recurso_PreCheck SHALL aceptar el body sin error de validación del modelo Swagger y SHALL construir `complete_campaign_data` con las mismas claves y valores que la implementación previa a esta especificación, más la clave `conversion_event` con valor `None`.
6. WHEN Caso_Objetivos retorna el catálogo de objetivos, THE Caso_Objetivos SHALL retornar para cada objetivo distinto de `OUTCOME_LEADS` los mismos `id`, `active` y `goals` que la implementación previa, y para `OUTCOME_LEADS` los mismos `goals` previos más únicamente el elemento `{'id': 'OFFSITE_CONVERSIONS', 'billing_event': 'IMPRESSIONS'}`.
7. WHILE Caso_PreCheck procesa Otras_Combinaciones en Rama_STANDARD, THE Caso_PreCheck SHALL aplicar el Requirement 15 como único cambio de comportamiento intencional respecto de la implementación previa, limitado a: el valor de `call_to_action.type.valid`, la normalización de `call_to_action.type` del Requirement 15 criterio 3, el error `cta-error` derivado de esa normalización y el valor de `call_to_action_types_valid_amount` en el elemento de `creatives` correspondiente.
8. WHERE una prueba preexistente de `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` codifica el comportamiento previo de herencia de `call_to_action.type.valid` desde la entrada (incluidos el caso que afirma `call_to_action_types_valid_amount is True` heredado del input y las aserciones y docstrings de `TestStandardCtaValidation` y de las fixtures asociadas que indican que `_validate_standard_cta` nunca escribe `type['valid']`), THE Suite_de_Pruebas SHALL actualizar únicamente esas aserciones y docstrings para que verifiquen el comportamiento corregido del Requirement 15, conservando sin cambios toda otra aserción preexistente.

### Requirement 14: Pruebas unitarias

**User Story:** Como desarrollador, quiero una suite exhaustiva y aislada, para verificar la combinación nueva y detectar regresiones sin dependencias externas.

#### Acceptance Criteria

1. THE Suite_de_Pruebas SHALL ubicar todos los archivos de prueba nuevos o ampliados exclusivamente bajo `sinergia/tests/v2/unit/use_cases/`, usando `pytest` y `pytest-mock` del virtualenv `sinergia/venv`.
2. THE Suite_de_Pruebas SHALL agregar las pruebas nuevas como clases nuevas en los archivos existentes (`test_facebook_generate_pre_check_creative.py`, `test_facebook_save_pre_check_*.py`, `test_facebook_launch_campaign.py`) y en los archivos nuevos `test_facebook_validator_leads_offsite_conversions.py` y `test_facebook_get_campaign_objective.py`, sin modificar ni eliminar las clases de prueba preexistentes de esos archivos, salvo las actualizaciones permitidas por el Requirement 13 criterio 8.
3. THE Suite_de_Pruebas SHALL reemplazar mediante mocks toda petición HTTP externa (`requests.get` de descarga de imágenes desde `visual_url`, `requests.post` hacia la Graph API de Meta), el acceso a Redis y los repositorios (`CampaignChannelPublishRepository`, `AdChannelRepository`, `CampaignRepository`, `StrapiClient`), de modo que ninguna prueba abra conexiones reales de red, a Redis ni a Strapi.
4. THE Suite_de_Pruebas SHALL incluir un caso feliz de Combinación_Leads_Offsite para Caso_PreCheck en Rama_DYNAMIC y otro en Rama_STANDARD, verificando que `valid_ctas` es igual a CTAs_Leads_Offsite, que `promoted_object_valid` es `True` y que los datos enviados a `save_or_update` contienen `meta_pixel_id` igual al Pixel_Id recibido y `meta_conversion_event` igual al Conversion_Event normalizado.
5. THE Suite_de_Pruebas SHALL incluir, en Rama_DYNAMIC y en Rama_STANDARD, casos de error de Caso_PreCheck para `pixel_id` ausente (`META012`), `conversion_event` ausente (`META013`) y `conversion_event` no permitido (`META014`), donde "ausente" se prueba como campo omitido del body, valor `None` y string vacío, verificando que se lanza `MetaException` con el código indicado, que `save_or_update` no es invocado y que el mock de `requests.get` de descarga de imágenes no es invocado.
6. THE Suite_de_Pruebas SHALL incluir pruebas parametrizadas que verifiquen la aceptación de cada uno de los siete valores de Eventos_Conversion_Leads, la aceptación de al menos un valor en minúsculas con espacios iniciales y finales (persistido en `meta_conversion_event` en mayúsculas y sin espacios), y el rechazo con `META014` de al menos dos valores que no pertenecen a Eventos_Conversion_Leads, incluido `PURCHASE`.
7. THE Suite_de_Pruebas SHALL incluir pruebas parametrizadas de `validate_cta_for_goal` que verifiquen como válido cada uno de los veinte valores de CTAs_Leads_Offsite y como inválidos al menos dos CTAs que no pertenecen a CTAs_Leads_Offsite, incluido `CALL_NOW`.
8. THE Suite_de_Pruebas SHALL incluir casos de Rama_DYNAMIC para Combinación_Leads_Offsite con `proposal_url` ausente y con `proposal_url` inválida que verifiquen `proposal_url_valid = False` en la Respuesta_PreCheck y el registro del error por-ad `url-error` (observado sobre el helper de validación de URL o sobre la lista interna de resultados), y un caso de Otras_Combinaciones en Rama_DYNAMIC con `proposal_url` ausente que verifique la ausencia del error `url-error`.
9. THE Suite_de_Pruebas SHALL incluir, para cada uno de los seis Casos_Save_PreCheck, un caso feliz de Combinación_Leads_Offsite en Rama_DYNAMIC y otro en Rama_STANDARD (doce casos en total), verificando que el caso de uso finaliza sin lanzar excepción e invoca la persistencia mockeada de `AdChannelRepository`.
10. THE Suite_de_Pruebas SHALL incluir casos felices de Caso_Launch para Combinación_Leads_Offsite en Rama_DYNAMIC y Rama_STANDARD que verifiquen, sobre los payloads capturados por el mock de `requests.post`, que Payload_AdSet tiene `destination_type` igual a `WEBSITE`, que el `promoted_object` de Payload_AdSet contiene el `meta_pixel_id` y el `meta_conversion_event` del Campaign_Setup mockeado, y que Payload_Ad contiene `tracking_specs` no vacío que referencia ese `meta_pixel_id`.
11. THE Suite_de_Pruebas SHALL incluir casos de error de Caso_Launch con `meta_pixel_id` ausente y con `meta_conversion_event` ausente en el Campaign_Setup (probados como `None` y como string vacío), verificando que se lanza `ParametersNotFoundException`, que el rollback es invocado exactamente una vez y que no se envía ningún Payload_Ad al mock de `requests.post`.
12. THE Suite_de_Pruebas SHALL incluir casos de regresión que verifiquen que `OUTCOME_LEADS` + `LEAD_GENERATION` y `OUTCOME_SALES` + `OFFSITE_CONVERSIONS` generan un Payload_Ad sin `tracking_specs` y un Payload_AdSet cuyo `promoted_object` es igual al generado por el código previo a este cambio para los mismos datos de entrada.
13. THE Suite_de_Pruebas SHALL incluir una prueba de Caso_Objetivos que verifique la presencia del elemento `OFFSITE_CONVERSIONS` dentro de `OUTCOME_LEADS` y que el catálogo, excluido ese elemento, es igual al catálogo retornado antes de este cambio.
14. THE Suite_de_Pruebas SHALL incluir, en Rama_DYNAMIC y en Rama_STANDARD, un caso de Caso_PreCheck con Otras_Combinaciones y un `conversion_event` no permitido en el body, verificando que no se lanza `MetaException` con `META013` ni `META014` y que los datos enviados a `save_or_update` no contienen la clave `meta_conversion_event`.
15. WHEN se ejecuta `pytest` sobre `sinergia/tests/v2/unit/use_cases/` con el intérprete de `sinergia/venv` y sin acceso a red, THE Suite_de_Pruebas SHALL finalizar con 0 pruebas fallidas y 0 errores, incluidas las pruebas preexistentes.
16. THE Suite_de_Pruebas SHALL incluir, para el Requirement 15, un caso de Caso_PreCheck en Rama_STANDARD con un `call_to_action` cuyo `type.value` no pertenece a los CTAs permitidos de la combinación y cuyo `type.valid` de entrada es `True`, verificando que tras la ejecución `call_to_action.type.valid` es `False`, que se registra exactamente un error `cta-error` para el ad y que `call_to_action_types_valid_amount` es `False` en el elemento de `creatives` correspondiente.
17. THE Suite_de_Pruebas SHALL incluir, para el Requirement 15, un caso de Caso_PreCheck en Rama_STANDARD con un `call_to_action` cuyo `type.value` pertenece a los CTAs permitidos de la combinación y cuyo `type` no contiene la clave `valid`, verificando que tras la ejecución `call_to_action.type.valid` es `True` y que `call_to_action_types_valid_amount` es `True` en el elemento de `creatives` correspondiente.
18. THE Suite_de_Pruebas SHALL verificar, en cada caso de los criterios 16 y 17, que `call_to_action.valid` (raíz) es igual a `call_to_action.type.valid`.
19. THE Suite_de_Pruebas SHALL parametrizar los casos de los criterios 16, 17 y 18 sobre al menos las combinaciones (`OUTCOME_LEADS`, `LEAD_GENERATION`), (`OUTCOME_LEADS`, `CONVERSATIONS`), (`OUTCOME_SALES`, `OFFSITE_CONVERSIONS`), (`OUTCOME_AWARENESS`, `REACH`) y Combinación_Leads_Offsite, usando para cada combinación un CTA permitido y un CTA no permitido según `MetaAdsValidator.get_allowed_ctas_for_goal`.
20. THE Suite_de_Pruebas SHALL incluir casos de Caso_PreCheck en Rama_STANDARD con `call_to_action` sin la clave `type` y con `call_to_action.type` de tipo no diccionario (por ejemplo, el string `"LEARN_MORE"`), verificando el resultado del Requirement 15 criterio 3.

### Requirement 15: Corrección de la anotación de validez del CTA en Rama_STANDARD

**User Story:** Como usuario, quiero que el PreCheck STANDARD marque la validez del CTA en el mismo campo que leen la respuesta y el Launch, para que un CTA no permitido no pase la compuerta del Launch y un CTA permitido no la bloquee.

#### Acceptance Criteria

1. WHEN Caso_PreCheck valida en Rama_STANDARD un ad cuyo `call_to_action` es un diccionario y cuyo `call_to_action.type` es un diccionario, para cualquier combinación (objective, optimization_goal) incluida en `_STANDARD_SUPPORTED_COMBINATIONS`, THE Caso_PreCheck SHALL escribir en `call_to_action['type']['valid']` el valor booleano (`True` o `False`) retornado por `MetaAdsValidator.validate_cta_for_goal(call_to_action['type'].get('value'), objective, optimization_goal, throw=False)`, donde objective y optimization_goal son los del PreCheck en curso, sobrescribiendo cualquier valor de `type.valid` recibido en la entrada y dejando `type.value` idéntico al recibido.
2. WHEN Caso_PreCheck escribe `call_to_action['type']['valid']` en Rama_STANDARD según los criterios 1 o 3, THE Caso_PreCheck SHALL escribir en `call_to_action['valid']` (raíz) el mismo valor booleano, para compatibilidad con consumidores existentes.
3. IF Caso_PreCheck valida en Rama_STANDARD un ad cuyo `call_to_action` es un diccionario no vacío y `call_to_action.type` está ausente o no es un diccionario (incluido `None`), THEN THE Caso_PreCheck SHALL reemplazar `call_to_action['type']` por `{'value': <valor original de type, o None si estaba ausente>, 'valid': False}`, escribir `call_to_action['valid'] = False` y continuar con la validación de los ads siguientes de la misma petición sin propagar ninguna excepción (la implementación actual retorna `False` cuando `type` está ausente y lanza `AttributeError` cuando `type` no es un diccionario).
4. IF un ad en Rama_STANDARD tiene `call_to_action` ausente, `None` o vacío (valor falsy), THEN THE Caso_PreCheck SHALL omitir la validación de CTA de ese ad, sin escribir `valid` en ningún nivel y sin registrar ningún error con slug `cta-error`, igual que la implementación actual.
5. IF un ad en Rama_STANDARD tiene `call_to_action` presente, no falsy y que no es un diccionario, THEN THE Caso_PreCheck SHALL registrar exactamente un error por-ad con slug `cta-error` y dejar `call_to_action` sin modificar, igual que la implementación actual.
6. IF `call_to_action['type']['valid']` resulta `False` según los criterios 1 o 3, THEN THE Caso_PreCheck SHALL registrar exactamente un error por-ad con slug `cta-error` en total para ese ad, con un mensaje que incluya el valor de CTA rechazado (`type.value`, o `None` si estaba ausente).
7. WHEN Caso_PreCheck construye el elemento de `creatives` de un ad en Rama_STANDARD, THE Caso_PreCheck SHALL retornar `call_to_action_types_valid_amount` igual al valor de `call_to_action['type']['valid']` escrito según los criterios 1 o 3, o `False` cuando `call_to_action` es ausente, `None` o vacío, con independencia del valor de `type.valid` recibido en la entrada.
8. THE Caso_PreCheck SHALL conservar en `_build_standard_creative_entry` y en los demás constructores de elementos STANDARD de `meta_ads.py` que usan el patrón `call_to_action.get('type', ...)` la lectura de `call_to_action['type']['valid']` sin otros cambios, con la única excepción de una guarda mínima previa a la lectura de `type`: cuando `call_to_action` no es un diccionario se trata como `{}`, de modo que el elemento retorna `call_to_action_types = []` y `call_to_action_types_valid_amount = False` sin lanzar excepción; el resto del código de esos constructores permanece sin modificaciones.
9. THE Caso_Launch SHALL conservar sin modificaciones `_is_campaign_valid`, que sigue leyendo `call_to_action['type']['valid']` para decidir la compuerta del Launch en Rama_STANDARD.
10. THE `FacebookSavePreCheckCTAsUseCase` SHALL conservar sin modificaciones `_validate_ctas_standard`, que sigue escribiendo `link_data.call_to_action = {'type': {'value': <cta>, 'valid': <bool>}}`.
11. WHEN Caso_PreCheck recibe en Rama_STANDARD, para cualquier combinación (objective, optimization_goal) incluida en `_STANDARD_SUPPORTED_COMBINATIONS`, un ad cuyo `link_data.call_to_action` es truthy y no es un diccionario (por ejemplo `'LEARN_MORE'`, `1` o `['SIGN_UP']`), THE Caso_PreCheck SHALL completar `execute()` sin lanzar excepción, registrar exactamente un error por-ad con slug `cta-error` para ese ad (criterio 5) y retornar el elemento de `creatives` correspondiente con `call_to_action_types = []` y `call_to_action_types_valid_amount = False`.

### Requirement 16: Seguimiento de robustez detectado durante la implementación

**User Story:** Como desarrollador, quiero eliminar dos excepciones no controladas detectadas al implementar esta especificación, para que la consulta de creativos publicados y el PreCheck DYNAMIC retornen una respuesta en lugar de fallar ante datos mal formados.

#### Acceptance Criteria

1. WHEN Caso_Consulta_Launch construye en `_build_standard_creative_published` el elemento de un creativo STANDARD cuyo `link_data.call_to_action` es truthy y no es un diccionario (por ejemplo `'LEARN_MORE'`, `1` o `['SIGN_UP']`), THE Caso_Consulta_Launch SHALL tratar `call_to_action` como `{}` y retornar el elemento con `call_to_action_types = []` y `call_to_action_types_valid_amount = False`, sin lanzar excepción.
2. WHEN Caso_Consulta_Launch construye en `_build_standard_creative_published` el elemento de un creativo STANDARD cuyo `link_data.call_to_action` es un diccionario y cuyo `call_to_action.type` es truthy y no es un diccionario (por ejemplo `'LEARN_MORE'`), THE Caso_Consulta_Launch SHALL tratar `call_to_action.type` como `{}` y retornar el elemento con `call_to_action_types = [{}]` y `call_to_action_types_valid_amount = False`, sin lanzar excepción.
3. THE Caso_Consulta_Launch SHALL conservar en `_build_standard_creative_published` las mismas 31 claves, el mismo orden y los mismos valores que produce la implementación previa para todo `call_to_action` ausente, `None`, vacío o diccionario cuyo `type` es ausente, `None` o diccionario, siendo las guardas de los criterios 1 y 2 el único cambio en ese método.
4. WHEN Caso_PreCheck construye en `_build_dynamic_creative_entry` el elemento de `creatives` de un ad de Rama_DYNAMIC, para cualquier combinación (objective, optimization_goal), THE Caso_PreCheck SHALL calcular `proposal_url` como la unión por coma (`,`) de los valores `website_url` de `asset_feed_spec.link_urls` que no son `None`, conservando el valor por defecto `''` para entradas sin la clave `website_url`, de modo que `proposal_url` sea un `str` sin el texto `None` y sea idéntico al valor previo cuando ningún `website_url` es `None`.
5. WHEN Caso_PreCheck procesa en Rama_DYNAMIC un ad de Otras_Combinaciones con una entrada de `asset_feed_spec.link_urls` cuyo `website_url` es `None`, THE Caso_PreCheck SHALL completar `execute()` y retornar Respuesta_PreCheck con status 200, conservando el bloque de URL existente: exactamente un error por-ad con slug `assets-budget-error`, ningún error con slug `url-error` (criterio 7.6 del Requirement 7) y `asset_feed_spec.link_url_valid` sin asignar. Este criterio es una excepción explícita al Requirement 13 criterio 1, que reemplaza el `TypeError` de la implementación previa.
6. WHERE un docstring de `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` indica la cantidad de `STANDARD_SUPPORTED_COMBINATIONS` (`make_standard_link_data_full` y `TestStandardCombinationSuccessScenarios.test_full_success_scenario_yields_ok_1_and_all_seven_success_annotations_true`), THE Suite_de_Pruebas SHALL indicar 5 combinaciones e incluir `LEADS_GOAL_ALLOWED_CTAS[OFFSITE_CONVERSIONS]` entre las listas de CTAs permitidos que contienen `"LEARN_MORE"`, modificando solo el texto de esos docstrings y sin tocar ninguna aserción.
