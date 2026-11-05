# Requirements Document

## Introduction

Este documento define los requisitos para implementar/completar la rama `creative_type == "STANDARD"` dentro de `FacebookGeneratePreCheckCreativeUseCase.execute()`, clase ubicada en `sinergia/app/v2/use_cases/meta_ads.py`. El objetivo es que la rama STANDARD alcance paridad funcional con la rama DYNAMIC ya existente en el mismo método: debe permitir construir un pre-check de campaña STANDARD que el usuario pueda validar antes de que la campaña sea publicada en Meta, reutilizando en la mayor medida posible las funciones de validación ya existentes en `MetaAdsValidator` (`sinergia/app/v2/use_cases/facebook_validator_service.py`), pero operando sobre `object_story_spec`/`link_data` en lugar de sobre `asset_feed_spec`.

**Declaración obligatoria de ubicación dentro del árbol `sinergia/`:** el proyecto `sinergia` es una aplicación Flask independiente ubicada en `sinergia/` dentro del monorepo, con su propio virtualenv en `sinergia/venv` y sus propios specs/steering en `sinergia/.kiro/`. TODOS los artefactos de esta especificación (`requirements.md`, `design.md`, `tasks.md`) y TODA mención de rutas de implementación o de pruebas SHALL declarar explícitamente que residen dentro del árbol `sinergia/`. En particular:

- El código productivo a modificar reside en `sinergia/app/v2/use_cases/meta_ads.py` (clase `FacebookGeneratePreCheckCreativeUseCase` y, únicamente en la porción heredada que su `execute()` invoca, `FacebookTestCreativeUploadUseCase`) y en `sinergia/app/v2/use_cases/facebook_validator_service.py` (clase `MetaAdsPayloadBuilder`, método(s) `build_asset_feed_spec`/`build_creative`, únicamente para la propagación de `ad_channel_id` hacia `object_story_spec`/`link_data` en la rama STANDARD, conforme al Requirement 11).
- Las dataclasses de soporte (`ObjectStorySpec`, `LinkData`, `AssetFeedSpec`) residen en `sinergia/app/v2/use_cases/facebook_validator_service.py`.
- El archivo de pruebas unitarias a actualizar/expandir es `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py`, conforme a la convención de ubicación de pruebas de `use_cases` documentada en `sinergia/.kiro/steering/structure.md` (`tests/v2/unit/use_cases/`, relativo a `sinergia/`).

## Out of Scope

- **Clases `FacebookSavePreCheckImagesUseCase`, `FacebookSavePreCheckTextsUseCase`, `FacebookSavePreCheckCTAsUseCase`, `FacebookSavePreCheckBudgetUseCase`, `FacebookSavePreCheckProposalURLUseCase` y `FacebookSavePreCheckLocationsUseCase`** (todas en `sinergia/app/v2/use_cases/meta_ads.py`): todas contienen hoy una rama `elif ... CreativeType.STANDARD.value: pass` sin implementar. Esta especificación NO las implementa. Quedan reservadas para especificaciones futuras que dependerán del resultado de esta spec (en particular, de las decisiones de diseño sobre cómo se anota `object_story_spec` y cómo se propaga `ad_channel_id`, documentadas aquí como Requirement 10 y Requirement 11).
- **`FacebookPublishCampaignUseCase`** y, en general, todo el flujo de publicación real hacia Meta (`sinergia/app/v2/use_cases/meta_ads.py`): esta especificación trata exclusivamente el pre-check/validación (`FacebookGeneratePreCheckCreativeUseCase.execute()`), no la publicación.
- **`FacebookTestCreativeUploadUseCase.execute()`** (el `execute()` propio de la clase padre, no invocado por `FacebookGeneratePreCheckCreativeUseCase`): fuera de alcance. Solo están en alcance los métodos heredados que `FacebookGeneratePreCheckCreativeUseCase.execute()` sí invoca (`_get_decoded_access_token`, `_build_meta_payload`, `_get_account_details` cuando aplique).
- **`MetaAdsPayloadBuilder`** (`sinergia/app/v2/use_cases/facebook_validator_service.py`): DENTRO de alcance únicamente para la propagación de `ad_channel_id` hacia `object_story_spec`/`link_data` en la rama `creative_type == STANDARD`, conforme al Requirement 11. El resto de `MetaAdsPayloadBuilder` —incluidas, entre otras, la construcción de `campaign`/`adsets`/`targeting`, la lógica de integración con Strapi, y cualquier otro campo o rama de `build_asset_feed_spec`/`build_creative` no relacionado con `ad_channel_id` en STANDARD— permanece fuera de alcance.
- Toda combinación de `objective`/`optimization_goal` distinta de las 4 combinaciones listadas en Requirement 2: su comportamiento se limita a lo definido en Requirement 13 (lanzamiento de `MetaException` con `code="META011"`); no se implementa ninguna validación de negocio adicional para ellas.

## Glossary

- **Caso_de_Uso**: `FacebookGeneratePreCheckCreativeUseCase`, definida en `sinergia/app/v2/use_cases/meta_ads.py`.
- **Caso_de_Uso_Padre**: `FacebookTestCreativeUploadUseCase`, superclase de la que el Caso_de_Uso hereda `_get_decoded_access_token` y `_build_meta_payload`.
- **Rama_DYNAMIC**: bloque `if self.creative_type == "DYNAMIC" and asset_feed:` dentro de `execute()`, ya implementado y fuera de alcance de modificación funcional en esta especificación (salvo por la extracción compartida descrita en Requirement 12, que no debe alterar su comportamiento actual).
- **Rama_STANDARD**: bloque `elif self.creative_type == "STANDARD" and story_spec:` dentro de `execute()`, objeto de esta especificación.
- **Object_Story_Spec**: diccionario `ad_creative.get('object_story_spec')` recibido por cada ad dentro de `execute()`; en producción corresponde a una instancia serializada de la dataclass `ObjectStorySpec` (`facebook_validator_service.py`).
- **Link_Data**: diccionario `object_story_spec.get('link_data')`; en producción corresponde a una instancia serializada de la dataclass `LinkData`.
- **Combinación_Objetivo_Optimización**: par ordenado `(objective, optimization_goal)` del Caso_de_Uso.
- **Combinación_Soportada**: cualquiera de las siguientes 4 Combinaciones_Objetivo_Optimización, únicas activadas para la Rama_STANDARD en esta especificación:
  1. `objective=OUTCOME_AWARENESS`, `optimization_goal=REACH`
  2. `objective=OUTCOME_LEADS`, `optimization_goal=LEAD_GENERATION`
  3. `objective=OUTCOME_LEADS`, `optimization_goal=CONVERSATIONS`
  4. `objective=OUTCOME_SALES`, `optimization_goal=OFFSITE_CONVERSIONS`
- **Título_STANDARD**: valor mapeado desde `Link_Data.name`.
- **Cuerpo_STANDARD**: valor mapeado desde `Link_Data.message`.
- **Descripción_STANDARD**: valor mapeado desde `Link_Data.description`.
- **Imagen_STANDARD**: valor mapeado desde `Link_Data.image_url`.
- **URL_STANDARD**: valor mapeado desde `Link_Data.link`.
- **CTA_STANDARD**: valor mapeado desde `Link_Data.call_to_action` (diccionario único, no lista).
- **Valor_Candidato**: para efectos de la validación de cantidad exacta (Requirements 3, 4, 5, 6), el contenido de Título_STANDARD/Cuerpo_STANDARD/Descripción_STANDARD/Imagen_STANDARD SHALL tratarse como una colección: si el valor es una lista, su longitud es la cantidad de candidatos; si el valor es un escalar (cadena, dict, o similar), se trata como una colección de longitud 1 cuando es verdadero (truthy) y de longitud 0 cuando es falsy o está ausente. Esta definición permite validar tanto el modelo de datos actual (campos escalares en `LinkData`) como un eventual origen de datos que aún no haya colapsado a un único valor.
- **Validador_Meta**: `MetaAdsValidator` (`facebook_validator_service.py`).
- **Ad_Set**, **Ad**, **Ad_Creative**: estructuras de diccionario ya usadas por la Rama_DYNAMIC, sin cambios de forma.
- **Resultado_de_Ad**: entrada `{"ad_name": ..., "status": "Created"|"Failed", "errors": [...]}` agregada a la lista interna `results` dentro de `execute()` (no forma parte de la Respuesta_Final).
- **Respuesta_Final**: tupla `(dict, 200)` retornada por `execute()`.
- **Creative_a_Publicar**: cada entrada de la lista `creatives` dentro de `data` en la Respuesta_Final.
- **Repositorio_de_Canal**: `AdChannelRepository`, usado por `_save_creative_to_publish`.
- **Suite_de_Pruebas**: conjunto de pruebas unitarias en `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py`.

## Requirements

### Requirement 1: Ubicación de artefactos dentro del árbol `sinergia/`

**User Story:** Como mantenedor del monorepo, quiero que toda la especificación y su implementación estén claramente delimitadas al árbol `sinergia/`, para evitar ambigüedad sobre qué proyecto se está modificando dentro del monorepo `docker-deploy`.

#### Acceptance Criteria

1. THE especificación (`requirements.md`, `design.md`, `tasks.md`) SHALL incluir, en la sección inicial de cada documento (Introducción o encabezado equivalente), una declaración textual explícita que indique que el documento reside en `sinergia/.kiro/specs/meta-ads-standard-precheck-validation/` y que describe cambios exclusivamente dentro del árbol `sinergia/`.
2. THE implementación resultante de esta especificación SHALL modificar únicamente archivos dentro de `sinergia/app/` y, para pruebas, dentro de `sinergia/tests/`.
3. THE archivo principal de pruebas unitarias de esta especificación SHALL ser exactamente `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py`, y dicho archivo SHALL contener la totalidad de los casos de prueba que caracterizan el comportamiento de la Rama_STANDARD exigido por esta especificación.
4. IF la implementación requiere archivos de prueba adicionales de soporte (por ejemplo, fixtures o utilidades compartidas), THEN dichos archivos SHALL residir dentro de `sinergia/tests/` y no SHALL contener ningún caso de prueba de comportamiento exigido por esta especificación, los cuales SHALL permanecer en el archivo indicado en el criterio 3.
5. WHEN una tarea de implementación en el documento de tareas (`tasks.md`) mencione una ruta de archivo, THE documento de tareas SHALL expresar dicha ruta como relativa a `sinergia/` o como ruta absoluta que incluya expresamente el segmento `sinergia/`, sin rutas ambiguas relativas a la raíz del monorepo `docker-deploy`.

### Requirement 2: Combinaciones Objetivo/Optimización soportadas para STANDARD

**User Story:** Como responsable de campañas, quiero que el pre-check STANDARD solo active sus validaciones de negocio para las combinaciones de objetivo/optimización efectivamente soportadas, para evitar validar o publicar campañas STANDARD en configuraciones no contempladas.

#### Acceptance Criteria

1. WHILE `self.creative_type` es `"STANDARD"`, IF la Combinación_Objetivo_Optimización del Caso_de_Uso (definida por los valores vigentes de `self.objective` y `self.optimization_goal`, fijos para toda la ejecución de `execute()`) es igual a alguna de las 4 Combinaciones_Soportadas, THEN THE Caso_de_Uso SHALL ejecutar, para cada `ad` procesado dentro del ciclo `for ad_set in ad_sets: for ad in ads:` de `execute()`, las validaciones de Título_STANDARD, Cuerpo_STANDARD, Descripción_STANDARD, Imagen_STANDARD, URL_STANDARD, presupuesto mínimo diario y CTA_STANDARD descritas en los Requirements 3 a 9.
2. WHILE `self.creative_type` es `"STANDARD"`, IF la Combinación_Objetivo_Optimización del Caso_de_Uso no es ninguna de las 4 Combinaciones_Soportadas —incluyendo los casos en que `self.objective` y/o `self.optimization_goal` sean `None`, estén ausentes o no correspondan a ningún valor reconocido por el Caso_de_Uso—, THEN THE Caso_de_Uso SHALL aplicar exclusivamente el comportamiento definido en Requirement 13 (lanzamiento de `MetaException` con `code="META011"`), sin ejecutar ninguna de las validaciones de los Requirements 3 a 9 ni iterar sobre `ad_sets`/`ads`.
3. THE Caso_de_Uso SHALL mantener sin cambios de comportamiento la Rama_DYNAMIC para cualquier Combinación_Objetivo_Optimización, incluidas las 4 Combinaciones_Soportadas de STANDARD.

### Requirement 3: Validación de Título_STANDARD

**User Story:** Como responsable de campañas, quiero que el título de un creativo STANDARD se valide en cantidad y longitud, para asegurar que Meta acepte el creativo antes de publicarlo.

#### Acceptance Criteria

1. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, WHEN el Valor_Candidato de Título_STANDARD tiene longitud exactamente igual a 1, THE Caso_de_Uso SHALL validar la longitud de ese único título usando una lógica equivalente a `MetaAdsValidator.is_valid_length('titles', [...])`, aplicada sobre una lista de un elemento construida a partir de Título_STANDARD.
2. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, IF el Valor_Candidato de Título_STANDARD tiene longitud igual a 0 (título ausente o falsy), THEN THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`, sin lanzar una excepción no controlada.
3. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, IF el Valor_Candidato de Título_STANDARD tiene longitud mayor a 1, THEN THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`, sin lanzar una excepción no controlada.
4. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, IF el título único validado en el criterio 1 excede 255 caracteres, THEN THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`, sin lanzar una excepción no controlada.
5. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, WHEN el título único validado en el criterio 1 tiene una longitud entre 1 y 255 caracteres inclusive, THE Caso_de_Uso SHALL anotar el resultado exitoso de esta validación sobre el Object_Story_Spec del ad, conforme a Requirement 10, sin agregar ningún error de validación para esta validación de título.

### Requirement 4: Validación de Cuerpo_STANDARD

**User Story:** Como responsable de campañas, quiero que el cuerpo (mensaje principal) de un creativo STANDARD se valide en cantidad y longitud, para asegurar que Meta acepte el creativo antes de publicarlo.

#### Acceptance Criteria

1. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, WHEN el Valor_Candidato de Cuerpo_STANDARD tiene longitud exactamente igual a 1, THE Caso_de_Uso SHALL validar la longitud de ese único cuerpo usando una lógica equivalente a `MetaAdsValidator.is_valid_length('bodies', [...])`, aplicada sobre una lista de un elemento construida a partir de Cuerpo_STANDARD.
2. IF el Valor_Candidato de Cuerpo_STANDARD tiene longitud igual a 0, THEN THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`, sin lanzar una excepción no controlada.
3. IF el Valor_Candidato de Cuerpo_STANDARD tiene longitud mayor a 1, THEN THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`, sin lanzar una excepción no controlada.
4. IF el cuerpo único validado en el criterio 1 excede 1024 caracteres, THEN THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`, sin lanzar una excepción no controlada.
5. WHEN el cuerpo único validado en el criterio 1 tiene una longitud entre 1 y 1024 caracteres inclusive, THE Caso_de_Uso SHALL anotar el resultado exitoso de esta validación sobre el Object_Story_Spec del ad, conforme a Requirement 10.

### Requirement 5: Validación de Descripción_STANDARD

**User Story:** Como responsable de campañas, quiero que la descripción de un creativo STANDARD se valide en cantidad y longitud, para asegurar que Meta acepte el creativo antes de publicarlo.

#### Acceptance Criteria

1. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, WHEN el Valor_Candidato de Descripción_STANDARD tiene longitud exactamente igual a 1, THE Caso_de_Uso SHALL validar la longitud de esa única descripción usando una lógica equivalente a `MetaAdsValidator.is_valid_length('descriptions', [...])`, aplicada sobre una lista de un elemento construida a partir de Descripción_STANDARD.
2. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, IF el Valor_Candidato de Descripción_STANDARD tiene longitud igual a 0, THEN THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`, sin lanzar una excepción no controlada y sin anotar ningún resultado exitoso de esta validación.
3. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, IF el Valor_Candidato de Descripción_STANDARD tiene longitud mayor a 1, THEN THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`, sin lanzar una excepción no controlada y sin anotar ningún resultado exitoso de esta validación.
4. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, IF la descripción única validada en el criterio 1 excede 255 caracteres, THEN THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`, sin lanzar una excepción no controlada y sin anotar ningún resultado exitoso de esta validación.
5. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, WHEN la descripción única validada en el criterio 1 tiene una longitud entre 1 y 255 caracteres inclusive, THE Caso_de_Uso SHALL anotar el resultado exitoso de esta validación sobre el Object_Story_Spec del ad, conforme a Requirement 10, sin agregar ningún error de validación para ese ad a `current_ad_errors`.

### Requirement 6: Validación de Imagen_STANDARD

**User Story:** Como responsable de campañas, quiero que la imagen de un creativo STANDARD se valide en cantidad e integridad (dimensiones, peso, formato), reutilizando la misma lógica de validación de imágenes ya usada en DYNAMIC, para evitar rechazos de Meta por imágenes inválidas.

#### Acceptance Criteria

1. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, WHEN el Valor_Candidato de Imagen_STANDARD tiene longitud exactamente igual a 1, THE Caso_de_Uso SHALL construir una lista de un único elemento, un diccionario con la clave `url` igual a Imagen_STANDARD, y SHALL invocar `MetaAdsValidator.validate_images_precheck` sobre esa lista, sin lanzar una excepción no controlada ante una imagen inválida (dado que `validate_images_precheck` anota `valid`/`error` por imagen en lugar de lanzar).
2. IF el Valor_Candidato de Imagen_STANDARD tiene longitud igual a 0 (imagen ausente o falsy), THEN THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`, sin invocar `validate_images_precheck` y sin lanzar una excepción no controlada.
3. IF el Valor_Candidato de Imagen_STANDARD tiene longitud mayor a 1, THEN THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`, sin lanzar una excepción no controlada.
4. WHEN `validate_images_precheck` anota, tras la invocación del criterio 1, la imagen única como inválida (`valid=False`), THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`, cuyo mensaje SHALL incluir el valor anotado en el campo `error` de esa imagen por `validate_images_precheck`.
5. WHEN `validate_images_precheck` anota la imagen única como válida (`valid=True`), THE Caso_de_Uso SHALL anotar el resultado exitoso de esta validación sobre el Object_Story_Spec del ad, conforme a Requirement 10, sin agregar ningún error para esta validación.
6. THE Caso_de_Uso SHALL evitar, para la validación de Imagen_STANDARD, cualquier solicitud HTTP real fuera de la ya realizada internamente por `MetaAdsValidator.validate_images_precheck`.
7. THE Caso_de_Uso SHALL NOT introducir, para la validación de Imagen_STANDARD, ninguna ruta de descarga o validación de imagen adicional distinta de `MetaAdsValidator.validate_images_precheck`.

### Requirement 7: Validación de URL_STANDARD

**User Story:** Como responsable de campañas, quiero que la URL de destino de un creativo STANDARD se valide con la misma lógica que usa DYNAMIC, para asegurar consistencia en el formato de URL exigido por Meta.

#### Acceptance Criteria

1. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, WHEN URL_STANDARD es truthy (no es `None` ni cadena vacía), THE Caso_de_Uso SHALL invocar `MetaAdsValidator.is_valid_link_url` con URL_STANDARD como argumento (no con `MetaAdsValidator.is_valid_proposal_url`), sin invocar `is_valid_link_url` cuando URL_STANDARD esté ausente o sea falsy.
2. WHEN `is_valid_link_url` retorna `True` para URL_STANDARD, THE Caso_de_Uso SHALL anotar el resultado exitoso de esta validación sobre el Object_Story_Spec del ad, conforme a Requirement 10.
3. IF URL_STANDARD está ausente o es falsy (por ejemplo, `None` o cadena vacía), THEN THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors` sin invocar `MetaAdsValidator.is_valid_link_url` sobre ese valor, evitando así la excepción `AttributeError` que produce `is_valid_link_url(None)`, y sin lanzar ninguna otra excepción no controlada.
4. IF URL_STANDARD es truthy y `MetaAdsValidator.is_valid_link_url` retorna `False` para ese valor, THEN THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`, sin lanzar una excepción no controlada.

### Requirement 8: Validación de presupuesto mínimo diario para STANDARD

**User Story:** Como responsable de campañas, quiero que el presupuesto diario mínimo se valide para un ad set STANDARD con la misma lógica que ya aplica DYNAMIC, para evitar publicar campañas por debajo del mínimo exigido por Meta.

#### Acceptance Criteria

1. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, WHEN `ad_set.get('daily_budget', 0)` es de tipo numérico (`int` o `float`), THE Caso_de_Uso SHALL anotar sobre el Object_Story_Spec del ad un campo equivalente a `min_daily_budget` con el valor de `min_budget` (el mismo valor ya calculado por `_get_minimum_budget` y reutilizado por la Rama_DYNAMIC), y un campo equivalente a `daily_budget_valid` con el resultado booleano de la comparación `ad_set.get('daily_budget', 0) >= min_budget`.
2. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, IF `ad_set.get('daily_budget', 0)` no es de tipo numérico (`int` o `float`) (por ejemplo, es `None`, `str`, `list` o `dict`), THEN THE Caso_de_Uso SHALL anotar igualmente sobre el Object_Story_Spec del ad el campo equivalente a `min_daily_budget` con el valor de `min_budget`, omitir el campo equivalente a `daily_budget_valid`, y agregar un error de validación para ese ad a `current_ad_errors`, sin lanzar una excepción no controlada fuera de `execute()`, replicando el mismo patrón de captura ya usado por la Rama_DYNAMIC para este mismo escenario.
3. THE Caso_de_Uso SHALL reutilizar exactamente `_get_minimum_budget` para calcular `min_budget` en la Rama_STANDARD, sin duplicar su lógica.

### Requirement 9: Validación de CTA_STANDARD

**User Story:** Como responsable de campañas, quiero que el llamado a la acción (CTA) de un creativo STANDARD se valide contra el objetivo y el objetivo de optimización de la campaña, igual que en DYNAMIC, para evitar configuraciones de CTA rechazadas por Meta.

#### Acceptance Criteria

1. WHILE la Combinación_Objetivo_Optimización es una Combinación_Soportada, WHEN CTA_STANDARD es un diccionario (`isinstance(call_to_action, dict)`) y es verdadero (truthy), THE Caso_de_Uso SHALL invocar `MetaAdsValidator.validate_cta_for_goal(cta_text, self.objective, self.optimization_goal, throw=False)`, donde `cta_text` es el valor obtenido de `call_to_action.get('type')` (pudiendo ser `None` si esa clave está ausente, en cuyo caso `validate_cta_for_goal` SHALL determinar el resultado de validez sin lanzar excepción), reemplazando el uso previo de `MetaAdsValidator.validate_cta`, sin lanzar una excepción no controlada fuera de `execute()`.
2. WHEN `validate_cta_for_goal` retorna un valor booleano para CTA_STANDARD (ya sea `True` o `False`), THE Caso_de_Uso SHALL anotar ese valor booleano sobre el propio diccionario de CTA_STANDARD (por ejemplo, `link_data['call_to_action']['valid']`), de forma análoga a como la Rama_DYNAMIC anota `cta['valid']` sobre cada entrada de `call_to_action_types`.
3. IF CTA_STANDARD está ausente o es falsy, THEN THE Caso_de_Uso SHALL omitir la validación de CTA para ese ad sin agregar ningún error por ese motivo, replicando el comportamiento actual de la Rama_STANDARD para `link_data` sin `call_to_action` y el comportamiento de la Rama_DYNAMIC ante una lista vacía de `call_to_action_types`.
4. IF CTA_STANDARD es verdadero (truthy) pero no es un diccionario, THEN THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`, sin invocar `validate_cta_for_goal` y sin lanzar una excepción no controlada.
5. WHEN `validate_cta_for_goal` anota CTA_STANDARD como inválido (`valid=False`), THE Caso_de_Uso SHALL agregar un error de validación para ese ad a `current_ad_errors`.

### Requirement 10: Anotación de resultados de validación sobre Object_Story_Spec

**User Story:** Como consumidor de la Respuesta_Final, quiero que los resultados de cada validación STANDARD queden anotados sobre la misma estructura que se envía a publicar, igual que ocurre hoy con `asset_feed_spec` en DYNAMIC, para poder mostrarle al usuario el detalle de qué es válido y qué no antes de publicar.

#### Acceptance Criteria

1. WHEN el Caso_de_Uso ejecuta cualquiera de las validaciones de los Requirements 3 a 9 para un ad STANDARD (haya resultado exitoso o fallido), THE Caso_de_Uso SHALL mutar in-place el mismo diccionario Object_Story_Spec recibido para ese ad (no una copia, incluyendo su Link_Data anidado cuando el campo de resultado corresponda a un valor mapeado desde Link_Data), agregando el campo de resultado correspondiente a esa validación específica, replicando el patrón de mutación in-place ya usado por la Rama_DYNAMIC sobre `asset_feed_spec`.
2. WHEN el Caso_de_Uso evalúa, para un ad STANDARD cuya Combinación_Objetivo_Optimización es una Combinación_Soportada, alguna de las validaciones de título, cuerpo, descripción, imagen, URL o presupuesto mínimo (Requirements 3 a 8), THE Caso_de_Uso SHALL anotar sobre el Object_Story_Spec de ese ad (incluyendo su Link_Data anidado cuando el campo se mapea desde Link_Data) un campo booleano por cada una de esas validaciones —cantidad/longitud de título, cantidad/longitud de cuerpo, cantidad/longitud de descripción, validez de imagen, `daily_budget_valid` y `link_url_valid`— indicando si esa validación específica resultó exitosa o fallida, independientemente del resultado obtenido (es decir, el campo SHALL anotarse tanto si la validación fue exitosa como si falló).
3. WHEN CTA_STANDARD está presente para un ad STANDARD cuya Combinación_Objetivo_Optimización es una Combinación_Soportada, THE Caso_de_Uso SHALL anotar sobre el propio `call_to_action` dentro del Link_Data del Object_Story_Spec un campo booleano que indique si la validación de CTA_STANDARD (Requirement 9) resultó exitosa o fallida, conforme a Requirement 9.2, independientemente del resultado obtenido.
4. THE nombres exactos de los campos de anotación agregados al Object_Story_Spec (por ejemplo si se reutilizan literalmente `unique_titles`/`titles_valid_amount` o se introducen nombres equivalentes adaptados a "cantidad exacta 1") SHALL definirse en la fase de diseño. Independientemente del naming elegido, THE conjunto de campos SHALL permitir a un consumidor de la Respuesta_Final distinguir, para cada una de las validaciones de los Requirements 3 a 9, entre exactamente tres estados observables: (a) no evaluada —cuando la Combinación_Objetivo_Optimización no es una Combinación_Soportada conforme a Requirement 13, o cuando CTA_STANDARD está ausente conforme a Requirement 9.3—, en cuyo caso el campo correspondiente SHALL estar ausente del Object_Story_Spec; (b) evaluada y exitosa, en cuyo caso el campo correspondiente SHALL estar presente con valor `True` (o equivalente); y (c) evaluada y fallida, en cuyo caso el campo correspondiente SHALL estar presente con valor `False` (o equivalente); de forma análoga a como lo permite hoy `asset_feed_spec` para DYNAMIC.

### Requirement 11: Propagación de `ad_channel_id` para STANDARD

**User Story:** Como mantenedor, quiero que `MetaAdsPayloadBuilder` propague `ad_channel_id` hacia el `object_story_spec`/`link_data` de un creativo STANDARD igual que ya lo hace hoy hacia `asset_feed_spec` en DYNAMIC, para que un creativo STANDARD quede vinculado a su canal de anuncio y para que `_save_creative_to_publish` y la construcción de `creatives[].adchannel_id` funcionen de forma equivalente entre ambos tipos de creativo.

#### Acceptance Criteria

1. WHEN `MetaAdsPayloadBuilder.build_asset_feed_spec` (`sinergia/app/v2/use_cases/facebook_validator_service.py`) calcula un `AssetFeedSpec` con `ad_channel_id` asignado para un `ad` dado, y `MetaAdsPayloadBuilder.build_creative` construye el `AdCreative` de ese mismo `ad` con `self.creative_type == CreativeType.STANDARD.value`, THE `object_story_spec`/`link_data` resultante de ese `AdCreative` SHALL contener un campo `ad_channel_id` con el mismo valor que `asset_feed_spec.ad_channel_id`, de forma análoga a como hoy `build_creative` asigna ese valor sobre `asset_feed_spec` cuando `self.creative_type == CreativeType.DYNAMIC.value`.
2. IF `MetaAdsPayloadBuilder.build_asset_feed_spec` retorna `None` (por ejemplo, por ausencia de `ad_channels_data` o de un canal seleccionado, conforme a la lógica ya existente de ese método) para un `ad` con `self.creative_type == CreativeType.STANDARD.value`, THEN THE `object_story_spec`/`link_data` resultante de ese `ad` SHALL omitir el campo `ad_channel_id` (o conservar su valor por defecto), sin lanzar una excepción no controlada, de forma análoga a como la Rama_DYNAMIC maneja hoy ese mismo caso sobre `asset_feed_spec`.
3. THE Caso_de_Uso (`FacebookGeneratePreCheckCreativeUseCase.execute()`) SHALL leer, para un ad STANDARD, el campo `ad_channel_id` propagado conforme al criterio 1 desde el Object_Story_Spec recibido, sin necesidad de calcular o resolver el canal de anuncio por sí mismo.
4. WHEN `_save_creative_to_publish` procesa un ad set STANDARD, THE Caso_de_Uso SHALL extraer `ad_channel_id` desde el Object_Story_Spec del primer ad del ad set que contenga `object_story_spec` con `link_data` (la misma definición de ad set STANDARD usada en el Requirement 12.2), usando `0` como valor por defecto cuando dicho campo esté ausente en ese Object_Story_Spec, de forma análoga a como hoy lo extrae desde `asset_feed_spec` con `.get('ad_channel_id', 0)` para DYNAMIC.
5. WHEN se construye un Creative_a_Publicar para un ad set STANDARD identificado según la misma definición del Requirement 12.2 (primer ad con `object_story_spec`/`link_data`), THE campo `adchannel_id` de ese Creative_a_Publicar SHALL provenir del mismo `ad_channel_id` anotado en el Object_Story_Spec de ese ad, o de `0` cuando dicho `ad_channel_id` esté ausente, de forma análoga a la Rama_DYNAMIC.

### Requirement 12: Construcción de `creatives[]` para ads STANDARD en la Respuesta_Final

**User Story:** Como consumidor de la Respuesta_Final, quiero que un ad STANDARD produzca una entrada de `creatives[]` con el mismo contrato de campos que ya produce un ad DYNAMIC, para no tener que distinguir el tipo de creativo en el consumidor.

#### Acceptance Criteria

1. WHEN se construye un Creative_a_Publicar para un ad set cuya rama aplicable es la Rama_DYNAMIC (es decir, `self.creative_type == CreativeType.DYNAMIC.value`, determinación a nivel de ejecución ya usada por el resto de `execute()` y por tanto aplicable a todos los ad sets de esa misma ejecución), THE Caso_de_Uso SHALL mantener exactamente el comportamiento actual de extracción de campos desde `ad_creative.get('asset_feed_spec', {})` del primer ad (`ads[0]`) de ese ad set, sin ninguna modificación de comportamiento observable respecto al código existente.
2. WHEN se construye un Creative_a_Publicar para un ad set cuya rama aplicable es la Rama_STANDARD (es decir, `self.creative_type == CreativeType.STANDARD.value`), THE Caso_de_Uso SHALL construir dicho Creative_a_Publicar con exactamente el mismo conjunto fijo de claves que produce hoy la Rama_DYNAMIC (`adchannel_id`, `images`, `bodies`, `titles`, `descriptions`, `call_to_action_types`, `images_valid_amount`, `titles_valid_amount`, `bodies_valid_amount`, `descriptions_valid_amount`, `call_to_action_types_valid_amount`, `images_max_amount`, `titles_max_amount`, `bodies_max_amount`, `descriptions_max_amount`, `call_to_action_types_max_amount`, `unique_titles`, `unique_bodies`, `unique_descriptions`, `daily_budget_valid`, `min_daily_budget`, `proposal_url`, `proposal_url_valid`, `locations`, `locations_valid`, `promoted_object_valid`), extrayendo desde `ad_creative.get('object_story_spec', {})` del primer ad (`ads[0]`) de ese ad set los campos `images`, `bodies`, `titles`, `descriptions`, `call_to_action_types`, los indicadores de cantidad válida equivalentes a `*_valid_amount`, los indicadores equivalentes a `unique_*`, `daily_budget_valid`, `min_daily_budget`, `proposal_url`, `proposal_url_valid`, `locations`, `locations_valid` y `adchannel_id`, conforme a las anotaciones de los Requirements 10 y 11. Para los campos restantes del conjunto fijo que no tienen equivalente anotado en Object_Story_Spec (`images_max_amount`, `titles_max_amount`, `bodies_max_amount`, `descriptions_max_amount`, `call_to_action_types_max_amount`, `promoted_object_valid`), THE Caso_de_Uso SHALL asignar el valor por defecto definido en el criterio 3, sin intentar extraerlos de `object_story_spec`.
3. IF, al construir un Creative_a_Publicar para un ad STANDARD, el propio Object_Story_Spec del primer ad está ausente (`None`), o alguna clave esperada del conjunto fijo del criterio 2 (por ejemplo `link_data`, cualquiera de los campos de anotación del Requirement 10, o cualquiera de los campos sin equivalente listados en el criterio 2) está ausente de él, THEN THE Caso_de_Uso SHALL aplicar, para ese campo, el valor por defecto seguro equivalente a los ya usados por la Rama_DYNAMIC (`False` para indicadores booleanos, `0` para montos/identificadores numéricos, `[]`/`""` para colecciones/cadenas), sin lanzar una excepción no controlada, tratando un Object_Story_Spec ausente como un diccionario vacío para efectos de esta extracción.
4. THE campos `images`, `bodies`, `titles`, `descriptions` de un Creative_a_Publicar construido a partir de un ad STANDARD SHALL representarse como listas de a lo sumo un elemento (envolviendo Imagen_STANDARD/Cuerpo_STANDARD/Título_STANDARD/Descripción_STANDARD en una lista de longitud 1 cuando están presentes, o listas vacías cuando están ausentes); en particular, cada elemento de `images` SHALL tener la misma forma de diccionario (`url`, `valid`, `error`) que ya produce la Rama_DYNAMIC para cada entrada de `asset_feed_spec.images`, poblado a partir de Imagen_STANDARD y de su resultado de validación anotado conforme al Requirement 6, para mantener un contrato de respuesta uniforme entre DYNAMIC y STANDARD frente al consumidor existente (frontend). **Nota:** esta decisión se adopta como recomendación de esta especificación por consistencia de contrato; SHALL confirmarse explícitamente en `design.md`, dado que las clases `FacebookSavePreCheck*UseCase` (fuera de alcance de esta spec, ver sección "Out of Scope") podrían imponer una forma distinta una vez se implementen en especificaciones futuras.

### Requirement 13: Manejo de combinación objetivo/optimización no soportada

**User Story:** Como responsable de calidad, quiero que una combinación de objetivo/optimización STANDARD no soportada detenga el pre-check con un error de aplicación explícito, para que el usuario reciba una señal clara de que esa configuración no está soportada, en lugar de un pre-check parcial o silenciosamente incompleto.

#### Acceptance Criteria

1. WHILE `self.creative_type` es `"STANDARD"`, IF la Combinación_Objetivo_Optimización del Caso_de_Uso (evaluada una única vez por ejecución de `execute()`, antes de iterar sobre `ad_sets`/`ads`, de forma análoga a como ya se evalúan hoy las validaciones de `self.objective`/`self.optimization_goal` que lanzan `MetaException` con códigos `META001`-`META010`) no corresponde a ninguna de las 4 Combinaciones_Soportadas listadas en Requirement 2, THEN THE Caso_de_Uso SHALL lanzar `MetaException` con `code="META011"`, sin ejecutar ninguna de las validaciones de los Requirements 3 a 9 ni continuar con el resto de `execute()`.
2. WHEN THE Caso_de_Uso lanza `MetaException("META011", ...)` conforme al criterio 1, THE excepción SHALL propagarse fuera de `execute()` sin ser capturada internamente, de la misma forma en que ya se propagan las demás instancias de `MetaException` lanzadas por `execute()` (`META001`, `META002`, `META006`-`META010`).
3. THE Caso_de_Uso SHALL preservar sin cambios el comportamiento de la Rama_DYNAMIC para cualquier Combinación_Objetivo_Optimización, incluidas aquellas que no sean Combinaciones_Soportadas para STANDARD: el criterio 1 SHALL aplicar únicamente cuando `self.creative_type` es `"STANDARD"`.
4. THE mensaje de `MetaException("META011", ...)` SHALL identificar la combinación de `self.objective`/`self.optimization_goal` evaluada, de forma análoga al detalle ya incluido en los mensajes de `META002`, `META007`, `META008` y `META009`.

### Requirement 14: No regresión de la Rama_DYNAMIC y del resto de la aplicación

**User Story:** Como mantenedor, quiero que la implementación de la Rama_STANDARD no introduzca cambios de comportamiento en la Rama_DYNAMIC ni en el resto de `FacebookGeneratePreCheckCreativeUseCase`, para no arriesgar funcionalidad ya en producción.

#### Acceptance Criteria

1. THE implementación de esta especificación SHALL preservar sin cambios de comportamiento observable la Rama_DYNAMIC de `execute()`, incluidas sus particularidades ya caracterizadas por la Suite_de_Pruebas existente (por ejemplo, la reutilización de un mismo slug de error para dos validaciones distintas, o el `TypeError` al final de `execute()` cuando `objective` no está en `META_ODAX_CTA_MAPPING`). A efectos de este Requirement, "cambio de comportamiento observable" SHALL significar cualquiera de los siguientes, comparado contra el comportamiento de la Rama_DYNAMIC antes de esta especificación: (a) un valor de retorno distinto de `execute()` para la misma entrada; (b) el lanzamiento de una excepción de tipo distinto, o de un mensaje/slug de error distinto, donde antes no se lanzaba o se lanzaba otra; (c) una llamada distinta (en tipo, cantidad, orden o argumentos) a un colaborador o dependencia externa (incluidos, entre otros, `_save_campaign_channel_publish`, `_save_creative_to_publish`, `_get_minimum_budget`, o cualquier método de `MetaAdsValidator`) para la misma entrada.
2. THE implementación de esta especificación SHALL preservar sin cambios de comportamiento observable, según la definición del criterio 1, el bloque de agregación de resultados (`has_errors`/`ok`), el bloque de creación simulada (dry-run) y los efectos secundarios de persistencia (`_save_campaign_channel_publish`, `_save_creative_to_publish`) para los ads que no sean STANDARD. THE extensión de este bloque para soportar STANDARD SHALL ser estrictamente aditiva: SHALL limitarse a agregar nuevas ramas condicionales, nuevos parámetros con valores por defecto que preserven el comportamiento previo, o nuevas llamadas exclusivas para ads STANDARD, y NO SHALL modificar la lógica, el orden de ejecución, ni las firmas de las llamadas existentes que aplican a ads que no sean STANDARD, en la forma descrita en los Requirements 10, 11 y 12.
3. WHEN se ejecuta la Suite_de_Pruebas completa de `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` tras la implementación, THE conjunto de pruebas que ya caracterizaban la Rama_DYNAMIC y el resto de `execute()` antes de esta especificación SHALL continuar pasando sin modificación de sus aserciones, salvo los ajustes estrictamente necesarios para acomodar la extracción compartida de `creatives[]` descrita en Requirement 12.1 (que SHALL mantener el mismo resultado observable para DYNAMIC).
4. IF una función o método es utilizado tanto por la Rama_DYNAMIC como por la Rama_STANDARD (incluidos, entre otros, `_get_minimum_budget` y los métodos de `MetaAdsValidator`), THEN THE implementación de esta especificación SHALL modificarlos únicamente de forma que, para toda entrada previamente válida en la Rama_DYNAMIC, el valor de retorno y las excepciones lanzadas por dicha función o método permanezcan idénticos a los previos a esta especificación.
5. THE implementación de esta especificación SHALL acotar el "resto de la aplicación" mencionado en el título y en la User Story al contrato observable de `execute()` de `FacebookGeneratePreCheckCreativeUseCase` para invocaciones cuya entrada no contenga ads de tipo STANDARD, definido como: el valor de retorno de `execute()`, las excepciones lanzadas por `execute()`, y las llamadas a colaboradores o dependencias externas realizadas durante dicha invocación, según la definición del criterio 1.

### Requirement 15: Pruebas unitarias de la Rama_STANDARD

**User Story:** Como equipo de desarrollo, quiero una cobertura de pruebas unitarias que caracterice la nueva Rama_STANDARD con el mismo rigor de aislamiento que ya exige la suite existente, para detectar regresiones futuras.

#### Acceptance Criteria

1. THE Suite_de_Pruebas SHALL residir exclusivamente en `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py`, ampliando el archivo ya existente sin relocalizarlo.
2. THE Suite_de_Pruebas SHALL cubrir, como mínimo, un escenario exitoso por cada una de las 4 Combinaciones_Soportadas listadas en Requirement 2, verificando en cada escenario tanto el valor `ok=1` para ese ad como las anotaciones de éxito adicionales definidas en Requirement 10.2.
3. THE Suite_de_Pruebas SHALL cubrir, como mínimo, un escenario de error por longitud de texto excedida para cada uno de Título_STANDARD, Cuerpo_STANDARD y Descripción_STANDARD.
4. THE Suite_de_Pruebas SHALL cubrir, como mínimo, un escenario de error por cantidad de ítems distinta de 1 (cantidad 0 y cantidad mayor a 1, conforme a la definición de Valor_Candidato) para cada uno de Título_STANDARD, Cuerpo_STANDARD, Descripción_STANDARD e Imagen_STANDARD.
5. THE Suite_de_Pruebas SHALL cubrir, como mínimo, un escenario de URL_STANDARD inválida.
6. THE Suite_de_Pruebas SHALL cubrir, como mínimo, un escenario de Combinación_Objetivo_Optimización no soportada para STANDARD, verificando que `execute()` lanza `MetaException` con `code="META011"` antes de iterar sobre `ad_sets`/`ads`, y que ninguna de las validaciones de los Requirements 3 a 9 se ejecuta (por ejemplo, verificando que ninguno de los colaboradores de `MetaAdsValidator` asociados —`is_valid_length`, `validate_images_precheck`, `is_valid_link_url`, `validate_cta_for_goal`— fue invocado).
7. THE Suite_de_Pruebas SHALL cubrir, como mínimo, un escenario que verifique que la construcción de `creatives[]` para un ad set STANDARD extrae sus campos desde `object_story_spec` conforme a Requirement 12.
8. WHEN una prueba de la Suite_de_Pruebas construye un Caso_de_Uso o ejercita `execute()`, THE Suite_de_Pruebas SHALL sustituir por Dobles_de_Prueba las mismas dependencias externas ya aisladas por la suite existente (`AdChannelRepository`, `CampaignChannelPublishRepository`, `redis_client`, `MetaAdsPayloadBuilder`, `FacebookGetAdAccountDetailsUseCase`, `FacebookMinimumBudgetUseCase`), sin realizar solicitudes HTTP reales, sin conexión real a Redis/Strapi, y sin requerir una aplicación o contexto Flask real, excepto cuando el propio Caso_de_Uso o alguna de sus dependencias invoque explícitamente una funcionalidad de Flask (por ejemplo, `current_app`) que exija un contexto de aplicación activo, en cuyo caso THE Suite_de_Pruebas SHALL proveer dicho contexto mediante `app.app_context()` o `app.test_request_context()` de la aplicación Flask ya definida por la suite existente.
9. WHERE un escenario de la Suite_de_Pruebas requiera ejercitar la validación de Imagen_STANDARD, THE Suite_de_Pruebas SHALL evitar solicitudes HTTP reales parcheando `MetaAdsValidator.validate_images_precheck` o construyendo el escenario sin URL de imagen, siguiendo el mismo patrón de aislamiento de red ya usado por la suite existente para DYNAMIC.
10. WHEN se ejecuta `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` con el intérprete de `sinergia/venv`, THE Suite_de_Pruebas SHALL finalizar con cero pruebas `failed`, cero `skipped` y cero errores de recopilación o ejecución.
11. THE Suite_de_Pruebas SHALL cubrir, como mínimo, tres escenarios de validación de CTA_STANDARD conforme a Requirement 9: uno con un valor de CTA_STANDARD válido (verificando el escenario exitoso correspondiente), uno con un valor de CTA_STANDARD inválido (verificando que se agrega un error controlado y que no se lanza una excepción no controlada), y uno con CTA_STANDARD ausente (verificando el comportamiento definido en Requirement 9 para ese caso).
12. THE Suite_de_Pruebas SHALL cubrir, como mínimo, un escenario en el que Imagen_STANDARD sea marcada como inválida por `MetaAdsValidator.validate_images_precheck` conforme a Requirement 6.4, verificando que se agrega un error controlado distinto del error de cantidad de ítems cubierto en el Criterio 4 y que no se lanza una excepción no controlada.
13. THE Suite_de_Pruebas SHALL cubrir, como mínimo, un escenario en el que `daily_budget` no sea comparable (por ejemplo, valor `None`) conforme a Requirement 8.2, verificando que se agrega un error controlado y que no se lanza una excepción no controlada.

## Testing Strategy

### Unit Tests
Toda la cobertura de esta especificación es unitaria, ejecutada dentro de `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py`, extendiendo la suite ya existente para `FacebookGeneratePreCheckCreativeUseCase` con las clases/escenarios de la Rama_STANDARD descritos en Requirement 15.

### Integration Tests
Fuera de alcance. No se ejercita Strapi, Redis, Meta Graph API ni ninguna infraestructura real; todas las dependencias externas se sustituyen por dobles de prueba, igual que en la suite existente.

### Property-Based Tests
No se exige un conjunto de propiedades con Hypothesis como requisito obligatorio de esta especificación. Si durante el diseño se identifica una invariante pura de amplio dominio (por ejemplo, la equivalencia entre el conteo de `Valor_Candidato` y el resultado de las validaciones de cantidad exacta 1 para título/cuerpo/descripción/imagen, independientemente de si el dato de origen es escalar o lista), puede añadirse como prueba basada en propiedades adicional sin que sea obligatoria.
