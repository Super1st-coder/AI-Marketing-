# Implementation Plan: get-ad-variant-image-use-case

## Overview

Implementación incremental en Python 3.8 dentro de `sinergia/`, siguiendo `design.md`: primero los dos métodos de repositorio, después los helpers privados y `GetAdVariantImageUseCase` en `image_library.py`, luego el Unit_Test_Suite en un único archivo y, por último, el recurso `ServiceAdVariantImage` que conecta todo con la ruta que ya consume Fury.

Todos los comandos se ejecutan desde `sinergia/`:

- Pruebas: `venv/bin/python -m pytest tests/v2/unit/use_cases/test_get_ad_variant_image.py -q`
- Importación (Req 2.6): `venv/bin/python -c "import app.v2.use_cases.image_library"`

`pytest-mock==3.14.0` ya está fijado en `requirements-test.txt` e instalado en `venv/` (Decisión D5). No requiere tarea; como mucho, verificar con `venv/bin/python -m pip show pytest-mock`.

## Tasks

- [x] 1. Añadir los métodos de repositorio
  - [x] 1.1 Implementar `CampaignRepository.get_by_id_and_brand(campaign_id, brand_id)` en `sinergia/app/v2/repository/campaign.py`
    - Una sola llamada a `self.get(self.content_type, params)` con exactamente `filters[id][$eq]` y `filters[brand_ref][id][$eq]`, sin filtro de `account_ref`
    - Devolver `None` si la respuesta es falsy, no tiene `data` o `data` está vacía; si no, `response.get('data')[0]`
    - Mismo estilo que `get_by_id_brand_and_account` (fragmento de la sección 1 del diseño)
    - _Requirements: 4.1, 4.5_

  - [x] 1.2 Implementar `AdChannelRepository.get_by_id_ad_campaign_and_channel(ad_channel_id, ad_id, campaign_id, channel_id)` en `sinergia/app/v2/repository/ad_channel.py`
    - Una sola petición a `ad-channels` con los cuatro filtros conjuntos: `filters[id][$eq]`, `filters[ad_ref2][id][$eq]`, `filters[ad_ref2][ad_set_ref2][funnel_flow_ref][campaign_ref][id][$eq]` y `filters[channel_ref][id][$eq]`, sin `populate`
    - Devolver `None` ante respuesta `None`, sin `data`, `data: null` o lista vacía; si no, el primer elemento de `data`
    - _Requirements: 5.1, 5.5, 5.6_

- [x] 2. Implementar el caso de uso en `sinergia/app/v2/use_cases/image_library.py`
  - [x] 2.1 Añadir imports y helpers privados de módulo
    - Añadir solo `from typing import Any, Dict`, `from app.v2.repository.campaign import CampaignRepository` y `from app.v2.repository.ad_channel import AdChannelRepository`; reutilizar `logger`, `logging.basicConfig` y las excepciones ya importadas (sin duplicarlos)
    - `_is_invalid_param(value: Any) -> bool`: `True` para `None`, `""`, `0` y cadenas solo con espacios en blanco; `"0"` es válido
    - `_is_existing_image(record: Any) -> bool`: `dict` no vacío con `url` de tipo `str` no vacía ni solo espacios
    - `_extract_prompt(record: Dict[str, Any]) -> str`: `image_prompt` si es `str` (incluida `""`), en otro caso `""`
    - Solo sintaxis compatible con Python 3.8
    - _Requirements: 2.5, 2.6, 3.1–3.6, 6.2, 6.8, 6.9_

  - [x] 2.2 Implementar la clase `GetAdVariantImageUseCase`
    - `__init__(self)` crea `self.campaign_repository`, `self.ad_channel_repository` y `self.image_library_repository` (una instancia de cada una)
    - `execute(brand_id, campaign_id, ad_id, channel_id, variant_id, image_id) -> Dict[str, str]` como único método público
    - Validación con la tupla ordenada `(valor, mensaje)` de la Decisión D2: en el primer inválido, `logger.error(message)` y `raise ParametersNotFoundException(message)` con los textos `Brand Id is required`, `Campaign Id is required`, `Ad Id is required`, `Channel Id is required`, `Variant Id is required`, `Image Id is required`
    - `get_by_id_and_brand(campaign_id, brand_id)`; si `is None` → un `logger.error` con texto e identificadores y `DataNotFoundException('Campaign not found for brand')`
    - `get_by_id_ad_campaign_and_channel(variant_id, ad_id, campaign_id, channel_id)`; si `is None` → un `logger.error` con texto e identificadores y `DataNotFoundException('Ad variant not found')`
    - `get_image(image_id)` con un solo argumento posicional y sin `url_expiry`; si no es Existing_Image → un `logger.error` con texto e `image_id` y `DataNotFoundException('Image not found')`
    - Devolver `{'id': image_id, 'url': image['url'], 'prompt': _extract_prompt(image)}` sin recortar `image_id` ni `url`
    - Sin `try/except`: `StrapiException` e `ImageLibraryException` se propagan como la misma instancia
    - Verificar con `venv/bin/python -c "import app.v2.use_cases.image_library"`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.7, 3.8, 3.9, 3.10, 3.11, 4.2, 4.3, 4.4, 4.6, 4.7, 5.2, 5.3, 5.4, 5.7, 6.1, 6.3, 6.4, 6.5, 6.6, 6.7_

- [x] 3. Escribir el Unit_Test_Suite en `sinergia/tests/v2/unit/use_cases/test_get_ad_variant_image.py`
  - Archivo único, sin `conftest.py` ni fixtures fuera de él; todas las funciones de prueba con `-> None`
  - Las pruebas de error comprueban la clase y el texto exacto de la excepción; las de propagación, que es la misma instancia (`exc_info.value is original`)
  - Pruebas de propiedad con `hypothesis` y `@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])`, reconfigurando los mocks en cada ejemplo con `reset_mock()`; cada una lleva el comentario `# Feature: get-ad-variant-image-use-case, Property {n}: {texto}`

  - [x] 3.1 Crear el archivo con la fixture `repos` y las pruebas de construcción y validación
    - Fixture `repos(mocker)` que parchea `app.v2.use_cases.image_library.CampaignRepository`, `AdChannelRepository` e `ImageLibraryRepository` con valores de éxito por defecto (sección "Aislamiento" del diseño)
    - `test_init_instantiates_repositories` (2.2), `test_execute_uses_injected_repositories_only` (2.3)
    - `test_invalid_param_raises_parameters_not_found` parametrizada por parámetro × `None`, `""`, `"   "`, `"\t\n"`, `0`, con código `PAR001` (3.1–3.6)
    - `test_validation_reports_first_invalid_param_in_order` (3.7), `test_invalid_param_does_not_call_repositories` (3.8)
    - `test_valid_edge_values_pass_validation` con enteros negativos e `image_id="0"` (3.10), `test_image_id_is_not_trimmed` (3.11)
    - _Requirements: 2.2, 2.3, 3.1–3.8, 3.10, 3.11, 7.1, 7.2, 7.4, 7.6_

  - [x] 3.2 Escribir la prueba de propiedad `test_property_invalid_params_rejected_in_order`
    - **Property 1: Los Path_Params inválidos se rechazan en orden y sin acceder a datos**
    - Generadores: 6-tupla válida + conjunto no vacío de posiciones a invalidar con `st.sampled_from([None, '', 0]) | st.text(alphabet=' \t\n\r', min_size=1)`
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

  - [x] 3.3 Escribir la prueba de propiedad `test_property_valid_params_forwarded_unchanged`
    - **Property 2: Los Path_Params válidos llegan sin transformar a cada colaborador**
    - Generadores: `st.integers().filter(lambda x: x != 0)` ×5; `image_id` con contenido no blanco y padding opcional de espacios; `@example` con `image_id="0"`
    - Comprobar orden y argumentos posicionales exactos de los tres lookups, sin kwargs
    - **Validates: Requirements 3.10, 3.11, 4.2, 5.2, 6.1**

  - [x] 3.4 Escribir las pruebas de ejemplo de campaña y variante
    - `test_success_calls_campaign_lookup_with_campaign_and_brand` (4.2)
    - `test_campaign_not_found_raises_and_short_circuits` (4.3, 4.4)
    - `test_campaign_found_continues_to_variant_lookup` parametrizada con valores distintos de `None`, incluido un `dict` mínimo (4.6)
    - `test_campaign_lookup_exception_propagates` (4.7)
    - `test_success_calls_variant_lookup_with_expected_args` (5.2)
    - `test_variant_not_found_raises_and_short_circuits` (5.3, 5.4, efecto de 5.6)
    - `test_variant_lookup_strapi_exception_propagates` con `StrapiException` código `STRAPI001` y `get_image` sin llamadas (5.7)
    - _Requirements: 4.2, 4.3, 4.4, 4.6, 4.7, 5.2, 5.3, 5.4, 5.7, 7.6_

  - [x] 3.5 Escribir las pruebas de ejemplo de imagen y de logging
    - `test_success_calls_get_image_once` (6.1, 6.4)
    - `test_image_not_found_raises_data_not_found` parametrizada: `None`, lista, cadena, `{}`, dict sin `url`, `url` no `str`, `url` vacía, `url` solo espacios, cuerpo de error de Image_Library (6.2)
    - `test_image_library_exception_propagates` (6.3)
    - `test_success_returns_id_url_prompt` (6.5–6.8)
    - `test_missing_or_null_image_prompt_returns_empty_string` parametrizada: clave ausente, `None`, `int`, `list`, `dict` (6.9)
    - `test_errors_are_logged_once_before_raising` parametrizada por camino de error (parámetro inválido, campaña, variante, imagen) con `mocker.patch('app.v2.use_cases.image_library.logger')`, comprobando `logger.error.call_count == 1`, el texto de la excepción y, en DataNotFoundException, los identificadores (2.4, 3.9)
    - _Requirements: 2.4, 3.9, 6.1–6.9, 7.6_

  - [x] 3.6 Escribir la prueba de propiedad `test_property_non_existing_image_raises_not_found`
    - **Property 3: Los registros que no son Existing_Image producen "Image not found"**
    - Generadores: `st.one_of(st.none(), st.integers(), st.lists(...), st.text(), st.just({}), dict sin url, dict con url no str, dict con url solo espacios)` con claves adicionales arbitrarias
    - **Validates: Requirements 6.2**

  - [x] 3.7 Escribir la prueba de propiedad `test_property_response_keys_and_types`
    - **Property 4: La respuesta es exactamente {id, url, prompt} con valores str derivados del registro**
    - Generadores: `url` con contenido no blanco; claves extra con `st.dictionaries(...)` excluyendo `url` e `image_prompt` (incluida una clave `id` distinta de `image_id`); `image_prompt` ausente, `None`, `st.text()`, `st.integers()`, listas o dicts
    - **Validates: Requirements 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 7.7**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ejecutar `venv/bin/python -m pytest tests/v2/unit/use_cases/test_get_ad_variant_image.py -q` desde `sinergia/` (0 fallos, 0 errores, 0 omitidas, < 60 s) y `venv/bin/python -c "import app.v2.use_cases.image_library"`
  - Ensure all tests pass, ask the user if questions arise.
  - _Requirements: 2.6, 7.3_

- [x] 5. Conectar el endpoint de servicio
  - [x] 5.1 Añadir el recurso `ServiceAdVariantImage` en `sinergia/app/v2/resources/service.py`
    - Ampliar el import existente a `from app.v2.use_cases.image_library import GetProductImagesUseCase, UploadImageFuryUseCase, GetAdVariantImageUseCase`
    - `@service_ns.route('/hiluca/brand/<int:brand_id>/campaign/<int:campaign_id>/ad/<int:ad_id>/channel/<int:channel_id>/variant/<int:variant_id>/image/<string:image_id>')` con un único método `get` decorado con `@service_api_key_required`
    - `get` llama a `GetAdVariantImageUseCase().execute(brand_id, campaign_id, ad_id, channel_id, variant_id, image_id)` en orden posicional y devuelve `{'ok': True, 'data': data}, 200`
    - Sin `try/except` ni acceso directo a repositorios o `StrapiClient`; bloque de comentario de cabecera como el resto de `service.py`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

  - [x] 5.2 Escribir la prueba de integración opcional del endpoint en `sinergia/tests/v2/integration/`
    - Con el cliente de pruebas de Flask y el caso de uso mockeado: sin cabecera → rechazo de Service_Auth sin invocar `execute`; segmento `-1` → 404 `E404`; éxito → 200 con Success_Envelope; `DataNotFoundException` → 400 con `DAT001`
    - _Requirements: 1.3, 1.4, 1.5, 1.6, 1.7_

- [x] 6. Final checkpoint - Ensure all tests pass
  - Repetir los dos comandos del checkpoint 4 y comprobar que `service.py` se importa sin errores (`venv/bin/python -c "import app.v2.resources.service"`)
  - Ensure all tests pass, ask the user if questions arise.
  - _Requirements: 1.1, 2.6, 7.3_

## Notes

- Las sub-tareas del Unit_Test_Suite (3.x) no se marcan como opcionales porque el Requisito 7 las exige. Solo la prueba de integración del endpoint (5.2) es opcional, como indica el diseño.
- Las tareas 3.1–3.7 escriben en el mismo archivo y se ejecutan en olas consecutivas; 2.1 y 2.2 también comparten archivo.
- Los criterios 1.x, 2.1, 2.5, 2.6, 4.1, 4.5, 5.1, 5.5 y 5.6 se verifican por revisión de código (Req 7.5); 2.6 además con la importación del módulo.
- `pytest-mock==3.14.0` ya está en `requirements-test.txt` e instalado en `venv/`; no se crea tarea para ello.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "2.1"] },
    { "id": 1, "tasks": ["2.2"] },
    { "id": 2, "tasks": ["3.1", "5.1"] },
    { "id": 3, "tasks": ["3.2", "5.2"] },
    { "id": 4, "tasks": ["3.3"] },
    { "id": 5, "tasks": ["3.4"] },
    { "id": 6, "tasks": ["3.5"] },
    { "id": 7, "tasks": ["3.6"] },
    { "id": 8, "tasks": ["3.7"] }
  ]
}
```
