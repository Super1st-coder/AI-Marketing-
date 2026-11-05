"""Fresh builders and local isolation harness for funnel flow validator tests.

Every mutable test value is local to one invocation. The function-scoped fixtures
patch Strapi before use-case construction and forbid accidental network access.

Traceability: Requirements 1.1-1.10 and 8.1-8.3, 8.7.
"""

from copy import deepcopy
from math import ceil
from typing import Any, Callable, Dict, Generator, List, Mapping, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest
import requests
from hypothesis import HealthCheck, given, settings, strategies as st

from app.tools.strapi import StrapiClient as RealStrapiClient
from app.v2.use_cases.funnel_flow_validator import FunnelFlowValidatorUseCase


_REGISTERED_VALIDATOR_KEYS = (
    "channel",
    "ads_structure",
    "audiences",
    "ads_experiment",
    "ads",
    "summary",
    "review",
    "launchpad",
)
_JSON_ATOM_STRATEGY = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.text(max_size=30),
)
_JSON_VALUE_STRATEGY = st.recursive(
    _JSON_ATOM_STRATEGY,
    lambda children: st.one_of(
        st.lists(children, max_size=3),
        st.dictionaries(st.text(max_size=12), children, max_size=3),
    ),
    max_leaves=10,
)
_VALIDATION_ERRORS_STRATEGY = st.lists(
    st.dictionaries(
        st.text(max_size=12),
        _JSON_VALUE_STRATEGY,
        max_size=4,
    ),
    max_size=4,
)
_STATE_ENTRY_STRATEGY = st.fixed_dictionaries(
    {},
    optional={
        "completed": st.booleans(),
        "errors": _VALIDATION_ERRORS_STRATEGY,
        "message": _JSON_VALUE_STRATEGY,
        "custom": _JSON_VALUE_STRATEGY,
    },
)


class TestPropertyContracts:
    """Exercise the specified contracts over generated in-memory values."""

    # Feature: funnel-flow-validator-tests, Property 1: El despacho conserva
    # contexto y resultado.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        validator_key=st.sampled_from(_REGISTERED_VALIDATOR_KEYS),
        completed=st.booleans(),
        context=_JSON_VALUE_STRATEGY,
        errors=_VALIDATION_ERRORS_STRATEGY,
    )
    def test_property_dispatch_preserves_context_and_exact_result(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        validator_key: str,
        completed: bool,
        context: Any,
        errors: List[Dict[str, Any]],
    ) -> None:
        """Dispatch preserves argument identity and replaces the entire state.

        **Validates: Requirements 2.7, 2.8**
        """
        use_case, _, _ = use_case_factory()
        validator_index = next(
            index
            for index, registered_validator in enumerate(use_case.validators)
            if registered_validator.key == validator_key
        )
        validator = MagicMock()
        validator.key = validator_key
        validator.validate_completion.return_value = (completed, errors)
        use_case.validators[validator_index] = validator
        previous_state = {
            "completed": not completed,
            "errors": [{"code": "STALE"}],
            "message": "stale state must be replaced",
        }
        use_case._state_map[validator_key] = previous_state

        use_case._run_validator(validator_key, context)

        validator.validate_completion.assert_called_once_with(context)
        assert validator.validate_completion.call_args.args[0] is context
        current_state = use_case._state_map[validator_key]
        assert current_state is not previous_state
        assert current_state == {
            "completed": completed,
            "errors": errors,
        }
        assert current_state["completed"] is completed
        assert current_state["errors"] is errors

    # Feature: funnel-flow-validator-tests, Property 2: La respuesta normaliza
    # estados en orden canónico.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        state_entries=st.tuples(
            *[
                _STATE_ENTRY_STRATEGY
                for _ in _REGISTERED_VALIDATOR_KEYS
            ]
        ),
        funnel_flow_data=_JSON_VALUE_STRATEGY,
    )
    def test_property_response_normalizes_states_in_canonical_order(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        state_entries: Tuple[Dict[str, Any], ...],
        funnel_flow_data: Any,
    ) -> None:
        """Response adds only missing defaults and preserves order and data.

        **Validates: Requirements 2.10, 2.11, 2.12, 7.12**
        """
        use_case, _, _ = use_case_factory()
        use_case._state_map = dict(
            zip(_REGISTERED_VALIDATOR_KEYS, state_entries)
        )
        original_entries = [dict(entry) for entry in state_entries]

        response = use_case._build_response(funnel_flow_data)

        returned_states = response["state"]
        returned_steps = [entry["step"] for entry in returned_states]
        assert response["funnel_flow_data"] is funnel_flow_data
        assert returned_steps == list(_REGISTERED_VALIDATOR_KEYS)
        assert len(returned_steps) == len(set(returned_steps)) == 8

        for step, source, snapshot, returned in zip(
            _REGISTERED_VALIDATOR_KEYS,
            state_entries,
            original_entries,
            returned_states,
        ):
            assert use_case._state_map[step] is source
            assert source == snapshot
            assert set(returned) == set(source) | {
                "step",
                "completed",
                "errors",
            }
            for field, value in source.items():
                assert returned[field] is value

            if "completed" in source:
                assert returned["completed"] is source["completed"]
            else:
                assert returned["completed"] is False
            if "errors" in source:
                assert returned["errors"] is source["errors"]
            else:
                assert returned["errors"] == []

    # Feature: funnel-flow-validator-tests, Property 3: El margen de longitud
    # está acotado por veinte por ciento y diez.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(original_length=st.integers(min_value=0))
    def test_property_length_margin_is_twenty_percent_capped_at_ten(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        original_length: int,
    ) -> None:
        """Length allowance exactly follows the bounded margin formula.

        **Validates: Requirements 2.13, 2.14, 6.24**
        """
        use_case, _, _ = use_case_factory()
        ads_validator = next(
            validator for validator in use_case.validators if validator.key == "ads"
        )
        expected_maximum = original_length + min(
            ceil(original_length * 0.2),
            10,
        )

        result = getattr(ads_validator, "_get_max_length_allowed")(
            original_length
        )

        assert result == expected_maximum

    # Feature: funnel-flow-validator-tests, Property 4: Las consultas indexadas
    # cubren cada identificador una sola vez.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        funnel_flow_ids=st.lists(
            st.integers(min_value=1, max_value=10_000),
            min_size=1,
            max_size=5,
            unique=True,
        ),
        ad_set_ids=st.lists(
            st.integers(min_value=10_001, max_value=20_000),
            min_size=1,
            max_size=5,
            unique=True,
        ),
        ad_ids=st.lists(
            st.integers(min_value=20_001, max_value=30_000),
            min_size=5,
            max_size=7,
            unique=True,
        ),
    )
    def test_property_indexed_queries_cover_each_unique_identifier_once(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        funnel_flow_ids: List[int],
        ad_set_ids: List[int],
        ad_ids: List[int],
    ) -> None:
        """Indexed queries contain every generated ID exactly once.

        **Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6**
        """
        ads_by_ad_set: List[List[Dict[str, Any]]] = [
            [] for _ in ad_set_ids
        ]
        for index, ad_id in enumerate(ad_ids):
            ads_by_ad_set[index % len(ad_set_ids)].append(
                make_raw_ad(ad_id=ad_id)
            )

        use_case, strapi_mock, _ = use_case_factory(
            campaign_id="property-indexed-queries",
            find_responses={
                "funnel-flows": {
                    "data": [
                        make_funnel_flow(flow_id=flow_id)
                        for flow_id in funnel_flow_ids
                    ]
                },
                "funnel-flow-channels": {
                    "data": [make_channel()]
                },
            },
            get_responses={
                "ad-sets": {
                    "data": [
                        make_raw_ad_set(
                            ad_set_id=ad_set_id,
                            ads=ads_by_ad_set[index],
                        )
                        for index, ad_set_id in enumerate(ad_set_ids)
                    ]
                },
                "audience-audiences": {"data": []},
                "experiment-experiments": {"data": []},
                "ad-channels": {"data": []},
            },
        )

        response, status_code = use_case.execute()

        assert status_code == 200
        assert response["ok"] == 1
        assert len(funnel_flow_ids) == len(set(funnel_flow_ids))
        assert len(ad_set_ids) == len(set(ad_set_ids))
        assert len(ad_ids) == len(set(ad_ids))

        find_calls = strapi_mock.find_by_filters.call_args_list
        assert len(find_calls) == 2
        assert (find_calls[0].args, find_calls[0].kwargs) == (
            ("funnel-flows",),
            {"filters": {"campaign_ref": "property-indexed-queries"}},
        )
        assert (find_calls[1].args, find_calls[1].kwargs) == (
            ("funnel-flow-channels",),
            {"filters": {"funnel_flow_ref": funnel_flow_ids}},
        )

        expected_ad_set_params = {
            f"filters[funnel_flow_ref][id][$in][{index}]": flow_id
            for index, flow_id in enumerate(funnel_flow_ids)
        }
        expected_ad_set_params["populate"] = (
            "ads,media_platform_project_id"
        )
        expected_audience_params = {
            f"filters[ad_set_ref][id][$in][{index}]": ad_set_id
            for index, ad_set_id in enumerate(ad_set_ids)
        }
        expected_audience_params["populate"] = "channel_ref,ad_set_ref"
        expected_experiment_params = {
            f"filters[ad_set_ref][id][$in][{index}]": ad_set_id
            for index, ad_set_id in enumerate(ad_set_ids)
        }
        expected_experiment_params["populate"] = (
            "ad_set_ref,subcategory_ref.category_ref"
        )
        traversed_ad_ids = [
            ad["id"]
            for ads_in_ad_set in ads_by_ad_set
            for ad in ads_in_ad_set
        ]
        assert len(traversed_ad_ids) == len(ad_ids)
        assert set(traversed_ad_ids) == set(ad_ids)
        expected_ad_channel_params = {
            f"filters[ad_ref][id][$in][{index}]": ad_id
            for index, ad_id in enumerate(traversed_ad_ids)
        }
        expected_ad_channel_params["populate"] = "channel_ref,ad_ref"
        expected_ad_channel_params["pagination[pageSize]"] = 1000

        get_calls = strapi_mock.get.call_args_list
        assert len(get_calls) == 4
        assert [
            (strapi_call.args, strapi_call.kwargs)
            for strapi_call in get_calls
        ] == [
            (("ad-sets",), {"params": expected_ad_set_params}),
            (
                ("audience-audiences",),
                {"params": expected_audience_params},
            ),
            (
                ("experiment-experiments",),
                {"params": expected_experiment_params},
            ),
            (
                ("ad-channels",),
                {"params": expected_ad_channel_params},
            ),
        ]

    # Feature: funnel-flow-validator-tests, Property 5: La consolidación
    # particiona relaciones y preserva proyecciones.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        graph_token=st.text(
            alphabet=st.characters(
                whitelist_categories=("Ll", "Lu", "Nd"),
            ),
            min_size=1,
            max_size=8,
        ),
        id_offset=st.integers(min_value=1, max_value=10_000),
        ad_set_count=st.integers(min_value=1, max_value=3),
        second_ad_flags=st.lists(
            st.booleans(),
            min_size=3,
            max_size=3,
        ),
        selected_values=st.lists(
            st.booleans(),
            min_size=6,
            max_size=6,
        ),
        reverse_relations=st.booleans(),
    )
    def test_property_consolidation_partitions_and_preserves_projections(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        graph_token: str,
        id_offset: int,
        ad_set_count: int,
        second_ad_flags: List[bool],
        selected_values: List[bool],
        reverse_relations: bool,
    ) -> None:
        """Known relations are uniquely partitioned and exactly projected.

        **Validates: Requirements 3.7, 3.8, 3.9, 3.10, 3.11, 3.12,
        3.13, 4.6, 4.7, 4.8**
        """
        raw_ad_sets: List[Dict[str, Any]] = []
        raw_audiences: List[Dict[str, Any]] = []
        raw_experiments: List[Dict[str, Any]] = []
        raw_ad_channels: List[Dict[str, Any]] = []
        expected_funnel_data: List[Dict[str, Any]] = []
        expected_audiences: Dict[int, List[Dict[str, Any]]] = {}
        expected_experiments: Dict[int, List[Dict[str, Any]]] = {}
        expected_channels: Dict[int, List[Dict[str, Any]]] = {}

        for ad_set_index in range(ad_set_count):
            ad_set_id = id_offset + ad_set_index
            project_id = f"{graph_token}-project-{ad_set_index}"
            ad_set_name = f"{graph_token}-set-{ad_set_index}"
            raw_ads: List[Dict[str, Any]] = []
            expected_ads: List[Dict[str, Any]] = []
            ad_count = 1 + int(second_ad_flags[ad_set_index])

            for ad_index in range(ad_count):
                ad_id = (id_offset * 10) + (ad_set_index * 2) + ad_index
                ad_name = f"{graph_token}-ad-{ad_set_index}-{ad_index}"
                ad_url = f"https://example.test/{graph_token}/{ad_id}"
                channel_id = (id_offset * 100) + ad_id
                channel_name = f"{graph_token}-channel-{ad_id}"
                elements = [
                    {
                        "name": f"element-{ad_id}",
                        "payload": f"payload-{graph_token}-{ad_id}",
                    }
                ]
                images_banner = [{"image": f"{graph_token}-{ad_id}"}]
                formats = [
                    {
                        "visual_id": f"visual-{ad_id}",
                        "visual_url": f"https://example.test/visual/{ad_id}",
                    }
                ]
                channel_attributes = [
                    {
                        "name": f"attribute-{ad_id}",
                        "payloads": [{"payload": graph_token}],
                    }
                ]
                channel_url = f"https://example.test/channel/{ad_id}"
                selected = selected_values[(ad_set_index * 2) + ad_index]
                raw_ads.append(
                    make_raw_ad(
                        ad_id=ad_id,
                        name=ad_name,
                        redirect_url=ad_url,
                    )
                )
                raw_ad_channels.append(
                    make_raw_ad_channel(
                        channel_record_id=(id_offset * 1_000) + ad_id,
                        ad_id=ad_id,
                        channel_id=channel_id,
                        channel_name=channel_name,
                        template_id=f"template-{graph_token}-{ad_id}",
                        elements=elements,
                        images_banner=images_banner,
                        formats=formats,
                        channel_attributes=channel_attributes,
                        redirect_url=channel_url,
                        selected=selected,
                    )
                )
                expected_channel = {
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                    "media": {
                        "template_id": f"template-{graph_token}-{ad_id}",
                        "elements": elements,
                        "images_banner": images_banner,
                        "formats": formats,
                    },
                    "channel_attributes": channel_attributes,
                    "url": channel_url,
                    "selected": selected,
                }
                expected_channels[ad_id] = [expected_channel]
                expected_ads.append(
                    {
                        "id": ad_id,
                        "attributes": {
                            "name": ad_name,
                            "ad_channels": [expected_channel],
                            "url": ad_url,
                        },
                    }
                )

            raw_ad_sets.append(
                make_raw_ad_set(
                    ad_set_id=ad_set_id,
                    name=ad_set_name,
                    ads=raw_ads,
                    project_id=project_id,
                )
            )

            preferred_audience = {"preferred": ad_set_index % 2}
            proposal_audiences = [
                {"segment": f"{graph_token}-segment-{ad_set_index}"}
            ]
            raw_audiences.append(
                make_raw_audience(
                    audience_id=(id_offset * 100) + ad_set_index,
                    ad_set_id=ad_set_id,
                    channel_id=(id_offset * 1_000) + ad_set_index,
                    channel_name=f"{graph_token}-audience-{ad_set_index}",
                    generation_method=f"method-{graph_token}-{ad_set_index}",
                    preferred=preferred_audience["preferred"],
                    proposal_audiences=proposal_audiences,
                )
            )
            expected_audience = {
                "channel_id": (id_offset * 1_000) + ad_set_index,
                "channel_name": f"{graph_token}-audience-{ad_set_index}",
                "generation_method": f"method-{graph_token}-{ad_set_index}",
                "preferred_audience": preferred_audience,
                "proposal_audiences": proposal_audiences,
            }
            expected_audiences[ad_set_id] = [expected_audience]

            raw_experiments.append(
                make_raw_experiment(
                    experiment_id=(id_offset * 10_000) + ad_set_index,
                    ad_set_id=ad_set_id,
                    experiment_type=f"type-{graph_token}-{ad_set_index}",
                    subcategory_id=(id_offset * 100_000) + ad_set_index,
                    subcategory_name=f"subcategory-{graph_token}-{ad_set_index}",
                    subcategory_description=(
                        f"subcategory-description-{graph_token}-{ad_set_index}"
                    ),
                    category_id=(id_offset * 1_000_000) + ad_set_index,
                    category_name=f"category-{graph_token}-{ad_set_index}",
                    category_description=(
                        f"category-description-{graph_token}-{ad_set_index}"
                    ),
                )
            )
            expected_experiment = {
                "id": (id_offset * 10_000) + ad_set_index,
                "type": f"type-{graph_token}-{ad_set_index}",
                "subcategory": {
                    "id": (id_offset * 100_000) + ad_set_index,
                    "name": f"subcategory-{graph_token}-{ad_set_index}",
                    "description": (
                        f"subcategory-description-{graph_token}-{ad_set_index}"
                    ),
                    "category": {
                        "id": (id_offset * 1_000_000) + ad_set_index,
                        "name": f"category-{graph_token}-{ad_set_index}",
                        "description": (
                            f"category-description-{graph_token}-{ad_set_index}"
                        ),
                    },
                },
            }
            expected_experiments[ad_set_id] = [expected_experiment]
            expected_funnel_data.append(
                {
                    "id": ad_set_id,
                    "name": ad_set_name,
                    "media_platform_project_id": project_id,
                    "ads": expected_ads,
                    "audiences": [expected_audience],
                    "experiments": [expected_experiment],
                }
            )

        unknown_ad_set_id = -(id_offset + 1)
        unknown_ad_id = -(id_offset + 2)
        unknown_audience = {
            "channel_id": -1,
            "channel_name": f"{graph_token}-unknown-audience",
            "generation_method": "unknown-method",
            "preferred_audience": {"preferred": 1},
            "proposal_audiences": [{"segment": "unknown"}],
        }
        raw_audiences.append(
            make_raw_audience(
                audience_id=-1,
                ad_set_id=unknown_ad_set_id,
                channel_id=unknown_audience["channel_id"],
                channel_name=unknown_audience["channel_name"],
                generation_method=unknown_audience["generation_method"],
                preferred=1,
                proposal_audiences=unknown_audience["proposal_audiences"],
            )
        )
        unknown_experiment = {
            "id": -2,
            "type": f"{graph_token}-unknown-experiment",
            "subcategory": {
                "id": -3,
                "name": "unknown-subcategory",
                "description": "unknown-subcategory-description",
                "category": {
                    "id": -4,
                    "name": "unknown-category",
                    "description": "unknown-category-description",
                },
            },
        }
        raw_experiments.append(
            make_raw_experiment(
                experiment_id=unknown_experiment["id"],
                ad_set_id=unknown_ad_set_id,
                experiment_type=unknown_experiment["type"],
                subcategory_id=unknown_experiment["subcategory"]["id"],
                subcategory_name=unknown_experiment["subcategory"]["name"],
                subcategory_description=(
                    unknown_experiment["subcategory"]["description"]
                ),
                category_id=unknown_experiment["subcategory"]["category"]["id"],
                category_name=(
                    unknown_experiment["subcategory"]["category"]["name"]
                ),
                category_description=(
                    unknown_experiment["subcategory"]["category"]["description"]
                ),
            )
        )
        unknown_channel = {
            "channel_id": -5,
            "channel_name": f"{graph_token}-unknown-channel",
            "media": {
                "template_id": "unknown-template",
                "elements": [{"name": "unknown-element"}],
                "images_banner": [{"image": "unknown-image"}],
                "formats": [{"visual_id": "unknown-visual", "pinned": True}],
            },
            "channel_attributes": [{"name": "unknown-attribute"}],
            "url": "https://example.test/unknown-channel",
            "selected": True,
        }
        raw_ad_channels.append(
            make_raw_ad_channel(
                channel_record_id=-6,
                ad_id=unknown_ad_id,
                channel_id=unknown_channel["channel_id"],
                channel_name=unknown_channel["channel_name"],
                template_id=unknown_channel["media"]["template_id"],
                elements=unknown_channel["media"]["elements"],
                images_banner=unknown_channel["media"]["images_banner"],
                formats=unknown_channel["media"]["formats"],
                channel_attributes=unknown_channel["channel_attributes"],
                redirect_url=unknown_channel["url"],
                selected=unknown_channel["selected"],
            )
        )

        if reverse_relations:
            raw_audiences.reverse()
            raw_experiments.reverse()
            raw_ad_channels.reverse()

        use_case, _, _ = use_case_factory(
            campaign_id="property-consolidation",
            find_responses={
                "funnel-flows": {"data": [make_funnel_flow("flow-property")]},
                "funnel-flow-channels": {"data": [make_channel()]},
            },
            get_responses={
                "ad-sets": {"data": raw_ad_sets},
                "audience-audiences": {"data": raw_audiences},
                "experiment-experiments": {"data": raw_experiments},
                "ad-channels": {"data": raw_ad_channels},
            },
        )
        for validator in use_case.validators:
            validator.validate_completion = MagicMock(return_value=(True, []))

        response, status_code = use_case.execute()

        assert status_code == 200
        actual_funnel_data = response["data"]["funnel_flow_data"]
        assert actual_funnel_data == expected_funnel_data

        actual_audiences = [
            (ad_set["id"], audience)
            for ad_set in actual_funnel_data
            for audience in ad_set["audiences"]
        ]
        actual_experiments = [
            (ad_set["id"], experiment)
            for ad_set in actual_funnel_data
            for experiment in ad_set["experiments"]
        ]
        actual_channels = [
            (ad["id"], channel)
            for ad_set in actual_funnel_data
            for ad in ad_set["ads"]
            for channel in ad["attributes"]["ad_channels"]
        ]
        for parent_id, relations in expected_audiences.items():
            for relation in relations:
                assert actual_audiences.count((parent_id, relation)) == 1
                assert sum(
                    candidate == relation
                    for _, candidate in actual_audiences
                ) == 1
        for parent_id, relations in expected_experiments.items():
            for relation in relations:
                assert actual_experiments.count((parent_id, relation)) == 1
                assert sum(
                    candidate == relation
                    for _, candidate in actual_experiments
                ) == 1
        for parent_id, relations in expected_channels.items():
            for relation in relations:
                assert actual_channels.count((parent_id, relation)) == 1
                assert sum(
                    candidate == relation
                    for _, candidate in actual_channels
                ) == 1

        assert all(
            audience != unknown_audience
            for _, audience in actual_audiences
        )
        assert all(
            experiment != unknown_experiment
            for _, experiment in actual_experiments
        )
        assert all(
            channel != unknown_channel
            for _, channel in actual_channels
        )

    # Feature: funnel-flow-validator-tests, Property 6: Una lista de canales
    # no vacía siempre es válida.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        channels=st.lists(
            _JSON_VALUE_STRATEGY,
            min_size=1,
            max_size=8,
        )
    )
    def test_property_any_non_empty_channel_list_is_valid(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        channels: List[Any],
    ) -> None:
        """Every non-empty channel list completes without errors.

        **Validates: Requirements 5.3**
        """
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "channel"
        )

        completed, errors = validator.validate_completion(channels)

        assert completed is True
        assert errors == []

    # Feature: funnel-flow-validator-tests, Property 7: Los errores de
    # estructura corresponden a los ad sets inválidos.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        ad_set_specs=st.lists(
            st.tuples(
                st.text(max_size=30),
                st.sampled_from(
                    ("valid", "omitted", "none", "empty", "non-list")
                ),
            ),
            min_size=1,
            max_size=8,
        )
    )
    def test_property_structure_errors_match_invalid_ad_sets(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        ad_set_specs: List[Tuple[str, str]],
    ) -> None:
        """Structure errors exactly match invalid ad sets in input order.

        **Validates: Requirements 5.5, 5.6, 5.7**
        """
        ad_sets: List[Dict[str, Any]] = []
        expected_errors: List[Dict[str, Any]] = []
        for index, (ad_set_name, ads_kind) in enumerate(ad_set_specs):
            ad_set: Dict[str, Any] = {"name": ad_set_name}
            if ads_kind == "valid":
                ad_set["ads"] = [{"id": index}]
            elif ads_kind == "none":
                ad_set["ads"] = None
            elif ads_kind == "empty":
                ad_set["ads"] = []
            elif ads_kind == "non-list":
                ad_set["ads"] = {"id": index}
            ad_sets.append(ad_set)

            if ads_kind != "valid":
                expected_errors.append(
                    {
                        "message": (
                            f"Ad Set '{ad_set_name}' has no ads created."
                        ),
                        "code": "ADS_STRUCT_02",
                        "metadata": {"ad_set_name": ad_set_name},
                    }
                )

        use_case, _, _ = use_case_factory()
        validator = next(
            item
            for item in use_case.validators
            if item.key == "ads_structure"
        )

        completed, errors = validator.validate_completion(ad_sets)

        assert completed is (not expected_errors)
        assert len(errors) == len(expected_errors)
        assert errors == expected_errors

    # Feature: funnel-flow-validator-tests, Property 8: La audiencia preferida
    # determina la validez por ad set.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        ad_set_specs=st.lists(
            st.tuples(
                st.text(max_size=30),
                st.lists(st.booleans(), min_size=1, max_size=6),
                st.sampled_from(("list", "tuple", "iterator")),
            ),
            min_size=1,
            max_size=8,
        )
    )
    def test_property_preferred_audience_determines_ad_set_validity(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        ad_set_specs: List[Tuple[str, List[bool], str]],
    ) -> None:
        """AUD_03 errors exactly match non-empty sets without preferred=1.

        **Validates: Requirements 5.10, 5.11, 5.12, 5.13**
        """
        ad_sets: List[Dict[str, Any]] = []
        expected_errors: List[Dict[str, Any]] = []
        for ad_set_name, preferred_flags, iterable_kind in ad_set_specs:
            audience_values = [
                {
                    "preferred_audience": {
                        "preferred": 1 if is_preferred else 0,
                    }
                }
                for is_preferred in preferred_flags
            ]
            audiences: Any
            if iterable_kind == "tuple":
                audiences = tuple(audience_values)
            elif iterable_kind == "iterator":
                audiences = iter(audience_values)
            else:
                audiences = audience_values
            ad_sets.append(
                {
                    "name": ad_set_name,
                    "audiences": audiences,
                }
            )

            if not any(preferred_flags):
                expected_errors.append(
                    {
                        "message": (
                            f"Ad Set '{ad_set_name}' is missing a Preferred "
                            "Audience."
                        ),
                        "code": "AUD_03",
                        "metadata": {"ad_set_name": ad_set_name},
                    }
                )

        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "audiences"
        )

        completed, errors = validator.validate_completion(ad_sets)

        assert completed is (not expected_errors)
        assert len(errors) == len(expected_errors)
        assert errors == expected_errors

    # Feature: funnel-flow-validator-tests, Property 9: Un experimento
    # verdadero determina la validez por ad set.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        ad_set_specs=st.lists(
            st.tuples(
                st.text(max_size=30),
                st.lists(st.booleans(), min_size=1, max_size=6),
                st.sampled_from(("list", "tuple", "iterator")),
            ),
            min_size=1,
            max_size=8,
        )
    )
    def test_property_truthy_experiment_determines_ad_set_validity(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        ad_set_specs: List[Tuple[str, List[bool], str]],
    ) -> None:
        """EXP_03 errors exactly match non-empty sets with only falsy values.

        **Validates: Requirements 5.18, 5.19, 5.20, 5.21**
        """
        ad_sets: List[Dict[str, Any]] = []
        expected_errors: List[Dict[str, Any]] = []
        for ad_set_name, truthy_flags, iterable_kind in ad_set_specs:
            experiment_values: List[bool] = list(truthy_flags)
            experiments: Any
            if iterable_kind == "tuple":
                experiments = tuple(experiment_values)
            elif iterable_kind == "iterator":
                experiments = iter(experiment_values)
            else:
                experiments = experiment_values
            ad_sets.append(
                {
                    "name": ad_set_name,
                    "experiments": experiments,
                }
            )

            if not any(truthy_flags):
                expected_errors.append(
                    {
                        "message": (
                            f"Ad Set '{ad_set_name}' has empty experiment data."
                        ),
                        "code": "EXP_03",
                        "metadata": {"ad_set_name": ad_set_name},
                    }
                )

        use_case, _, _ = use_case_factory()
        validator = next(
            item
            for item in use_case.validators
            if item.key == "ads_experiment"
        )

        completed, errors = validator.validate_completion(ad_sets)

        assert completed is (not expected_errors)
        assert len(errors) == len(expected_errors)
        assert errors == expected_errors

    # Feature: funnel-flow-validator-tests, Property 10: Los límites de
    # atributos se aplican salvo para CTA.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        is_cta=st.booleans(),
        cta_uppercase=st.tuples(
            st.booleans(),
            st.booleans(),
            st.booleans(),
        ),
        non_cta_suffix=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            min_size=1,
            max_size=12,
        ),
        max_char=st.integers(min_value=0, max_value=100),
        excess=st.integers(min_value=1, max_value=20),
    )
    def test_property_attribute_limits_apply_except_for_cta(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        is_cta: bool,
        cta_uppercase: Tuple[bool, bool, bool],
        non_cta_suffix: str,
        max_char: int,
        excess: int,
    ) -> None:
        """Only case-insensitive CTA names exclude an over-limit payload.

        **Validates: Requirements 6.17, 6.18**
        """
        if is_cta:
            attribute_name = "".join(
                letter.upper() if uppercase else letter
                for letter, uppercase in zip("cta", cta_uppercase)
            )
        else:
            attribute_name = f"Headline-{non_cta_suffix}"
        payload = "x" * (max_char + excess)
        ad_name = "Attribute Limit Ad"
        channel_name = "Search"
        context = make_valid_ads_context(ad_name=ad_name)
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["channel_name"] = channel_name
        selected_channel["channel_attributes"] = [
            {
                "name": attribute_name,
                "max_char": max_char,
                "payloads": [{"payload": payload}],
            }
        ]
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "ads"
        )

        completed, errors = validator.validate_completion(context)

        if is_cta:
            assert attribute_name.lower() == "cta"
            assert completed is True
            assert errors == []
        else:
            assert attribute_name.lower() != "cta"
            assert completed is False
            assert errors == [
                {
                    "message": (
                        "Ad 'Attribute Limit Ad' has a payload that exceeds "
                        "the maximum allowed length in channel attributes, "
                        "in channel 'Search'."
                    ),
                    "code": "ADS_05_02",
                    "metadata": {
                        "ad_name": ad_name,
                        "channel_name": channel_name,
                        "payload_length": len(payload),
                        "max_allowed_length": max_char,
                        "attribute_name": attribute_name,
                    },
                }
            ]

    # Feature: funnel-flow-validator-tests, Property 11: Los errores de medios
    # corresponden al subconjunto inválido.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        invalid_media=st.dictionaries(
            keys=st.sampled_from(("elements", "images_banner", "formats")),
            values=st.sampled_from(("omitted", "none", "non-list", "empty")),
            min_size=1,
            max_size=3,
        )
    )
    def test_property_media_errors_match_invalid_subset(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        invalid_media: Dict[str, str],
    ) -> None:
        """Each invalid media field contributes one canonical ADS_07 error.

        **Validates: Requirements 6.19, 6.20**
        """
        canonical_media_keys = ("elements", "images_banner", "formats")
        ad_name = "Property Media Ad"
        channel_name = "Property Media Channel"
        context = make_valid_ads_context(ad_name=ad_name)
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["channel_name"] = channel_name
        media = selected_channel["media"]

        for media_key, invalid_shape in invalid_media.items():
            if invalid_shape == "omitted":
                del media[media_key]
            elif invalid_shape == "none":
                media[media_key] = None
            elif invalid_shape == "non-list":
                media[media_key] = {"invalid": media_key}
            else:
                media[media_key] = []

        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "ads"
        )

        completed, errors = validator.validate_completion(context)

        expected_invalid_keys = [
            media_key
            for media_key in canonical_media_keys
            if media_key in invalid_media
        ]
        assert completed is False
        assert len(errors) == len(expected_invalid_keys)
        assert errors == [
            {
                "message": (
                    f"Ad '{ad_name}' missing media '{media_key}' in channel "
                    f"'{channel_name}'."
                ),
                "code": "ADS_07",
                "metadata": {
                    "ad_name": ad_name,
                    "media_element": media_key,
                    "channel_name": channel_name,
                },
            }
            for media_key in expected_invalid_keys
        ]

    # Feature: funnel-flow-validator-tests, Property 12: El exceso de payload
    # de elemento usa el límite derivado.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        original_payload=st.text(min_size=1, max_size=80),
        excess=st.integers(min_value=1, max_value=20),
        ad_name=st.text(min_size=1, max_size=30),
        channel_name=st.text(min_size=1, max_size=30),
        element_name=st.text(min_size=1, max_size=30),
    )
    def test_property_element_payload_excess_uses_derived_limit(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        original_payload: str,
        excess: int,
        ad_name: str,
        channel_name: str,
        element_name: str,
    ) -> None:
        """An exceeded element payload reports the exact derived-limit error.

        **Validates: Requirements 6.25**
        """
        original_length = len(original_payload)
        max_allowed_length = original_length + min(
            ceil(original_length * 0.2),
            10,
        )
        payload = "x" * (max_allowed_length + excess)
        context = make_valid_ads_context(ad_name=ad_name)
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["channel_name"] = channel_name
        selected_channel["media"]["elements"] = [
            {
                "name": element_name,
                "original_payload": original_payload,
                "payload": payload,
                "intention": "awareness",
            }
        ]
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "ads"
        )

        completed, errors = validator.validate_completion(context)

        assert completed is False
        assert errors == [
            {
                "message": (
                    f"Ad '{ad_name}' has a payload that exceeds the maximum "
                    "allowed length in media 'elements', in channel "
                    f"'{channel_name}'."
                ),
                "code": "ADS_08_02",
                "metadata": {
                    "ad_name": ad_name,
                    "channel_name": channel_name,
                    "payload_length": len(payload),
                    "max_allowed_length": max_allowed_length,
                    "element_name": element_name,
                },
            }
        ]

    # Feature: funnel-flow-validator-tests, Property 13: Todo contexto de
    # anuncio válido completa sin errores.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        ad_set_specs=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=24),
                st.text(min_size=1, max_size=24),
                st.lists(
                    st.tuples(
                        st.text(min_size=1, max_size=24),
                        st.text(min_size=1, max_size=40),
                        st.text(min_size=1, max_size=24),
                        st.text(min_size=1, max_size=24),
                        st.text(min_size=1, max_size=24),
                        st.text(min_size=1, max_size=24),
                        st.text(min_size=1, max_size=40),
                        st.text(min_size=1, max_size=24),
                        st.text(min_size=1, max_size=24),
                        st.text(min_size=1, max_size=40),
                    ),
                    min_size=1,
                    max_size=3,
                ),
            ),
            min_size=1,
            max_size=3,
        )
    )
    def test_property_every_valid_ads_context_completes_without_errors(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        ad_set_specs: List[
            Tuple[str, str, List[Tuple[str, ...]]]
        ],
    ) -> None:
        """Every constructively valid generated context completes cleanly.

        **Validates: Requirements 6.29**
        """
        context: List[Dict[str, Any]] = []
        for ad_set_index, (
            ad_set_name,
            project_id,
            ad_specs,
        ) in enumerate(ad_set_specs):
            ads: List[Dict[str, Any]] = []
            for ad_index, ad_spec in enumerate(ad_specs):
                (
                    ad_name,
                    ad_url,
                    channel_name,
                    attribute_name,
                    attribute_payload,
                    element_name,
                    original_payload,
                    intention,
                    visual_id,
                    visual_url,
                ) = ad_spec
                selected_channel = make_valid_selected_channel(
                    channel_id=f"channel-{ad_set_index}-{ad_index}",
                    channel_name=channel_name,
                    template_id=f"template-{ad_set_index}-{ad_index}",
                    attribute_name=attribute_name,
                    attribute_payload=attribute_payload,
                    max_char=len(attribute_payload),
                    element_name=element_name,
                    original_payload=original_payload,
                    element_payload=original_payload,
                    intention=intention,
                )
                selected_channel["media"]["images_banner"] = [
                    {"id": f"image-{ad_set_index}-{ad_index}"}
                ]
                selected_channel["media"]["formats"] = [
                    {
                        "visual_id": visual_id,
                        "visual_url": visual_url,
                        "pinned": True,
                    }
                ]
                ads.append(
                    make_consolidated_ad(
                        ad_id=f"ad-{ad_set_index}-{ad_index}",
                        name=ad_name,
                        url=ad_url,
                        ad_channels=[selected_channel],
                    )
                )

            context.append(
                make_consolidated_ad_set(
                    ad_set_id=f"ad-set-{ad_set_index}",
                    name=ad_set_name,
                    media_platform_project_id=project_id,
                    ads=ads,
                    audiences=[
                        {"preferred_audience": {"preferred": 1}}
                    ],
                    experiments=[{"id": f"experiment-{ad_set_index}"}],
                )
            )

        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "ads"
        )

        completed, errors = validator.validate_completion(context)

        assert completed is True
        assert errors == []

    # Feature: funnel-flow-validator-tests, Property 14: Las infracciones
    # independientes se acumulan de forma estable.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        ad_set_violations=st.lists(
            st.lists(
                st.fixed_dictionaries(
                    {
                        "missing_url": st.booleans(),
                        "attribute_overflow": st.booleans(),
                        "element_overflow": st.booleans(),
                        "missing_visual_id": st.booleans(),
                        "missing_visual_url": st.booleans(),
                    }
                ),
                min_size=1,
                max_size=3,
            ),
            min_size=1,
            max_size=3,
        )
    )
    def test_property_independent_violations_accumulate_stably(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        ad_set_violations: List[List[Dict[str, bool]]],
    ) -> None:
        """Every independent violation contributes one error in code order.

        **Validates: Requirements 6.30, 6.31**
        """
        context: List[Dict[str, Any]] = []
        expected_errors: List[Dict[str, Any]] = []

        for ad_set_index, ad_violations in enumerate(ad_set_violations):
            ad_set_name = f"Property Set {ad_set_index}"
            ads: List[Dict[str, Any]] = []

            for ad_index, violations in enumerate(ad_violations):
                ad_name = f"Property Ad {ad_set_index}-{ad_index}"
                channel_name = f"Property Channel {ad_set_index}-{ad_index}"
                channel = make_valid_selected_channel(
                    channel_name=channel_name,
                )

                if violations["attribute_overflow"]:
                    channel["channel_attributes"] = [
                        {
                            "name": "Headline",
                            "max_char": 1,
                            "payloads": [{"payload": "xx"}],
                        }
                    ]
                if violations["element_overflow"]:
                    channel["media"]["elements"] = [
                        {
                            "name": "Element",
                            "original_payload": "x",
                            "payload": "xxx",
                            "intention": "awareness",
                        }
                    ]
                if violations["missing_visual_id"]:
                    channel["media"]["formats"][0]["visual_id"] = ""
                if violations["missing_visual_url"]:
                    channel["media"]["formats"][0]["visual_url"] = ""

                ad_url: Any = (
                    _OMITTED
                    if violations["missing_url"]
                    else f"https://example.test/{ad_set_index}/{ad_index}"
                )
                ads.append(
                    make_consolidated_ad(
                        ad_id=f"property-ad-{ad_set_index}-{ad_index}",
                        name=ad_name,
                        url=ad_url,
                        ad_channels=[channel],
                    )
                )

                if violations["missing_url"]:
                    expected_errors.append(
                        {
                            "message": f"Ad '{ad_name}' missing redirect url",
                            "code": "ADS_06",
                            "metadata": {"ad_name": ad_name},
                        }
                    )
                if violations["attribute_overflow"]:
                    expected_errors.append(
                        {
                            "message": (
                                f"Ad '{ad_name}' has a payload that exceeds "
                                "the maximum allowed length in channel "
                                f"attributes, in channel '{channel_name}'."
                            ),
                            "code": "ADS_05_02",
                            "metadata": {
                                "ad_name": ad_name,
                                "channel_name": channel_name,
                                "payload_length": 2,
                                "max_allowed_length": 1,
                                "attribute_name": "Headline",
                            },
                        }
                    )
                if violations["element_overflow"]:
                    expected_errors.append(
                        {
                            "message": (
                                f"Ad '{ad_name}' has a payload that exceeds "
                                "the maximum allowed length in media "
                                f"'elements', in channel '{channel_name}'."
                            ),
                            "code": "ADS_08_02",
                            "metadata": {
                                "ad_name": ad_name,
                                "channel_name": channel_name,
                                "payload_length": 3,
                                "max_allowed_length": 2,
                                "element_name": "Element",
                            },
                        }
                    )
                if violations["missing_visual_id"]:
                    expected_errors.append(
                        {
                            "message": (
                                f"Ad '{ad_name}' visual id not found in media "
                                f"'formats', in channel '{channel_name}'."
                            ),
                            "code": "ADS_07_01",
                            "metadata": {
                                "ad_name": ad_name,
                                "media_element": "formats",
                                "channel_name": channel_name,
                            },
                        }
                    )
                if violations["missing_visual_url"]:
                    expected_errors.append(
                        {
                            "message": (
                                f"Ad '{ad_name}' image link not found in media "
                                f"'formats', in channel '{channel_name}'."
                            ),
                            "code": "ADS_07_02",
                            "metadata": {
                                "ad_name": ad_name,
                                "media_element": "formats",
                                "channel_name": channel_name,
                            },
                        }
                    )

            context.append(
                make_consolidated_ad_set(
                    ad_set_id=f"property-set-{ad_set_index}",
                    name=ad_set_name,
                    media_platform_project_id=(
                        f"property-project-{ad_set_index}"
                    ),
                    ads=ads,
                    audiences=[
                        {"preferred_audience": {"preferred": 1}}
                    ],
                    experiments=[
                        {"id": f"property-experiment-{ad_set_index}"}
                    ],
                )
            )

        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "ads"
        )

        completed, errors = validator.validate_completion(context)

        assert completed is (not expected_errors)
        assert len(errors) == len(expected_errors)
        assert errors == expected_errors

    # Feature: funnel-flow-validator-tests, Property 15: Los agregados
    # reflejan exactamente las dependencias fallidas.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        aggregate_case=st.sampled_from(
            tuple(
                (
                    validator_key,
                    code_prefix,
                    tuple(
                        dependency_index
                        for dependency_index in range(5)
                        if failure_mask & (1 << dependency_index)
                    ),
                )
                for validator_key, code_prefix in (
                    ("summary", "SUM"),
                    ("review", "REV"),
                    ("launchpad", "LAUNCH"),
                )
                for failure_mask in range(1 << 5)
            )
        )
    )
    def test_property_aggregates_exactly_reflect_failed_dependencies(
        self,
        use_case_factory: Callable[
            ...,
            Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
        ],
        aggregate_case: Tuple[str, str, Tuple[int, ...]],
    ) -> None:
        """Every aggregate and failure subset yields the exact ordered result.

        **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6,
        7.7, 7.8, 7.9, 7.10, 7.11**
        """
        validator_key, code_prefix, failed_dependency_indexes = aggregate_case
        dependency_names = (
            "ChannelValidator",
            "AdsStructureValidator",
            "AudiencesValidator",
            "ExperimentsValidator",
            "AdsContentValidator",
        )
        dependency_messages = (
            "Ad Channel is not completed.",
            "Ads Structure is not completed.",
            "Audiences is not completed.",
            "Ads Experiment is not completed.",
            "Ads is not completed.",
        )
        constructors: Dict[str, MagicMock] = {}
        for index, dependency_name in enumerate(dependency_names):
            constructor = MagicMock(name=f"{dependency_name}Class")
            constructor.return_value.validate_completion.return_value = (
                index not in failed_dependency_indexes,
                [{"ignored_dependency_error": index}],
            )
            constructors[dependency_name] = constructor

        context: List[Dict[str, Any]] = [{"context": "same-object"}]
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == validator_key
        )

        with patch.multiple(
            "app.v2.use_cases.funnel_flow_validator",
            **constructors,
        ):
            completed, errors = validator.validate_completion(context)

        assert completed is (not failed_dependency_indexes)
        assert errors == [
            {
                "message": dependency_messages[index],
                "code": f"{code_prefix}_{index + 1:02d}",
                "metadata": {},
            }
            for index in failed_dependency_indexes
        ]
        assert [error["code"] for error in errors] == [
            f"{code_prefix}_{index + 1:02d}"
            for index in failed_dependency_indexes
        ]
        assert all(error["metadata"] == {} for error in errors)
        for constructor in constructors.values():
            constructor.assert_called_once_with()
            dependency_double = constructor.return_value
            dependency_double.validate_completion.assert_called_once_with(
                context
            )
            assert (
                dependency_double.validate_completion.call_args.args[0]
                is context
            )


class _OmittedType:
    """Marker used to omit a field while allowing an explicit ``None`` value."""


_OMITTED = _OmittedType()


def _set_if_present(target: Dict[str, Any], key: str, value: Any) -> None:
    """Set a deeply copied value unless the caller explicitly requests omission."""
    if value is not _OMITTED:
        target[key] = deepcopy(value)


def make_funnel_flow(flow_id: Any = 1) -> Dict[str, Any]:
    """Build a minimal raw funnel flow with no shared mutable state."""
    funnel_flow: Dict[str, Any] = {}
    _set_if_present(funnel_flow, "id", flow_id)
    return funnel_flow


def make_channel(
    channel_id: Any = 10,
    name: Any = "Search",
) -> Dict[str, Any]:
    """Build a minimal raw funnel-flow channel."""
    attributes: Dict[str, Any] = {}
    _set_if_present(attributes, "name", name)

    channel: Dict[str, Any] = {"attributes": attributes}
    _set_if_present(channel, "id", channel_id)
    return channel


def make_raw_ad(
    ad_id: Any = 100,
    name: Any = "Ad",
    redirect_url: Any = "https://example.test/ad",
) -> Dict[str, Any]:
    """Build an ad in the Strapi shape consumed by the use case."""
    attributes: Dict[str, Any] = {}
    _set_if_present(attributes, "name", name)
    _set_if_present(attributes, "redirect_url", redirect_url)

    ad: Dict[str, Any] = {"attributes": attributes}
    _set_if_present(ad, "id", ad_id)
    return ad


def make_raw_ad_set(
    ad_set_id: Any = 20,
    name: Any = "Ad Set",
    ads: Any = _OMITTED,
    project_id: Any = "project-1",
) -> Dict[str, Any]:
    """Build a raw ad set, preserving omitted fields versus explicit ``None``."""
    attributes: Dict[str, Any] = {}
    _set_if_present(attributes, "name", name)

    if ads is not _OMITTED:
        attributes["ads"] = {"data": deepcopy(ads)}

    if project_id is not _OMITTED:
        project_data = (
            None
            if project_id is None
            else {"attributes": {"project_id": deepcopy(project_id)}}
        )
        attributes["media_platform_project_id"] = {"data": project_data}

    ad_set: Dict[str, Any] = {"attributes": attributes}
    _set_if_present(ad_set, "id", ad_set_id)
    return ad_set


def make_raw_audience(
    audience_id: Any = 30,
    ad_set_id: Any = 20,
    channel_id: Any = 10,
    channel_name: Any = "Search",
    generation_method: Any = "manual",
    preferred: Any = 1,
    proposal_audiences: Any = _OMITTED,
) -> Dict[str, Any]:
    """Build a raw audience relation with fresh nested relationship objects."""
    attributes: Dict[str, Any] = {}

    if ad_set_id is not _OMITTED:
        attributes["ad_set_ref"] = {
            "data": None if ad_set_id is None else {"id": deepcopy(ad_set_id)}
        }

    if channel_id is not _OMITTED:
        channel_data = None
        if channel_id is not None:
            channel_attributes: Dict[str, Any] = {}
            _set_if_present(channel_attributes, "name", channel_name)
            channel_data = {
                "id": deepcopy(channel_id),
                "attributes": channel_attributes,
            }
        attributes["channel_ref"] = {"data": channel_data}

    _set_if_present(attributes, "generation_method", generation_method)
    if preferred is not _OMITTED:
        attributes["preferred_audience"] = {"preferred": deepcopy(preferred)}
    _set_if_present(attributes, "proposal_audiences", proposal_audiences)

    audience: Dict[str, Any] = {"attributes": attributes}
    _set_if_present(audience, "id", audience_id)
    return audience


def make_raw_experiment(
    experiment_id: Any = 40,
    ad_set_id: Any = 20,
    experiment_type: Any = "copy",
    subcategory_id: Any = 400,
    subcategory_name: Any = "Messaging",
    subcategory_description: Any = "Messaging experiment",
    category_id: Any = 401,
    category_name: Any = "Creative",
    category_description: Any = "Creative category",
) -> Dict[str, Any]:
    """Build a raw experiment with its complete projected category hierarchy."""
    attributes: Dict[str, Any] = {}

    if ad_set_id is not _OMITTED:
        attributes["ad_set_ref"] = {
            "data": None if ad_set_id is None else {"id": deepcopy(ad_set_id)}
        }

    _set_if_present(attributes, "type", experiment_type)

    if subcategory_id is not _OMITTED:
        subcategory_data = None
        if subcategory_id is not None:
            category_data = None
            if category_id is not _OMITTED and category_id is not None:
                category_attributes: Dict[str, Any] = {}
                _set_if_present(category_attributes, "name", category_name)
                _set_if_present(
                    category_attributes,
                    "description",
                    category_description,
                )
                category_data = {
                    "id": deepcopy(category_id),
                    "attributes": category_attributes,
                }

            subcategory_attributes: Dict[str, Any] = {}
            _set_if_present(subcategory_attributes, "name", subcategory_name)
            _set_if_present(
                subcategory_attributes,
                "description",
                subcategory_description,
            )
            if category_id is not _OMITTED:
                subcategory_attributes["category_ref"] = {"data": category_data}

            subcategory_data = {
                "id": deepcopy(subcategory_id),
                "attributes": subcategory_attributes,
            }

        attributes["subcategory_ref"] = {"data": subcategory_data}

    experiment: Dict[str, Any] = {"attributes": attributes}
    _set_if_present(experiment, "id", experiment_id)
    return experiment


def make_raw_ad_channel(
    channel_record_id: Any = 50,
    ad_id: Any = 100,
    channel_id: Any = 10,
    channel_name: Any = "Search",
    template_id: Any = "template-1",
    elements: Any = _OMITTED,
    images_banner: Any = _OMITTED,
    formats: Any = _OMITTED,
    channel_attributes: Any = _OMITTED,
    redirect_url: Any = "https://example.test/channel",
    selected: Any = True,
) -> Dict[str, Any]:
    """Build a raw ad-channel relation in the exact mapping input shape."""
    attributes: Dict[str, Any] = {}

    if ad_id is not _OMITTED:
        attributes["ad_ref"] = {
            "data": None if ad_id is None else {"id": deepcopy(ad_id)}
        }

    if channel_id is not _OMITTED:
        channel_data = None
        if channel_id is not None:
            raw_channel_attributes: Dict[str, Any] = {}
            _set_if_present(raw_channel_attributes, "name", channel_name)
            channel_data = {
                "id": deepcopy(channel_id),
                "attributes": raw_channel_attributes,
            }
        attributes["channel_ref"] = {"data": channel_data}

    _set_if_present(attributes, "media_template_id", template_id)
    _set_if_present(attributes, "media_elements", elements)
    _set_if_present(attributes, "media_images_banner", images_banner)
    _set_if_present(attributes, "media_formats", formats)
    _set_if_present(attributes, "channel_attributes", channel_attributes)
    _set_if_present(attributes, "redirect_url", redirect_url)
    _set_if_present(attributes, "selected", selected)

    ad_channel: Dict[str, Any] = {"attributes": attributes}
    _set_if_present(ad_channel, "id", channel_record_id)
    return ad_channel


def make_consolidated_ad(
    ad_id: Any = 100,
    name: Any = "Ad",
    url: Any = "https://example.test/ad",
    ad_channels: Any = _OMITTED,
) -> Dict[str, Any]:
    """Build the ad shape validated after Strapi data consolidation."""
    attributes: Dict[str, Any] = {}
    _set_if_present(attributes, "name", name)
    _set_if_present(attributes, "url", url)
    _set_if_present(attributes, "ad_channels", ad_channels)

    ad: Dict[str, Any] = {"attributes": attributes}
    _set_if_present(ad, "id", ad_id)
    return ad


def make_consolidated_ad_set(
    ad_set_id: Any = 20,
    name: Any = "Ad Set",
    media_platform_project_id: Any = "project-1",
    ads: Any = _OMITTED,
    audiences: Any = _OMITTED,
    experiments: Any = _OMITTED,
) -> Dict[str, Any]:
    """Build a consolidated ad set with independently fresh collections."""
    ad_set: Dict[str, Any] = {}
    _set_if_present(ad_set, "id", ad_set_id)
    _set_if_present(ad_set, "name", name)
    _set_if_present(
        ad_set,
        "media_platform_project_id",
        media_platform_project_id,
    )
    _set_if_present(ad_set, "ads", ads)
    _set_if_present(ad_set, "audiences", audiences)
    _set_if_present(ad_set, "experiments", experiments)
    return ad_set


def make_valid_selected_channel(
    channel_id: Any = 10,
    channel_name: Any = "Search",
    template_id: Any = "template-1",
    attribute_name: Any = "Headline",
    attribute_payload: Any = "Campaign headline",
    max_char: Any = 255,
    element_name: Any = "Headline",
    original_payload: Any = "Original headline",
    element_payload: Any = "Original headline",
    intention: Any = "awareness",
) -> Dict[str, Any]:
    """Build a selected channel satisfying all AdsContentValidator rules."""
    channel_attributes: List[Dict[str, Any]] = [
        {
            "name": deepcopy(attribute_name),
            "max_char": deepcopy(max_char),
            "payloads": [{"payload": deepcopy(attribute_payload)}],
        }
    ]
    elements: List[Dict[str, Any]] = [
        {
            "name": deepcopy(element_name),
            "original_payload": deepcopy(original_payload),
            "payload": deepcopy(element_payload),
            "intention": deepcopy(intention),
        }
    ]
    images_banner: List[Dict[str, Any]] = [{"id": "image-1"}]
    formats: List[Dict[str, Any]] = [
        {
            "visual_id": "visual-1",
            "visual_url": "https://example.test/visual-1.png",
            "pinned": True,
        }
    ]

    return {
        "channel_id": deepcopy(channel_id),
        "channel_name": deepcopy(channel_name),
        "media": {
            "template_id": deepcopy(template_id),
            "elements": elements,
            "images_banner": images_banner,
            "formats": formats,
        },
        "channel_attributes": channel_attributes,
        "url": "https://example.test/channel",
        "selected": True,
    }


def make_valid_ads_context(
    ad_set_id: Any = 20,
    ad_set_name: Any = "Ad Set",
    ad_id: Any = 100,
    ad_name: Any = "Ad",
) -> List[Dict[str, Any]]:
    """Build a fully valid, fresh consolidated context for ads validators."""
    selected_channel = make_valid_selected_channel()
    ad = make_consolidated_ad(
        ad_id=ad_id,
        name=ad_name,
        ad_channels=[selected_channel],
    )
    audience: Dict[str, Any] = {
        "preferred_audience": {"preferred": 1},
    }
    experiment: Dict[str, Any] = {"id": 40, "type": "copy"}
    ad_set = make_consolidated_ad_set(
        ad_set_id=ad_set_id,
        name=ad_set_name,
        ads=[ad],
        audiences=[audience],
        experiments=[experiment],
    )
    return [ad_set]


StrapiResponseMap = Mapping[str, Any]
UseCaseFactory = Callable[
    [str, Optional[StrapiResponseMap], Optional[StrapiResponseMap]],
    Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock],
]


def _configured_response(
    responses: StrapiResponseMap,
    method_name: str,
    endpoint: str,
) -> Any:
    """Return an in-memory endpoint response or fail on an unplanned call."""
    if endpoint not in responses:
        raise AssertionError(
            f"unexpected Strapi {method_name} endpoint: {endpoint!r}"
        )

    response = responses[endpoint]
    if isinstance(response, BaseException):
        raise response
    return response


@pytest.fixture(scope="function")
def mock_strapi_client() -> Generator[MagicMock, None, None]:
    """Patch the exact imported Strapi symbol for one test function.

    Validates: Requirements 1.2-1.4, 1.6, 8.7.
    """
    with patch(
        "app.v2.use_cases.funnel_flow_validator.StrapiClient"
    ) as constructor_mock:
        yield constructor_mock


@pytest.fixture(scope="function")
def use_case_factory(mock_strapi_client: MagicMock) -> UseCaseFactory:
    """Create fresh use cases and strict in-memory Strapi doubles.

    The constructor patch is already active when the use case is instantiated.
    Validates: Requirements 1.1-1.4, 1.7-1.9, 8.3, 8.7.
    """

    def factory(
        campaign_id: str = "campaign-1",
        find_responses: Optional[StrapiResponseMap] = None,
        get_responses: Optional[StrapiResponseMap] = None,
    ) -> Tuple[FunnelFlowValidatorUseCase, MagicMock, MagicMock]:
        find_responses_snapshot = dict(find_responses or {})
        get_responses_snapshot = dict(get_responses or {})
        strapi_mock = MagicMock(spec=RealStrapiClient)

        def find_by_filters(endpoint: str, **_kwargs: Any) -> Any:
            return _configured_response(
                find_responses_snapshot,
                "find_by_filters",
                endpoint,
            )

        def get(endpoint: str, **_kwargs: Any) -> Any:
            return _configured_response(get_responses_snapshot, "get", endpoint)

        strapi_mock.find_by_filters.side_effect = find_by_filters
        strapi_mock.get.side_effect = get
        mock_strapi_client.return_value = strapi_mock

        use_case = FunnelFlowValidatorUseCase(campaign_id)
        return use_case, strapi_mock, mock_strapi_client

    return factory


@pytest.fixture(scope="function", autouse=True)
def deny_network() -> Generator[MagicMock, None, None]:
    """Fail immediately if this unit-test module attempts an HTTP request.

    Validates: Requirements 1.1, 1.5, 1.6, 1.9.
    """
    with patch(
        "requests.sessions.Session.request",
        side_effect=AssertionError("network access is forbidden in unit tests"),
    ) as request_mock:
        yield request_mock


def _mutable_object_ids(value: Any) -> List[int]:
    """Collect identities of every nested mutable list and dictionary."""
    mutable_ids: List[int] = []
    if isinstance(value, dict):
        mutable_ids.append(id(value))
        for nested_value in value.values():
            mutable_ids.extend(_mutable_object_ids(nested_value))
    elif isinstance(value, list):
        mutable_ids.append(id(value))
        for nested_value in value:
            mutable_ids.extend(_mutable_object_ids(nested_value))
    return mutable_ids


class TestUseCaseInitialization:
    """Characterize the use case's canonical initial configuration."""

    def test_state_map_has_canonical_order_and_pending_values(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """The eight initial states have exact order and pending values.

        Validates: Requirements 2.1, 2.2.
        """
        use_case, _, _ = use_case_factory()
        expected_state = {
            "channel": {
                "completed": False,
                "errors": [],
                "message": "Pending validation",
            },
            "ads_structure": {
                "completed": False,
                "errors": [],
                "message": "Pending validation",
            },
            "audiences": {
                "completed": False,
                "errors": [],
                "message": "Pending validation",
            },
            "ads_experiment": {
                "completed": False,
                "errors": [],
                "message": "Pending validation",
            },
            "ads": {
                "completed": False,
                "errors": [],
                "message": "Pending validation",
            },
            "summary": {
                "completed": False,
                "errors": [],
                "message": "Pending validation",
            },
            "review": {
                "completed": False,
                "errors": [],
                "message": "Pending validation",
            },
            "launchpad": {
                "completed": False,
                "errors": [],
                "message": "Pending validation",
            },
        }

        assert list(use_case._state_map) == list(expected_state)
        assert use_case._state_map == expected_state

    def test_validators_have_exact_count_and_canonical_key_order(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """The validator registry has eight instances in state-map order.

        Validates: Requirements 2.3.
        """
        use_case, _, _ = use_case_factory()
        validator_keys = [validator.key for validator in use_case.validators]

        assert len(use_case.validators) == 8
        assert len({id(validator) for validator in use_case.validators}) == 8
        assert validator_keys == list(use_case._state_map)


class TestUseCaseHelpers:
    """Characterize Strapi bulk fetching and validator dispatch helpers."""

    def test_fetch_bulk_calls_get_exactly_and_preserves_data_identity(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """Bulk fetching forwards exact arguments and returns data unchanged.

        Validates: Requirements 2.4, 2.5, 8.4.
        """
        data: List[Dict[str, Any]] = [{"id": 1}]
        params: Dict[str, Any] = {
            "filters[id][$in][0]": 1,
            "populate": "relation",
        }
        use_case, strapi_mock, _ = use_case_factory(
            get_responses={"bulk-endpoint": {"data": data}},
        )

        result = use_case._fetch_bulk("bulk-endpoint", params)

        strapi_mock.get.assert_called_once_with("bulk-endpoint", params=params)
        assert result is data

    def test_fetch_bulk_returns_empty_list_when_data_is_missing(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """A Strapi response without data uses the exact empty-list fallback.

        Validates: Requirements 2.4, 2.6, 8.4.
        """
        params: Dict[str, Any] = {"populate": "relation"}
        use_case, strapi_mock, _ = use_case_factory(
            get_responses={"bulk-endpoint": {"meta": {"count": 0}}},
        )

        result = use_case._fetch_bulk("bulk-endpoint", params)

        strapi_mock.get.assert_called_once_with("bulk-endpoint", params=params)
        assert result == []

    def test_run_validator_preserves_context_and_replaces_entire_state_entry(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """Registered dispatch preserves context and validator result identity.

        Validates: Requirements 2.7, 2.8, 8.5.
        """
        use_case, _, _ = use_case_factory()
        context: Dict[str, Any] = {"nested": ["same-object"]}
        errors: List[Dict[str, Any]] = [
            {
                "message": "Sentinel validation error",
                "code": "SENTINEL_ERR",
                "metadata": {"source": "double"},
            }
        ]
        validator = MagicMock()
        validator.key = "channel"
        validator.validate_completion.return_value = (False, errors)
        use_case.validators[0] = validator

        use_case._run_validator("channel", context)

        validator.validate_completion.assert_called_once_with(context)
        assert validator.validate_completion.call_args.args[0] is context
        assert use_case._state_map["channel"] == {
            "completed": False,
            "errors": errors,
        }
        assert use_case._state_map["channel"]["errors"] is errors

    def test_run_validator_unregistered_key_creates_exact_system_error_state(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """Missing dispatch creates only completed and the exact SYS_ERR.

        Validates: Requirements 2.9, 8.5.
        """
        use_case, _, _ = use_case_factory()

        use_case._run_validator("unregistered", {"unused": True})

        assert use_case._state_map["unregistered"] == {
            "completed": False,
            "errors": [
                {
                    "message": "Validator implementation missing",
                    "code": "SYS_ERR",
                }
            ],
        }

    def test_build_response_preserves_order_identity_and_only_missing_defaults(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """Response keeps canonical states and defaults only absent fields.

        Validates: Requirements 2.10, 2.11, 2.12, 7.12.
        """
        use_case, _, _ = use_case_factory()
        existing_errors: List[Dict[str, Any]] = [
            {"message": "Existing error", "code": "EXISTING"}
        ]
        use_case._state_map = {
            "channel": {
                "completed": True,
                "errors": existing_errors,
                "message": "Preserved message",
            },
            "ads_structure": {
                "errors": [{"message": "Structure", "code": "STRUCTURE"}],
                "custom": "preserved without completed",
            },
            "audiences": {
                "completed": False,
                "custom": "preserved without errors",
            },
            "ads_experiment": {"completed": None, "errors": None},
            "ads": {"completed": True, "errors": []},
            "summary": {"completed": False, "errors": []},
            "review": {"completed": True, "errors": []},
            "launchpad": {"completed": False, "errors": []},
        }
        funnel_flow_data: List[Dict[str, Any]] = [{"id": "same-object"}]

        response = use_case._build_response(funnel_flow_data)

        expected_states = [
            {
                "step": "channel",
                "completed": True,
                "errors": existing_errors,
                "message": "Preserved message",
            },
            {
                "step": "ads_structure",
                "errors": [{"message": "Structure", "code": "STRUCTURE"}],
                "custom": "preserved without completed",
                "completed": False,
            },
            {
                "step": "audiences",
                "completed": False,
                "custom": "preserved without errors",
                "errors": [],
            },
            {
                "step": "ads_experiment",
                "completed": None,
                "errors": None,
            },
            {"step": "ads", "completed": True, "errors": []},
            {"step": "summary", "completed": False, "errors": []},
            {"step": "review", "completed": True, "errors": []},
            {"step": "launchpad", "completed": False, "errors": []},
        ]
        steps = [state["step"] for state in response["state"]]

        assert response["funnel_flow_data"] is funnel_flow_data
        assert response["state"] == expected_states
        assert steps == list(use_case._state_map)
        assert len(steps) == len(set(steps)) == 8
        assert response["state"][0]["errors"] is existing_errors

    @pytest.mark.parametrize(
        ("original_length", "expected_maximum"),
        [(0, 0), (1, 2), (49, 59), (50, 60), (51, 61)],
        ids=["zero", "one", "below-cap", "at-cap", "above-cap"],
    )
    def test_get_max_length_allowed_returns_expected_boundary_values(
        self,
        use_case_factory: UseCaseFactory,
        original_length: int,
        expected_maximum: int,
    ) -> None:
        """Length allowance follows the 20 percent margin capped at ten.

        Validates: Requirements 2.13, 2.14.
        """
        use_case, _, _ = use_case_factory()
        ads_validator = next(
            validator for validator in use_case.validators if validator.key == "ads"
        )

        result = getattr(ads_validator, "_get_max_length_allowed")(
            original_length
        )

        assert result == expected_maximum


@pytest.mark.parametrize(
    "builder",
    [
        make_funnel_flow,
        make_channel,
        make_raw_ad,
        make_raw_ad_set,
        make_raw_audience,
        make_raw_experiment,
        make_raw_ad_channel,
        make_consolidated_ad,
        make_consolidated_ad_set,
        make_valid_selected_channel,
        make_valid_ads_context,
    ],
    ids=lambda builder: builder.__name__,
)
def test_builders_do_not_share_nested_mutables(
    builder: Callable[[], Any],
) -> None:
    """Each builder invocation owns all nested mutable values.

    Validates: Requirements 1.7, 1.8, 8.3, 8.7.
    """
    first = builder()
    second = builder()

    assert first == second
    assert set(_mutable_object_ids(first)).isdisjoint(_mutable_object_ids(second))

    if isinstance(first, dict):
        first["test_mutation"] = True
        assert "test_mutation" not in second
    else:
        first.append({"test_mutation": True})
        assert {"test_mutation": True} not in second


def test_use_case_factory_patches_constructor_before_fresh_construction(
    use_case_factory: UseCaseFactory,
) -> None:
    """The patched constructor supplies a new use case and double each time.

    Validates: Requirements 1.2, 1.3, 1.4, 1.7, 1.8.
    """
    first_use_case, first_strapi, constructor = use_case_factory("campaign-1")
    second_use_case, second_strapi, second_constructor = use_case_factory(
        "campaign-2"
    )

    assert first_use_case is not second_use_case
    assert first_strapi is not second_strapi
    assert first_use_case.strapi_service is first_strapi
    assert second_use_case.strapi_service is second_strapi
    assert constructor is second_constructor
    assert constructor.call_count == 2


def test_use_case_factory_uses_memory_responses_and_rejects_unknown_endpoints(
    use_case_factory: UseCaseFactory,
) -> None:
    """Configured calls preserve response identity; unknown calls fail fast.

    Validates: Requirements 1.3, 1.4, 1.5, 8.7.
    """
    find_response = {"data": [make_funnel_flow()]}
    get_response = {"data": [make_channel()]}
    use_case, strapi_mock, _ = use_case_factory(
        find_responses={"funnel-flows": find_response},
        get_responses={"funnel-flow-channels": get_response},
    )

    assert use_case.strapi_service is strapi_mock
    assert (
        strapi_mock.find_by_filters(
            "funnel-flows",
            filters={"campaign_ref": "campaign-1"},
        )
        is find_response
    )
    assert strapi_mock.get("funnel-flow-channels", params={}) is get_response

    with pytest.raises(
        AssertionError,
        match="unexpected Strapi find_by_filters endpoint: 'unknown-find'",
    ):
        strapi_mock.find_by_filters("unknown-find", filters={})

    with pytest.raises(
        AssertionError,
        match="unexpected Strapi get endpoint: 'unknown-get'",
    ):
        strapi_mock.get("unknown-get", params={})


def test_network_guard_blocks_session_requests(deny_network: MagicMock) -> None:
    """The local autouse guard prevents requests without Flask infrastructure.

    Validates: Requirements 1.1, 1.5, 1.6, 1.9, 1.10.
    """
    with pytest.raises(
        AssertionError,
        match="network access is forbidden in unit tests",
    ):
        requests.Session().request("GET", "https://example.test")

    deny_network.assert_called_once()


class TestExecuteOrchestration:
    """Characterize successful fetching, consolidation, and validation."""

    def test_execute_success_consolidates_all_relations_and_queries_exactly(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """A multi-parent flow preserves projections and completes every stage.

        Validates: Requirements 3.1-3.13, 7.12, 8.4, 8.5.
        """
        funnel_flows = [
            make_funnel_flow(flow_id="flow-1"),
            make_funnel_flow(flow_id="flow-2"),
        ]
        channels = [
            make_channel(channel_id=11, name="Search"),
            make_channel(channel_id=12, name="Social"),
        ]
        raw_ads = {
            101: make_raw_ad(
                ad_id=101,
                name="Search Alpha",
                redirect_url="https://example.test/search-alpha",
            ),
            102: make_raw_ad(
                ad_id=102,
                name="Social Beta",
                redirect_url="https://example.test/social-beta",
            ),
            201: make_raw_ad(
                ad_id=201,
                name="Display Gamma",
                redirect_url="https://example.test/display-gamma",
            ),
        }
        ad_sets = [
            make_raw_ad_set(
                ad_set_id=21,
                name="Prospecting",
                ads=[raw_ads[101], raw_ads[102]],
                project_id="media-project-a",
            ),
            make_raw_ad_set(
                ad_set_id=22,
                name="Retargeting",
                ads=[raw_ads[201]],
                project_id="media-project-b",
            ),
        ]
        audiences = [
            make_raw_audience(
                audience_id=301,
                ad_set_id=21,
                channel_id=11,
                channel_name="Search",
                generation_method="manual-a",
                preferred=1,
                proposal_audiences=[{"segment": "new-users"}],
            ),
            make_raw_audience(
                audience_id=302,
                ad_set_id=22,
                channel_id=12,
                channel_name="Social",
                generation_method="automatic-b",
                preferred=1,
                proposal_audiences=[{"segment": "returning-users"}],
            ),
        ]
        experiments = [
            make_raw_experiment(
                experiment_id=401,
                ad_set_id=21,
                experiment_type="copy-a",
                subcategory_id=411,
                subcategory_name="Headlines",
                subcategory_description="Headline variants",
                category_id=421,
                category_name="Copy",
                category_description="Copy experiments",
            ),
            make_raw_experiment(
                experiment_id=402,
                ad_set_id=22,
                experiment_type="visual-b",
                subcategory_id=412,
                subcategory_name="Images",
                subcategory_description="Image variants",
                category_id=422,
                category_name="Creative",
                category_description="Creative experiments",
            ),
        ]
        ad_channels = [
            make_raw_ad_channel(
                channel_record_id=501,
                ad_id=101,
                channel_id=11,
                channel_name="Search",
                template_id="template-search",
                elements=[
                    {
                        "name": "Headline",
                        "original_payload": "Alpha headline",
                        "payload": "Alpha headline",
                        "intention": "awareness",
                    }
                ],
                images_banner=[{"id": "image-search"}],
                formats=[
                    {
                        "visual_id": "visual-search",
                        "visual_url": "https://example.test/search.png",
                        "pinned": True,
                    }
                ],
                channel_attributes=[
                    {
                        "name": "Headline",
                        "max_char": 50,
                        "payloads": [{"payload": "Alpha headline"}],
                    }
                ],
                redirect_url="https://example.test/search-channel",
                selected=True,
            ),
            make_raw_ad_channel(
                channel_record_id=502,
                ad_id=102,
                channel_id=12,
                channel_name="Social",
                template_id="template-social",
                elements=[
                    {
                        "name": "Primary text",
                        "original_payload": "Beta text",
                        "payload": "Beta text",
                        "intention": "conversion",
                    }
                ],
                images_banner=[{"id": "image-social"}],
                formats=[
                    {
                        "visual_id": "visual-social",
                        "visual_url": "https://example.test/social.png",
                        "pinned": True,
                    }
                ],
                channel_attributes=[
                    {
                        "name": "Primary text",
                        "max_char": 50,
                        "payloads": [{"payload": "Beta text"}],
                    }
                ],
                redirect_url="https://example.test/social-channel",
                selected=True,
            ),
            make_raw_ad_channel(
                channel_record_id=503,
                ad_id=201,
                channel_id=13,
                channel_name="Display",
                template_id="template-display",
                elements=[
                    {
                        "name": "Banner text",
                        "original_payload": "Gamma banner",
                        "payload": "Gamma banner",
                        "intention": "retargeting",
                    }
                ],
                images_banner=[{"id": "image-display"}],
                formats=[
                    {
                        "visual_id": "visual-display",
                        "visual_url": "https://example.test/display.png",
                        "pinned": True,
                    }
                ],
                channel_attributes=[
                    {
                        "name": "Banner text",
                        "max_char": 50,
                        "payloads": [{"payload": "Gamma banner"}],
                    }
                ],
                redirect_url="https://example.test/display-channel",
                selected=True,
            ),
        ]
        use_case, strapi_mock, _ = use_case_factory(
            campaign_id="campaign-success",
            find_responses={
                "funnel-flows": {"data": funnel_flows},
                "funnel-flow-channels": {"data": channels},
            },
            get_responses={
                "ad-sets": {"data": ad_sets},
                "audience-audiences": {"data": audiences},
                "experiment-experiments": {"data": experiments},
                "ad-channels": {"data": ad_channels},
            },
        )

        response, status_code = use_case.execute()

        expected_ad_channels = {
            101: {
                "channel_id": 11,
                "channel_name": "Search",
                "media": {
                    "template_id": "template-search",
                    "elements": [
                        {
                            "name": "Headline",
                            "original_payload": "Alpha headline",
                            "payload": "Alpha headline",
                            "intention": "awareness",
                        }
                    ],
                    "images_banner": [{"id": "image-search"}],
                    "formats": [
                        {
                            "visual_id": "visual-search",
                            "visual_url": "https://example.test/search.png",
                            "pinned": True,
                        }
                    ],
                },
                "channel_attributes": [
                    {
                        "name": "Headline",
                        "max_char": 50,
                        "payloads": [{"payload": "Alpha headline"}],
                    }
                ],
                "url": "https://example.test/search-channel",
                "selected": True,
            },
            102: {
                "channel_id": 12,
                "channel_name": "Social",
                "media": {
                    "template_id": "template-social",
                    "elements": [
                        {
                            "name": "Primary text",
                            "original_payload": "Beta text",
                            "payload": "Beta text",
                            "intention": "conversion",
                        }
                    ],
                    "images_banner": [{"id": "image-social"}],
                    "formats": [
                        {
                            "visual_id": "visual-social",
                            "visual_url": "https://example.test/social.png",
                            "pinned": True,
                        }
                    ],
                },
                "channel_attributes": [
                    {
                        "name": "Primary text",
                        "max_char": 50,
                        "payloads": [{"payload": "Beta text"}],
                    }
                ],
                "url": "https://example.test/social-channel",
                "selected": True,
            },
            201: {
                "channel_id": 13,
                "channel_name": "Display",
                "media": {
                    "template_id": "template-display",
                    "elements": [
                        {
                            "name": "Banner text",
                            "original_payload": "Gamma banner",
                            "payload": "Gamma banner",
                            "intention": "retargeting",
                        }
                    ],
                    "images_banner": [{"id": "image-display"}],
                    "formats": [
                        {
                            "visual_id": "visual-display",
                            "visual_url": "https://example.test/display.png",
                            "pinned": True,
                        }
                    ],
                },
                "channel_attributes": [
                    {
                        "name": "Banner text",
                        "max_char": 50,
                        "payloads": [{"payload": "Gamma banner"}],
                    }
                ],
                "url": "https://example.test/display-channel",
                "selected": True,
            },
        }
        expected_funnel_flow_data = [
            {
                "id": 21,
                "name": "Prospecting",
                "media_platform_project_id": "media-project-a",
                "ads": [
                    {
                        "id": 101,
                        "attributes": {
                            "name": "Search Alpha",
                            "ad_channels": [expected_ad_channels[101]],
                            "url": "https://example.test/search-alpha",
                        },
                    },
                    {
                        "id": 102,
                        "attributes": {
                            "name": "Social Beta",
                            "ad_channels": [expected_ad_channels[102]],
                            "url": "https://example.test/social-beta",
                        },
                    },
                ],
                "audiences": [
                    {
                        "channel_id": 11,
                        "channel_name": "Search",
                        "generation_method": "manual-a",
                        "preferred_audience": {"preferred": 1},
                        "proposal_audiences": [{"segment": "new-users"}],
                    }
                ],
                "experiments": [
                    {
                        "id": 401,
                        "type": "copy-a",
                        "subcategory": {
                            "id": 411,
                            "name": "Headlines",
                            "description": "Headline variants",
                            "category": {
                                "id": 421,
                                "name": "Copy",
                                "description": "Copy experiments",
                            },
                        },
                    }
                ],
            },
            {
                "id": 22,
                "name": "Retargeting",
                "media_platform_project_id": "media-project-b",
                "ads": [
                    {
                        "id": 201,
                        "attributes": {
                            "name": "Display Gamma",
                            "ad_channels": [expected_ad_channels[201]],
                            "url": "https://example.test/display-gamma",
                        },
                    }
                ],
                "audiences": [
                    {
                        "channel_id": 12,
                        "channel_name": "Social",
                        "generation_method": "automatic-b",
                        "preferred_audience": {"preferred": 1},
                        "proposal_audiences": [
                            {"segment": "returning-users"}
                        ],
                    }
                ],
                "experiments": [
                    {
                        "id": 402,
                        "type": "visual-b",
                        "subcategory": {
                            "id": 412,
                            "name": "Images",
                            "description": "Image variants",
                            "category": {
                                "id": 422,
                                "name": "Creative",
                                "description": "Creative experiments",
                            },
                        },
                    }
                ],
            },
        ]
        expected_steps = [
            "channel",
            "ads_structure",
            "audiences",
            "ads_experiment",
            "ads",
            "summary",
            "review",
            "launchpad",
        ]

        assert status_code == 200
        assert response["ok"] == 1
        assert response["data"]["funnel_flow_data"] == expected_funnel_flow_data
        assert response["data"]["state"] == [
            {"step": step, "completed": True, "errors": []}
            for step in expected_steps
        ]
        assert len({state["step"] for state in response["data"]["state"]}) == 8

        assert strapi_mock.find_by_filters.call_count == 2
        find_calls = strapi_mock.find_by_filters.call_args_list
        assert (find_calls[0].args, find_calls[0].kwargs) == (
            ("funnel-flows",),
            {"filters": {"campaign_ref": "campaign-success"}},
        )
        assert (find_calls[1].args, find_calls[1].kwargs) == (
            ("funnel-flow-channels",),
            {"filters": {"funnel_flow_ref": ["flow-1", "flow-2"]}},
        )

        assert strapi_mock.get.call_count == 4
        get_calls = [
            (strapi_call.args, strapi_call.kwargs)
            for strapi_call in strapi_mock.get.call_args_list
        ]
        assert get_calls == [
            (
                ("ad-sets",),
                {
                    "params": {
                        "filters[funnel_flow_ref][id][$in][0]": "flow-1",
                        "filters[funnel_flow_ref][id][$in][1]": "flow-2",
                        "populate": "ads,media_platform_project_id",
                    }
                },
            ),
            (
                ("audience-audiences",),
                {
                    "params": {
                        "filters[ad_set_ref][id][$in][0]": 21,
                        "filters[ad_set_ref][id][$in][1]": 22,
                        "populate": "channel_ref,ad_set_ref",
                    }
                },
            ),
            (
                ("experiment-experiments",),
                {
                    "params": {
                        "filters[ad_set_ref][id][$in][0]": 21,
                        "filters[ad_set_ref][id][$in][1]": 22,
                        "populate": "ad_set_ref,subcategory_ref.category_ref",
                    }
                },
            ),
            (
                ("ad-channels",),
                {
                    "params": {
                        "filters[ad_ref][id][$in][0]": 101,
                        "filters[ad_ref][id][$in][1]": 102,
                        "filters[ad_ref][id][$in][2]": 201,
                        "populate": "channel_ref,ad_ref",
                        "pagination[pageSize]": 1000,
                    }
                },
            ),
        ]

    def test_execute_with_data_returns_exact_canonical_final_contract(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """The final response has eight unique ordered stages and mapped data.

        Validates: Requirements 2.10, 7.12, 8.4, 8.5.
        """
        raw_ad = make_raw_ad(
            ad_id="ad-final",
            name="Final Ad",
            redirect_url="https://example.test/final-ad",
        )
        selected_channel = make_raw_ad_channel(
            channel_record_id="ad-channel-final",
            ad_id="ad-final",
            channel_id="channel-final",
            channel_name="Final Channel",
            template_id="template-final",
            elements=[
                {
                    "name": "Headline",
                    "original_payload": "Final headline",
                    "payload": "Final headline",
                    "intention": "conversion",
                }
            ],
            images_banner=[{"id": "image-final"}],
            formats=[
                {
                    "visual_id": "visual-final",
                    "visual_url": "https://example.test/final.png",
                    "pinned": True,
                }
            ],
            channel_attributes=[
                {
                    "name": "Headline",
                    "max_char": 50,
                    "payloads": [{"payload": "Final headline"}],
                }
            ],
            redirect_url="https://example.test/final-channel",
            selected=True,
        )
        use_case, strapi_mock, _ = use_case_factory(
            campaign_id="campaign-final-contract",
            find_responses={
                "funnel-flows": {
                    "data": [make_funnel_flow(flow_id="flow-final")]
                },
                "funnel-flow-channels": {
                    "data": [
                        make_channel(
                            channel_id="channel-final",
                            name="Final Channel",
                        )
                    ]
                },
            },
            get_responses={
                "ad-sets": {
                    "data": [
                        make_raw_ad_set(
                            ad_set_id="ad-set-final",
                            name="Final Ad Set",
                            ads=[raw_ad],
                            project_id="project-final",
                        )
                    ]
                },
                "audience-audiences": {
                    "data": [
                        make_raw_audience(
                            audience_id="audience-final",
                            ad_set_id="ad-set-final",
                            channel_id="channel-final",
                            channel_name="Final Channel",
                            generation_method="manual",
                            preferred=1,
                            proposal_audiences=[{"segment": "final"}],
                        )
                    ]
                },
                "experiment-experiments": {
                    "data": [
                        make_raw_experiment(
                            experiment_id="experiment-final",
                            ad_set_id="ad-set-final",
                            experiment_type="copy",
                            subcategory_id="subcategory-final",
                            subcategory_name="Headlines",
                            subcategory_description="Headline experiments",
                            category_id="category-final",
                            category_name="Creative",
                            category_description="Creative experiments",
                        )
                    ]
                },
                "ad-channels": {"data": [selected_channel]},
            },
        )

        response, status_code = use_case.execute()

        expected_steps = [
            "channel",
            "ads_structure",
            "audiences",
            "ads_experiment",
            "ads",
            "summary",
            "review",
            "launchpad",
        ]
        expected_funnel_flow_data = [
            {
                "id": "ad-set-final",
                "name": "Final Ad Set",
                "media_platform_project_id": "project-final",
                "ads": [
                    {
                        "id": "ad-final",
                        "attributes": {
                            "name": "Final Ad",
                            "ad_channels": [
                                {
                                    "channel_id": "channel-final",
                                    "channel_name": "Final Channel",
                                    "media": {
                                        "template_id": "template-final",
                                        "elements": [
                                            {
                                                "name": "Headline",
                                                "original_payload": "Final headline",
                                                "payload": "Final headline",
                                                "intention": "conversion",
                                            }
                                        ],
                                        "images_banner": [
                                            {"id": "image-final"}
                                        ],
                                        "formats": [
                                            {
                                                "visual_id": "visual-final",
                                                "visual_url": "https://example.test/final.png",
                                                "pinned": True,
                                            }
                                        ],
                                    },
                                    "channel_attributes": [
                                        {
                                            "name": "Headline",
                                            "max_char": 50,
                                            "payloads": [
                                                {"payload": "Final headline"}
                                            ],
                                        }
                                    ],
                                    "url": "https://example.test/final-channel",
                                    "selected": True,
                                }
                            ],
                            "url": "https://example.test/final-ad",
                        },
                    }
                ],
                "audiences": [
                    {
                        "channel_id": "channel-final",
                        "channel_name": "Final Channel",
                        "generation_method": "manual",
                        "preferred_audience": {"preferred": 1},
                        "proposal_audiences": [{"segment": "final"}],
                    }
                ],
                "experiments": [
                    {
                        "id": "experiment-final",
                        "type": "copy",
                        "subcategory": {
                            "id": "subcategory-final",
                            "name": "Headlines",
                            "description": "Headline experiments",
                            "category": {
                                "id": "category-final",
                                "name": "Creative",
                                "description": "Creative experiments",
                            },
                        },
                    }
                ],
            }
        ]
        expected_state = [
            {"step": step, "completed": True, "errors": []}
            for step in expected_steps
        ]

        assert status_code == 200
        assert response == {
            "ok": 1,
            "data": {
                "state": expected_state,
                "funnel_flow_data": expected_funnel_flow_data,
            },
        }
        actual_steps = [state["step"] for state in response["data"]["state"]]
        assert actual_steps == expected_steps
        assert len(actual_steps) == 8
        assert len(set(actual_steps)) == 8

        find_calls = [
            (strapi_call.args, strapi_call.kwargs)
            for strapi_call in strapi_mock.find_by_filters.call_args_list
        ]
        assert find_calls == [
            (
                ("funnel-flows",),
                {"filters": {"campaign_ref": "campaign-final-contract"}},
            ),
            (
                ("funnel-flow-channels",),
                {"filters": {"funnel_flow_ref": ["flow-final"]}},
            ),
        ]
        get_calls = [
            (strapi_call.args, strapi_call.kwargs)
            for strapi_call in strapi_mock.get.call_args_list
        ]
        assert get_calls == [
            (
                ("ad-sets",),
                {
                    "params": {
                        "filters[funnel_flow_ref][id][$in][0]": "flow-final",
                        "populate": "ads,media_platform_project_id",
                    }
                },
            ),
            (
                ("audience-audiences",),
                {
                    "params": {
                        "filters[ad_set_ref][id][$in][0]": "ad-set-final",
                        "populate": "channel_ref,ad_set_ref",
                    }
                },
            ),
            (
                ("experiment-experiments",),
                {
                    "params": {
                        "filters[ad_set_ref][id][$in][0]": "ad-set-final",
                        "populate": "ad_set_ref,subcategory_ref.category_ref",
                    }
                },
            ),
            (
                ("ad-channels",),
                {
                    "params": {
                        "filters[ad_ref][id][$in][0]": "ad-final",
                        "populate": "channel_ref,ad_ref",
                        "pagination[pageSize]": 1000,
                    }
                },
            ),
        ]


class TestExecuteAlternateAndFailureFlows:
    """Characterize empty data and tolerant relationship consolidation."""

    def test_execute_without_funnel_flows_returns_pending_state_and_stops(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """An empty campaign preserves pending states and skips later queries.

        Validates: Requirements 4.1, 4.2, 8.4, 8.5.
        """
        use_case, strapi_mock, _ = use_case_factory(
            campaign_id="campaign-empty",
            find_responses={"funnel-flows": {"data": []}},
        )

        response, status_code = use_case.execute()

        expected_steps = [
            "channel",
            "ads_structure",
            "audiences",
            "ads_experiment",
            "ads",
            "summary",
            "review",
            "launchpad",
        ]
        assert status_code == 200
        assert response == {
            "ok": 1,
            "data": {
                "state": [
                    {
                        "step": step,
                        "completed": False,
                        "errors": [],
                        "message": "Pending validation",
                    }
                    for step in expected_steps
                ],
                "funnel_flow_data": [],
            },
        }
        strapi_mock.find_by_filters.assert_called_once_with(
            "funnel-flows",
            filters={"campaign_ref": "campaign-empty"},
        )
        strapi_mock.get.assert_not_called()

    def test_execute_with_empty_ad_sets_returns_exact_errors_and_skips_relations(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """Empty ad sets validate channels only and omit every relation query.

        Validates: Requirements 4.3, 4.4, 8.4, 8.5.
        """
        use_case, strapi_mock, _ = use_case_factory(
            campaign_id="campaign-no-ad-sets",
            find_responses={
                "funnel-flows": {"data": [make_funnel_flow("flow-empty")]},
                "funnel-flow-channels": {
                    "data": [make_channel(10, "Search")]
                },
            },
            get_responses={"ad-sets": {"data": []}},
        )

        response, status_code = use_case.execute()

        expected_state = [
            {"step": "channel", "completed": True, "errors": []},
            {
                "step": "ads_structure",
                "completed": False,
                "errors": [
                    {"message": "No Ad Sets found.", "code": "ADS_STRUCT_01"}
                ],
            },
            {
                "step": "audiences",
                "completed": False,
                "errors": [
                    {
                        "message": "No Ad Sets to validate audiences.",
                        "code": "AUD_01",
                    }
                ],
            },
            {
                "step": "ads_experiment",
                "completed": False,
                "errors": [
                    {
                        "message": "No Ad Sets to validate experiments.",
                        "code": "EXP_01",
                    }
                ],
            },
            {
                "step": "ads",
                "completed": False,
                "errors": [
                    {
                        "message": "No Ad Sets to validate ads.",
                        "code": "ADS_01",
                    }
                ],
            },
        ]
        aggregate_messages = [
            "Ad Channel is not completed.",
            "Ads Structure is not completed.",
            "Audiences is not completed.",
            "Ads Experiment is not completed.",
            "Ads is not completed.",
        ]
        for step, prefix in (
            ("summary", "SUM"),
            ("review", "REV"),
            ("launchpad", "LAUNCH"),
        ):
            expected_state.append(
                {
                    "step": step,
                    "completed": False,
                    "errors": [
                        {
                            "message": message,
                            "code": f"{prefix}_0{index}",
                            "metadata": {},
                        }
                        for index, message in enumerate(
                            aggregate_messages,
                            start=1,
                        )
                    ],
                }
            )

        assert status_code == 200
        assert response == {
            "ok": 1,
            "data": {
                "state": expected_state,
                "funnel_flow_data": [],
            },
        }
        assert [
            (strapi_call.args, strapi_call.kwargs)
            for strapi_call in strapi_mock.find_by_filters.call_args_list
        ] == [
            (
                ("funnel-flows",),
                {"filters": {"campaign_ref": "campaign-no-ad-sets"}},
            ),
            (
                ("funnel-flow-channels",),
                {"filters": {"funnel_flow_ref": ["flow-empty"]}},
            ),
        ]
        assert [
            (strapi_call.args, strapi_call.kwargs)
            for strapi_call in strapi_mock.get.call_args_list
        ] == [
            (
                ("ad-sets",),
                {
                    "params": {
                        "filters[funnel_flow_ref][id][$in][0]": "flow-empty",
                        "populate": "ads,media_platform_project_id",
                    }
                },
            )
        ]

    def test_execute_with_ad_set_without_ads_fetches_parent_relations_only(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """An ad-less set fetches audiences/experiments but no ad channels.

        Validates: Requirements 4.5, 8.4, 8.5.
        """
        raw_ad_set = make_raw_ad_set(
            ad_set_id=20,
            name="Ad-less Set",
            ads=[],
            project_id="project-ad-less",
        )
        audience = make_raw_audience(
            audience_id=30,
            ad_set_id=20,
            channel_id=10,
            channel_name="Search",
            generation_method="manual",
            preferred=1,
            proposal_audiences=[],
        )
        experiment = make_raw_experiment(
            experiment_id=40,
            ad_set_id=20,
            experiment_type="copy",
            subcategory_id=41,
            subcategory_name="Headline",
            subcategory_description="Headline tests",
            category_id=42,
            category_name="Creative",
            category_description="Creative tests",
        )
        use_case, strapi_mock, _ = use_case_factory(
            campaign_id="campaign-ad-less",
            find_responses={
                "funnel-flows": {"data": [make_funnel_flow("flow-ad-less")]},
                "funnel-flow-channels": {
                    "data": [make_channel(10, "Search")]
                },
            },
            get_responses={
                "ad-sets": {"data": [raw_ad_set]},
                "audience-audiences": {"data": [audience]},
                "experiment-experiments": {"data": [experiment]},
            },
        )

        response, status_code = use_case.execute()

        expected_funnel_data = [
            {
                "id": 20,
                "name": "Ad-less Set",
                "media_platform_project_id": "project-ad-less",
                "ads": [],
                "audiences": [
                    {
                        "channel_id": 10,
                        "channel_name": "Search",
                        "generation_method": "manual",
                        "preferred_audience": {"preferred": 1},
                        "proposal_audiences": [],
                    }
                ],
                "experiments": [
                    {
                        "id": 40,
                        "type": "copy",
                        "subcategory": {
                            "id": 41,
                            "name": "Headline",
                            "description": "Headline tests",
                            "category": {
                                "id": 42,
                                "name": "Creative",
                                "description": "Creative tests",
                            },
                        },
                    }
                ],
            }
        ]
        ad_set_metadata = {"ad_set_name": "Ad-less Set"}
        expected_state = [
            {"step": "channel", "completed": True, "errors": []},
            {
                "step": "ads_structure",
                "completed": False,
                "errors": [
                    {
                        "message": "Ad Set 'Ad-less Set' has no ads created.",
                        "code": "ADS_STRUCT_02",
                        "metadata": ad_set_metadata,
                    }
                ],
            },
            {"step": "audiences", "completed": True, "errors": []},
            {"step": "ads_experiment", "completed": True, "errors": []},
            {
                "step": "ads",
                "completed": False,
                "errors": [
                    {
                        "message": "Ad Set 'Ad-less Set' has no ads.",
                        "code": "ADS_03",
                        "metadata": ad_set_metadata,
                    }
                ],
            },
        ]
        for step, prefix in (
            ("summary", "SUM"),
            ("review", "REV"),
            ("launchpad", "LAUNCH"),
        ):
            expected_state.append(
                {
                    "step": step,
                    "completed": False,
                    "errors": [
                        {
                            "message": "Ads Structure is not completed.",
                            "code": f"{prefix}_02",
                            "metadata": {},
                        },
                        {
                            "message": "Ads is not completed.",
                            "code": f"{prefix}_05",
                            "metadata": {},
                        },
                    ],
                }
            )

        assert status_code == 200
        assert response == {
            "ok": 1,
            "data": {
                "state": expected_state,
                "funnel_flow_data": expected_funnel_data,
            },
        }
        assert [
            (strapi_call.args, strapi_call.kwargs)
            for strapi_call in strapi_mock.get.call_args_list
        ] == [
            (
                ("ad-sets",),
                {
                    "params": {
                        "filters[funnel_flow_ref][id][$in][0]": "flow-ad-less",
                        "populate": "ads,media_platform_project_id",
                    }
                },
            ),
            (
                ("audience-audiences",),
                {
                    "params": {
                        "filters[ad_set_ref][id][$in][0]": 20,
                        "populate": "channel_ref,ad_set_ref",
                    }
                },
            ),
            (
                ("experiment-experiments",),
                {
                    "params": {
                        "filters[ad_set_ref][id][$in][0]": 20,
                        "populate": "ad_set_ref,subcategory_ref.category_ref",
                    }
                },
            ),
        ]

    def test_execute_filters_unknown_and_malformed_relations_then_continues(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """Only valid known-parent relations survive malformed predecessors.

        Validates: Requirements 4.6, 4.7, 4.8, 4.9, 8.4, 8.5.
        """
        raw_ad = make_raw_ad(
            ad_id=100,
            name="Known Ad",
            redirect_url="https://example.test/known-ad",
        )
        raw_ad_set = make_raw_ad_set(
            ad_set_id=20,
            name="Known Set",
            ads=[raw_ad],
            project_id="known-project",
        )
        malformed_audience = {
            "id": "malformed-audience",
            "attributes": {"ad_set_ref": {"data": []}},
        }
        malformed_experiment = {
            "id": "malformed-experiment",
            "attributes": {"ad_set_ref": {"data": []}},
        }
        malformed_ad_channel = {
            "id": "malformed-ad-channel",
            "attributes": {"ad_ref": {"data": []}},
        }
        valid_audience = make_raw_audience(
            audience_id=301,
            ad_set_id=20,
            channel_id=11,
            channel_name="Search",
            generation_method="manual-known",
            preferred=1,
            proposal_audiences=[{"segment": "known"}],
        )
        valid_experiment = make_raw_experiment(
            experiment_id=401,
            ad_set_id=20,
            experiment_type="copy-known",
            subcategory_id=411,
            subcategory_name="Headlines",
            subcategory_description="Known subcategory",
            category_id=421,
            category_name="Copy",
            category_description="Known category",
        )
        valid_ad_channel = make_raw_ad_channel(
            channel_record_id=501,
            ad_id=100,
            channel_id=11,
            channel_name="Search",
            template_id="known-template",
            elements=[
                {
                    "name": "Headline",
                    "original_payload": "Known headline",
                    "payload": "Known headline",
                    "intention": "awareness",
                }
            ],
            images_banner=[{"id": "known-image"}],
            formats=[
                {
                    "visual_id": "known-visual",
                    "visual_url": "https://example.test/known-visual.png",
                    "pinned": True,
                }
            ],
            channel_attributes=[
                {
                    "name": "Headline",
                    "max_char": 50,
                    "payloads": [{"payload": "Known headline"}],
                }
            ],
            redirect_url="https://example.test/known-channel",
            selected=True,
        )
        use_case, strapi_mock, _ = use_case_factory(
            campaign_id="campaign-relations",
            find_responses={
                "funnel-flows": {"data": [make_funnel_flow("flow-known")]},
                "funnel-flow-channels": {
                    "data": [make_channel(11, "Search")]
                },
            },
            get_responses={
                "ad-sets": {"data": [raw_ad_set]},
                "audience-audiences": {
                    "data": [
                        malformed_audience,
                        make_raw_audience(
                            audience_id=302,
                            ad_set_id=999,
                            channel_id=12,
                            channel_name="Unknown",
                            preferred=1,
                        ),
                        valid_audience,
                    ]
                },
                "experiment-experiments": {
                    "data": [
                        malformed_experiment,
                        make_raw_experiment(
                            experiment_id=402,
                            ad_set_id=999,
                        ),
                        valid_experiment,
                    ]
                },
                "ad-channels": {
                    "data": [
                        malformed_ad_channel,
                        make_raw_ad_channel(
                            channel_record_id=502,
                            ad_id=999,
                        ),
                        valid_ad_channel,
                    ]
                },
            },
        )

        response, status_code = use_case.execute()

        expected_funnel_data = [
            {
                "id": 20,
                "name": "Known Set",
                "media_platform_project_id": "known-project",
                "ads": [
                    {
                        "id": 100,
                        "attributes": {
                            "name": "Known Ad",
                            "ad_channels": [
                                {
                                    "channel_id": 11,
                                    "channel_name": "Search",
                                    "media": {
                                        "template_id": "known-template",
                                        "elements": [
                                            {
                                                "name": "Headline",
                                                "original_payload": "Known headline",
                                                "payload": "Known headline",
                                                "intention": "awareness",
                                            }
                                        ],
                                        "images_banner": [{"id": "known-image"}],
                                        "formats": [
                                            {
                                                "visual_id": "known-visual",
                                                "visual_url": "https://example.test/known-visual.png",
                                                "pinned": True,
                                            }
                                        ],
                                    },
                                    "channel_attributes": [
                                        {
                                            "name": "Headline",
                                            "max_char": 50,
                                            "payloads": [
                                                {"payload": "Known headline"}
                                            ],
                                        }
                                    ],
                                    "url": "https://example.test/known-channel",
                                    "selected": True,
                                }
                            ],
                            "url": "https://example.test/known-ad",
                        },
                    }
                ],
                "audiences": [
                    {
                        "channel_id": 11,
                        "channel_name": "Search",
                        "generation_method": "manual-known",
                        "preferred_audience": {"preferred": 1},
                        "proposal_audiences": [{"segment": "known"}],
                    }
                ],
                "experiments": [
                    {
                        "id": 401,
                        "type": "copy-known",
                        "subcategory": {
                            "id": 411,
                            "name": "Headlines",
                            "description": "Known subcategory",
                            "category": {
                                "id": 421,
                                "name": "Copy",
                                "description": "Known category",
                            },
                        },
                    }
                ],
            }
        ]
        expected_steps = [
            "channel",
            "ads_structure",
            "audiences",
            "ads_experiment",
            "ads",
            "summary",
            "review",
            "launchpad",
        ]
        assert status_code == 200
        assert response == {
            "ok": 1,
            "data": {
                "state": [
                    {"step": step, "completed": True, "errors": []}
                    for step in expected_steps
                ],
                "funnel_flow_data": expected_funnel_data,
            },
        }
        assert [
            (strapi_call.args, strapi_call.kwargs)
            for strapi_call in strapi_mock.get.call_args_list
        ] == [
            (
                ("ad-sets",),
                {
                    "params": {
                        "filters[funnel_flow_ref][id][$in][0]": "flow-known",
                        "populate": "ads,media_platform_project_id",
                    }
                },
            ),
            (
                ("audience-audiences",),
                {
                    "params": {
                        "filters[ad_set_ref][id][$in][0]": 20,
                        "populate": "channel_ref,ad_set_ref",
                    }
                },
            ),
            (
                ("experiment-experiments",),
                {
                    "params": {
                        "filters[ad_set_ref][id][$in][0]": 20,
                        "populate": "ad_set_ref,subcategory_ref.category_ref",
                    }
                },
            ),
            (
                ("ad-channels",),
                {
                    "params": {
                        "filters[ad_ref][id][$in][0]": 100,
                        "populate": "channel_ref,ad_ref",
                        "pagination[pageSize]": 1000,
                    }
                },
            ),
        ]

    @pytest.mark.parametrize(
        "failure_endpoint",
        [
            "funnel-flows",
            "funnel-flow-channels",
            "ad-sets",
            "audience-audiences",
            "experiment-experiments",
            "ad-channels",
        ],
        ids=[
            "funnel-flows-failure",
            "funnel-flow-channels-failure",
            "ad-sets-failure",
            "audience-audiences-failure",
            "experiment-experiments-failure",
            "ad-channels-failure",
        ],
    )
    def test_execute_propagates_strapi_failure_and_stops_later_phases(
        self,
        use_case_factory: UseCaseFactory,
        failure_endpoint: str,
    ) -> None:
        """Each Strapi phase propagates its sentinel and stops orchestration.

        Validates: Requirements 4.10, 4.11, 4.12, 4.13, 4.14, 4.15,
        8.4, 8.6.
        """
        phase_order: List[str] = [
            "funnel-flows",
            "funnel-flow-channels",
            "ad-sets",
            "audience-audiences",
            "experiment-experiments",
            "ad-channels",
        ]
        failure_index = phase_order.index(failure_endpoint)
        sentinel_exception = RuntimeError(
            f"sentinel Strapi failure at {failure_endpoint}"
        )
        raw_ads: List[Dict[str, Any]] = (
            [make_raw_ad(ad_id=100)]
            if failure_endpoint == "ad-channels"
            else []
        )
        raw_ad_set = make_raw_ad_set(
            ad_set_id=20,
            ads=raw_ads,
            project_id="project-failure-matrix",
        )
        find_responses: Dict[str, Any] = {}
        get_responses: Dict[str, Any] = {}

        find_responses["funnel-flows"] = (
            sentinel_exception
            if failure_endpoint == "funnel-flows"
            else {"data": [make_funnel_flow("flow-failure-matrix")]}
        )
        if failure_index >= 1:
            find_responses["funnel-flow-channels"] = (
                sentinel_exception
                if failure_endpoint == "funnel-flow-channels"
                else {"data": []}
            )
        if failure_index >= 2:
            get_responses["ad-sets"] = (
                sentinel_exception
                if failure_endpoint == "ad-sets"
                else {"data": [raw_ad_set]}
            )
        if failure_index >= 3:
            get_responses["audience-audiences"] = (
                sentinel_exception
                if failure_endpoint == "audience-audiences"
                else {"data": []}
            )
        if failure_index >= 4:
            get_responses["experiment-experiments"] = (
                sentinel_exception
                if failure_endpoint == "experiment-experiments"
                else {"data": []}
            )
        if failure_index >= 5:
            get_responses["ad-channels"] = sentinel_exception

        use_case, strapi_mock, _ = use_case_factory(
            campaign_id="campaign-failure-matrix",
            find_responses=find_responses,
            get_responses=get_responses,
        )
        no_success_response = object()
        execution_result: Any = no_success_response

        with pytest.raises(RuntimeError) as exc_info:
            execution_result = use_case.execute()

        assert exc_info.value is sentinel_exception
        assert execution_result is no_success_response

        expected_find_calls: List[
            Tuple[Tuple[str, ...], Dict[str, Any]]
        ] = [
            (
                ("funnel-flows",),
                {"filters": {"campaign_ref": "campaign-failure-matrix"}},
            )
        ]
        if failure_index >= 1:
            expected_find_calls.append(
                (
                    ("funnel-flow-channels",),
                    {
                        "filters": {
                            "funnel_flow_ref": ["flow-failure-matrix"]
                        }
                    },
                )
            )

        expected_get_calls: List[
            Tuple[Tuple[str, ...], Dict[str, Any]]
        ] = []
        if failure_index >= 2:
            expected_get_calls.append(
                (
                    ("ad-sets",),
                    {
                        "params": {
                            "filters[funnel_flow_ref][id][$in][0]": (
                                "flow-failure-matrix"
                            ),
                            "populate": "ads,media_platform_project_id",
                        }
                    },
                )
            )
        if failure_index >= 3:
            expected_get_calls.append(
                (
                    ("audience-audiences",),
                    {
                        "params": {
                            "filters[ad_set_ref][id][$in][0]": 20,
                            "populate": "channel_ref,ad_set_ref",
                        }
                    },
                )
            )
        if failure_index >= 4:
            expected_get_calls.append(
                (
                    ("experiment-experiments",),
                    {
                        "params": {
                            "filters[ad_set_ref][id][$in][0]": 20,
                            "populate": (
                                "ad_set_ref,subcategory_ref.category_ref"
                            ),
                        }
                    },
                )
            )
        if failure_index >= 5:
            expected_get_calls.append(
                (
                    ("ad-channels",),
                    {
                        "params": {
                            "filters[ad_ref][id][$in][0]": 100,
                            "populate": "channel_ref,ad_ref",
                            "pagination[pageSize]": 1000,
                        }
                    },
                )
            )

        actual_find_calls: List[
            Tuple[Tuple[str, ...], Dict[str, Any]]
        ] = [
            (strapi_call.args, strapi_call.kwargs)
            for strapi_call in strapi_mock.find_by_filters.call_args_list
        ]
        actual_get_calls: List[
            Tuple[Tuple[str, ...], Dict[str, Any]]
        ] = [
            (strapi_call.args, strapi_call.kwargs)
            for strapi_call in strapi_mock.get.call_args_list
        ]
        assert actual_find_calls == expected_find_calls
        assert actual_get_calls == expected_get_calls


class TestChannelValidator:
    """Characterize the complete ChannelValidator input matrix."""

    @pytest.mark.parametrize(
        ("scenario", "expected_completed", "expected_errors"),
        [
            (
                "none",
                False,
                [
                    {
                        "message": "No channels found for this funnel flow.",
                        "code": "CHA_01",
                    }
                ],
            ),
            (
                "empty-list",
                False,
                [
                    {
                        "message": "No channels found for this funnel flow.",
                        "code": "CHA_01",
                    }
                ],
            ),
            (
                "non-list",
                False,
                [
                    {
                        "message": "Channels data is empty or invalid format.",
                        "code": "CHA_02",
                    }
                ],
            ),
            ("non-empty-list", True, []),
        ],
        ids=["none", "empty-list", "non-list", "non-empty-list"],
    )
    def test_channel_input_matrix_returns_exact_state_and_errors(
        self,
        use_case_factory: UseCaseFactory,
        scenario: str,
        expected_completed: bool,
        expected_errors: List[Dict[str, Any]],
    ) -> None:
        """None, empty, invalid-type, and non-empty list preserve the contract.

        Validates: Requirements 5.1, 5.2, 5.3, 8.2, 8.5.
        """
        contexts: Dict[str, Any] = {
            "none": None,
            "empty-list": [],
            "non-list": ("channel",),
            "non-empty-list": [{"id": "channel-1"}],
        }
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "channel"
        )

        completed, errors = validator.validate_completion(contexts[scenario])

        assert completed is expected_completed
        assert len(errors) == len(expected_errors)
        assert errors == expected_errors
        assert all("metadata" not in error for error in errors)


class TestAdsStructureValidator:
    """Characterize all AdsStructureValidator branches and error ordering."""

    @pytest.mark.parametrize(
        "ad_sets",
        [None, []],
        ids=["none", "empty-list"],
    )
    def test_missing_ad_sets_return_exact_structure_error(
        self,
        use_case_factory: UseCaseFactory,
        ad_sets: Any,
    ) -> None:
        """Absent or empty ad sets return one metadata-free ADS_STRUCT_01.

        Validates: Requirements 5.4, 8.2, 8.5.
        """
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators
            if item.key == "ads_structure"
        )

        completed, errors = validator.validate_completion(ad_sets)

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {"message": "No Ad Sets found.", "code": "ADS_STRUCT_01"}
        ]
        assert "metadata" not in errors[0]

    @pytest.mark.parametrize(
        "ads_kind",
        ["omitted", "none", "empty-list", "non-list"],
        ids=["ads-omitted", "ads-none", "ads-empty-list", "ads-non-list"],
    )
    def test_invalid_ads_collection_returns_exact_named_structure_error(
        self,
        use_case_factory: UseCaseFactory,
        ads_kind: str,
    ) -> None:
        """Every invalid ads shape returns one exact ADS_STRUCT_02.

        Validates: Requirements 5.5, 8.2, 8.5.
        """
        ad_set_name = f"Invalid {ads_kind}"
        if ads_kind == "omitted":
            ad_set = make_consolidated_ad_set(name=ad_set_name)
        else:
            invalid_ads: Dict[str, Any] = {
                "none": None,
                "empty-list": [],
                "non-list": {"id": "not-a-list"},
            }
            ad_set = make_consolidated_ad_set(
                name=ad_set_name,
                ads=invalid_ads[ads_kind],
            )
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators
            if item.key == "ads_structure"
        )

        completed, errors = validator.validate_completion([ad_set])

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    f"Ad Set '{ad_set_name}' has no ads created."
                ),
                "code": "ADS_STRUCT_02",
                "metadata": {"ad_set_name": ad_set_name},
            }
        ]

    def test_non_empty_ads_list_completes_without_errors(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """A non-empty ads list is structurally valid regardless of contents.

        Validates: Requirements 5.6, 8.2, 8.5.
        """
        ad_sets = [
            make_consolidated_ad_set(
                name="Valid Set",
                ads=[{"id": "ad-1"}],
            )
        ]
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators
            if item.key == "ads_structure"
        )

        completed, errors = validator.validate_completion(ad_sets)

        assert completed is True
        assert len(errors) == 0
        assert errors == []

    def test_multiple_invalid_ad_sets_accumulate_exact_errors_in_input_order(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """One ADS_STRUCT_02 is emitted per invalid set in stable order.

        Validates: Requirements 5.7, 8.2, 8.5.
        """
        ad_sets = [
            make_consolidated_ad_set(name="First Missing"),
            make_consolidated_ad_set(
                name="Valid Middle",
                ads=[{"id": "ad-valid"}],
            ),
            make_consolidated_ad_set(name="Second None", ads=None),
            make_consolidated_ad_set(
                name="Third Non-list",
                ads="invalid",
            ),
        ]
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators
            if item.key == "ads_structure"
        )

        completed, errors = validator.validate_completion(ad_sets)

        assert completed is False
        assert len(errors) == 3
        assert errors == [
            {
                "message": "Ad Set 'First Missing' has no ads created.",
                "code": "ADS_STRUCT_02",
                "metadata": {"ad_set_name": "First Missing"},
            },
            {
                "message": "Ad Set 'Second None' has no ads created.",
                "code": "ADS_STRUCT_02",
                "metadata": {"ad_set_name": "Second None"},
            },
            {
                "message": "Ad Set 'Third Non-list' has no ads created.",
                "code": "ADS_STRUCT_02",
                "metadata": {"ad_set_name": "Third Non-list"},
            },
        ]


class TestAudiencesValidator:
    """Characterize audience presence, preference, ordering, and exceptions."""

    @pytest.mark.parametrize(
        "ad_sets",
        [None, []],
        ids=["none", "empty-list"],
    )
    def test_missing_ad_sets_return_exact_audience_error(
        self,
        use_case_factory: UseCaseFactory,
        ad_sets: Any,
    ) -> None:
        """Absent or empty ad sets return one metadata-free AUD_01.

        Validates: Requirements 5.8, 8.5.
        """
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "audiences"
        )

        completed, errors = validator.validate_completion(ad_sets)

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": "No Ad Sets to validate audiences.",
                "code": "AUD_01",
            }
        ]
        assert "metadata" not in errors[0]

    @pytest.mark.parametrize(
        "audiences_kind",
        ["omitted", "none", "empty-list"],
        ids=["audiences-omitted", "audiences-none", "audiences-empty-list"],
    )
    def test_missing_audiences_return_exact_named_error(
        self,
        use_case_factory: UseCaseFactory,
        audiences_kind: str,
    ) -> None:
        """Every absent audience collection returns one exact AUD_02.

        Validates: Requirements 5.9, 8.5.
        """
        ad_set_name = f"Missing {audiences_kind}"
        if audiences_kind == "omitted":
            ad_set = make_consolidated_ad_set(name=ad_set_name)
        else:
            audiences_by_kind: Dict[str, Any] = {
                "none": None,
                "empty-list": [],
            }
            ad_set = make_consolidated_ad_set(
                name=ad_set_name,
                audiences=audiences_by_kind[audiences_kind],
            )
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "audiences"
        )

        completed, errors = validator.validate_completion([ad_set])

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    f"Ad Set '{ad_set_name}' has no proposal audiences "
                    "neither preferred audiences."
                ),
                "code": "AUD_02",
                "metadata": {"ad_set_name": ad_set_name},
            }
        ]

    def test_non_preferred_audiences_return_exact_named_error(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """A non-empty collection without preferred=1 returns AUD_03.

        Validates: Requirements 5.10, 8.5.
        """
        ad_set_name = "No Preferred Audience"
        ad_set = make_consolidated_ad_set(
            name=ad_set_name,
            audiences=[
                {},
                {"preferred_audience": None},
                {"preferred_audience": {"preferred": 0}},
            ],
        )
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "audiences"
        )

        completed, errors = validator.validate_completion([ad_set])

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    f"Ad Set '{ad_set_name}' is missing a Preferred Audience."
                ),
                "code": "AUD_03",
                "metadata": {"ad_set_name": ad_set_name},
            }
        ]

    def test_preferred_audience_completes_without_errors(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """At least one preferred=1 audience makes each ad set valid.

        Validates: Requirements 5.11, 8.5.
        """
        ad_sets = [
            make_consolidated_ad_set(
                name="Preferred First",
                audiences=[
                    {"preferred_audience": {"preferred": 1}},
                    {"preferred_audience": {"preferred": 0}},
                ],
            ),
            make_consolidated_ad_set(
                name="Preferred Last",
                audiences=[
                    {"preferred_audience": {"preferred": 0}},
                    {"preferred_audience": {"preferred": 1}},
                ],
            ),
        ]
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "audiences"
        )

        completed, errors = validator.validate_completion(ad_sets)

        assert completed is True
        assert len(errors) == 0
        assert errors == []

    def test_multiple_invalid_ad_sets_accumulate_exact_errors_in_input_order(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """AUD_02 and AUD_03 accumulate once per affected set in order.

        Validates: Requirements 5.12, 8.5.
        """
        ad_sets = [
            make_consolidated_ad_set(name="First Missing"),
            make_consolidated_ad_set(
                name="Valid Middle",
                audiences=[{"preferred_audience": {"preferred": 1}}],
            ),
            make_consolidated_ad_set(
                name="Second Not Preferred",
                audiences=[{"preferred_audience": {"preferred": 0}}],
            ),
            make_consolidated_ad_set(
                name="Third Empty",
                audiences=[],
            ),
        ]
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "audiences"
        )

        completed, errors = validator.validate_completion(ad_sets)

        assert completed is False
        assert len(errors) == 3
        assert errors == [
            {
                "message": (
                    "Ad Set 'First Missing' has no proposal audiences neither "
                    "preferred audiences."
                ),
                "code": "AUD_02",
                "metadata": {"ad_set_name": "First Missing"},
            },
            {
                "message": (
                    "Ad Set 'Second Not Preferred' is missing a Preferred "
                    "Audience."
                ),
                "code": "AUD_03",
                "metadata": {"ad_set_name": "Second Not Preferred"},
            },
            {
                "message": (
                    "Ad Set 'Third Empty' has no proposal audiences neither "
                    "preferred audiences."
                ),
                "code": "AUD_02",
                "metadata": {"ad_set_name": "Third Empty"},
            },
        ]

    @pytest.mark.parametrize(
        "iterable_kind",
        ["tuple", "iterator"],
        ids=["tuple", "iterator"],
    )
    def test_non_list_audience_iterables_are_evaluated_by_content(
        self,
        use_case_factory: UseCaseFactory,
        iterable_kind: str,
    ) -> None:
        """Non-list iterables complete when one mapping has preferred=1.

        Validates: Requirements 5.13, 8.5.
        """
        audience_values = (
            {"preferred_audience": {"preferred": 0}},
            {"preferred_audience": {"preferred": 1}},
        )
        audiences: Any = (
            audience_values
            if iterable_kind == "tuple"
            else iter(audience_values)
        )
        ad_set = make_consolidated_ad_set(
            name=f"Valid {iterable_kind}",
            audiences=audiences,
        )
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "audiences"
        )

        completed, errors = validator.validate_completion([ad_set])

        assert completed is True
        assert len(errors) == 0
        assert errors == []

    def test_truthy_non_iterable_audiences_propagate_type_error(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """A truthy non-iterable audience value propagates TypeError.

        Validates: Requirements 5.14, 8.6.
        """
        ad_set = make_consolidated_ad_set(
            name="Non-iterable Audiences",
            audiences=1,
        )
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "audiences"
        )

        with pytest.raises(TypeError):
            validator.validate_completion([ad_set])

    @pytest.mark.parametrize(
        "invalid_level",
        ["ad-set", "audience"],
        ids=["ad-set-without-get", "audience-without-get"],
    )
    def test_elements_without_get_propagate_attribute_error(
        self,
        use_case_factory: UseCaseFactory,
        invalid_level: str,
    ) -> None:
        """Non-mapping ad-set or audience elements propagate AttributeError.

        Validates: Requirements 5.15, 8.6.
        """
        context: List[Any]
        if invalid_level == "ad-set":
            context = [object()]
        else:
            context = [
                make_consolidated_ad_set(
                    name="Invalid Audience Element",
                    audiences=[object()],
                )
            ]
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators if item.key == "audiences"
        )

        with pytest.raises(AttributeError):
            validator.validate_completion(context)


class TestExperimentsValidator:
    """Characterize experiment presence, truthiness, ordering, and exceptions."""

    @pytest.mark.parametrize(
        "ad_sets",
        [None, []],
        ids=["none", "empty-list"],
    )
    def test_missing_ad_sets_return_exact_experiment_error(
        self,
        use_case_factory: UseCaseFactory,
        ad_sets: Any,
    ) -> None:
        """Absent or empty ad sets return one metadata-free EXP_01.

        Validates: Requirements 5.16, 8.5.
        """
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators
            if item.key == "ads_experiment"
        )

        completed, errors = validator.validate_completion(ad_sets)

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": "No Ad Sets to validate experiments.",
                "code": "EXP_01",
            }
        ]
        assert "metadata" not in errors[0]

    @pytest.mark.parametrize(
        "experiments_kind",
        ["omitted", "none", "empty-list"],
        ids=[
            "experiments-omitted",
            "experiments-none",
            "experiments-empty-list",
        ],
    )
    def test_missing_experiments_return_exact_named_error(
        self,
        use_case_factory: UseCaseFactory,
        experiments_kind: str,
    ) -> None:
        """Every absent experiment collection returns one exact EXP_02.

        Validates: Requirements 5.17, 8.5.
        """
        ad_set_name = f"Missing {experiments_kind}"
        if experiments_kind == "omitted":
            ad_set = make_consolidated_ad_set(name=ad_set_name)
        else:
            experiments_by_kind: Dict[str, Any] = {
                "none": None,
                "empty-list": [],
            }
            ad_set = make_consolidated_ad_set(
                name=ad_set_name,
                experiments=experiments_by_kind[experiments_kind],
            )
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators
            if item.key == "ads_experiment"
        )

        completed, errors = validator.validate_completion([ad_set])

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": f"Ad Set '{ad_set_name}' has no experiments.",
                "code": "EXP_02",
                "metadata": {"ad_set_name": ad_set_name},
            }
        ]

    def test_exclusively_falsy_experiments_return_exact_named_error(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """A non-empty collection containing only falsy values returns EXP_03.

        Validates: Requirements 5.18, 8.5.
        """
        ad_set_name = "Falsy Experiments"
        ad_set = make_consolidated_ad_set(
            name=ad_set_name,
            experiments=[None, False, 0, "", [], {}],
        )
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators
            if item.key == "ads_experiment"
        )

        completed, errors = validator.validate_completion([ad_set])

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    f"Ad Set '{ad_set_name}' has empty experiment data."
                ),
                "code": "EXP_03",
                "metadata": {"ad_set_name": ad_set_name},
            }
        ]

    def test_truthy_experiment_completes_each_ad_set_without_errors(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """At least one truthy experiment makes each ad set valid.

        Validates: Requirements 5.19, 8.5.
        """
        ad_sets = [
            make_consolidated_ad_set(
                name="Truthy First",
                experiments=[{"id": "experiment-1"}, False],
            ),
            make_consolidated_ad_set(
                name="Truthy Last",
                experiments=[None, 0, "experiment-2"],
            ),
        ]
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators
            if item.key == "ads_experiment"
        )

        completed, errors = validator.validate_completion(ad_sets)

        assert completed is True
        assert len(errors) == 0
        assert errors == []

    def test_multiple_invalid_ad_sets_accumulate_exact_errors_in_input_order(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """EXP_02 and EXP_03 accumulate once per affected set in order.

        Validates: Requirements 5.20, 8.5.
        """
        ad_sets = [
            make_consolidated_ad_set(name="First Missing"),
            make_consolidated_ad_set(
                name="Valid Middle",
                experiments=[{"id": "valid-experiment"}],
            ),
            make_consolidated_ad_set(
                name="Second Falsy",
                experiments=[False, None, 0],
            ),
            make_consolidated_ad_set(
                name="Third Empty",
                experiments=[],
            ),
        ]
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators
            if item.key == "ads_experiment"
        )

        completed, errors = validator.validate_completion(ad_sets)

        assert completed is False
        assert len(errors) == 3
        assert errors == [
            {
                "message": "Ad Set 'First Missing' has no experiments.",
                "code": "EXP_02",
                "metadata": {"ad_set_name": "First Missing"},
            },
            {
                "message": (
                    "Ad Set 'Second Falsy' has empty experiment data."
                ),
                "code": "EXP_03",
                "metadata": {"ad_set_name": "Second Falsy"},
            },
            {
                "message": "Ad Set 'Third Empty' has no experiments.",
                "code": "EXP_02",
                "metadata": {"ad_set_name": "Third Empty"},
            },
        ]

    @pytest.mark.parametrize(
        "iterable_kind",
        ["tuple", "iterator"],
        ids=["tuple", "iterator"],
    )
    def test_non_list_experiment_iterables_are_evaluated_by_truthiness(
        self,
        use_case_factory: UseCaseFactory,
        iterable_kind: str,
    ) -> None:
        """Non-list iterables complete when at least one element is truthy.

        Validates: Requirements 5.21, 8.5.
        """
        experiment_values = (False, None, {"id": "experiment-1"})
        experiments: Any = (
            experiment_values
            if iterable_kind == "tuple"
            else iter(experiment_values)
        )
        ad_set = make_consolidated_ad_set(
            name=f"Valid {iterable_kind}",
            experiments=experiments,
        )
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators
            if item.key == "ads_experiment"
        )

        completed, errors = validator.validate_completion([ad_set])

        assert completed is True
        assert len(errors) == 0
        assert errors == []

    def test_truthy_non_iterable_experiments_propagate_type_error(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """A truthy non-iterable experiment value propagates TypeError.

        Validates: Requirements 5.22, 8.6.
        """
        ad_set = make_consolidated_ad_set(
            name="Non-iterable Experiments",
            experiments=1,
        )
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators
            if item.key == "ads_experiment"
        )

        with pytest.raises(TypeError):
            validator.validate_completion([ad_set])

    def test_ad_set_without_get_propagates_attribute_error(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """A non-mapping ad-set element propagates AttributeError.

        Validates: Requirements 5.23, 8.6.
        """
        use_case, _, _ = use_case_factory()
        validator = next(
            item for item in use_case.validators
            if item.key == "ads_experiment"
        )

        with pytest.raises(AttributeError):
            validator.validate_completion([object()])


class TestAdsContentValidator:
    """Characterize AdsContentValidator preconditions and early continues."""

    @pytest.mark.parametrize(
        "ad_sets_data",
        [None, []],
        ids=["none", "empty-list"],
    )
    def test_missing_ad_sets_return_exact_ads_error(
        self,
        use_case_factory: UseCaseFactory,
        ad_sets_data: Any,
    ) -> None:
        """Missing ad sets return only ADS_01 without metadata.

        Validates: Requirements 6.1, 8.5.
        """
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(ad_sets_data)

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": "No Ad Sets to validate ads.",
                "code": "ADS_01",
            }
        ]

    def test_invalid_audiences_as_only_dependency_return_exact_ads_error(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """An otherwise valid context with invalid audiences returns only ADS_02.

        Validates: Requirements 6.2, 8.5.
        """
        context = make_valid_ads_context()
        del context[0]["audiences"]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": "Audiences is not completed.",
                "code": "ADS_02",
                "metadata": {},
            }
        ]

    def test_missing_project_returns_exact_named_ads_error(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """An ad set without a media project returns only ADS_09.

        Validates: Requirements 6.3, 8.5.
        """
        context = make_valid_ads_context(ad_set_name="Missing Project")
        del context[0]["media_platform_project_id"]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    "Ad Set 'Missing Project' is missing Media Platform Project ID."
                ),
                "code": "ADS_09",
                "metadata": {"ad_set_name": "Missing Project"},
            }
        ]

    def test_missing_project_skips_its_ads_and_continues_with_next_ad_set(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """ADS_09 skips affected ads but the following ad set is validated.

        Validates: Requirements 6.4, 8.5.
        """
        skipped = make_valid_ads_context(
            ad_set_id=20,
            ad_set_name="Skipped Project",
            ad_id=100,
            ad_name="Skipped Ad",
        )[0]
        del skipped["media_platform_project_id"]
        reached = make_valid_ads_context(
            ad_set_id=21,
            ad_set_name="Reached Set",
            ad_id=101,
            ad_name="Reached Ad",
        )[0]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        with patch.object(
            validator,
            "_get_max_length_allowed",
            wraps=validator._get_max_length_allowed,
        ) as max_length:
            completed, errors = validator.validate_completion([skipped, reached])

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    "Ad Set 'Skipped Project' is missing Media Platform Project ID."
                ),
                "code": "ADS_09",
                "metadata": {"ad_set_name": "Skipped Project"},
            }
        ]
        max_length.assert_called_once_with(len("Original headline"))

    def test_missing_ads_return_exact_named_ads_error(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """An ad set without ads returns only ADS_03.

        Validates: Requirements 6.5, 8.5.
        """
        ad_set = make_consolidated_ad_set(
            name="Missing Ads",
            audiences=[{"preferred_audience": {"preferred": 1}}],
        )
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion([ad_set])

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": "Ad Set 'Missing Ads' has no ads.",
                "code": "ADS_03",
                "metadata": {"ad_set_name": "Missing Ads"},
            }
        ]

    def test_missing_ads_continue_with_next_ad_set(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """ADS_03 does not prevent validation of the following ad set.

        Validates: Requirements 6.6, 8.5.
        """
        missing_ads = make_consolidated_ad_set(
            ad_set_id=20,
            name="Missing Ads",
            audiences=[{"preferred_audience": {"preferred": 1}}],
        )
        reached = make_valid_ads_context(
            ad_set_id=21,
            ad_set_name="Reached Set",
            ad_id=101,
            ad_name="Reached Ad",
        )[0]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        with patch.object(
            validator,
            "_get_max_length_allowed",
            wraps=validator._get_max_length_allowed,
        ) as max_length:
            completed, errors = validator.validate_completion(
                [missing_ads, reached]
            )

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": "Ad Set 'Missing Ads' has no ads.",
                "code": "ADS_03",
                "metadata": {"ad_set_name": "Missing Ads"},
            }
        ]
        max_length.assert_called_once_with(len("Original headline"))

    def test_missing_url_returns_ads_error_and_continues_same_ad(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """ADS_06 is exact and the same ad still reaches attributes and media.

        Validates: Requirements 6.7, 6.8, 8.5.
        """
        context = make_valid_ads_context(ad_name="Missing URL")
        del context[0]["ads"][0]["attributes"]["url"]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        with patch.object(
            validator,
            "_get_max_length_allowed",
            wraps=validator._get_max_length_allowed,
        ) as max_length:
            completed, errors = validator.validate_completion(context)

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": "Ad 'Missing URL' missing redirect url",
                "code": "ADS_06",
                "metadata": {"ad_name": "Missing URL"},
            }
        ]
        max_length.assert_called_once_with(len("Original headline"))

    @pytest.mark.parametrize(
        "ad_channels",
        [_OMITTED, []],
        ids=["omitted", "empty-list"],
    )
    def test_missing_channels_return_exact_variant_error(
        self,
        use_case_factory: UseCaseFactory,
        ad_channels: Any,
    ) -> None:
        """Missing or empty channel variants return only ADS_04.

        Validates: Requirements 6.9, 8.5.
        """
        ad = make_consolidated_ad(
            name="Missing Channels",
            ad_channels=ad_channels,
        )
        ad_set = make_consolidated_ad_set(
            name="Variant Set",
            ads=[ad],
            audiences=[{"preferred_audience": {"preferred": 1}}],
        )
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion([ad_set])

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    "Ad 'Missing Channels' in 'Variant Set' has no Variants "
                    "configured."
                ),
                "code": "ADS_04",
                "metadata": {
                    "ad_set_name": "Variant Set",
                    "ad_name": "Missing Channels",
                },
            }
        ]

    def test_missing_channels_skip_to_next_ad(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """ADS_04 skips the affected ad and validates the following ad.

        Validates: Requirements 6.10, 8.5.
        """
        skipped = make_consolidated_ad(name="Skipped Channels")
        reached = make_consolidated_ad(
            ad_id=101,
            name="Reached Ad",
            ad_channels=[make_valid_selected_channel()],
        )
        ad_set = make_consolidated_ad_set(
            name="Variant Set",
            ads=[skipped, reached],
            audiences=[{"preferred_audience": {"preferred": 1}}],
        )
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        with patch.object(
            validator,
            "_get_max_length_allowed",
            wraps=validator._get_max_length_allowed,
        ) as max_length:
            completed, errors = validator.validate_completion([ad_set])

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    "Ad 'Skipped Channels' in 'Variant Set' has no Variants "
                    "configured."
                ),
                "code": "ADS_04",
                "metadata": {
                    "ad_set_name": "Variant Set",
                    "ad_name": "Skipped Channels",
                },
            }
        ]
        max_length.assert_called_once_with(len("Original headline"))

    def test_unselected_channels_return_exact_variant_selection_error(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """A non-empty variant list without selection returns ADS_04_01.

        Validates: Requirements 6.11, 8.5.
        """
        unselected = make_valid_selected_channel()
        unselected["selected"] = False
        ad = make_consolidated_ad(
            name="Unselected Ad",
            ad_channels=[unselected],
        )
        ad_set = make_consolidated_ad_set(
            name="Selection Set",
            ads=[ad],
            audiences=[{"preferred_audience": {"preferred": 1}}],
        )
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion([ad_set])

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    "Ad 'Unselected Ad' in 'Selection Set' has no Variant selected."
                ),
                "code": "ADS_04_01",
                "metadata": {
                    "ad_set_name": "Selection Set",
                    "ad_name": "Unselected Ad",
                },
            }
        ]

    def test_unselected_channels_skip_to_next_ad(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """ADS_04_01 skips the affected ad and validates the following ad.

        Validates: Requirements 6.12, 8.5.
        """
        unselected = make_valid_selected_channel()
        unselected["selected"] = False
        skipped = make_consolidated_ad(
            name="Unselected Ad",
            ad_channels=[unselected],
        )
        reached = make_consolidated_ad(
            ad_id=101,
            name="Reached Ad",
            ad_channels=[make_valid_selected_channel()],
        )
        ad_set = make_consolidated_ad_set(
            name="Selection Set",
            ads=[skipped, reached],
            audiences=[{"preferred_audience": {"preferred": 1}}],
        )
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        with patch.object(
            validator,
            "_get_max_length_allowed",
            wraps=validator._get_max_length_allowed,
        ) as max_length:
            completed, errors = validator.validate_completion([ad_set])

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    "Ad 'Unselected Ad' in 'Selection Set' has no Variant selected."
                ),
                "code": "ADS_04_01",
                "metadata": {
                    "ad_set_name": "Selection Set",
                    "ad_name": "Unselected Ad",
                },
            }
        ]
        max_length.assert_called_once_with(len("Original headline"))
    def test_empty_channel_attributes_return_exact_missing_attributes_error(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """An empty attribute list returns only ADS_05 with exact metadata.

        Validates: Requirements 6.13, 8.5.
        """
        context = make_valid_ads_context(ad_name="Empty Attributes")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["channel_attributes"] = []
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    "Ad 'Empty Attributes' missing attributes in channel "
                    "'Search'."
                ),
                "code": "ADS_05",
                "metadata": {
                    "ad_name": "Empty Attributes",
                    "channel_name": "Search",
                },
            }
        ]

    @pytest.mark.parametrize(
        "channel_attributes",
        [None, 1],
        ids=["none", "non-iterable"],
    )
    def test_non_iterable_channel_attributes_record_error_then_raise_type_error(
        self,
        use_case_factory: UseCaseFactory,
        channel_attributes: Any,
    ) -> None:
        """Invalid non-iterables record ADS_05 before propagating TypeError.

        Validates: Requirements 6.14, 8.5, 8.6.
        """
        context = make_valid_ads_context(ad_name="Invalid Attributes")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["channel_attributes"] = channel_attributes
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        with pytest.raises(TypeError) as exc_info:
            validator.validate_completion(context)

        traceback = exc_info.value.__traceback__
        assert traceback is not None
        while traceback.tb_next is not None:
            traceback = traceback.tb_next
        assert traceback.tb_frame.f_locals["errors"] == [
            {
                "message": (
                    "Ad 'Invalid Attributes' missing attributes in channel "
                    "'Search'."
                ),
                "code": "ADS_05",
                "metadata": {
                    "ad_name": "Invalid Attributes",
                    "channel_name": "Search",
                },
            }
        ]

    def test_empty_attribute_payload_returns_exact_missing_payload_error(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """An empty attribute payload returns only ADS_05_01.

        Validates: Requirements 6.15, 8.5.
        """
        context = make_valid_ads_context(ad_name="Empty Payload")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["channel_attributes"][0]["payloads"][0]["payload"] = ""
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    "Ad 'Empty Payload' missing at least one payload in channel "
                    "'Search'."
                ),
                "code": "ADS_05_01",
                "metadata": {
                    "ad_name": "Empty Payload",
                    "channel_name": "Search",
                },
            }
        ]

    def test_empty_payload_stops_remaining_payload_and_attribute_traversal(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """An empty payload suppresses later over-limit attribute errors.

        Validates: Requirements 6.16, 8.5.
        """
        context = make_valid_ads_context(ad_name="Traversal Cutoff")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["channel_attributes"] = [
            {
                "name": "First Attribute",
                "max_char": 1,
                "payloads": [
                    {"payload": ""},
                    {"payload": "not reached"},
                ],
            },
            {
                "name": "Second Attribute",
                "max_char": 1,
                "payloads": [{"payload": "also not reached"}],
            },
        ]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is False
        assert len(errors) == 1
        assert [error["code"] for error in errors] == ["ADS_05_01"]
        assert errors[0]["metadata"] == {
            "ad_name": "Traversal Cutoff",
            "channel_name": "Search",
        }

    def test_over_limit_non_cta_payload_returns_exact_length_error(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """A non-CTA payload over max_char returns exact ADS_05_02 metadata.

        Validates: Requirements 6.17, 8.5.
        """
        context = make_valid_ads_context(ad_name="Long Payload")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["channel_attributes"] = [
            {
                "name": "Headline",
                "max_char": 3,
                "payloads": [{"payload": "four"}],
            }
        ]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    "Ad 'Long Payload' has a payload that exceeds the maximum "
                    "allowed length in channel attributes, in channel 'Search'."
                ),
                "code": "ADS_05_02",
                "metadata": {
                    "ad_name": "Long Payload",
                    "channel_name": "Search",
                    "payload_length": 4,
                    "max_allowed_length": 3,
                    "attribute_name": "Headline",
                },
            }
        ]

    @pytest.mark.parametrize(
        "attribute_name",
        ["cta", "CTA", "CtA", "cTa"],
        ids=["lower", "upper", "mixed-title", "mixed-alternate"],
    )
    def test_over_limit_cta_payload_is_excluded_case_insensitively(
        self,
        use_case_factory: UseCaseFactory,
        attribute_name: str,
    ) -> None:
        """CTA payloads never produce ADS_05_02 regardless of casing.

        Validates: Requirements 6.18, 8.5.
        """
        context = make_valid_ads_context(ad_name="CTA Payload")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["channel_attributes"] = [
            {
                "name": attribute_name,
                "max_char": 1,
                "payloads": [{"payload": "long CTA"}],
            }
        ]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is True
        assert len(errors) == 0
        assert errors == []

    @pytest.mark.parametrize(
        ("media_key", "invalid_value"),
        [
            ("elements", _OMITTED),
            ("elements", None),
            ("elements", "not-a-list"),
            ("elements", []),
            ("images_banner", _OMITTED),
            ("images_banner", None),
            ("images_banner", "not-a-list"),
            ("images_banner", []),
            ("formats", _OMITTED),
            ("formats", None),
            ("formats", "not-a-list"),
            ("formats", []),
        ],
        ids=[
            "elements-omitted",
            "elements-none",
            "elements-non-list",
            "elements-empty",
            "images-banner-omitted",
            "images-banner-none",
            "images-banner-non-list",
            "images-banner-empty",
            "formats-omitted",
            "formats-none",
            "formats-non-list",
            "formats-empty",
        ],
    )
    def test_invalid_single_media_field_returns_exact_media_error(
        self,
        use_case_factory: UseCaseFactory,
        media_key: str,
        invalid_value: Any,
    ) -> None:
        """Each invalid media shape returns one ADS_07 for that field.

        Validates: Requirements 6.19, 8.5.
        """
        context = make_valid_ads_context(ad_name="Invalid Media")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        media = selected_channel["media"]
        if invalid_value is _OMITTED:
            del media[media_key]
        else:
            media[media_key] = invalid_value
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    f"Ad 'Invalid Media' missing media '{media_key}' in channel "
                    "'Search'."
                ),
                "code": "ADS_07",
                "metadata": {
                    "ad_name": "Invalid Media",
                    "media_element": media_key,
                    "channel_name": "Search",
                },
            }
        ]

    @pytest.mark.parametrize(
        ("invalid_media", "expected_media_keys"),
        [
            (
                {"elements": _OMITTED, "images_banner": None},
                ["elements", "images_banner"],
            ),
            (
                {"elements": "not-a-list", "formats": []},
                ["elements", "formats"],
            ),
            (
                {"images_banner": [], "formats": None},
                ["images_banner", "formats"],
            ),
            (
                {
                    "elements": None,
                    "images_banner": "not-a-list",
                    "formats": _OMITTED,
                },
                ["elements", "images_banner", "formats"],
            ),
        ],
        ids=[
            "elements-and-images-banner",
            "elements-and-formats",
            "images-banner-and-formats",
            "all-media-fields",
        ],
    )
    def test_invalid_media_combinations_preserve_canonical_error_order(
        self,
        use_case_factory: UseCaseFactory,
        invalid_media: Dict[str, Any],
        expected_media_keys: List[str],
    ) -> None:
        """Multiple invalid media fields produce one ordered ADS_07 each.

        Validates: Requirements 6.20, 8.5.
        """
        context = make_valid_ads_context(ad_name="Combined Invalid Media")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        media = selected_channel["media"]
        for media_key, invalid_value in invalid_media.items():
            if invalid_value is _OMITTED:
                del media[media_key]
            else:
                media[media_key] = invalid_value
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is False
        assert len(errors) == len(expected_media_keys)
        assert errors == [
            {
                "message": (
                    "Ad 'Combined Invalid Media' missing media "
                    f"'{media_key}' in channel 'Search'."
                ),
                "code": "ADS_07",
                "metadata": {
                    "ad_name": "Combined Invalid Media",
                    "media_element": media_key,
                    "channel_name": "Search",
                },
            }
            for media_key in expected_media_keys
        ]

    @pytest.mark.parametrize(
        ("visual_id", "visual_url", "expected_codes"),
        [
            ("", "https://example.test/visual.png", ["ADS_07_01"]),
            ("visual-1", "", ["ADS_07_02"]),
            ("", "", ["ADS_07_01", "ADS_07_02"]),
        ],
        ids=["empty-visual-id", "empty-visual-url", "both-empty"],
    )
    def test_empty_format_visual_data_returns_exact_errors(
        self,
        use_case_factory: UseCaseFactory,
        visual_id: str,
        visual_url: str,
        expected_codes: List[str],
    ) -> None:
        """Empty visual fields produce their independent ordered errors.

        Validates: Requirements 6.21, 6.22, 6.23, 8.5.
        """
        context = make_valid_ads_context(ad_name="Invalid Format")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["media"]["formats"] = [
            {"visual_id": visual_id, "visual_url": visual_url, "pinned": True}
        ]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")
        messages = {
            "ADS_07_01": (
                "Ad 'Invalid Format' visual id not found in media 'formats', "
                "in channel 'Search'."
            ),
            "ADS_07_02": (
                "Ad 'Invalid Format' image link not found in media 'formats', "
                "in channel 'Search'."
            ),
        }

        completed, errors = validator.validate_completion(context)

        assert completed is False
        assert len(errors) == len(expected_codes)
        assert errors == [
            {
                "message": messages[code],
                "code": code,
                "metadata": {
                    "ad_name": "Invalid Format",
                    "media_element": "formats",
                    "channel_name": "Search",
                },
            }
            for code in expected_codes
        ]

    def test_invalid_format_visual_data_continues_with_later_formats(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """Both errors in one format do not prevent checking later formats.

        Validates: Requirements 6.23, 8.5.
        """
        context = make_valid_ads_context(ad_name="Multiple Invalid Formats")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["media"]["formats"] = [
            {"visual_id": "", "visual_url": "", "pinned": True},
            {"visual_id": "later-visual", "visual_url": "", "pinned": False},
            {
                "visual_id": "valid-visual",
                "visual_url": "https://example.test/valid.png",
                "pinned": False,
            },
        ]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is False
        assert len(errors) == 3
        assert [error["code"] for error in errors] == [
            "ADS_07_01",
            "ADS_07_02",
            "ADS_07_02",
        ]
        assert [error["metadata"] for error in errors] == [
            {
                "ad_name": "Multiple Invalid Formats",
                "media_element": "formats",
                "channel_name": "Search",
            },
            {
                "ad_name": "Multiple Invalid Formats",
                "media_element": "formats",
                "channel_name": "Search",
            },
            {
                "ad_name": "Multiple Invalid Formats",
                "media_element": "formats",
                "channel_name": "Search",
            },
        ]

    @pytest.mark.parametrize(
        ("pinned_count", "expected_code"),
        [
            (0, "ADS_07_03"),
            (2, "ADS_07_03"),
        ],
        ids=["zero-pinned", "multiple-pinned"],
    )
    def test_pinned_format_validation_errors_for_zero_or_multiple_pinned(
        self,
        use_case_factory: UseCaseFactory,
        pinned_count: int,
        expected_code: str,
    ) -> None:
        """Zero or multiple pinned formats return ADS_07_03.

        Validates: New business rule for pinned format validation.
        """
        context = make_valid_ads_context(ad_name="Pinned Validation Test")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]

        # Build formats with specified number of pinned items
        formats: List[Dict[str, Any]] = [
            {"visual_id": f"visual-{i}", "visual_url": f"https://example.test/visual-{i}.png", "pinned": True}
            for i in range(2)
        ]
        # Set pinned=True for the first N formats based on pinned_count
        for i in range(min(pinned_count, len(formats))):
            formats[i]["pinned"] = True

        selected_channel["media"]["formats"] = formats
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    "Ad 'Pinned Validation Test' exactly one pinned format is required "
                    "in media 'formats', in channel 'Search'."
                ),
                "code": expected_code,
                "metadata": {
                    "ad_name": "Pinned Validation Test",
                    "media_element": "formats",
                    "channel_name": "Search",
                },
            }
        ]

    def test_pinned_format_validation_succeeds_with_exactly_one_pinned(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """Exactly one pinned format completes validation without errors.

        Validates: New business rule for pinned format validation.
        """
        context = make_valid_ads_context(ad_name="Valid Pinned Test")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["media"]["formats"] = [
            {
                "visual_id": "visual-1",
                "visual_url": "https://example.test/visual-1.png",
                "pinned": True,
            },
            {
                "visual_id": "visual-2",
                "visual_url": "https://example.test/visual-2.png",
                "pinned": False,
            },
        ]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is True
        assert len(errors) == 0
        assert errors == []

    def test_pinned_format_validation_ignores_unpinned_when_none_marked(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """Formats without pinned attribute fail when none are marked pinned.

        Validates: New business rule for pinned format validation.
        """
        context = make_valid_ads_context(ad_name="No Pinned Test")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["media"]["formats"] = [
            {"visual_id": "visual-1", "visual_url": "https://example.test/visual-1.png", "pinned": True},
            {"visual_id": "visual-2", "visual_url": "https://example.test/visual-2.png", "pinned": True},
        ]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is False
        assert len(errors) == 1
        assert errors[0]["code"] == "ADS_07_03"


    def test_element_payload_limit_uses_original_length_and_exact_metadata(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """An over-limit element uses the derived original-payload limit.

        Validates: Requirements 6.24, 6.25, 8.5.
        """
        context = make_valid_ads_context(ad_name="Long Element Payload")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["media"]["elements"] = [
            {
                "name": "Short Headline",
                "original_payload": "12345",
                "payload": "1234567",
                "intention": "awareness",
            }
        ]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        with patch.object(
            validator,
            "_get_max_length_allowed",
            wraps=validator._get_max_length_allowed,
        ) as max_length:
            completed, errors = validator.validate_completion(context)

        max_length.assert_called_once_with(5)
        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    "Ad 'Long Element Payload' has a payload that exceeds the "
                    "maximum allowed length in media 'elements', in channel "
                    "'Search'."
                ),
                "code": "ADS_08_02",
                "metadata": {
                    "ad_name": "Long Element Payload",
                    "channel_name": "Search",
                    "payload_length": 7,
                    "max_allowed_length": 6,
                    "element_name": "Short Headline",
                },
            }
        ]

    def test_missing_element_intention_returns_exact_error_and_stops_elements(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """ADS_08_01 stops later elements after checking a calculable payload.

        Validates: Requirements 6.26, 6.27, 8.5.
        """
        context = make_valid_ads_context(ad_name="Missing Intention")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["media"]["elements"] = [
            {
                "name": "First Element",
                "original_payload": "12345",
                "payload": "123456",
                "intention": None,
            },
            {
                "name": "Unreached Element",
                "original_payload": "x",
                "payload": "far too long",
                "intention": "conversion",
            },
        ]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        with patch.object(
            validator,
            "_get_max_length_allowed",
            wraps=validator._get_max_length_allowed,
        ) as max_length:
            completed, errors = validator.validate_completion(context)

        max_length.assert_called_once_with(5)
        assert completed is False
        assert len(errors) == 1
        assert errors == [
            {
                "message": (
                    "Ad 'Missing Intention' intention not found in media "
                    "'elements', in channel 'Search'."
                ),
                "code": "ADS_08_01",
                "metadata": {
                    "ad_name": "Missing Intention",
                    "media_element": "elements",
                    "channel_name": "Search",
                },
            }
        ]

    def test_truthy_element_payload_without_prior_limit_raises_unbound_local(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """A truthy payload before any max calculation propagates the error.

        Validates: Requirements 6.28, 8.6.
        """
        context = make_valid_ads_context(ad_name="Missing Original Payload")
        selected_channel = context[0]["ads"][0]["attributes"]["ad_channels"][0]
        selected_channel["media"]["elements"] = [
            {
                "name": "Unbounded Element",
                "original_payload": "",
                "payload": "truthy",
                "intention": "awareness",
            }
        ]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        with pytest.raises(UnboundLocalError):
            validator.validate_completion(context)

    def test_fully_valid_ads_context_completes_without_errors(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """A minimal context satisfying every ad rule completes cleanly.

        Validates: Requirements 6.29, 8.2, 8.5.
        """
        context = make_valid_ads_context()
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is True
        assert errors == []

    def test_independent_errors_accumulate_across_ads_and_ad_sets_in_order(
        self,
        use_case_factory: UseCaseFactory,
    ) -> None:
        """Independent violations accumulate in evaluation order throughout context.

        Validates: Requirements 6.30, 6.31, 8.2, 8.5.
        """
        first_ad_set = make_valid_ads_context(
            ad_set_id=20,
            ad_set_name="First Set",
            ad_id=100,
            ad_name="Missing URL",
        )[0]
        del first_ad_set["ads"][0]["attributes"]["url"]

        mixed_channel = make_valid_selected_channel(
            channel_name="Social",
            attribute_name="Primary Text",
            attribute_payload="12345",
            max_char=4,
        )
        mixed_channel["media"]["formats"] = [
            {
                "visual_id": "",
                "visual_url": "https://example.test/social.png",
                "pinned": True,
            }
        ]
        first_ad_set["ads"].append(
            make_consolidated_ad(
                ad_id=101,
                name="Mixed Violations",
                ad_channels=[mixed_channel],
            )
        )

        second_ad_set = make_valid_ads_context(
            ad_set_id=21,
            ad_set_name="Second Set",
            ad_id=200,
            ad_name="Media Violations",
        )[0]
        media_channel = second_ad_set["ads"][0]["attributes"]["ad_channels"][0]
        media_channel["channel_name"] = "Display"
        media_channel["media"]["elements"] = [
            {
                "name": "Short Headline",
                "original_payload": "12345",
                "payload": "1234567",
                "intention": "awareness",
            }
        ]
        media_channel["media"]["formats"] = [
            {"visual_id": "visual-2", "visual_url": "", "pinned": True}
        ]

        context = [first_ad_set, second_ad_set]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == "ads")

        completed, errors = validator.validate_completion(context)

        assert completed is False
        assert errors == [
            {
                "message": "Ad 'Missing URL' missing redirect url",
                "code": "ADS_06",
                "metadata": {"ad_name": "Missing URL"},
            },
            {
                "message": (
                    "Ad 'Mixed Violations' has a payload that exceeds the "
                    "maximum allowed length in channel attributes, in channel "
                    "'Social'."
                ),
                "code": "ADS_05_02",
                "metadata": {
                    "ad_name": "Mixed Violations",
                    "channel_name": "Social",
                    "payload_length": 5,
                    "max_allowed_length": 4,
                    "attribute_name": "Primary Text",
                },
            },
            {
                "message": (
                    "Ad 'Mixed Violations' visual id not found in media "
                    "'formats', in channel 'Social'."
                ),
                "code": "ADS_07_01",
                "metadata": {
                    "ad_name": "Mixed Violations",
                    "media_element": "formats",
                    "channel_name": "Social",
                },
            },
            {
                "message": (
                    "Ad 'Media Violations' has a payload that exceeds the "
                    "maximum allowed length in media 'elements', in channel "
                    "'Display'."
                ),
                "code": "ADS_08_02",
                "metadata": {
                    "ad_name": "Media Violations",
                    "channel_name": "Display",
                    "payload_length": 7,
                    "max_allowed_length": 6,
                    "element_name": "Short Headline",
                },
            },
            {
                "message": (
                    "Ad 'Media Violations' image link not found in media "
                    "'formats', in channel 'Display'."
                ),
                "code": "ADS_07_02",
                "metadata": {
                    "ad_name": "Media Violations",
                    "media_element": "formats",
                    "channel_name": "Display",
                },
            },
        ]


class TestAggregateValidators:
    @pytest.mark.parametrize(
        ("validator_key", "code_prefix"),
        [
            pytest.param("summary", "SUM", id="summary"),
            pytest.param("review", "REV", id="review"),
            pytest.param("launchpad", "LAUNCH", id="launchpad"),
        ],
    )
    @pytest.mark.parametrize(
        "failed_dependency_indexes",
        [
            pytest.param((), id="all-complete"),
            pytest.param((0,), id="channel-failure"),
            pytest.param((1,), id="ads-structure-failure"),
            pytest.param((2,), id="audiences-failure"),
            pytest.param((3,), id="experiments-failure"),
            pytest.param((4,), id="ads-content-failure"),
            pytest.param((0, 2, 4), id="multiple-failures"),
        ],
    )
    def test_aggregate_reflects_exact_failed_dependencies_in_canonical_order(
        self,
        use_case_factory: UseCaseFactory,
        validator_key: str,
        code_prefix: str,
        failed_dependency_indexes: Tuple[int, ...],
    ) -> None:
        """Each aggregate reports only failed dependency doubles in order.

        Validates: Requirements 7.1-7.11, 8.5.
        """
        dependency_names = (
            "ChannelValidator",
            "AdsStructureValidator",
            "AudiencesValidator",
            "ExperimentsValidator",
            "AdsContentValidator",
        )
        dependency_messages = (
            "Ad Channel is not completed.",
            "Ads Structure is not completed.",
            "Audiences is not completed.",
            "Ads Experiment is not completed.",
            "Ads is not completed.",
        )
        constructors: Dict[str, MagicMock] = {}
        for index, dependency_name in enumerate(dependency_names):
            constructor = MagicMock(name=f"{dependency_name}Class")
            constructor.return_value.validate_completion.return_value = (
                index not in failed_dependency_indexes,
                [{"ignored_dependency_error": index}],
            )
            constructors[dependency_name] = constructor

        context: List[Dict[str, Any]] = [{"context": "same-object"}]
        use_case, _, _ = use_case_factory()
        validator = next(item for item in use_case.validators if item.key == validator_key)

        with patch.multiple(
            "app.v2.use_cases.funnel_flow_validator",
            **constructors,
        ):
            completed, errors = validator.validate_completion(context)

        assert completed is (not failed_dependency_indexes)
        assert errors == [
            {
                "message": dependency_messages[index],
                "code": f"{code_prefix}_{index + 1:02d}",
                "metadata": {},
            }
            for index in failed_dependency_indexes
        ]
        for constructor in constructors.values():
            constructor.assert_called_once_with()
            dependency_double = constructor.return_value
            dependency_double.validate_completion.assert_called_once_with(context)
            assert dependency_double.validate_completion.call_args.args[0] is context
