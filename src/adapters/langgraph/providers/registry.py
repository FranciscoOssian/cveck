from dotenv import load_dotenv

load_dotenv()

import json
import os
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.core.paths import PROJECT_ROOT

PRESETS_FILE = Path(__file__).resolve().parent / "presets.json"
USER_CONFIG_FILE = PROJECT_ROOT / "providers.json"


class NoProviderConfiguredError(Exception):
    pass


def load_presets() -> Dict[str, Dict[str, Any]]:
    if not PRESETS_FILE.exists():
        return {}
    return json.loads(PRESETS_FILE.read_text(encoding="utf-8"))


def load_providers_config() -> Dict[str, Any]:
    if not USER_CONFIG_FILE.exists():
        initial = {"active_provider": None, "providers": {}}
        save_providers_config(initial)
        return initial
    return json.loads(USER_CONFIG_FILE.read_text(encoding="utf-8"))


def save_providers_config(config: Dict[str, Any]) -> None:
    USER_CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def get_active_provider_info() -> Dict[str, Any]:
    config = load_providers_config()
    active_key = config.get("active_provider")
    provider = config.get("providers", {}).get(active_key) if active_key else None

    if not provider:
        raise NoProviderConfiguredError("No provider configured. Use /provider to add one.")

    return {
        "key": active_key,
        "name": provider["name"],
        "model": provider.get("active_model", provider.get("models", ["default"])[0]),
        "provider_type": provider.get("provider_type", "openai"),
        "base_url": provider.get("base_url"),
        "api_key_env": provider.get("api_key_env"),
        "models": provider.get("models", [])
    }


def set_active_provider_and_model(provider_key: str, model_name: Optional[str] = None) -> None:
    config = load_providers_config()
    if provider_key not in config["providers"]:
        raise ValueError(f"Provider '{provider_key}' not found.")

    config["active_provider"] = provider_key
    if model_name:
        config["providers"][provider_key]["active_model"] = model_name
        if model_name not in config["providers"][provider_key].get("models", []):
            config["providers"][provider_key].setdefault("models", []).append(model_name)
    save_providers_config(config)


def remove_provider(provider_key: str) -> None:
    """Removes a provider from providers.json."""
    config = load_providers_config()
    if provider_key in config["providers"]:
        if len(config["providers"]) <= 1:
            raise ValueError("Cannot remove the only registered provider.")
        del config["providers"][provider_key]
        if config.get("active_provider") == provider_key:
            config["active_provider"] = next(iter(config["providers"]))
        save_providers_config(config)


def remove_model_from_provider(provider_key: str, model_name: str) -> None:
    """Removes a model from a specific provider."""
    config = load_providers_config()
    provider = config["providers"].get(provider_key)
    if not provider:
        return
    models = provider.get("models", [])
    if model_name in models:
        if len(models) <= 1:
            raise ValueError("The provider must have at least one registered model.")
        models.remove(model_name)
        if provider.get("active_model") == model_name:
            provider["active_model"] = models[0]
        save_providers_config(config)


def add_model_to_provider(provider_key: str, model_name: str, set_as_active: bool = True) -> None:
    """Adds a new model to the provider catalog."""
    config = load_providers_config()
    provider = config["providers"].get(provider_key)
    if not provider:
        return
    models = provider.setdefault("models", [])
    if model_name not in models:
        models.append(model_name)
    if set_as_active:
        provider["active_model"] = model_name
    save_providers_config(config)


def fetch_models_from_endpoint(base_url: str, api_key: Optional[str] = None) -> List[str]:
    """Queries the /models endpoint to list available models."""
    url = f"{base_url.rstrip('/')}/models"
    req = urllib.request.Request(url)
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("User-Agent", "CVECK/2.0")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            models_data = data.get("data", [])
            return sorted([m["id"] for m in models_data if isinstance(m, dict) and "id" in m])
    except Exception as e:
        raise RuntimeError(f"Could not fetch models from {url}: {e}")


def get_dynamic_llm(temperature: float = 0.1):
    p = get_active_provider_info()
    model = p["model"]
    provider_type = p["provider_type"]
    base_url = p["base_url"]
    env_var = p.get("api_key_env")
    api_key = os.getenv(env_var) if env_var else None

    # Defensive validation
    if env_var and not api_key:
        raise ValueError(
            f"Environment variable '{env_var}' was not found in .env or is empty."
        )

    if provider_type == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model_name=model, temperature=temperature, max_tokens=8192, api_key=api_key)
    else:
        from langchain_openai import ChatOpenAI
        kwargs = {"model": model, "temperature": temperature, "max_tokens": 8192}
        if base_url:
            kwargs["base_url"] = base_url
        if api_key:
            kwargs["api_key"] = api_key
        return ChatOpenAI(**kwargs)