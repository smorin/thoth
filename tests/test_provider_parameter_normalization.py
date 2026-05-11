from types import SimpleNamespace
from typing import Any, cast

import pytest

from thoth.config import ConfigManager
from thoth.providers.parameter_config import build_provider_runtime_config


def _config(data: dict[str, Any]) -> ConfigManager:
    return cast(ConfigManager, SimpleNamespace(data=data))


def test_provider_defaults_precedence_l2_to_l5() -> None:
    config = _config(
        {
            "providers": {
                "defaults": {
                    "timeout": 30,
                    "temperature": 0.2,
                    "kind": "background",
                },
                "gemini": {
                    "api_key": "AIza-test",
                    "temperature": 0.4,
                    "kind": "immediate",
                },
            },
            "profiles": {
                "work": {
                    "providers": {
                        "defaults": {"timeout": 45},
                        "gemini": {"temperature": 0.6, "kind": "background"},
                    }
                }
            },
        }
    )

    runtime = build_provider_runtime_config(
        provider_name="gemini",
        config=config,
        active_profile="work",
        mode_name=None,
        mode_config=None,
        timeout_override=None,
    )

    assert runtime.auth["api_key"] == "AIza-test"
    assert runtime.client["timeout"] == 45
    assert runtime.common_request["temperature"] == 0.6
    assert runtime.routing["kind"] == "background"


def test_mode_common_and_provider_namespace_precedence_l6_to_l9() -> None:
    config = _config(
        {
            "providers": {
                "defaults": {"temperature": 0.1},
                "perplexity": {"api_key": "pplx-test"},
            },
            "profiles": {
                "work": {
                    "modes": {
                        "focused": {
                            "top_p": 0.8,
                            "kind": "immediate",
                            "temperature": 0.4,
                            "perplexity": {
                                "kind": "background",
                                "temperature": 0.7,
                                "response_format": {"type": "json_schema"},
                            },
                        }
                    }
                }
            },
        }
    )
    mode_config = {
        "provider": "perplexity",
        "model": "sonar",
        "kind": "immediate",
        "temperature": 0.3,
        "perplexity": {
            "temperature": 0.5,
            "kind": "immediate",
            "response_format": {"type": "json_object"},
        },
    }

    runtime = build_provider_runtime_config(
        provider_name="perplexity",
        config=config,
        active_profile="work",
        mode_name="focused",
        mode_config=mode_config,
        timeout_override=None,
    )

    assert runtime.common_request["temperature"] == 0.7
    assert runtime.common_request["top_p"] == 0.8
    assert runtime.common_request["response_format"] == {"type": "json_schema"}
    assert runtime.routing["kind"] == "background"
    assert runtime.provider_request == {}


def test_provider_namespace_model_is_provider_specific_override() -> None:
    config = _config(
        {
            "providers": {
                "perplexity": {"api_key": "pplx-test"},
            }
        }
    )

    runtime = build_provider_runtime_config(
        provider_name="perplexity",
        config=config,
        active_profile=None,
        mode_name="focused",
        mode_config={
            "provider": "perplexity",
            "model": "sonar",
            "perplexity": {"model": "sonar-pro"},
        },
        timeout_override=None,
    )

    assert runtime.common_request["model"] == "sonar"
    assert runtime.provider_request["model"] == "sonar-pro"
    assert runtime.to_legacy_config()["model"] == "sonar-pro"
    assert runtime.to_legacy_config()["perplexity"]["model"] == "sonar-pro"


def test_runtime_timeout_override_wins_over_config_layers() -> None:
    config = _config(
        {
            "providers": {
                "defaults": {"timeout": 30},
                "openai": {"api_key": "sk-test", "timeout": 45},
            }
        }
    )

    runtime = build_provider_runtime_config(
        provider_name="openai",
        config=config,
        active_profile=None,
        mode_name=None,
        mode_config=None,
        timeout_override=60,
    )

    assert runtime.client["timeout"] == 60


def test_all_provider_defaults_only_promote_shared_fields() -> None:
    config = _config(
        {
            "providers": {
                "defaults": {
                    "timeout": 30,
                    "temperature": 0.2,
                    "kind": "immediate",
                },
                "openai": {"api_key": "sk-provider"},
            },
            "profiles": {
                "work": {
                    "providers": {
                        "defaults": {
                            "timeout": 45,
                            "temperature": 0.4,
                            "kind": "background",
                        },
                        "openai": {"api_key": "sk-profile"},
                    }
                }
            },
        }
    )

    runtime = build_provider_runtime_config(
        provider_name="openai",
        config=config,
        active_profile="work",
        mode_name=None,
        mode_config=None,
        timeout_override=None,
    )

    assert runtime.auth == {"api_key": "sk-profile"}
    assert runtime.client == {"timeout": 45}
    assert runtime.common_request["temperature"] == 0.4
    assert runtime.routing["kind"] == "background"
    assert runtime.provider_request == {}
    assert runtime.to_legacy_config() == {
        "api_key": "sk-profile",
        "timeout": 45,
        "kind": "background",
        "temperature": 0.4,
        "openai": {"temperature": 0.4},
    }


def test_all_provider_defaults_reject_disallowed_fields() -> None:
    config = _config(
        {
            "providers": {
                "defaults": {
                    "api_key": "shared-secret",
                },
                "openai": {"api_key": "sk-provider"},
            }
        }
    )

    with pytest.raises(ValueError, match="providers\\.defaults\\.api_key"):
        build_provider_runtime_config(
            provider_name="openai",
            config=config,
            active_profile=None,
            mode_name=None,
            mode_config=None,
            timeout_override=None,
        )


def test_mode_generic_params_do_not_promote_auth_client_or_unknown_keys() -> None:
    config = _config(
        {
            "providers": {
                "openai": {
                    "api_key": "sk-provider",
                    "timeout": 30,
                }
            }
        }
    )

    runtime = build_provider_runtime_config(
        provider_name="openai",
        config=config,
        active_profile=None,
        mode_name="fast",
        mode_config={
            "api_key": "mode-secret-should-not-promote",
            "timeout": 5,
            "temperature": 0.2,
            "unknown_mode_key": "ignored",
        },
        timeout_override=None,
    )

    assert runtime.auth == {"api_key": "sk-provider"}
    assert runtime.client == {"timeout": 30}
    assert runtime.common_request == {"temperature": 0.2}
    assert runtime.provider_request == {}


def test_legacy_flat_mode_provider_native_key_is_preserved_for_selected_provider() -> None:
    config = _config(
        {
            "providers": {
                "openai": {"api_key": "sk-provider"},
            }
        }
    )

    runtime = build_provider_runtime_config(
        provider_name="openai",
        config=config,
        active_profile=None,
        mode_name="fast",
        mode_config={
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "kind": "immediate",
            "max_tool_calls": 12,
        },
        timeout_override=None,
    )

    assert runtime.provider_request["max_tool_calls"] == 12
    assert runtime.to_legacy_config()["openai"]["max_tool_calls"] == 12


def test_root_provider_recognized_native_keys_become_provider_request() -> None:
    config = _config(
        {
            "providers": {
                "openai": {
                    "api_key": "sk-provider",
                    "max_tool_calls": 50,
                },
                "perplexity": {
                    "api_key": "pplx-provider",
                    "stream_mode": "full",
                },
            },
            "profiles": {
                "work": {
                    "providers": {
                        "openai": {
                            "max_tool_calls": 30,
                        }
                    }
                }
            },
        }
    )

    openai_runtime = build_provider_runtime_config(
        provider_name="openai",
        config=config,
        active_profile="work",
        mode_name=None,
        mode_config=None,
        timeout_override=None,
    )
    perplexity_runtime = build_provider_runtime_config(
        provider_name="perplexity",
        config=config,
        active_profile=None,
        mode_name=None,
        mode_config=None,
        timeout_override=None,
    )

    assert openai_runtime.provider_request == {"max_tool_calls": 30}
    assert perplexity_runtime.provider_request == {"stream_mode": "full"}


def test_unknown_root_provider_key_is_rejected() -> None:
    config = _config(
        {
            "providers": {
                "perplexity": {
                    "api_key": "pplx-test",
                    "definitely_not_real": "x",
                }
            }
        }
    )

    with pytest.raises(ValueError, match="providers\\.perplexity\\.definitely_not_real"):
        build_provider_runtime_config(
            provider_name="perplexity",
            config=config,
            active_profile=None,
            mode_name=None,
            mode_config=None,
            timeout_override=None,
        )


def test_unknown_mode_provider_namespace_key_is_rejected() -> None:
    config = _config(
        {
            "providers": {
                "perplexity": {"api_key": "pplx-test"},
            }
        }
    )

    with pytest.raises(ValueError, match="mode_config\\.perplexity\\.future_sdk_option"):
        build_provider_runtime_config(
            provider_name="perplexity",
            config=config,
            active_profile=None,
            mode_name="focused",
            mode_config={
                "provider": "perplexity",
                "model": "sonar",
                "kind": "immediate",
                "perplexity": {"future_sdk_option": True},
            },
            timeout_override=None,
        )


def test_mode_provider_namespace_extra_body_is_allowed() -> None:
    config = _config(
        {
            "providers": {
                "perplexity": {"api_key": "pplx-test"},
            }
        }
    )

    runtime = build_provider_runtime_config(
        provider_name="perplexity",
        config=config,
        active_profile=None,
        mode_name="focused",
        mode_config={
            "provider": "perplexity",
            "model": "sonar",
            "kind": "immediate",
            "perplexity": {"extra_body": {"new_vendor_flag": True}},
        },
        timeout_override=None,
    )

    assert runtime.extension_bags["perplexity"]["extra_body"] == {"new_vendor_flag": True}


def test_profile_mode_provider_namespace_extra_body_is_allowed() -> None:
    config = _config(
        {
            "providers": {
                "perplexity": {"api_key": "pplx-test"},
            },
            "profiles": {
                "work": {
                    "modes": {
                        "focused": {
                            "perplexity": {"extra_body": {"profile_vendor_flag": True}},
                        }
                    }
                }
            },
        }
    )

    runtime = build_provider_runtime_config(
        provider_name="perplexity",
        config=config,
        active_profile="work",
        mode_name="focused",
        mode_config={
            "provider": "perplexity",
            "model": "sonar",
            "kind": "immediate",
        },
        timeout_override=None,
    )

    assert runtime.extension_bags["perplexity"]["extra_body"] == {"profile_vendor_flag": True}


def test_perplexity_extra_body_survives_runtime_to_legacy_request_shapes() -> None:
    from thoth.providers.perplexity import PerplexityProvider

    config = _config(
        {
            "providers": {
                "perplexity": {"api_key": "pplx-test"},
            }
        }
    )
    runtime = build_provider_runtime_config(
        provider_name="perplexity",
        config=config,
        active_profile=None,
        mode_name="focused",
        mode_config={
            "provider": "perplexity",
            "model": "sonar",
            "kind": "immediate",
            "perplexity": {"extra_body": {"new_vendor_flag": True}},
        },
        timeout_override=None,
    )

    provider = PerplexityProvider(
        api_key=runtime.auth["api_key"],
        config=runtime.to_legacy_config(),
    )
    sync_params = provider._build_request_params("prompt", None)
    async_body = provider._build_async_request_body("prompt", None, "idem-test")

    assert sync_params["extra_body"]["new_vendor_flag"] is True
    assert async_body["request"]["extra_body"]["new_vendor_flag"] is True


def test_profile_perplexity_extra_body_survives_runtime_to_legacy_request_shapes() -> None:
    from thoth.providers.perplexity import PerplexityProvider

    config = _config(
        {
            "providers": {
                "perplexity": {"api_key": "pplx-test"},
            },
            "profiles": {
                "work": {
                    "modes": {
                        "focused": {
                            "perplexity": {"extra_body": {"profile_vendor_flag": True}},
                        }
                    }
                }
            },
        }
    )
    runtime = build_provider_runtime_config(
        provider_name="perplexity",
        config=config,
        active_profile="work",
        mode_name="focused",
        mode_config={
            "provider": "perplexity",
            "model": "sonar",
            "kind": "immediate",
        },
        timeout_override=None,
    )

    provider = PerplexityProvider(
        api_key=runtime.auth["api_key"],
        config=runtime.to_legacy_config(),
    )
    sync_params = provider._build_request_params("prompt", None)
    async_body = provider._build_async_request_body("prompt", None, "idem-test")

    assert sync_params["extra_body"]["profile_vendor_flag"] is True
    assert async_body["request"]["extra_body"]["profile_vendor_flag"] is True


def test_builtin_mode_provider_namespace_user_override_deep_merges() -> None:
    from thoth.config import ConfigManager

    manager = ConfigManager.__new__(ConfigManager)
    manager.data = {
        "modes": {
            "gemini_quick": {
                "gemini": {"temperature": 0.2},
            }
        }
    }

    mode = manager.get_mode_config("gemini_quick")

    assert mode["gemini"]["temperature"] == 0.2
    assert mode["gemini"]["tools"] == ["google_search"]
    assert mode["gemini"]["thinking_budget"] == 0
