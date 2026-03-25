"""LLM client — Protocol for DI + Anthropic implementation."""

from typing import Any, Protocol, cast

import anthropic
import structlog

logger = structlog.get_logger()


class LLMClient(Protocol):
    """Protocol for LLM calls. Implement this for testing stubs."""

    async def call(
        self,
        *,
        system: str,
        user_prompt: str,
        tool: dict[str, Any],
        model: str,
        max_tokens: int = 8192,
    ) -> dict[str, Any]: ...


class AnthropicLLMClient:
    """Production LLM client using Anthropic API with tool-use."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def call(
        self,
        *,
        system: str,
        user_prompt: str,
        tool: dict[str, Any],
        model: str,
        max_tokens: int = 8192,
    ) -> dict[str, Any]:
        tool_name = str(tool.get("name", "unknown"))
        logger.info("llm_call_start", model=model, tool=tool_name)

        response = await self._client.messages.create(  # type: ignore[call-overload]
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[tool],
            tool_choice={"type": "tool", "name": tool_name},
        )

        usage = response.usage
        logger.info(
            "llm_call_end",
            model=model,
            tool=tool_name,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )

        for block in response.content:
            if block.type == "tool_use":
                return cast("dict[str, Any]", block.input)

        msg = f"No tool_use block in response for tool {tool_name}"
        raise ValueError(msg)
