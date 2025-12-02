"""API key validation logic."""

import asyncio
from typing import Tuple, Optional

from anthropic import Anthropic, APIError


async def validate_anthropic_key(api_key: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Anthropic API key with a minimal test call.

    Args:
        api_key: The Anthropic API key to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if key is valid, False otherwise
        - error_message: None if valid, error description if invalid

    Cost: ~$0.000001 (uses cheapest model with minimal tokens)
    """
    def sync_validate():
        try:
            client = Anthropic(api_key=api_key)

            # Ultra-minimal test request
            response = client.messages.create(
                model="claude-haiku-4-5",  # Alias for cheapest model
                max_tokens=1,  # Minimal completion
                messages=[{"role": "user", "content": "Hi"}]
            )

            return True, None

        except APIError as e:
            if e.status_code == 401:
                return False, "Invalid API key. Please check your key and try again."
            elif e.status_code == 429:
                return False, "Rate limit exceeded. Please try again in a moment."
            else:
                return False, f"API error: {str(e)}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_validate)


async def validate_api_key(provider: str, api_key: str, max_retries: int = 3) -> Tuple[bool, Optional[str]]:
    """
    Validate an API key for a given provider with retry logic.

    Args:
        provider: The provider name ("anthropic", "openai", etc.)
        api_key: The API key to validate
        max_retries: Maximum number of retry attempts

    Returns:
        Tuple of (is_valid, error_message)
    """
    for attempt in range(max_retries):
        if provider == "anthropic":
            is_valid, error_msg = await validate_anthropic_key(api_key)
        elif provider == "openai":
            # Placeholder for OpenAI validation
            return False, "OpenAI provider not yet supported"
        else:
            return False, f"Unknown provider: {provider}"

        # If successful or non-retryable error, return immediately
        if is_valid or (error_msg and "Invalid API key" in error_msg):
            return is_valid, error_msg

        # If this was a retryable error and we have retries left, wait a bit
        if attempt < max_retries - 1:
            await asyncio.sleep(1)

    # Max retries reached
    return False, error_msg
