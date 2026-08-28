import json
import os
import urllib.request
from pathlib import Path
from src.i18n import _
from typing import Dict, Any, List, Optional
from src.config import BASE_DIR

PRESETS_FILE = Path(__file__).resolve().parent / "presets.json"
USER_CONFIG_FILE = BASE_DIR / "providers.json"


class NoProviderConfiguredError(Exception):
    """Raised when the user has no provider registered in providers.json yet."""
    pass


def load_presets() -> Dict[str, Dict[str, Any]]:
    """Load default project presets."""
    if not PRESETS_FILE.exists():
        return {}
    with open(PRESETS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_providers_config() -> Dict[str, Any]:
    presets = load_presets()

    if not USER_CONFIG_FILE.exists():
        initial_config = {
            "active_provider": None,
            "providers": {}
        }
        save_providers_config(initial_config)
        return initial_config

    with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    return config


def save_providers_config(config: Dict[str, Any]) -> None:
    """Save user local preferences in root."""
    with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_active_provider_info() -> Dict[str, Any]:
    """Return current active provider and model data.

    Raises NoProviderConfiguredError if the user hasn't registered any
    provider yet — callers must handle this and guide the user to /provider.
    """
    config = load_providers_config()
    active_key = config.get("active_provider")
    provider = config.get("providers", {}).get(active_key) if active_key else None

    if not provider:
        raise NoProviderConfiguredError(
            _("No provider configured. Use /provider to add one.")
        )

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
    """Set active provider and model in providers.json."""
    config = load_providers_config()
    if provider_key not in config["providers"]:
        raise ValueError(_("Provider '{key}' not found.").format(key=provider_key))
    
    config["active_provider"] = provider_key
    if model_name:
        config["providers"][provider_key]["active_model"] = model_name
        if model_name not in config["providers"][provider_key].get("models", []):
            config["providers"][provider_key].setdefault("models", []).append(model_name)
            
    save_providers_config(config)


def remove_provider(provider_key: str) -> None:
    """Remove a provider from registry."""
    config = load_providers_config()
    if provider_key in config["providers"]:
        if len(config["providers"]) <= 1:
            raise ValueError(_("Cannot remove the only registered provider."))
        del config["providers"][provider_key]
        if config.get("active_provider") == provider_key:
            config["active_provider"] = next(iter(config["providers"]))
        save_providers_config(config)


def remove_model_from_provider(provider_key: str, model_name: str) -> None:
    """Remove a model from a specific provider."""
    config = load_providers_config()
    provider = config["providers"].get(provider_key)
    if not provider:
        return
    models = provider.get("models", [])
    if model_name in models:
        if len(models) <= 1:
            raise ValueError(_("The provider must have at least one registered model."))
        models.remove(model_name)
        if provider.get("active_model") == model_name:
            provider["active_model"] = models[0]
        save_providers_config(config)


def add_model_to_provider(provider_key: str, model_name: str, set_as_active: bool = True) -> None:
    """Add a new model to provider catalog."""
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
    """Query /models route to list real models from endpoint."""
    url = f"{base_url.rstrip('/')}/models"
    req = urllib.request.Request(url)
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("User-Agent", "CVECK/1.0")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            models_data = data.get("data", [])
            models = [m["id"] for m in models_data if isinstance(m, dict) and "id" in m]
            return sorted(models)
    except Exception as e:
        raise RuntimeError(_("Could not fetch models from {url}: {error}").format(url=url, error=e))


def get_dynamic_llm(temperature: float = 0.1):
    """Instantiate LLM according to active provider/model in providers.json."""
    p = get_active_provider_info()
    model = p["model"]
    provider_type = p["provider_type"]
    base_url = p["base_url"]
    api_key_env = p["api_key_env"]
    api_key = os.getenv(api_key_env) if api_key_env else None

    if provider_type == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model_name=model,
            temperature=temperature,
            max_tokens=8192,
            api_key=api_key
        )
    else:
        from langchain_openai import ChatOpenAI
        kwargs = {
            "model": model,
            "temperature": temperature,
            "max_tokens": 8192,
        }
        if base_url:
            kwargs["base_url"] = base_url
        if api_key:
            kwargs["api_key"] = api_key
        return ChatOpenAI(**kwargs)