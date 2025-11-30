"""Base agent class with non-blocking API calls."""

import asyncio
import json
from abc import ABC, abstractmethod

from anthropic import Anthropic, APIError

from ..config import settings


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(self):
        """Initialize the agent with Anthropic client."""
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.model
        self.max_tokens = 4096

    @abstractmethod
    async def call(self, *args, **kwargs) -> dict:
        """
        Call the agent with specific inputs.

        Returns:
            Dictionary with agent-specific response fields
        """
        pass

    async def _call_api(self, system_prompt: str, user_message: str) -> str:
        """
        Call the Anthropic API without blocking the event loop by running
        the synchronous client call in a thread executor.

        Args:
            system_prompt: System prompt for the agent
            user_message: User message

        Returns:
            Response text from the API

        Raises:
            APIError: If the API call fails after retries
        """
        loop = asyncio.get_event_loop()

        def sync_call():
            return self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

        try:
            response = await loop.run_in_executor(None, sync_call)

            # Extract text from response
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                raise ValueError("Empty response from API")

        except APIError as e:
            raise APIError(f"Anthropic API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error calling API: {str(e)}")

    def _parse_json_response(self, response_text: str) -> dict:
        """
        Parse JSON from agent response.

        Args:
            response_text: Raw response text from the agent

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If JSON parsing fails
        """
        # Try to extract JSON from markdown code blocks if present
        response_text = response_text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]  # Remove ```json
        elif response_text.startswith("```"):
            response_text = response_text[3:]  # Remove ```

        if response_text.endswith("```"):
            response_text = response_text[:-3]  # Remove closing ```

        response_text = response_text.strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse agent response as JSON: {e}\nResponse: {response_text[:200]}"
            )
