# Implementation Plan: edit-ad-variant-image-use-case

## Overview

Implementación incremental en Python 3.8 dentro de `sinergia/`, siguiendo `design.md`: primero las constantes y los helpers privados `_edit_image_*` en `app/v2/use_cases/ad.py`, después la clase `EditAdVariantImageUseCase`, luego el Unit_Test_Suite en un único archivo y, por último, el modelo Swagger `EditAdVariantImageStruct` y el recurso `HilucaResourceAdChannelMediaImageEdit` en `app/v2/resources/ad.py`, que conectan el caso de uso con la ruta HTTP.

No se crean repositorios ni métodos de repositorio, y no se modifican `FuryClient` ni las excepciones.

Todos los comandos se ejecutan desde `sinergia/`:

- Pruebas: `venv/bin/python -m pytest tests/v2/unit/use_cases/test_edit_ad_variant_image_use_case.py -q`
- Importación del caso de uso (Req 2.5): `venv/bin/python -c "import app.v2.use_cases.ad"`
- Importación del recurso: `venv/bin/python -c "import app.v2.resources.ad"`

`pytest-mock==3.14.0` e `hypothesis==6.112.2` ya están fijados en `requirements-test.txt` (Req 10.1). No requieren tarea; como mucho, verificar con `venv/bin/python -m pip show pytest-mock hypothesis`.

## Tasks

- [x] 1. Implementar el caso de uso en `sinergia/app/v2/use_cases/ad.py`
  - [x] 1.1 Añadir imports, constantes de módulo y helpers privados `_edit_image_*`
    - Ampliar el import de `app.exceptions.base` con `IncorrectValidationException`, `FuryException` y `SinergiaException`, y añadir `from typing import Any, Dict, List, Optional`; reutilizar `logger`, `logging.basicConfig`, `AccountRepository`, `CampaignRepository`, `AdChannelRepository`, `FuryClient`, `DataNotFoundException` y `ParametersNotFoundException` ya importados (sin duplicarlos)
    - Declarar tras `logger = logging.getLogger(__name__)` las constantes `EDIT_IMAGE_FURY_ENDPOINT`, `EDIT_IMAGE_ID_FIELDS`, `EDIT_IMAGE_STRING_FIELDS`, `EDIT_IMAGE_REQUIRED_FIELDS` (orden del Glosario), `EDIT_IMAGE_EXPAND_ZOOM_OPTIONS`, `EDIT_IMAGE_MIN_ID`, `EDIT_IMAGE_MIN_VARIATIONS`, `EDIT_IMAGE_MAX_VARIATIONS`, `EDIT_IMAGE_MAX_STRING_LENGTH` y `EDIT_IMAGE_MAX_PROMPT_LENGTH` (sección 1 del diseño)
    - `_edit_image_fail(exc)`: un único `logger.error(exc.text)` y devuelve `exc` para `raise` (D3)
    - `_edit_image_is_missing`, `_edit_image_is_valid_int` (`int` y no `bool`, D4) y `_edit_image_normalize_prompt`
    - `_edit_image_check_presence(payload)`: `Payload is required` si no es `dict`; `<campo> is required` para el primer campo de `EDIT_IMAGE_REQUIRED_FIELDS` con Missing_Value (D2)
    - `_edit_image_validate(payload)`: criterios 4.1–4.6 en el orden del Req 4.7 (IDs, `image_name`, `image_id`, `n_variations`, `custom_prompt`, `expand_zoom_option`, regla combinada), con textos construidos a partir de las constantes; `isinstance(v, str)` antes de `in` para `expand_zoom_option`; devuelve el diccionario de valores normalizados (D5)
    - `_edit_image_parent_account_id(account)`: resolución tolerante sin `KeyError`/`TypeError`
    - `_edit_image_has_banner_image(ad_variant, image_id)`: Banner_Images defensivas, igualdad exacta `==` sin conversión de tipos, omite elementos no `dict` o sin `image_id`
    - `_edit_image_build_fury_payload(values)`: exactamente las 10 claves, con `id_base_image = values['image_id']` y sin `image_id`
    - `_edit_image_extract_job_id(response)`: `data.edit_job_id` sin modificar si es `str` con `strip() != ""`; si no, `raise _edit_image_fail(FuryException('Fury response does not contain edit_job_id'))`
    - Solo sintaxis y anotaciones compatibles con Python 3.8 (sin `dict[...]`, `list[...]` ni `|`)
    - _Requirements: 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.9, 5.3, 8.1, 8.2, 8.3, 9.2, 9.3, 9.4, 9.7_

  - [x] 1.2 Implementar la clase `EditAdVariantImageUseCase`
    - `__init__(self, user_id: str)` guarda `self.user_id` y crea una instancia de cada colaborador: `self.account_repo`, `self.campaign_repo`, `self.ad_channel_repo` y `self.fury_client`; sin `AdRepository`, `BrandRepository` ni otros clientes
    - `execute(self, payload: Dict[str, Any]) -> Dict[str, str]` como único método público, orquestando según la sección 3 del diseño: presencia → validación → `get_by_email(self.user_id)` → Parent_Account → `get_by_id_brand_and_account(campaign_id, brand_id, parent_account_id)` → `get_by_id_ad_campaign_and_channel(variant_id, ad_id, campaign_id, channel_id)` → banner → payload de Fury
    - Resultados falsy → `raise _edit_image_fail(DataNotFoundException(...))` con `Account not found`, `Campaign not found or does not belong to account`, `Ad variant not found` e `Image not found in ad variant`
    - Excepciones de los repositorios sin capturar (misma instancia)
    - Un único `logger.info` antes de `post` con `variant_id`, `image_id` recortado, `n_variations`, `expand_zoom_option` y la longitud del prompt (`0` si es `None`), nunca su texto
    - `try/except` acotado a `self.fury_client.post(EDIT_IMAGE_FURY_ENDPOINT, fury_edit_payload)` (D7): `except SinergiaException: raise`; `except Exception as e: raise _edit_image_fail(FuryException('Failed to enqueue image edit job in Fury')) from e`
    - Devolver `{'job_id': _edit_image_extract_job_id(response)}`, fuera del `try`
    - Verificar con `venv/bin/python -c "import app.v2.use_cases.ad"`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 4.8, 5.1, 5.2, 5.4, 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3, 8.4, 9.1, 9.4, 9.5, 9.6, 9.8_

- [x] 2. Escribir el Unit_Test_Suite en `sinergia/tests/v2/unit/use_cases/test_edit_ad_variant_image_use_case.py`
  - Archivo único, sin `conftest.py` ni fixtures fuera de él; todas las funciones de prueba con `-> None` (Req 10.1, 10.4)
  - Las pruebas de error comprueban la clase, el `code` y el texto exacto de la excepción; las de propagación, que es la misma instancia (`excinfo.value is original`)
  - Pruebas de propiedad con `hypothesis` y `@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])`, reiniciando los mocks en cada ejemplo con `reset_mock()`; cada una lleva el comentario `# Feature: edit-ad-variant-image-use-case, Property {n}: {texto}`

  - [x] 2.1 Crear el archivo con la fixture, los helpers y las pruebas de constructor y camino feliz
    - Fixture `collaborators(mocker)` que parchea `app.v2.use_cases.ad.AccountRepository`, `CampaignRepository`, `AdChannelRepository`, `FuryClient` y `logger` con los valores de éxito por defecto de la sección "Aislamiento" del diseño (Req 10.2)
    - Constante `VALID_PAYLOAD`, centinela `MISSING`, helper `_payload(**overrides)` y helper `_assert_not_called_after(step, collaborators)` (Req 10.10)
    - `test_init_stores_user_id_and_instantiates_collaborators_once`: `self.user_id`, las 4 clases con `assert_called_once_with()`, siguen con `call_count == 1` tras `execute` y `get_by_email.assert_called_once_with(user_id)` (Req 10.14)
    - `test_happy_path_returns_job_id_and_posts_expected_payload`: resultado `== {'job_id': 'job-1'}` y `post.assert_called_once_with('/api/v2/variants/image/edit', expected)` con `expected` literal de 10 claves, `id_base_image` presente e `image_id` ausente (Req 10.5)
    - _Requirements: 2.2, 2.3, 5.1, 9.1, 9.2, 9.3, 9.4, 10.1, 10.2, 10.4, 10.5, 10.14_

  - [x] 2.2 Escribir las pruebas de ejemplo de presencia, valores y límites válidos
    - `test_missing_required_field_raises_parameters_not_found` parametrizada sobre las 8 Required_Fields × {`None`, `""`, `"   "`, `MISSING`}, y `test_non_dict_payload_raises_parameters_not_found` con `None`, `[]` y `"x"`; código `PAR001`, texto exacto y `_assert_not_called_after('validation', ...)` (Req 10.6)
    - `test_invalid_value_raises_incorrect_validation` parametrizada con la lista exacta del Req 10.7 (5 ID_Fields × {`0`, `-1`, `True`, `1.0`, `"5"`}; `n_variations` {`0`, `11`, `True`, `"5"`}; 256 caracteres tras recortar y `123` para `image_name`/`image_id`; 2001 caracteres tras recortar y `123` para `custom_prompt`; `"top"`, `"ZOOM_3X"`, `" TOP"`, `""` para `expand_zoom_option`; `custom_prompt` {`None`, `""`, `"   "`} sin option); código `SYSVAL001`, texto exacto y cero invocaciones de colaboradores (Req 10.7, 10.10)
    - `test_valid_boundary_values_return_job_id` parametrizada: IDs `1`; `n_variations` `1` y `10`; `image_name`/`image_id` de 255 caracteres con espacios alrededor (banner configurado con el valor recortado); `custom_prompt` de 2000 tras recortar; cada uno de los 7 ExpandZoomOption_Values (Req 10.8)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.8, 10.6, 10.7, 10.8, 10.10_

  - [x] 2.3 Escribir la prueba de propiedad `test_property_valid_payload_maps_to_fury_payload`
    - **Property 1: Invariante de mapeo del Edit_Payload válido**
    - Generadores de la tabla de la Propiedad 1 del diseño (IDs `st.integers(1, 10**9)`, `n_variations` `st.integers(1, 10)`, textos con padding de espacios, `custom_prompt`/`expand_zoom_option` con `assume` de al menos uno, claves extra que no colisionen); banner configurado con el `image_id` recortado en cada ejemplo
    - Comprobar argumentos de los dos lookups, una llamada a `post` con exactamente 10 claves, `id_base_image == image_id.strip()`, `custom_prompt` normalizado, sin `image_id`, y que ningún argumento de `logger.info` contiene un `custom_prompt` de ≥ 20 caracteres
    - **Validates: Requirements 4.9, 6.1, 7.1, 9.1, 9.2, 9.3, 9.8 (Req 10.13)**

  - [x] 2.4 Escribir la prueba de propiedad `test_property_missing_required_fields_rejected_in_order`
    - **Property 2: Los parámetros obligatorios ausentes se rechazan en orden y sin acceder a datos**
    - Generadores: `st.sets(st.sampled_from(EDIT_IMAGE_REQUIRED_FIELDS), min_size=1)`; Missing_Value de `st.one_of(st.just(MISSING), st.none(), st.text(alphabet=' \t\n\r\x0b\x0c'))`; opcionalmente valores inválidos en otros campos; rama de `payload` no `dict` (`st.none()`, `st.lists`, `st.text`, `st.integers`)
    - Esperado: `PAR001` con el texto del primer campo ausente en el orden del Glosario y cero invocaciones de los 4 colaboradores
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 4.8**

  - [x] 2.5 Escribir la prueba de propiedad `test_property_invalid_values_rejected_in_order`
    - **Property 3: Los valores inválidos se rechazan en orden y sin acceder a datos**
    - Generadores por campo de valores inválidos presentes (`st.booleans()`, `st.floats()`, `st.integers(max_value=0)`, cadenas numéricas no vacías, textos > 255/2000 tras recortar, `expand_zoom_option` fuera de los 7 valores) y rama "ni prompt ni option"; mensaje esperado calculado con un oráculo que recorre el orden del Req 4.7
    - Esperado: `SYSVAL001` con el texto exacto y cero invocaciones de los 4 colaboradores
    - **Validates: Requirements 3.3, 3.6, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8**

  - [x] 2.6 Escribir las pruebas de ejemplo de cuenta, campaña, variante e imagen
    - Para cada repositorio: `return_value` `None` y `{}` → DataNotFoundException `DAT001` con el texto exacto; `side_effect = StrapiException(...)` → misma instancia (`is`); en todos los casos `_assert_not_called_after(...)` para los pasos posteriores (Req 10.9, 10.10)
    - Imagen: Banner_Images vacía, ausente, `None`, `"x"`, sin coincidencia, `image_id` `5` (int) frente a `"5"`, `attributes` `None` y elementos no `dict` → `Image not found in ad variant` sin `KeyError`/`TypeError` y `post` sin llamadas
    - `test_campaign_lookup_uses_parent_account_id`: `parent_account.data = {'id': 99}` → Campaign_Lookup recibe `99`; `data = None` → recibe `7` (Req 10.11)
    - _Requirements: 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3, 8.1, 8.2, 8.3, 8.4, 10.9, 10.10, 10.11_

  - [x] 2.7 Escribir la prueba de propiedad `test_property_parent_account_resolution`
    - **Property 4: Resolución tolerante de la Parent_Account**
    - Importar `_edit_image_parent_account_id` de `app.v2.use_cases.ad`; generadores con `st.one_of` para `attributes`, `parent_account` y `data` (ausente, `None`, no `dict`, `{}`, con o sin `id`); oráculo explícito
    - **Validates: Requirements 5.3**

  - [x] 2.8 Escribir la prueba de propiedad `test_property_banner_image_lookup_matches_oracle`
    - **Property 5: Búsqueda de imagen equivalente al oráculo**
    - Importar `_edit_image_has_banner_image`; listas de `st.one_of(dicts con image_id str/int, dicts sin image_id, st.integers(), st.text(), st.none())`, formas inválidas de `attributes` y `media_images_banner`, e `image_id` tomado a veces de un elemento existente para forzar coincidencias
    - **Validates: Requirements 8.1, 8.2, 8.3**

  - [x] 2.9 Escribir las pruebas de ejemplo de Fury y de logging
    - `post.side_effect = FuryException('Failed to POST /api/v2/variants/image/edit')` → misma instancia (`is`); `side_effect = RuntimeError()` → FuryException `FURY001` `Failed to enqueue image edit job in Fury` (Req 10.12)
    - Respuestas `None`, `[]`, `{}`, `{'data': {}}`, `{'data': {'edit_job_id': None}}`, `{'data': {'edit_job_id': 123}}`, `{'data': {'edit_job_id': '   '}}` → `Fury response does not contain edit_job_id`; `' abc '` se devuelve sin recortar (Req 10.12, 9.4)
    - `test_own_errors_are_logged_once_before_raising` parametrizada por cada camino de error propio (presencia, valor, cuenta, campaña, variante, imagen, Fury no Sinergia, respuesta sin `edit_job_id`): `logger.error.call_count == 1` y el texto de la excepción en su argumento; en los caminos propagados (repositorios y `FuryException` de `post`), `logger.error.assert_not_called()` (Req 10.15)
    - `test_happy_path_logs_info_without_prompt_text`: con un `custom_prompt` de ≥ 20 caracteres, `logger.info.call_count == 1` y ningún argumento contiene ese texto (Req 10.15)
    - _Requirements: 2.4, 9.4, 9.5, 9.6, 9.7, 9.8, 10.12, 10.15_

  - [x] 2.10 Escribir la prueba de propiedad `test_property_extract_job_id_matches_oracle`
    - **Property 6: Extracción del edit_job_id equivalente al oráculo**
    - Importar `_edit_image_extract_job_id` (con `logger` parcheado); `st.one_of` de no dicts, dicts sin `data`, `data` no `dict` y `edit_job_id` de `st.one_of(st.none(), st.integers(), st.text())`
    - **Validates: Requirements 9.4, 9.7**

- [x] 3. Checkpoint - Ensure all tests pass
  - Ejecutar desde `sinergia/` `venv/bin/python -m pytest tests/v2/unit/use_cases/test_edit_ad_variant_image_use_case.py -q` (0 fallos, 0 errores, 0 omitidas, < 60 s) y `venv/bin/python -c "import app.v2.use_cases.ad"`
  - Ensure all tests pass, ask the user if questions arise.
  - _Requirements: 2.5, 10.3_

- [x] 4. Conectar el endpoint en `sinergia/app/v2/resources/ad.py`
  - [x] 4.1 Añadir el modelo `EditAdVariantImageStruct` y el recurso `HilucaResourceAdChannelMediaImageEdit`
    - Ampliar el import de `app.v2.use_cases.ad` con `EditAdVariantImageUseCase`
    - Modelo `EditAdVariantImageStruct = v2_api.model(...)` tras `UnpinFormatAdVariantStruct`, con `fields.Integer` para los ID_Fields y `n_variations`, `fields.String` para `image_name`, `image_id` y `custom_prompt`, y `expand_zoom_option` como `fields.String(enum=['TOP', 'BOTTOM', 'LEFT', 'RIGHT', 'ZOOM_2X', 'ZOOM_1_5X', 'ZOOM_1_25X'])` (decisión del usuario: se mantiene el enum, solo documentación)
    - Recurso al final del archivo, heredando de `ProxySecureResource`, con `@ad_ns.route('/hiluca/brand/campaign/ad/channel/media/image/edit')` y `@v2_api.expect(secureHeader)` a nivel de clase
    - Único método `post` con decoradores en orden `@ad_ns.doc('Edit an Ad Variant Image')`, `@v2_api.expect(EditAdVariantImageStruct)`, `@jwt_required`, `@check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)`
    - `post` obtiene `user_id = self.checkCredentials()['username']`, llama una vez a `EditAdVariantImageUseCase(user_id).execute(request.json)` y devuelve `{'ok': 1, 'data': data}, 200`; sin `try/except` ni acceso directo a repositorios o `FuryClient`
    - Comprobar con grep que `EditAdVariantImageStruct` y `HilucaResourceAdChannelMediaImageEdit` no existían ya en el archivo
    - Verificar con `venv/bin/python -c "import app.v2.resources.ad"`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

  - [x] 4.2 Escribir la prueba de integración opcional del endpoint en `sinergia/tests/v2/integration/`
    - Con el cliente de pruebas de Flask y `EditAdVariantImageUseCase` parcheado: sin JWT → rechazo del decorador sin instanciar el caso de uso; éxito → 200 con `{"ok": 1, "data": {"job_id": ...}}` y `execute` llamado una vez con `request.json`; `IncorrectValidationException` → 400 con `SYSVAL001`
    - _Requirements: 1.3, 1.5, 1.6, 1.7_

- [x] 5. Final checkpoint - Ensure all tests pass
  - Repetir los dos comandos del checkpoint 3 y comprobar que el recurso se importa sin errores (`venv/bin/python -c "import app.v2.resources.ad"`)
  - Ensure all tests pass, ask the user if questions arise.
  - _Requirements: 1.1, 2.5, 10.3_

## Notes

- Las sub-tareas del Unit_Test_Suite (2.x) no se marcan como opcionales porque el Requisito 10 las exige. Solo la prueba de integración del endpoint (4.2) es opcional, como indica el diseño.
- 1.1 y 1.2 comparten `use_cases/ad.py`, y 2.1–2.10 comparten el archivo de pruebas, por lo que se ejecutan en olas consecutivas.
- Los criterios 1.1–1.8 y 2.1, 2.5 y 2.6 se verifican por revisión de código (sección Trazabilidad de `requirements.md`); 2.5 además con la importación del módulo.
- El `enum` de `expand_zoom_option` en el modelo Swagger duplica los 7 literales a propósito para no acoplar el recurso a las constantes del caso de uso.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["2.1", "4.1"] },
    { "id": 3, "tasks": ["2.2", "4.2"] },
    { "id": 4, "tasks": ["2.3"] },
    { "id": 5, "tasks": ["2.4"] },
    { "id": 6, "tasks": ["2.5"] },
    { "id": 7, "tasks": ["2.6"] },
    { "id": 8, "tasks": ["2.7"] },
    { "id": 9, "tasks": ["2.8"] },
    { "id": 10, "tasks": ["2.9"] },
    { "id": 11, "tasks": ["2.10"] }
  ]
}
```
