"""Configuration management."""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

# Import TOML libraries
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w


class ConfigurationError(Exception):
    """Raised when there's a configuration error."""
    pass


class ProviderConfig(BaseModel):
    """Base configuration for an AI provider."""
    enabled: bool = False
    api_key: Optional[str] = None
    model: Optional[str] = None
    validated_at: Optional[datetime] = None


class AnthropicConfig(ProviderConfig):
    """Anthropic-specific configuration."""
    model: str = "claude-sonnet-4-5"


class OpenAIConfig(ProviderConfig):
    """OpenAI-specific configuration (future)."""
    model: str = "gpt-4o"


class GlobalConfig(BaseModel):
    """Global application settings."""
    default_provider: str = "anthropic"
    max_output_size: int = 100_000
    read_timeout: int = 60
    write_timeout: int = 300


class AppConfig(BaseModel):
    """Complete application configuration."""
    global_: GlobalConfig = Field(default_factory=GlobalConfig, alias="global")
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


def get_config_dir() -> Path:
    """
    Get OS-appropriate configuration directory.

    Returns:
        Path to configuration directory
    """
    if os.name == 'nt':  # Windows
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    else:  # Linux/Mac
        base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))

    config_dir = base / 'directory'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file() -> Path:
    """
    Get path to configuration file.

    Returns:
        Path to config.toml
    """
    return get_config_dir() / 'config.toml'


def is_configured() -> bool:
    """
    Check if a valid configuration exists.

    Returns:
        True if configuration exists and is valid
    """
    config_file = get_config_file()
    if not config_file.exists():
        return False

    try:
        load_config()
        return True
    except Exception:
        return False


def load_config() -> AppConfig:
    """
    Load configuration from TOML file.

    Returns:
        Loaded AppConfig

    Raises:
        ConfigurationError: If config file doesn't exist or is invalid
    """
    config_file = get_config_file()

    if not config_file.exists():
        raise ConfigurationError(
            "Configuration file not found. Run 'dy --configure' to set up."
        )

    try:
        with open(config_file, 'rb') as f:
            data = tomllib.load(f)

        # Convert provider configs to proper types
        providers = {}
        if 'providers' in data:
            for provider_name, provider_data in data['providers'].items():
                if provider_name == 'anthropic':
                    providers[provider_name] = AnthropicConfig(**provider_data)
                elif provider_name == 'openai':
                    providers[provider_name] = OpenAIConfig(**provider_data)
                else:
                    providers[provider_name] = ProviderConfig(**provider_data)

        # Build config
        config_data = {'providers': providers}
        if 'global' in data:
            config_data['global'] = GlobalConfig(**data['global'])
        else:
            config_data['global'] = GlobalConfig()

        return AppConfig(**config_data)

    except tomllib.TOMLDecodeError as e:
        raise ConfigurationError(
            f"Configuration file is corrupted (invalid TOML).\n"
            f"Run 'dy --configure' to create a new configuration.\n"
            f"Error: {e}"
        )
    except Exception as e:
        raise ConfigurationError(
            f"Failed to load configuration: {e}\n"
            f"Run 'dy --configure' to reconfigure."
        )


def save_config(config: AppConfig) -> None:
    """
    Save configuration to TOML file.

    Args:
        config: Configuration to save
    """
    config_file = get_config_file()

    # Convert to dictionary
    data = {
        'global': config.global_.model_dump(mode='json'),
        'providers': {}
    }

    for provider_name, provider_config in config.providers.items():
        provider_dict = provider_config.model_dump(mode='json')
        # Convert datetime to ISO string if present
        if provider_dict.get('validated_at'):
            provider_dict['validated_at'] = provider_dict['validated_at']
        data['providers'][provider_name] = provider_dict

    # Write to file
    with open(config_file, 'wb') as f:
        tomli_w.dump(data, f)


class Settings:
    """Lazy-loading settings accessor."""

    def __init__(self):
        self._config: Optional[AppConfig] = None

    @property
    def config(self) -> AppConfig:
        """Get loaded configuration."""
        if self._config is None:
            self._config = load_config()
        return self._config

    def reload(self):
        """Reload configuration from disk."""
        self._config = None

    @property
    def anthropic_api_key(self) -> str:
        """Get Anthropic API key."""
        provider = self.config.providers.get("anthropic")
        if not provider or not provider.enabled or not provider.api_key:
            raise ConfigurationError(
                "Anthropic provider not configured. Run 'dy --configure' to set up."
            )
        return provider.api_key

    @property
    def model(self) -> str:
        """Get model for the default provider."""
        default_provider = self.config.global_.default_provider
        provider = self.config.providers.get(default_provider)
        if not provider or not provider.model:
            raise ConfigurationError(
                f"{default_provider} provider not configured. Run 'dy --configure' to set up."
            )
        return provider.model

    @property
    def max_output_size(self) -> int:
        """Get max output size setting."""
        return self.config.global_.max_output_size

    @property
    def read_timeout(self) -> int:
        """Get read timeout setting."""
        return self.config.global_.read_timeout

    @property
    def write_timeout(self) -> int:
        """Get write timeout setting."""
        return self.config.global_.write_timeout


# Global settings instance (lazy-loading)
settings = Settings()
