# Meta Ads Unit Tests Sync Fix Bugfix Design

## Overview

Dos commits de HL-2671 cambiaron el contrato observable de `sinergia/app/v2/use_cases/meta_ads.py` sin actualizar las suites unitarias:

- `99a93414`: `FacebookGetLaunchCampaignCreativesUseCase._build_result` añade `'conversion_event': setup_attributes.get('meta_conversion_event')` como séptima clave del bloque `campaign`, después de `'mode'` (verificado en `meta_ads.py:5363-5369`).
- `7ef9a47d`: `FacebookLaunchCampaignUseCase._build_leads_offsite_tracking_specs` devuelve `[{"action.type": ["offsite_conversion"], "fb_pixel": [self.pixel_id]}]` (verificado en `meta_ads.py:3184-3186`).

La ejecución actual de las dos suites confirma 16 fallos y 969 tests en verde (`venv/bin/python -m pytest` desde `sinergia/`). La lista coincide exactamente con la de bugfix.md (1.1–1.6).

La estrategia es mínima y se limita a los tests. El código de producción es la fuente de verdad y no se toca. Solo cambian constantes, helpers de expectativa, aserciones, nombres de test y documentación dentro de:

- `sinergia/tests/v2/unit/use_cases/test_facebook_get_launch_campaign_creatives.py`
- `sinergia/tests/v2/unit/use_cases/test_facebook_launch_campaign.py`

## Glossary

- **Bug_Condition (C)**: un test de las suites afectadas cuya aserción o documentación codifica el contrato anterior a HL-2671: bloque `campaign` de seis claves, conjuntos de atributos leídos sin `meta_conversion_event`, o `tracking_specs` con clave `"dataset"`.
- **Property (P)**: el test afirma exactamente el contrato actual de producción (siete claves en orden, `meta_conversion_event` entre los atributos leídos, `"fb_pixel": [pixel]`) y conserva su intención original.
- **Preservation**: todo test que no cumple C sigue igual (mismo id de pytest, mismas aserciones, mismo resultado). El código bajo `sinergia/app/v2/` no cambia.
- **F / F'**: la suite antes y después del fix. El código bajo prueba es idéntico en ambos casos.
- **Campaign_Setup**: registro `campaign-channel-publishes` construido por `make_campaign_setup` (`test_facebook_get_launch_campaign_creatives.py:540`).
- **Resultado_de_Consulta**: diccionario `{'campaign', 'creatives', 'meta_url'}` devuelto por `FacebookGetLaunchCampaignCreativesUseCase`.
- **Combinación_Leads_Offsite**: `OUTCOME_LEADS` + `OFFSITE_CONVERSIONS`.
- **Payload_Ad**: cuerpo del POST a `/ads` construido por `_publish_ad`.
- **`CAMPAIGN_BLOCK_KEYS`**: tupla congelada con el orden de claves del bloque `campaign` (línea 5082).
- **`_expected_campaign_block`**: helper que construye el bloque esperado para los fixtures canónicos (línea 5114).
- **`SETUP_ATTRIBUTES_READ_END_TO_END`**: conjunto de atributos que lee todo el flujo `execute()` (línea 6548).
- **`_RecordingDict`**: dict que registra cada clave consultada en `consulted_keys`, incluidas las lecturas con `.get` de claves ausentes (línea 1947).
- **`_merge`**: helper que aplica `**attribute_overrides` sobre el nodo `attributes` (línea 147).

## Bug Details

### Bug Condition

El bug aparece cuando un test compara el resultado real del caso de uso contra una expectativa escrita para el contrato previo. Hay tres variantes: igualdad exacta del bloque `campaign` (falta `conversion_event`), igualdad exacta del conjunto de atributos consultados (falta `meta_conversion_event`) e igualdad exacta de `tracking_specs` (clave `"dataset"` en lugar de `"fb_pixel"`). La variante documental (1.7) afecta a nombres, docstrings y comentarios que describen el contrato anterior sin provocar fallos.

**Formal Specification:**
```
FUNCTION isBugCondition(test)
  INPUT: test of type PytestCase  (función de test, parametrización incluida, o su documentación)
  OUTPUT: boolean

  RETURN test.file IN [test_facebook_get_launch_campaign_creatives.py,
                       test_facebook_launch_campaign.py]
         AND (
              test.expects(campaign_block_keys) = 6 claves sin 'conversion_event'
           OR test.expects(consulted_setup_attributes) no contiene 'meta_conversion_event'
              mientras producción sí lo consulta
           OR test.expects(tracking_specs) = [{"action.type": [...], "dataset": [pixel]}]
           OR test.name/docstring/comentario describe "six keys", "three keys",
              "three remaining keys", "five/six attributes" o "dataset": [pixel]
         )
END FUNCTION
```

### Examples

- `TestResultComposition::test_campaign_block_equals_the_six_keys_derived_from_the_fixtures`: espera `{name, channel_name, creatives_no, objective, optimization_goal, mode}` y recibe además `'conversion_event': None`. Falla la igualdad de dict.
- `TestResultComposition::test_absent_setup_attributes_yield_none_in_the_three_keys`: `tuple(keys) == CAMPAIGN_BLOCK_KEYS` falla porque el resultado tiene siete claves.
- `TestMetaUrl::test_meta_resources_is_never_read_end_to_end`: `set(consulted_keys)` incluye `'meta_conversion_event'`, que no está en `SETUP_ATTRIBUTES_READ_END_TO_END`.
- `TestLeadsOffsiteAdPayload::test_tracking_specs_only_for_leads_offsite`: Hypothesis reduce a `pixel='0'`. Se esperaba `[{"action.type": ["offsite_conversion"], "dataset": ["0"]}]` y se obtiene `[{"action.type": ["offsite_conversion"], "fb_pixel": ["0"]}]`.
- `TestLeadsOffsiteLaunchRollback::test_happy_path_publishes_website_adset_and_tracked_ads[DYNAMIC]`: mismo desajuste con `"pixel-123"`.
- Caso límite, Campaign_Setup sin `attributes`: producción compone `conversion_event = None`. El test actual no lo afirma, y el fix debe añadir esa aserción (2.2).

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Código de producción bajo `sinergia/app/v2/` sin cambios (3.1).
- Los 2875 tests que pasan hoy siguen pasando. El total de la suite unitaria queda en 2891 y los fallos en 0 (3.2).
- Se sigue afirmando que `'meta_resources'` está en el fixture y no se consulta (3.3).
- Comparación por igualdad exacta de dict y de orden de claves. Siguen vigentes las comprobaciones de `channel_name == 'Meta'`, `creatives_no`, `name` y las tres claves originales del Campaign_Setup (3.4).
- Fuera de la Combinación_Leads_Offsite, el Payload_Ad no contiene `tracking_specs` y conserva `name`, `adset_id`, `creative`, `status` y `access_token` (3.5).
- `@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])` y las estrategias `@given` de Property 14 no cambian (3.6).
- `TestLeadsOffsiteLaunchRollback` sigue verificando el adset WEBSITE, el orden de llamadas y el rollback (3.7).
- `deny_network`, `TestSuiteSelfAudit` y `TestBuildersIndependence` siguen activos y en verde (3.8).
- Los ids de pytest que ya describen bien el contrato no cambian, incluidos los de `parametrize` (`DYNAMIC`, `STANDARD`, `one-creative`, `two-creatives`, `four-creatives`) (3.9).
- Los tests renombrados conservan clase, fixtures, intención y su línea `Requirements:` (3.10, 2.10).

**Scope:**
Todo test que no cumple isBugCondition queda intacto. Esto incluye:
- El resto de clases de ambas suites (constructor, repositorio de ad-sets, `_as_list`, entradas de creativos, Properties 1–3, 13 y 15, etc.).
- `make_campaign_setup` en su firma y comportamiento. Solo cambia su docstring.
- Cualquier otro archivo de tests, `conftest.py`, CI, `Makefile` y las demás specs.

## Hypothesized Root Cause

La causa está confirmada por inspección del código y por la ejecución actual:

1. **Expectativas congeladas del bloque `campaign`**: `CAMPAIGN_BLOCK_KEYS` (líneas 5078-5089) y `_expected_campaign_block` (líneas 5114-5133) codifican seis claves. Además, `TestCampaignBlock::test_campaign_block_equals_the_six_keys_derived_from_the_fixtures` afirma `len(result['campaign']) == 6` (línea 6581). Esto explica los 11 fallos de 1.1 y 1.2.

2. **Conjuntos de atributos leídos sin `meta_conversion_event`**: el literal de `TestResultComposition::test_meta_resources_is_never_read` (líneas 5437-5443) y `SETUP_ATTRIBUTES_READ_END_TO_END` (líneas 6548-6555) no incluyen la nueva lectura. `_RecordingDict` registra la llamada `.get('meta_conversion_event')` aunque el fixture no tenga la clave. Esto explica 1.3 y 1.4.

3. **Literal `"dataset"` en `tracking_specs`**: `test_facebook_launch_campaign.py:3223` (Property 14) y `:3562` (happy path del rollback) mantienen la clave anterior. Esto explica 1.5 y 1.6.

4. **Documentación desfasada**: el docstring de `make_campaign_setup` (línea 552) habla de "six attributes". El comentario de `CAMPAIGN_BLOCK_KEYS` (línea 5078) y el docstring de `_expected_campaign_block` (línea 5119) hablan de "six keys". También quedan desfasados los comentarios de sección (5221, 6565, 6700), los docstrings de las líneas 5224, 5242-5243, 5336-5337, 5425, 6569, 6588, 6704-6707, 6745-6746 ("three ``None`` values") y 6866, y el comentario de la constante en 6544-6547. En la suite de lanzamiento, la etiqueta `# Feature: ... Property 14` (línea 3155) sigue describiendo `"dataset": [pixel]`. Esto explica 1.7.

## Correctness Properties

Property 1: Bug Condition - Las suites afirman el contrato actual de HL-2671

_For any_ test de las suites afectadas donde isBugCondition es verdadero, el test corregido SHALL afirmar exactamente el contrato actual de producción. Eso significa: un bloque `campaign` de siete claves en el orden `name`, `channel_name`, `creatives_no`, `objective`, `optimization_goal`, `mode`, `conversion_event`, con `conversion_event` igual al `meta_conversion_event` del Campaign_Setup (o `None` si falta); conjuntos de atributos consultados que incluyen `meta_conversion_event`; y, para todo `pixel` en la Combinación_Leads_Offsite, `tracking_specs == [{"action.type": ["offsite_conversion"], "fb_pixel": [pixel]}]`. Además, nombres y documentación SHALL describir ese contrato y el test SHALL pasar contra el código de producción sin modificar.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10**

Property 2: Preservation - Los tests no afectados y la producción no cambian

_For any_ test donde isBugCondition es falso, la suite corregida SHALL producir el mismo resultado que la suite original, con el mismo id de pytest y las mismas aserciones. Se conservan las comprobaciones de `meta_resources`, la ausencia de `tracking_specs` fuera de la Combinación_Leads_Offsite, la configuración de Hypothesis, las auditorías (`TestSuiteSelfAudit`, `TestBuildersIndependence`), `deny_network` y el código bajo `sinergia/app/v2/`. La suite unitaria completa termina con 2891 tests y 0 fallos.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10**

## Fix Implementation

### Changes Required

Los números de línea son los verificados en el estado actual de los archivos.

**File**: `sinergia/tests/v2/unit/use_cases/test_facebook_get_launch_campaign_creatives.py`

**Specific Changes**:
1. **`CAMPAIGN_BLOCK_KEYS` (líneas 5078-5089)**: añadir `'conversion_event'` al final de la tupla y cambiar el comentario a "The seven keys of the ``campaign`` block...".

2. **`_expected_campaign_block` (líneas 5114-5133)**: añadir el parámetro `conversion_event=None` después de `mode` y la entrada `'conversion_event': conversion_event` al final del dict. El docstring pasa a hablar de siete claves. El valor por defecto `None` refleja que el `make_campaign_setup()` canónico no declara `meta_conversion_event`. Así, los tests de 1.1 que no lo sobrescriben (`test_the_block_is_the_same_in_both_modes_except_for_the_mode_key[*]`, `test_creatives_no_follows_the_size_of_the_fixture[*]`, `test_name_is_the_name_attribute_of_the_resolved_campaign`) pasan sin tocar su cuerpo.

3. **`TestResultComposition`**:
   - Línea 5221: el comentario de sección pasa a `# -- The ``campaign`` block of seven keys (Requirement 7.3) ---`.
   - Línea 5223: renombrar `test_campaign_block_equals_the_six_keys_derived_from_the_fixtures` a `test_campaign_block_equals_the_seven_keys_derived_from_the_fixtures` y poner "seven-key dict" en el docstring.
   - Línea 5240, `test_campaign_block_reflects_the_values_of_a_non_canonical_fixture` (2.8): pasar `meta_conversion_event='LEAD'` a `make_campaign_setup` (llega por `**attribute_overrides` y `_merge`) y `conversion_event='LEAD'` a `_expected_campaign_block`. Añadir `assert result['campaign']['conversion_event'] == 'LEAD'`. El docstring menciona las cuatro claves del Campaign_Setup.
   - Línea 5334: renombrar `test_absent_setup_attributes_yield_none_in_the_three_keys` a `test_absent_setup_attributes_yield_none_in_the_four_keys`. Añadir `assert result['campaign']['conversion_event'] is None`. El docstring dice "four keys" y "seven keys of the block".
   - Línea 5423, `test_meta_resources_is_never_read`: añadir `'meta_conversion_event'` al conjunto esperado, que queda en `{'meta_campaign_objective', 'meta_optimization_goal', 'meta_campaign_mode', 'meta_conversion_event', 'meta_account_id', 'meta_campaign_id'}`. El docstring pasa a "six attributes". La aserción sobre `'meta_resources'` no cambia.

4. **`SETUP_ATTRIBUTES_READ_END_TO_END` (líneas 6544-6555)**: añadir `'meta_conversion_event'`. El comentario pasa a "seven attribute names" y menciona `meta_conversion_event` para la clave `conversion_event`.

5. **`TestCampaignBlock`**:
   - Línea 6565: el comentario de sección pasa a "Exact equality of the seven keys".
   - Línea 6567: renombrar a `test_campaign_block_equals_the_seven_keys_derived_from_the_fixtures`, poner "seven-key dict" en el docstring y cambiar `len(result['campaign']) == 6` por `== 7` (línea 6581).
   - Línea 6588: en el docstring de `test_the_block_is_the_same_in_both_modes_except_for_the_mode_key`, "six keys" pasa a "seven keys". El nombre se mantiene.
   - Línea 6700: el comentario de sección pasa a "The four keys of the Campaign_Setup".
   - Línea 6702: renombrar `test_the_three_remaining_keys_come_from_the_campaign_setup` a `test_the_four_remaining_keys_come_from_the_campaign_setup` (2.8). Añadir `meta_conversion_event='LEAD'` al `make_campaign_setup(...)`, `conversion_event='LEAD'` a `_expected_campaign_block(...)` y `assert result['campaign']['conversion_event'] == 'LEAD'`. El docstring enumera las cuatro claves. El caso de uso de creativos no valida `meta_conversion_event` (en esa clase solo se lee en `meta_ads.py:5368`), así que `'LEAD'` con `OUTCOME_SALES` no altera el flujo.
   - Líneas 6745-6746: en el docstring de `test_absent_setup_attributes_would_not_reach_the_block`, "three ``None`` values" pasa a "four ``None`` values". Solo cambia el docstring.

6. **`TestMetaUrl::test_meta_resources_is_never_read_end_to_end` (línea 6864)**: en el docstring, "six attributes" pasa a "seven attributes". La aserción no cambia porque usa la constante del punto 4.

7. **Docstring de `make_campaign_setup` (líneas 552-556)**: enumerar los siete atributos que lee el caso de uso, añadiendo `meta_conversion_event`. Debe indicar que el fixture canónico no lo incluye (y por eso el valor esperado es `None`) y que se inyecta con `**attribute_overrides`. La firma y el cuerpo no cambian, así que `TestBuildersIndependence` no se ve afectado.

**File**: `sinergia/tests/v2/unit/use_cases/test_facebook_launch_campaign.py`

8. **Etiqueta Property 14 (línea 3155)**: cambiar `"dataset": [pixel]` por `"fb_pixel": [pixel]` en el comentario `# Feature: meta-ads-leads-offsite-conversions, Property 14: ...`. El resto del texto se mantiene.

9. **`TestLeadsOffsiteAdPayload::test_tracking_specs_only_for_leads_offsite` (línea 3223)**: el literal esperado pasa a `{"action.type": ["offsite_conversion"], "fb_pixel": [pixel]}`, dentro de una lista de un único elemento. No cambian `@settings`, `@given`, la rama `else` ni la comprobación de `set(payload)`.

10. **`TestLeadsOffsiteLaunchRollback::test_happy_path_publishes_website_adset_and_tracked_ads` (línea 3562)**: el literal esperado pasa a `{"action.type": ["offsite_conversion"], "fb_pixel": [_LO_PIXEL_ID]}`. La comparación por igualdad de lista garantiza una sola entrada sin clave `"dataset"`. En esta suite no se renombra nada (2.9).

**Fuera de alcance:** `sinergia/app/v2/**`, `conftest.py`, otras suites y specs, CI y `Makefile`. Los renombrados no requieren cambios externos: `TestSuiteSelfAudit` descubre los casos por AST y por la línea `Requirements:` del docstring (`_suite_test_cases`, `REQUIREMENT_REFERENCE`). Cada test renombrado conserva su línea `Requirements: ...` (`7.3` en `TestResultComposition`, `7.3, 11.8` en `TestCampaignBlock`).

## Testing Strategy

### Validation Approach

Como el defecto está en los tests, el "código sin corregir" es la suite actual y el "código corregido" es la suite modificada. Producción es idéntica en ambos casos. Primero se confirma que los 16 fallos se deben solo a las expectativas desfasadas. Después se aplica el fix y se comprueba el total de la suite completa.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples on the UNFIXED suite and confirm the root cause.

**Test Plan**: ejecutar desde `sinergia/`:

```
venv/bin/python -m pytest tests/v2/unit/use_cases/test_facebook_get_launch_campaign_creatives.py tests/v2/unit/use_cases/test_facebook_launch_campaign.py -q
```

Ya ejecutado durante este diseño: 16 failed, 969 passed. La lista coincide con 1.1–1.6.

**Test Cases**:
1. **Bloque de seis claves**: `TestResultComposition::test_campaign_block_equals_the_six_keys_derived_from_the_fixtures` (falla en la suite actual; diff = `'conversion_event': None`).
2. **Atributos leídos**: `TestMetaUrl::test_meta_resources_is_never_read_end_to_end` (falla en la suite actual; sobra `'meta_conversion_event'`).
3. **Property 14**: `TestLeadsOffsiteAdPayload::test_tracking_specs_only_for_leads_offsite` (falla en la suite actual; contraejemplo mínimo `pixel='0'`).
4. **Happy path del rollback**: `TestLeadsOffsiteLaunchRollback::test_happy_path_publishes_website_adset_and_tracked_ads[DYNAMIC|STANDARD]` (falla en la suite actual).

**Expected Counterexamples**:
- Diff de dict con una clave extra `conversion_event`, diff de conjunto con `meta_conversion_event` y diff de clave `dataset` frente a `fb_pixel`.
- Ninguno apunta a un cambio de producción distinto de los commits `99a93414` y `7ef9a47d`, lo que confirma la causa raíz.

### Fix Checking

**Goal**: Verify that every test in C passes against unmodified production and asserts the new contract.

**Pseudocode:**
```
FOR ALL test WHERE isBugCondition(test) DO
  result := run_pytest(test_fixed)
  ASSERT result = PASSED
  ASSERT test_fixed afirma 7 claves / meta_conversion_event / "fb_pixel"
END FOR
```

### Preservation Checking

**Goal**: Verify that every test outside C keeps its id and result.

**Pseudocode:**
```
FOR ALL test WHERE NOT isBugCondition(test) DO
  ASSERT run_pytest(test_original) = run_pytest(test_fixed) = PASSED
  ASSERT id(test_original) = id(test_fixed)
END FOR
ASSERT git diff --stat sinergia/app/v2/ = vacío
```

**Testing Approach**: Property 14 sigue siendo un test property-based con Hypothesis (100 ejemplos por combinación y píxel) y cubre a la vez la corrección (Leads_Offsite → `fb_pixel`) y la preservación (otras combinaciones → sin `tracking_specs`). Para el resto, la preservación se comprueba con la suite completa, que ejecuta todo el dominio de tests existentes.

**Test Plan**: guardar la lista de ids que pasan antes del fix (`--co -q` más el resultado actual). Tras el fix, comprobar que es la misma salvo los cuatro renombrados de 2.9.

**Test Cases**:
1. **Rama no Leads_Offsite de Property 14**: sigue afirmando la ausencia de `tracking_specs` y el conjunto de cinco claves del payload.
2. **Auditorías**: `TestSuiteSelfAudit` y `TestBuildersIndependence` en verde tras los renombrados y el cambio de docstrings.
3. **`meta_resources`**: `'meta_resources' in dict(attributes)` y `not in consulted_keys` en ambos tests.
4. **Ids de `parametrize`**: `DYNAMIC`, `STANDARD`, `one-creative`, `two-creatives` y `four-creatives` sin cambios.

### Unit Tests

- Ejecutar las dos suites afectadas: 0 fallos y 985 tests, el mismo total que antes.
- Ejecutar por nombre los cuatro tests renombrados (`-k "seven_keys or four_keys or four_remaining_keys"`) y comprobar que existen y pasan.
- Comprobar que ningún nombre de test conserva "six_keys", "three_keys" ni "three_remaining" (`--co -q | grep`), y que no queda `"dataset"` en `test_facebook_launch_campaign.py`.

### Property-Based Tests

- `TestLeadsOffsiteAdPayload::test_tracking_specs_only_for_leads_offsite` con su configuración actual (`max_examples=100`, `deadline=None`, `suppress_health_check=[HealthCheck.function_scoped_fixture]`): para todo `pixel` generado en la Combinación_Leads_Offsite, `tracking_specs == [{"action.type": ["offsite_conversion"], "fb_pixel": [pixel]}]`; para el resto, ausencia de `tracking_specs`.
- Las demás propiedades Hypothesis de la suite de lanzamiento (Properties 1–3, 13 y 15) se ejecutan sin cambios como parte de la preservación.

### Integration Tests

- Suite unitaria completa desde `sinergia/` con `venv/bin/python -m pytest`: 2891 tests, 0 fallos, sin skips nuevos y con `deny_network` activo.
- Los tests de `TestCampaignBlock` y `TestMetaUrl` recorren el flujo `execute()` completo con dobles de repositorio. Validan de punta a punta el bloque de siete claves y el conjunto de siete atributos leídos.
- `TestLeadsOffsiteLaunchRollback` recorre `execute()` con `_publish_adset`, `_publish_ad_creative` y `_publish_ad` reales. Valida `tracking_specs` con `fb_pixel` en el flujo de lanzamiento y el resto de comprobaciones del adset y del rollback.
