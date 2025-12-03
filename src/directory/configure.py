"""Interactive configuration wizard."""

import asyncio
from datetime import datetime

import questionary
from questionary import Style

from .config import (
    AppConfig,
    AnthropicConfig,
    GlobalConfig,
    get_config_file,
    is_configured,
    load_config,
    save_config,
)
from .validation import validate_api_key


# Provider metadata for configuration
PROVIDER_METADATA = {
    "anthropic": {
        "name": "Anthropic (Claude)",
        "supported": True,
        "default_model": "claude-sonnet-4-5",
        "available_models": [
            "claude-haiku-4-5",
            "claude-sonnet-4-5",
            "claude-opus-4-5",
        ],
    },
    # "openai": {
    #     "name": "OpenAI (GPT)",
    #     "supported": False,
    #     "default_model": "gpt-4o",
    #     "available_models": ["gpt-4o", "gpt-4o-mini"],
    # },
}

# Custom style for questionary
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#f44336 bold'),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#673ab7 bold'),
    ('selected', 'fg:#cc5454'),
    ('separator', 'fg:#cc5454'),
    ('instruction', ''),
    ('text', ''),
    ('disabled', 'fg:#858585 italic')
])


def print_header():
    """Print welcome header."""
    print("\n" + "=" * 60)
    print("  Directory.y Configuration")
    print("=" * 60 + "\n")


def print_section(title: str):
    """Print section header."""
    print(f"\n{title}")
    print("-" * len(title))


async def select_provider() -> str:
    """
    Prompt user to select a provider.

    Returns:
        Selected provider name
    """
    print_section("Step 1: Provider Selection")

    # Build choices list
    choices = []
    for provider_id, metadata in PROVIDER_METADATA.items():
        if metadata["supported"]:
            choices.append(questionary.Choice(
                title=metadata["name"],
                value=provider_id
            ))
        else:
            choices.append(questionary.Choice(
                title=f"{metadata['name']} (Coming Soon)",
                value=provider_id,
                disabled="Not yet supported"
            ))

    provider = await questionary.select(
        "Which AI provider would you like to use?",
        choices=choices,
        style=custom_style
    ).ask_async()

    if not provider:
        raise KeyboardInterrupt()

    return provider


async def input_and_validate_api_key(provider: str) -> str:
    """
    Prompt for API key and validate it.

    Args:
        provider: Provider name

    Returns:
        Validated API key
    """
    print_section("Step 2: API Key")

    provider_name = PROVIDER_METADATA[provider]["name"]

    while True:
        api_key = await questionary.password(
            f"Enter your {provider_name} API key:",
            style=custom_style
        ).ask_async()

        if not api_key:
            raise KeyboardInterrupt()

        if not api_key.strip():
            print("Error: API key cannot be empty.\n")
            continue

        # Validate API key
        print_section("Step 3: API Key Validation")
        print("Testing API key with a minimal request...\n")

        is_valid, error_msg = await validate_api_key(provider, api_key.strip())

        if is_valid:
            print("✓ API key validated successfully!\n")
            return api_key.strip()
        else:
            print(f"✗ Validation failed: {error_msg}\n")

            retry = await questionary.confirm(
                "Would you like to try again?",
                default=True,
                style=custom_style
            ).ask_async()

            if not retry:
                # Offer to save without validation
                save_anyway = await questionary.confirm(
                    "Save configuration without validation?",
                    default=False,
                    style=custom_style
                ).ask_async()

                if save_anyway:
                    print("\n⚠ Warning: Saving unvalidated API key\n")
                    return api_key.strip()
                else:
                    raise KeyboardInterrupt()


async def select_model(provider: str, existing_model: str = None) -> str:
    """
    Prompt user to select a model.

    Args:
        provider: Provider name
        existing_model: Existing model selection (if reconfiguring)

    Returns:
        Selected model alias
    """
    print_section("Step 4: Model Selection")

    metadata = PROVIDER_METADATA[provider]
    default_model = existing_model or metadata["default_model"]

    # Build choices
    choices = [
        questionary.Choice(
            title=f"{model}{' (default)' if model == default_model else ''}",
            value=model
        )
        for model in metadata["available_models"]
    ]

    model = await questionary.select(
        "Which model would you like to use?",
        choices=choices,
        default=default_model,
        style=custom_style
    ).ask_async()

    if not model:
        raise KeyboardInterrupt()

    return model


async def configure_global_settings(existing_config: GlobalConfig = None) -> GlobalConfig:
    """
    Prompt user to configure global settings.

    Args:
        existing_config: Existing configuration (if reconfiguring)

    Returns:
        GlobalConfig with user selections
    """
    print_section("Step 5: Global Settings")

    defaults = existing_config if existing_config else GlobalConfig()

    max_output = await questionary.text(
        "Maximum output size (bytes):",
        default=str(defaults.max_output_size),
        style=custom_style,
        validate=lambda x: x.isdigit() and int(x) > 0
    ).ask_async()

    if not max_output:
        raise KeyboardInterrupt()

    read_timeout = await questionary.text(
        "Read timeout (seconds):",
        default=str(defaults.read_timeout),
        style=custom_style,
        validate=lambda x: x.isdigit() and int(x) > 0
    ).ask_async()

    if not read_timeout:
        raise KeyboardInterrupt()

    write_timeout = await questionary.text(
        "Write timeout (seconds):",
        default=str(defaults.write_timeout),
        style=custom_style,
        validate=lambda x: x.isdigit() and int(x) > 0
    ).ask_async()

    if not write_timeout:
        raise KeyboardInterrupt()

    return GlobalConfig(
        default_provider=defaults.default_provider,
        max_output_size=int(max_output),
        read_timeout=int(read_timeout),
        write_timeout=int(write_timeout)
    )


def mask_api_key(api_key: str) -> str:
    """
    Mask API key for display.

    Args:
        api_key: Full API key

    Returns:
        Masked API key (shows first 7 and last 4 chars)
    """
    if len(api_key) <= 11:
        return "***"
    return f"{api_key[:7]}...{api_key[-4:]}"


async def confirm_and_save(config: AppConfig, provider: str, api_key: str) -> bool:
    """
    Show summary and confirm save.

    Args:
        config: Complete configuration
        provider: Provider name
        api_key: API key (for masked display)

    Returns:
        True if user confirmed save
    """
    print_section("Step 6: Confirmation")

    provider_name = PROVIDER_METADATA[provider]["name"]
    provider_config = config.providers[provider]

    print("\nConfiguration Summary:")
    print(f"  Provider:       {provider_name}")
    print(f"  Model:          {provider_config.model}")
    print(f"  API Key:        {mask_api_key(api_key)}")
    print(f"  Max Output:     {config.global_.max_output_size} bytes")
    print(f"  Read Timeout:   {config.global_.read_timeout}s")
    print(f"  Write Timeout:  {config.global_.write_timeout}s")
    print()

    confirmed = await questionary.confirm(
        "Save this configuration?",
        default=True,
        style=custom_style
    ).ask_async()

    return confirmed


async def run_configure_wizard():
    """
    Run the interactive configuration wizard.

    This is the main entry point for the configuration process.
    """
    try:
        print_header()

        # Check if already configured
        existing_config = None
        if is_configured():
            print("⚠ Existing configuration found.\n")
            reconfigure = await questionary.confirm(
                "Would you like to reconfigure?",
                default=True,
                style=custom_style
            ).ask_async()

            if not reconfigure:
                print("\nConfiguration cancelled.\n")
                return

            try:
                existing_config = load_config()
            except Exception:
                existing_config = None

        # Step 1: Select provider
        provider = await select_provider()

        # Step 2-3: API key input and validation
        api_key = await input_and_validate_api_key(provider)

        # Step 4: Model selection
        existing_model = None
        if existing_config and provider in existing_config.providers:
            existing_model = existing_config.providers[provider].model

        model = await select_model(provider, existing_model)

        # Step 5: Global settings
        existing_global = existing_config.global_ if existing_config else None
        global_config = await configure_global_settings(existing_global)

        # Set default provider
        global_config.default_provider = provider

        # Build provider config
        if provider == "anthropic":
            provider_config = AnthropicConfig(
                enabled=True,
                api_key=api_key,
                model=model,
                validated_at=datetime.now()
            )
        else:
            # Future providers
            from .config import ProviderConfig
            provider_config = ProviderConfig(
                enabled=True,
                api_key=api_key,
                model=model,
                validated_at=datetime.now()
            )

        # Build complete config
        config = AppConfig(
            global_=global_config,
            providers={provider: provider_config}
        )

        # Step 6: Confirm and save
        confirmed = await confirm_and_save(config, provider, api_key)

        if confirmed:
            save_config(config)
            config_file = get_config_file()

            print_section("Complete")
            print(f"✓ Configuration saved to: {config_file}\n")
            print("You're all set! Run 'dy' to start using Directory.y\n")
        else:
            print("\nConfiguration cancelled.\n")

    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled by user.\n")
    except Exception as e:
        print(f"\n\nError during configuration: {e}\n")
        raise
