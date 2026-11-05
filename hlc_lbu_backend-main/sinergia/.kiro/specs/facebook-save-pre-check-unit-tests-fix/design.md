# Realineamiento de `TestBuildResponse` tras el cambio de despacho por modo — Diseño del Bugfix

## Overview

El commit `be390b56` (HL-2496) reemplazó el criterio de despacho de
`FacebookSavePreCheckBaseUseCase._build_response` por una lectura del modo **declarado** de la
campaña (`self.creative_type`). Siete nodos de pytest invocan ese método de forma directa y aislada,
sin atravesar `execute()`, de modo que `_set_creative_type` nunca corre y `self.creative_type`
conserva el `''` del constructor: la rama DYNAMIC se toma siempre y las aserciones heredadas de la
heurística anterior quedan contradichas.

El defecto está en las pruebas. El arreglo consiste en **hacer explícito el modo** en los nodos que
invocan `_build_response` directamente, parametrizando sobre ambas ramas los seis casos de valores
por defecto y fijando STANDARD en el caso de la tabla de mapeo. Ni una línea bajo `sinergia/app/`
cambia.

Dos hallazgos de esta fase acotan el trabajo mucho más de lo que sugieren los siete fallos:

1. **Solo cinco aserciones por caso son dependientes de rama.** Para las tres formas de `adCreative`
   que usan los seis casos de defaults, las dos ramas producen resultados **idénticos** en las 25
   claves restantes de la respuesta. La única diferencia son los cinco `*_max_amount`. Verificado
   empíricamente (ver Hypothesized Root Cause).
2. **Hay 15 nodos que invocan `_build_response` directamente, no 7.** Los 8 que hoy pasan lo hacen
   *por accidente*: `creative_type == ''` es indistinguible de `'DYNAMIC'` para el despacho, y esos
   8 casos caracterizan precisamente la extracción DYNAMIC. La cláusula 2.5 exige fijar el modo en
   todo invocador directo, así que esos 8 también se tocan — con una sola línea cada uno y **cero**
   cambios de aserción, lo que preserva 3.2 al pie de la letra y elimina la fragilidad latente que
   produjo este bugfix.

La estrategia de validación invierte la habitual: no se escriben pruebas exploratorias nuevas,
porque los contraejemplos ya existen y son exactamente los siete fallos. El baseline está capturado
y la preservación se demuestra comparando el resultado nodo por nodo.

## Glossary

- **Bug_Condition (C)**: un nodo de pytest `X` de `TestBuildResponse` (en uno de los dos archivos
  objetivo) que invoca `_build_response` directamente, no fija `self.creative_type`, y asevera al
  menos un valor dependiente de la rama de extracción.
- **Property (P)**: el nodo pasa (`outcome == PASSED`) sin que ningún archivo bajo `sinergia/app/`
  haya cambiado.
- **Preservation**: todo nodo que no cumple C mantiene exactamente el mismo `outcome` antes y
  después. Incluye los 2567 nodos que hoy pasan en `tests/v2/unit`.
- **F**: la suite en su estado actual (`7 failed, 2567 passed`, 2574 recolectados).
- **F'**: la suite realineada (`0 failed, 2580 passed`, 2580 recolectados).
- **`creative_type`**: atributo de instancia inicializado a `''` por el constructor del ancestro
  (`app/v2/use_cases/meta_ads.py:988`, `creative_type: str = ''`) y reasignado por
  `_set_creative_type`. No es un parámetro de construcción de los casos de uso de pre-check.
- **`_set_creative_type`**: `app/v2/use_cases/meta_ads.py:2523`. Ejecuta
  `CreativeType(campaign_setup.get('attributes', {}).get('meta_campaign_mode')).value`. Aborta con
  `ValueError` ante cualquier valor fuera de `{"STANDARD", "DYNAMIC"}`. Se invoca desde los seis
  `execute()` de pre-check (líneas 2664, 2705, 2813, …) **antes** de `_build_response`.
- **`_build_response`**: `app/v2/use_cases/meta_ads.py:2526`. Despacha en la línea 2533 con
  `if self.creative_type == CreativeType.STANDARD.value:`.
- **Rama STANDARD**: bloque `if` de `_build_response` (líneas 2534–2577). Deriva todo de
  `object_story_spec`/`link_data` y **fija por literal** los cinco `*_max_amount` a `1`.
- **Rama DYNAMIC**: bloque `else` (líneas 2579–2618). Deriva todo de `asset_feed_spec` y resuelve
  los cinco `*_max_amount` con `.get('*_max_amount', 0)`.
- **Invocación directa aislada**: llamar `use_case._build_response(creative)` sobre una instancia
  construida por `use_case_factory`, sin pasar por `execute()`. Es el patrón de 15 nodos de
  `TestBuildResponse`.
- **Nodo vacuo**: nodo que pasa por una razón distinta de la que su docstring declara. Los 8 nodos
  DYNAMIC que hoy pasan son vacuos en sentido débil: aciertan la rama, pero por omisión y no por
  declaración.

## Bug Details

### Bug Condition

El sujeto bajo prueba no es el código productivo sino la propia suite.

**Formal Specification:**

```
FUNCTION isBugCondition(X)
  INPUT: X of type PytestNodeId
  OUTPUT: boolean

  RETURN X.file IN TARGET_TEST_FILES
         AND X.class = 'TestBuildResponse'
         AND invokesBuildResponseDirectly(X)
         AND NOT setsCreativeTypeExplicitly(X)
         AND (
              assertsStandardMaxAmountDefaults(X)   // Grupo A - 6 nodos
           OR assertsStandardMappingTable(X)        // Grupo B - 1 nodo
         )
END FUNCTION
```

donde

```
TARGET_TEST_FILES = {
  tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py,
  tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py
}
```

```
FUNCTION expectedBehavior(result)
  INPUT: result of type PytestOutcome
  OUTPUT: boolean

  RETURN result.outcome = PASSED
         AND result.outcome NOT IN {SKIPPED, XFAIL, XPASS, ERROR}
         AND productionSourceUnchanged() = TRUE   // git diff --stat -- app/ vacío
END FUNCTION
```

Nótese que `invokesBuildResponseDirectly(X) AND NOT setsCreativeTypeExplicitly(X)` se cumple hoy en
**15** nodos, pero solo 7 aseveran algo dependiente de rama. Los otros 8 no cumplen C y por tanto
están cubiertos por la Preservation Property: sus aserciones no se tocan (ver Fix Implementation,
§ *Nodos DYNAMIC que hoy pasan*).

### Examples

Todos los contraejemplos reproducidos en este entorno con
`venv/bin/python -m pytest tests/v2/unit -q` (`HEAD = 4c510b40`).

- `test_facebook_save_pre_check_images.py::TestBuildResponse::test_response_uses_exact_defaults_for_every_omitted_field`
  invoca `_build_response` con `adCreative = {'asset_feed_spec': {}}` y asevera
  `response["images_max_amount"] == 1` (línea 3079). Obtiene `AssertionError: assert 0 == 1`.
  Esperado tras el arreglo: `0` en la parametrización DYNAMIC y `1` en la STANDARD.
- `test_facebook_save_pre_check_texts.py::TestBuildResponse::test_defaults_for_all_omitted_fields`
  falla idénticamente en la línea 4417, y su docstring además **justifica** el `1` invocando la
  heurística `object_story_spec or not asset_feed_spec` ya eliminada.
- `..._images.py::TestBuildResponse::test_direct_isolated_call_returns_default_response_when_ad_creative_is_explicit_none`
  falla en la línea 3446 pese a que su intención principal —que `adCreative = None` no propague
  `AttributeError`— sí se cumple: la normalización `ads_to_publish.get('adCreative') or {}` sigue
  vigente.
- `..._images.py::TestBuildResponse::test_direct_isolated_call_reflects_pre_annotated_standard_link_data_per_mapping_table`
  falla en la **primera** aserción derivada de `object_story_spec`:
  `AssertionError: assert 0 == 'channel-7-7'` (línea 3347). Las 29 aserciones restantes de la tabla
  de mapeo quedan sin evaluar.
- Caso borde ya correcto que debe seguir pasando:
  `..._images.py::TestBuildResponse::test_execute_standard_branch_response_contains_expected_keys_and_reflects_validated_image`
  atraviesa `execute()` con `meta_campaign_mode="STANDARD"`, así que `_set_creative_type` sí corre y
  el despacho es correcto hoy. No se toca (3.3).

## Expected Behavior

### Preservation Requirements

**Comportamientos que no deben cambiar:**

- Los 2567 nodos que pasan en `tests/v2/unit` siguen pasando, sin cambiar a `failed`, `error`,
  `skipped` ni `xfail` (3.1).
- Los nodos que pasan dentro de los dos archivos objetivo siguen pasando **sin modificación de sus
  aserciones** (3.2). Esto incluye los 8 invocadores directos DYNAMIC, a los que se añade una línea
  de asignación de estado pero ni una aserción nueva, modificada ni eliminada.
- Todo nodo que llega a `_build_response` a través de `execute()` sigue obteniendo el modo desde
  `_set_creative_type(campaign_setup)`, sin fijación manual (3.3).
- `TestUnsupportedMetaCampaignModeRaisesValueError` sigue aseverando `use_case.creative_type == ""`
  (`..._images.py:2285`, `..._texts.py:3636`). La fijación manual introducida en `TestBuildResponse`
  opera sobre instancias distintas y no altera esa expectativa (3.4).
- Los builders y fixtures compartidos (`make_ad_creative`, `make_asset_feed_spec`,
  `make_object_story_spec`, `make_link_data`, `make_ad`, `make_creative`, `use_case_factory`, el
  centinela `ABSENT`) conservan su firma y su semántica de valores por defecto: **ninguno se
  modifica** (3.7).
- `AdChannelRepository` y `CampaignChannelPublishRepository` siguen sustituidos por dobles
  parcheados en `app.v2.use_cases.meta_ads`; `redis_client` y toda llamada HTTP siguen parcheados.
  La fixture `deny_network` (autouse) nunca se dispara (3.8).
- Las suites de los otros cuatro casos de uso de pre-check, `test_facebook_launch_campaign.py`,
  `test_facebook_get_launch_campaign_creatives.py` y `test_funnel_flow_validator.py` no se tocan
  (3.5, 3.6).
- Los fallos preexistentes ajenos al alcance (`tests/v2/integration`, `tests/v1/`) se comportan
  igual que hoy (3.10).
- El tiempo de ejecución de `tests/v2/unit` se mantiene en el orden de 51–53 s, sin esperas reales,
  reintentos ni E/S de red (3.11).

**Alcance:**

Todo nodo que no cumple `isBugCondition` queda inafectado en su resultado. En particular:

- Los 8 invocadores directos DYNAMIC de `TestBuildResponse`: sus aserciones se preservan
  literalmente y su `outcome` sigue siendo `PASSED`, ahora por la razón declarada en lugar de por
  omisión.
- Los 4 nodos de `TestBuildResponse` que atraviesan `execute()` (2 en imágenes, 1 en textos, más
  `test_execute_standard_branch_...`).
- Los nodos de los 11 archivos restantes de `tests/v2/unit/use_cases/`.

El comportamiento correcto esperado para los nodos que sí cumplen la condición está definido en
Correctness Properties (Property 1).

## Hypothesized Root Cause

La causa está **confirmada**, no hipotetizada: no queda ninguna hipótesis abierta.

1. **El despacho pasó de la forma del creativo al modo declarado.** `app/v2/use_cases/meta_ads.py`
   línea 2533 evalúa `self.creative_type == CreativeType.STANDARD.value`. La expresión anterior
   (`object_story_spec or not asset_feed_spec`) ya no existe en el archivo.

2. **La invocación directa deja `creative_type == ''`.** El constructor del ancestro (línea 988)
   inicializa `creative_type: str = ''`; `_set_creative_type` solo corre dentro de `execute()`
   (líneas 2664, 2705, …), así que un nodo que llama `_build_response` directamente nunca lo
   ejecuta. `'' != 'STANDARD'` ⇒ rama `else` ⇒ extracción DYNAMIC.

3. **El estado `creative_type == ''` es inalcanzable en producción.** Los seis invocadores de
   `_build_response` en `app/` son los `execute()` de los seis casos de uso de pre-check, y los seis
   llaman `_set_creative_type` antes, método que aborta con `ValueError` ante cualquier modo que no
   sea `"DYNAMIC"` o `"STANDARD"`. El nuevo despacho es además estrictamente más correcto que la
   heurística anterior, que podía enrutar un anuncio STANDARD con `asset_feed_spec` presente hacia
   la extracción DYNAMIC.

### Hallazgo: solo los cinco `*_max_amount` son dependientes de rama

Caracterización empírica de `_build_response` invocado directamente sobre las tres formas de
`adCreative` que usan los seis casos de defaults, comparando las 30 claves de la respuesta entre
`creative_type = 'DYNAMIC'` y `creative_type = 'STANDARD'`:

| Forma de `adCreative` | Conjunto de claves | Cinco `*_max_amount` | Otras 25 claves |
|---|---|---|---|
| `{'asset_feed_spec': {}}` | idéntico | DYNAMIC `[0,0,0,0,0]` / STANDARD `[1,1,1,1,1]` | **idénticas** |
| `None` (clave presente) | idéntico | DYNAMIC `[0,0,0,0,0]` / STANDARD `[1,1,1,1,1]` | **idénticas** |
| clave `adCreative` ausente | idéntico | DYNAMIC `[0,0,0,0,0]` / STANDARD `[1,1,1,1,1]` | **idénticas** |

Valor común de las 25 claves invariantes en las tres formas:

```
adchannel_id=0, images=[], bodies=[], titles=[], descriptions=[], call_to_action_types=[],
*_valid_amount=False (×5), unique_titles=False, unique_bodies=False, unique_descriptions=False,
daily_budget_valid=False, min_daily_budget=0, proposal_url='', proposal_url_valid=False,
proposal_locations=[], locations=[], locations_valid=False
```

`adchannel_id` coincide en `0` porque la rama STANDARD lo lee de
`object_story_spec.get('ad_channel_id', 0)` con `object_story_spec == {}` y la DYNAMIC de
`asset_feed_spec.get('ad_channel_id', 0)` con `asset_feed_spec == {}`. `proposal_url` coincide en
`''` porque `link_data.get('link') or ''` y `','.join([])` producen lo mismo.

Consecuencia de diseño: en los seis casos del Grupo A **solo cinco aserciones** se vuelven
dependientes de la parametrización. Las 20–25 aserciones restantes de cada caso se conservan
literalmente, lo que reduce la superficie del cambio y hace que la parametrización sobre ambas ramas
tenga coste marginal casi nulo.

### Hallazgo: la forma del caso de la tabla de mapeo solo admite STANDARD

El `creative` de `test_direct_isolated_call_reflects_pre_annotated_standard_link_data_per_mapping_table`
lleva `object_story_spec` poblado y **carece** de `asset_feed_spec`. Bajo DYNAMIC toda clave derivada
de `object_story_spec`/`link_data` colapsa a su valor por defecto y solo sobreviven las cuatro que se
leen de `creative`/`ads[0]` (`name`, `adset_id`, `ad_id`, `daily_budget`): la parametrización DYNAMIC
sería un duplicado degenerado de los casos de defaults. Por eso 2.4 excluye ese caso de la
parametrización. Con `creative_type = 'STANDARD'` fijado, la respuesta real reproduce **las 30
aserciones existentes sin excepción**, verificado clave por clave:

```
adchannel_id='channel-7-7'   images=[{'url': …, 'valid': True, 'error': None}]
titles=[{'text': 'Headline…', 'valid_length': True}]
bodies=[{'text': 'Body…', 'valid_length': False}]
descriptions=[{'text': 'Description…', 'valid_length': True}]
call_to_action_types=[{'value': 'SIGN_UP', 'valid': True}]
images_valid_amount=True  titles_valid_amount=True  bodies_valid_amount=False
descriptions_valid_amount=True  call_to_action_types_valid_amount=True
*_max_amount=1 (×5)  unique_titles=True  unique_bodies=False  unique_descriptions=True
daily_budget_valid=True  min_daily_budget=750  proposal_url='https://example.test/proposal'
proposal_url_valid=True  proposal_locations=['proposal-location-7-7']
locations=['location-7-7-a','location-7-7-b']  locations_valid=True
name='Creative 7.7'  adset_id='adset-1'  ad_id='ad-7-7'  daily_budget=321
```

No hace falta tocar ninguna aserción de ese caso: basta una línea de asignación.

## Correctness Properties

Property 1: Bug Condition - Los 7 nodos desalineados pasan sin tocar el código productivo

_For any_ nodo de pytest `X` donde la condición de bug se cumple (`isBugCondition(X)` devuelve
`true`), la suite realineada `F'` SHALL producir `outcome == PASSED` para toda parametrización de
`X`, con el modo de campaña fijado explícitamente antes de la invocación y con las aserciones
dependientes de rama expresadas en función de ese modo, sin que `X` haya sido eliminado, marcado
`skip`/`xfail` ni relajado, y sin que ningún archivo bajo `sinergia/app/` haya sido modificado
(`git diff --stat -- app/` vacío).

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10**

Property 2: Preservation - Todo nodo alineado conserva su resultado

_For any_ nodo de pytest `X` donde la condición de bug NO se cumple (`isBugCondition(X)` devuelve
`false`), la suite realineada `F'` SHALL producir para `X` exactamente el mismo `outcome` que la
suite original `F`, preservando los 2567 nodos que hoy pasan en `tests/v2/unit`, las aserciones
literales de los 8 invocadores directos DYNAMIC, la ruta de producción vía `_set_creative_type` en
los nodos que atraviesan `execute()`, la firma y la semántica de todo builder y fixture compartido,
el aislamiento de red y repositorios, y el orden de magnitud del tiempo de ejecución.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11**

## Fix Implementation

### Inventario de los 15 invocadores directos

Rutas relativas a `sinergia/`. Todas las líneas verificadas contra `HEAD = 4c510b40`.

#### `tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py` — `class TestBuildResponse` (2844)

| # | Caso (línea `def`) | `use_case_factory()` | Invocación | Rama que caracteriza | Estado | Acción |
|---|---|---|---|---|---|---|
| I1 | `test_response_contains_exactly_the_keys_from_requirement_14_1` (2936) | 2950 | 2952 | DYNAMIC | passed | fijar DYNAMIC (2.5) |
| I2 | `test_response_reflects_exact_explicit_asset_feed_spec_values_including_images_projection` (2956) | 3009 | 3011 | DYNAMIC | passed | fijar DYNAMIC (2.5) |
| **I3** | `test_response_uses_exact_defaults_for_every_omitted_field` (3047) | 3070 | 3072 | **ambas** | **failed** | parametrizar (2.1) |
| I4 | `test_proposal_url_is_comma_joined_website_urls_in_the_same_order` (3099) | 3118 | 3120 | DYNAMIC | passed | fijar DYNAMIC (2.5) |
| I5 | `test_proposal_locations_is_empty_list_when_creative_omits_the_key` (3126) | 3147 | 3149 | DYNAMIC | passed | fijar DYNAMIC (2.5) |
| **I6** | `test_direct_isolated_call_reflects_pre_annotated_standard_link_data_per_mapping_table` (3273) | 3340 | 3342 | STANDARD | **failed** | fijar STANDARD (2.4) |
| **I7** | `test_direct_isolated_call_returns_default_response_when_ad_creative_is_explicit_none` (3387) | 3425 | 3427 | **ambas** | **failed** | parametrizar (2.2) |
| **I8** | `test_direct_isolated_call_returns_default_response_when_ad_creative_key_absent` (3461) | 3493 | 3495 | **ambas** | **failed** | parametrizar (2.3) |

Nodos de la misma clase que atraviesan `execute()` y **no se tocan** (3.3):
`test_execute_dynamic_branch_response_reflects_images_mutated_by_validate_images_dynamic` (3153),
`test_execute_standard_branch_response_contains_expected_keys_and_reflects_validated_image` (3223).

#### `tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py` — `class TestBuildResponse` (4172)

| # | Caso (línea `def`) | `use_case_factory()` | Invocación | Rama que caracteriza | Estado | Acción |
|---|---|---|---|---|---|---|
| T1 | `test_exact_key_set_and_explicit_values_reflected` (4242) | 4255 | 4299 | DYNAMIC | passed | fijar DYNAMIC (2.5) |
| T2 | `test_images_mapped_to_url_valid_error_subdicts` (4334) | 4343 | 4360 | DYNAMIC | passed | fijar DYNAMIC (2.5) |
| **T3** | `test_defaults_for_all_omitted_fields` (4368) | 4397 | 4403 | **ambas** | **failed** | parametrizar (2.1) |
| T4 | `test_proposal_url_is_comma_join_of_link_urls_website_url_in_order` (4439) | 4449 | 4461 | DYNAMIC | passed | fijar DYNAMIC (2.5) |
| T5 | `test_proposal_locations_defaults_to_empty_list_when_creative_omits_key` (4465) | 4474 | 4483 | DYNAMIC | passed | fijar DYNAMIC (2.5) |
| **T6** | `test_isolated_call_with_explicit_none_ad_creative_returns_default_response` (4561) | 4589 | 4594 | **ambas** | **failed** | parametrizar (2.2) |
| **T7** | `test_isolated_call_with_ad_creative_key_absent_returns_default_response` (4621) | 4645 | 4651 | **ambas** | **failed** | parametrizar (2.3) |

Nodo de la misma clase que atraviesa `execute()` y **no se toca** (3.3):
`test_full_execute_dynamic_scenario_response_reflects_mutated_asset_feed` (4487).

#### Sitios exactos de las aserciones dependientes de rama

| Nodo | Bloque de cinco `*_max_amount` |
|---|---|
| I3 | 3079–3083 |
| I7 | 3446–3450 |
| I8 | 3514–3518 |
| T3 | 4417–4421 |
| T6 | 4606–4610 |
| T7 | 4663–4667 |

I6 no tiene aserciones a cambiar: sus `*_max_amount == 1` (3371–3375) ya son correctos bajo STANDARD.

### Decisión de diseño: dónde vive la parametrización

Se evaluaron tres opciones.

| Opción | Efecto sobre 3.7 y sobre el resto de la suite | Veredicto |
|---|---|---|
| Crear `tests/v2/unit/use_cases/conftest.py` con la constante compartida | **No existe ningún `conftest.py` bajo `tests/`** (verificado con `find tests -name conftest.py`, sin resultados, pese a que `structure.md` lo menciona). Introducir uno haría visibles sus definiciones a los 13 módulos del directorio y rompería la convención auto-contenida que ambos archivos siguen hoy, duplicando deliberadamente `make_ad_creative`, `make_ad`, `make_creative` y `ABSENT`. Radio de acción desproporcionado para 6 nodos | **Rechazada** |
| Añadir un parámetro `creative_type=` a `use_case_factory` | La fixture la consumen ~100 nodos en cada archivo; ampliar su firma para un solo escenario roza 3.7. Y desinforma: en producción el modo **no** es un parámetro de construcción, lo asigna `_set_creative_type` después de leer el `campaign_setup` | **Rechazada** |
| Constante de parametrización a nivel de módulo en cada uno de los dos archivos, más asignación explícita del atributo en el cuerpo del caso | Cero impacto sobre helpers y fixtures compartidos; refleja la convención de duplicación ya vigente entre estos dos archivos; deja la asignación visible en el punto de uso, donde el lector ve exactamente lo que `execute()` haría en su lugar | **Adoptada** |

### Cambio 1 — Importar `CreativeType` (ambos archivos)

`CreativeType` se menciona hoy solo dentro de docstrings, nunca se importa. Se añade al import ya
existente de `facebook_validator_service`, que es de donde lo importan las otras cuatro suites que
lo usan (`test_facebook_launch_campaign.py:51`,
`test_facebook_get_launch_campaign_creatives.py:52`, `test_facebook_export_assets_post_launch_campaign.py:58`,
`test_meta_ads_payload_builder_standard_ad_channel_id.py:25`) y donde lo importa el propio código
productivo (`meta_ads.py:23`).

`test_facebook_save_pre_check_images.py`, línea 29:

```diff
-from app.v2.use_cases.facebook_validator_service import MetaAdsValidator
+from app.v2.use_cases.facebook_validator_service import CreativeType, MetaAdsValidator
```

`test_facebook_save_pre_check_texts.py`, línea 33: idéntico.

Es un `Enum`, nunca se parchea, así que el módulo de origen no tiene efecto observable; se elige por
consistencia.

### Cambio 2 — Constante de parametrización (ambos archivos)

Se inserta inmediatamente **antes** de `class TestBuildResponse` (línea 2844 en imágenes, 4172 en
textos), por ser de uso exclusivo de esa clase:

```python
_BUILD_RESPONSE_DEFAULTS_BRANCHES = [
    pytest.param(CreativeType.DYNAMIC.value, 0, id="dynamic-max-amount-0"),
    pytest.param(CreativeType.STANDARD.value, 1, id="standard-max-amount-1"),
]
"""Parametrización de las dos ramas de extracción de ``_build_response`` para
los escenarios de valores por defecto.

``_build_response`` despacha con ``self.creative_type == CreativeType.STANDARD.value``
(``app/v2/use_cases/meta_ads.py:2533``), atributo que ``_set_creative_type``
asigna dentro de ``execute()`` a partir de
``campaign_setup['attributes']['meta_campaign_mode']``. Los escenarios que
invocan ``_build_response`` de forma directa y aislada deben fijarlo ellos
mismos: el ``''`` que deja el constructor no es ``"STANDARD"``, así que sin
fijación explícita se tomaría siempre la rama DYNAMIC, y el estado ``''`` es
inalcanzable en producción porque ``_set_creative_type`` aborta con
``ValueError`` ante cualquier modo distinto de ``"DYNAMIC"``/``"STANDARD"``.

Para las tres formas de ``adCreative`` de estos escenarios (``asset_feed_spec``
vacío, ``adCreative`` explícitamente ``None`` y clave ``adCreative`` ausente) las
dos ramas coinciden en 25 de las 30 claves de la respuesta; la única diferencia
son los cinco ``*_max_amount``, que la rama STANDARD fija por literal a ``1``
(cardinalidad exacta 1 de un ad set STANDARD) y la DYNAMIC resuelve con
``asset_feed_spec.get('*_max_amount', 0)``. De ahí el segundo parámetro.
"""
```

El `id` explícito cumple 2.7: cada parametrización es distinguible por su `id` de pytest
(`…[dynamic-max-amount-0]`, `…[standard-max-amount-1]`) y nombra la rama efectivamente ejercitada.

### Cambio 3 — Los seis casos de defaults (I3, I7, I8, T3, T6, T7)

Patrón uniforme. Ejemplo sobre I3 (`..._images.py:3047`):

```diff
+    @pytest.mark.parametrize(
+        "creative_type, expected_max_amount", _BUILD_RESPONSE_DEFAULTS_BRANCHES
+    )
     def test_response_uses_exact_defaults_for_every_omitted_field(
-        self, use_case_factory
+        self, use_case_factory, creative_type, expected_max_amount
     ):
         ad_creative = make_ad_creative(asset_feed_spec={})
         creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])

         use_case, _, _ = use_case_factory()
+        use_case.creative_type = creative_type

         response = use_case._build_response(creative)

         assert response["images_valid_amount"] is False
         …
-        assert response["images_max_amount"] == 1
-        assert response["titles_max_amount"] == 1
-        assert response["bodies_max_amount"] == 1
-        assert response["descriptions_max_amount"] == 1
-        assert response["call_to_action_types_max_amount"] == 1
+        assert response["images_max_amount"] == expected_max_amount
+        assert response["titles_max_amount"] == expected_max_amount
+        assert response["bodies_max_amount"] == expected_max_amount
+        assert response["descriptions_max_amount"] == expected_max_amount
+        assert response["call_to_action_types_max_amount"] == expected_max_amount
```

Reglas del patrón, aplicables a los seis:

1. El decorador se añade sobre el `def`, y los dos parámetros al final de la firma, después de
   `use_case_factory`.
2. `use_case.creative_type = creative_type` se inserta **inmediatamente después** de la línea
   `use_case, _, _ = use_case_factory()`, que en ambos archivos precede a la invocación. En imágenes
   esa línea aparece tras la construcción del `creative`; en textos, antes. El diseño respeta el
   orden local de cada archivo y no reordena nada.
3. Solo el bloque de cinco `*_max_amount` se vuelve paramétrico. **Todas** las demás aserciones
   —listas vacías, indicadores `False`, `min_daily_budget == 0`, `proposal_url == ''`,
   `adchannel_id == 0`, `set(response.keys()) == EXPECTED_RESPONSE_KEYS`, `name`/`adset_id`/`ad_id`/
   `daily_budget`, `proposal_locations == []`— se conservan literalmente (2.1, 2.2, 2.3), respaldadas
   por la caracterización empírica de las 25 claves invariantes.
4. Las aserciones de forma de entrada que preceden a la invocación
   (`assert "adCreative" not in creative["ads"][0]` en I8, `assert "adCreative" not in ad` en T7) se
   conservan intactas.
5. La aserción de conjunto de claves de I7/I8 (`set(response.keys()) == self.EXPECTED_RESPONSE_KEYS`)
   se conserva: el conjunto es idéntico en ambas ramas (verificado).

Sitios exactos por nodo:

| Nodo | Decorador antes de | Asignación tras | Aserciones a parametrizar |
|---|---|---|---|
| I3 | 3047 | 3070 | 3079–3083 |
| I7 | 3387 | 3425 | 3446–3450 |
| I8 | 3461 | 3493 | 3514–3518 |
| T3 | 4368 | 4397 | 4417–4421 |
| T6 | 4561 | 4589 | 4606–4610 |
| T7 | 4621 | 4645 | 4663–4667 |

### Cambio 4 — El caso de la tabla de mapeo (I6)

Una sola línea, sin parametrización y sin tocar ninguna de las 30 aserciones (2.4):

```diff
         use_case, _, _ = use_case_factory()
+        use_case.creative_type = CreativeType.STANDARD.value

         response = use_case._build_response(creative)
```

(inserción tras `..._images.py:3340`.)

### Cambio 5 — Los ocho invocadores directos DYNAMIC (I1, I2, I4, I5, T1, T2, T4, T5)

La cláusula 2.5 alcanza a **todo** caso de `TestBuildResponse` que invoca `_build_response`
directamente, no solo a los siete fallidos. Estos ocho caracterizan la extracción DYNAMIC y hoy
aciertan la rama por omisión, porque `''` y `'DYNAMIC'` son indistinguibles para el despacho. Se
hace explícito el modo con una línea por caso:

```diff
         use_case, _, _ = use_case_factory()
+        use_case.creative_type = CreativeType.DYNAMIC.value

         response = use_case._build_response(creative)
```

Inserciones tras las líneas 2950, 3009, 3118, 3147 (imágenes) y 4255, 4343, 4449, 4474 (textos).

Dos garantías explícitas:

- **Ni una aserción cambia** en estos ocho casos, lo que satisface 3.2 en su lectura más literal
  («sin modificación de sus aserciones»).
- **El resultado no puede cambiar**: `'' != 'STANDARD'` y `'DYNAMIC' != 'STANDARD'`, así que ambos
  estados producen exactamente la misma rama y la misma salida. Verificado en la tabla de
  Hypothesized Root Cause.

Su valor es eliminar la fragilidad que causó este bugfix: tras el cambio, ningún nodo de
`TestBuildResponse` depende del valor inicial del constructor.

### Cambio 6 — Docstrings (2.6)

Cinco docstrings de caso contradicen el despacho vigente y deben reescribirse; dos más deben
incorporar la declaración del modo. Además, los dos docstrings de clase contienen una copia literal
**obsoleta** del código productivo.

| Sitio | Contenido a corregir | Corrección |
|---|---|---|
| I3, docstring (3048–3066) | Enuncia literalmente «``0`` for each of the five ``*_max_amount`` values» mientras la aserción exige `1`: contradicción interna | Describir el despacho por `self.creative_type` y enunciar los defaults **por rama**: `0` bajo DYNAMIC (lookup en `asset_feed_spec`), `1` bajo STANDARD (literal). Conservar el párrafo que explica por qué se usa `{}` en vez de `make_asset_feed_spec()` |
| I7, docstring (3390–3422) | Dos párrafos que razonan sobre `if object_story_spec or not asset_feed_spec:` y concluyen que se toma la rama STANDARD | Sustituir por: la normalización `ads_to_publish.get('adCreative') or {}` sigue evitando el `AttributeError` —que es la intención principal del caso— y la rama la determina ahora `self.creative_type`, fijado por la parametrización. Conservar la referencia a la autorización de cambio de comportamiento (Requirement 1.5 / 7.8) del spec hermano |
| I8, docstring (3464–3489) | Idem: «``object_story_spec`` and ``asset_feed_spec`` are both ``None`` -- falsy -- so ``_build_response`` takes the STANDARD extraction branch» | Idem, más la equivalencia observable «clave ausente ≡ clave presente con `None`», que se conserva y ahora se asevera en ambas ramas |
| T3, docstring (4369–4396) | El bloque «Note on ``*_max_amount == 1`` (not ``0``)» justifica el `1` invocando la heurística eliminada y afirma que la rama STANDARD se toma «even though this specific Caso_de_Uso never populates ``object_story_spec`` itself» | Reescribir la nota en términos del despacho por modo declarado y de los defaults por rama. La observación de fondo sigue siendo válida y vale conservarla: la suite de textos nunca puebla `object_story_spec`, por lo que la parametrización STANDARD es hoy **la única cobertura de la rama STANDARD de `_build_response` en este archivo** |
| T6, docstring (4564–4588) | Contiene `(``object_story_spec or not asset_feed_spec`` is ``True``)` | Idem que I7 |
| T7, docstring (4624–4644) | Contiene «taking the STANDARD extraction branch» | Idem que I8 |
| I6, docstring (3276–3309) | No menciona la heurística, pero tampoco declara el modo del que depende toda la tabla de mapeo | Añadir un párrafo corto: el caso fija `creative_type = STANDARD` porque su `creative` lleva `object_story_spec` y carece de `asset_feed_spec` por diseño, y no se parametriza sobre DYNAMIC porque bajo esa rama toda la tabla colapsa a los defaults |

**Docstrings de clase.** `..._images.py:2845–2899` y `..._texts.py:4173–4207` embeben una copia
literal de `_build_response` **anterior** a `be390b56`: sin el bloque de despacho, sin la
normalización `or {}`, con `ad_creative = ads_to_publish.get('adCreative')` y con
`u.get('website_url')` donde el código vigente tiene `u.get('website_url', '')`. Se actualizan a la
forma vigente —con el `if self.creative_type == CreativeType.STANDARD.value:` y un resumen de ambas
ramas— por dos razones: son la fuente de la contradicción que estos siete casos heredaron, y son el
docstring compartido por los casos modificados, dentro del alcance de 2.6. El cambio es
exclusivamente documental y no puede alterar ningún `outcome`.

Regla transversal para las siete reescrituras: ninguna menciona `object_story_spec or not asset_feed_spec`
salvo, si acaso, para señalarlo como expresión retirada en `be390b56`.

### Cambio 7 — Nombres de caso (2.7)

Evaluación de los siete identificadores frente al comportamiento aseverado tras el realineamiento:

| Nodo | Nombre | ¿Contradice? | Decisión |
|---|---|---|---|
| I3 | `test_response_uses_exact_defaults_for_every_omitted_field` | No: neutral respecto a la rama | Conservar |
| I6 | `test_direct_isolated_call_reflects_pre_annotated_standard_link_data_per_mapping_table` | No: ya dice `standard` | Conservar |
| I7 | `test_direct_isolated_call_returns_default_response_when_ad_creative_is_explicit_none` | No | Conservar |
| I8 | `test_direct_isolated_call_returns_default_response_when_ad_creative_key_absent` | No | Conservar |
| T3 | `test_defaults_for_all_omitted_fields` | No | Conservar |
| T6 | `test_isolated_call_with_explicit_none_ad_creative_returns_default_response` | No | Conservar |
| T7 | `test_isolated_call_with_ad_creative_key_absent_returns_default_response` | No | Conservar |

Ningún nombre afirma nada sobre la rama ni sobre los `*_max_amount`, así que ninguno contradice el
comportamiento aseverado y el antecedente `IF` de 2.7 no se activa para el nombre del caso. La
exigencia de distinguibilidad por `id` de pytest sí se activa y queda cubierta por los `id=`
explícitos del Cambio 2 (`dynamic-max-amount-0`, `standard-max-amount-1`).

Ninguna clase se renombra: `TestBuildResponse` describe con exactitud el método bajo prueba.

### Recuento de nodos resultante (2.8)

| Concepto | F | F' |
|---|---|---|
| Nodos recolectados en `tests/v2/unit` | 2574 | 2580 |
| Los seis casos de defaults | 6 nodos | 12 nodos (6 × 2 ramas) |
| I6 (tabla de mapeo) | 1 | 1 |
| Los ocho invocadores DYNAMIC | 8 | 8 |
| `failed` | 7 | 0 |
| `passed` | 2567 | 2580 |

`2574 − 6 + 12 = 2580`, consistente con 2.8.

### Orden de ejecución

Sin acoplamientos entre cambios: los dos archivos son independientes y dentro de cada uno los casos
también. Orden recomendado por comodidad de verificación incremental:

1. Cambio 1 (import) y Cambio 2 (constante) en ambos archivos. Verificar que la recolección sigue
   funcionando: `venv/bin/python -m pytest tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py --collect-only -q | tail -3`.
2. Cambio 4 (I6): un solo nodo, la verificación más rápida.
3. Cambio 3 (los seis casos de defaults), archivo por archivo.
4. Cambio 5 (los ocho DYNAMIC): la comprobación de preservación más sensible; se ejecuta después
   para poder atribuirle sin ambigüedad cualquier cambio de resultado.
5. Cambio 6 y 7 (documental).
6. Verificación completa de `tests/v2/unit` y de que `app/` no cambió.

### Riesgos

- **R1 — La asignación del atributo se coloca después de la invocación.** Sería un no-op silencioso:
  el caso volvería a tomar la rama DYNAMIC y la parametrización STANDARD fallaría de forma visible.
  Fallo ruidoso, no silencioso. Mitigación: la tabla de sitios exactos del Cambio 3 fija la línea de
  inserción caso por caso.
- **R2 — Fuga de estado entre casos.** Nula: cada caso construye una instancia nueva vía
  `use_case_factory`, que no comparte nada entre invocaciones (cubierto por
  `test_builders_placeholder_smoke` y por el propio docstring de la fixture). No existe ninguna
  instancia a nivel de módulo o de clase.
- **R3 — Interferencia con `TestUnsupportedMetaCampaignModeRaisesValueError`.** Esa clase asevera
  `use_case.creative_type == ""` (`..._images.py:2285`, `..._texts.py:3636`) sobre instancias
  propias. La fijación manual vive en `TestBuildResponse` y no la alcanza (3.4).
- **R4 — Los ocho casos DYNAMIC cambian de resultado.** Imposible por construcción (`''` y
  `'DYNAMIC'` producen la misma rama), y verificado empíricamente. Si alguno cambiara, indicaría que
  el caso dependía de algo más que la rama y sería un hallazgo a escalar bajo 2.10.
- **R5 — Aserción obsoleta imposible de realinear sin tocar `app/`.** No se ha encontrado ninguna:
  las 30 aserciones de I6 y las 25 claves invariantes de los casos de defaults se reproducen
  exactamente con el código vigente. Si apareciera durante la implementación, 2.10 prohíbe eliminar,
  `xfail` o `skip` el caso: se escala al usuario.
- **R6 — El import de `CreativeType` colisiona con un nombre existente.** No: hoy `CreativeType`
  aparece en esos dos archivos solo dentro de docstrings y literales de mensaje de error.

## Testing Strategy

### Validation Approach

Los contraejemplos ya existen: son los siete fallos del baseline. No se escriben pruebas
exploratorias nuevas. La estrategia es (1) capturar el baseline nodo por nodo antes de tocar nada,
(2) demostrar Fix Checking sobre los nodos que cumplen C, (3) demostrar Preservation Checking
comparando los resultados de todos los demás, y (4) verificar que `app/` no cambió.

Todos los comandos se ejecutan desde el directorio `sinergia/` con el intérprete del entorno virtual
local, `venv/bin/python`, conforme a `.kiro/steering/tech.md`.

### Exploratory Bug Condition Checking

**Goal**: los contraejemplos ya están surfaced y la causa raíz está confirmada, no hipotetizada.

**Baseline capturado** (`HEAD = 4c510b40`):

```bash
venv/bin/python -m pytest tests/v2/unit -q
# 7 failed, 2567 passed, 12 warnings in 51.40s
```

Los siete nodos fallidos son exactamente los listados en el Inventario (I3, I6, I7, I8, T3, T6, T7).

**Baseline nodo por nodo**, para poder diferenciar después con precisión:

```bash
venv/bin/python -m pytest tests/v2/unit -q --no-header -rN > /tmp/baseline_summary.txt
venv/bin/python -m pytest tests/v2/unit --collect-only -q | sort > /tmp/baseline_nodes.txt
```

**Confirmación de la causa raíz**: la caracterización directa de `_build_response` con
`creative_type` en `''`, `'DYNAMIC'` y `'STANDARD'` sobre las tres formas de `adCreative` ya se
ejecutó en la fase de diseño; sus resultados están en Hypothesized Root Cause. Confirma que la rama
`else` se toma con `''`, que solo los cinco `*_max_amount` difieren entre ramas para esas formas, y
que la forma de I6 reproduce sus 30 aserciones bajo STANDARD. No se refuta nada, así que no hay que
re-hipotetizar.

### Fix Checking

**Goal**: para todo nodo donde la condición de bug se cumple, la suite realineada pasa sin que el
código productivo haya cambiado.

**Pseudocódigo:**

```
FOR ALL X WHERE isBugCondition(X) DO
  result := runTest(F', X)
  ASSERT result.outcome = PASSED
  ASSERT productionSourceUnchanged() = TRUE
END FOR
```

**Comandos:**

```bash
# Los 13 nodos resultantes de los 7 casos desalineados (6 × 2 ramas + I6)
venv/bin/python -m pytest \
  "tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py::TestBuildResponse" \
  "tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py::TestBuildResponse" \
  -v

# Verificación dirigida de que ambas parametrizaciones existen y pasan
venv/bin/python -m pytest \
  tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py \
  tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py \
  -v -k "max_amount"
```

**Criterio de aceptación:** los 12 nodos parametrizados aparecen con sus `id` `dynamic-max-amount-0`
y `standard-max-amount-1`, y los 13 pasan. Ninguno reporta `skipped`, `xfail` ni `xpass`.

### Preservation Checking

**Goal**: para todo nodo donde la condición de bug NO se cumple, el resultado es el mismo antes y
después.

**Pseudocódigo:**

```
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT runTest(F, X).outcome = runTest(F', X).outcome
END FOR
```

**Testing Approach**: comparación exhaustiva del conjunto completo de nodos, no muestreo. El dominio
de entrada es finito y enumerable (los nodos recolectados por pytest), así que la comparación nodo
por nodo es una verificación total, más fuerte que cualquier generación aleatoria. Por eso este
bugfix no introduce pruebas basadas en propiedades nuevas: no hay ningún dominio infinito que
muestrear. Las propiedades Hypothesis ya existentes en la suite
(`test_property_is_valid_images_amount_iff_length_in_1_to_10`,
`test_property_is_valid_texts_amount_true_iff_count_in_1_to_5`,
`test_property_is_unique_texts_true_iff_no_duplicates_among_nonempty`) entran en el alcance de
preservación como cualquier otro nodo y deben seguir pasando sin cambios.

**Plan de verificación:**

```bash
# 1. Suite de alcance completa: 0 failed y 2580 recolectados
venv/bin/python -m pytest tests/v2/unit -q

# 2. Diferencia nodo por nodo contra el baseline: solo deben aparecer los 12
#    nodos parametrizados sustituyendo a los 6 originales
venv/bin/python -m pytest tests/v2/unit --collect-only -q | sort > /tmp/after_nodes.txt
diff /tmp/baseline_nodes.txt /tmp/after_nodes.txt

# 3. Los otros cuatro casos de uso de pre-check, intactos (3.5)
venv/bin/python -m pytest \
  tests/v2/unit/use_cases/test_facebook_save_pre_check_ctas.py \
  tests/v2/unit/use_cases/test_facebook_save_pre_check_budget.py \
  tests/v2/unit/use_cases/test_facebook_save_pre_check_proposal_url.py \
  tests/v2/unit/use_cases/test_facebook_save_pre_check_locations.py -q

# 4. Las tres suites con referencias a _build_response en otras clases o dobles (3.6)
venv/bin/python -m pytest \
  tests/v2/unit/use_cases/test_facebook_launch_campaign.py \
  tests/v2/unit/use_cases/test_facebook_get_launch_campaign_creatives.py \
  tests/v2/unit/use_cases/test_funnel_flow_validator.py -q

# 5. Las clases que aseveran el ''' del constructor siguen pasando (3.4)
venv/bin/python -m pytest \
  tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py \
  tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py \
  -q -k "UnsupportedMetaCampaignMode"

# 6. El código productivo no cambió (2.9)
git diff --stat -- app/    # debe ser vacío
git status --porcelain -- app/   # debe ser vacío
```

**Casos de preservación concretos a observar** (todos pasan hoy; se verifica que siguen pasando):

1. **Los ocho invocadores directos DYNAMIC** (I1, I2, I4, I5, T1, T2, T4, T5): pasan hoy con
   `creative_type == ''` y deben seguir pasando con `'DYNAMIC'` explícito, con sus aserciones
   literalmente intactas. Es la comprobación más directa de que la asignación manual es un no-op
   observable para la rama DYNAMIC.
2. **Los cuatro nodos que atraviesan `execute()`** (`..._images.py:3153`, `3223`, `..._texts.py:4487`,
   y el recorrido STANDARD de imágenes): siguen obteniendo el modo vía `_set_creative_type`, sin
   fijación manual (3.3).
3. **`TestUnsupportedMetaCampaignModeRaisesValueError`** en ambos archivos: sigue aseverando el
   mensaje exacto de `CreativeType` y `use_case.creative_type == ""` (3.4).
4. **Aislamiento**: ningún nodo dispara `deny_network`; los repositorios siguen sustituidos por
   dobles y `redis_client` parcheado (3.8). Una fuga se manifestaría como
   `AssertionError: Network access is forbidden in this unit test suite`.
5. **Identidad por referencia**: los nodos que aseveran que el mismo objeto `creative` fluye hacia
   `_save_creative_to_publish` y `_build_response`, y los que cuentan instanciaciones de
   repositorios, siguen cumpliéndose sin cambios (3.9).
6. **Tiempo de ejecución**: `tests/v2/unit` se mantiene en el orden de 51–53 s (3.11).

**Fuera de alcance, comportamiento sin cambios (3.10):** no se ejecutan `tests/v2` ni `tests/`
completos como criterio de aceptación, porque arrastran fallos preexistentes y ajenos
(`test_pin_format_ad_variant_integration.py::…::test_end_to_end_pin_format_workflow_persists_pinned_state`
y los fallos y errores de `tests/v1/`). Si se ejecutan, deben comportarse exactamente igual que
hoy: ni corregidos ni agravados.

### Unit Tests

No se añaden casos de prueba nuevos: los seis casos parametrizados y el caso de la tabla de mapeo
cubren el despacho por ambas ramas. Los 12 nodos resultantes de la parametrización sí **amplían** la
cobertura efectiva en un punto concreto: la rama STANDARD de `_build_response` pasa a estar
ejercitada en `test_facebook_save_pre_check_texts.py`, que hoy no la ejercita en absoluto porque ese
caso de uso nunca puebla `object_story_spec`.

### Property-Based Tests

No se introducen. El dominio de verificación de este bugfix es el conjunto finito y enumerable de
nodos de pytest, y la comparación nodo por nodo del apartado anterior es exhaustiva sobre ese
dominio, por lo que una generación aleatoria no aportaría garantía adicional. Las propiedades
Hypothesis existentes en las dos suites se preservan sin modificación y entran en el alcance de
Preservation Checking.

### Integration Tests

No se añaden ni se modifican. `tests/v2/integration` queda fuera del alcance de referencia y su
fallo preexistente debe comportarse igual que hoy (3.10). La cobertura del recorrido completo de
`execute()` en ambos modos ya existe dentro de los dos archivos objetivo
(`test_execute_dynamic_branch_response_reflects_images_mutated_by_validate_images_dynamic`,
`test_execute_standard_branch_response_contains_expected_keys_and_reflects_validated_image`,
`test_full_execute_dynamic_scenario_response_reflects_mutated_asset_feed`) y se preserva intacta.
