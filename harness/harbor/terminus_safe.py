"""Bounded Terminus adapter for local-model evaluation.

Harbor's stock Terminus 2 implementation recursively retries a response that
hit ``max_tokens``. Small local models can repeat that condition indefinitely,
turning one malformed response into an unbounded trial. This adapter keeps the
stock parser and execution loop while bounding only that recovery path.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, cast

from harbor.agents.terminus_2.terminus_2 import Command, Terminus2
from harbor.agents.terminus_2.tmux_session import TmuxSession
from harbor.llms.base import LLMResponse, OutputLengthExceededError


class SafeTerminus2(Terminus2):
    """Terminus 2 with bounded output-length recovery."""

    def __init__(
        self,
        *args: Any,
        max_output_retries: int = 2,
        terminal_command_timeout_sec: float = 30.0,
        **kwargs: Any,
    ) -> None:
        if max_output_retries < 0:
            raise ValueError("max_output_retries must be non-negative")
        if terminal_command_timeout_sec <= 0:
            raise ValueError("terminal_command_timeout_sec must be positive")
        self._max_output_retries = max_output_retries
        self._terminal_command_timeout_sec = terminal_command_timeout_sec
        super().__init__(*args, **kwargs)

    async def _execute_commands(
        self,
        commands: list[Command],
        session: TmuxSession,
    ) -> tuple[bool, str]:
        """Bound both tmux input and output collection per agent turn."""
        for command in commands:
            try:
                await asyncio.wait_for(
                    session.send_keys(
                        command.keystrokes,
                        block=False,
                        min_timeout_sec=command.duration_sec,
                    ),
                    timeout=self._terminal_command_timeout_sec,
                )
            except TimeoutError:
                return True, self._timeout_template.format(
                    timeout_sec=command.duration_sec,
                    command=command.keystrokes,
                    terminal_state=self._limit_output_length(
                        await session.get_incremental_output()
                    ),
                )

        try:
            output = await asyncio.wait_for(
                session.get_incremental_output(),
                timeout=self._terminal_command_timeout_sec,
            )
        except TimeoutError:
            return True, self._timeout_template.format(
                timeout_sec=self._terminal_command_timeout_sec,
                command="<terminal output collection>",
                terminal_state="Terminal output collection timed out.",
            )
        return False, self._limit_output_length(output)

    async def _query_llm(
        self,
        chat: Any,
        prompt: str,
        original_instruction: str = "",
        session: Any = None,
    ) -> LLMResponse:
        """Call the model and stop after bounded truncation recovery."""
        retry_prompt = prompt
        for attempt in range(self._max_output_retries + 1):
            try:
                start_time = time.time()
                response = await chat.chat(
                    retry_prompt,
                    **self._llm_call_kwargs,
                )
                self._api_request_times.append((time.time() - start_time) * 1000)
                return cast(LLMResponse, response)
            except OutputLengthExceededError as exc:
                if attempt >= self._max_output_retries:
                    raise

                truncated = getattr(
                    exc,
                    "truncated_response",
                    "[TRUNCATED RESPONSE NOT AVAILABLE]",
                )
                chat.messages.append({"role": "user", "content": retry_prompt})
                chat.messages.append({"role": "assistant", "content": truncated})
                chat.reset_response_chain()
                retry_prompt = (
                    "The previous response exceeded the output limit and no actions "
                    "were executed. Continue in a compact JSON response. Emit only "
                    "the next one or two shell commands, with no lengthy source "
                    "listing or explanation. Keep the response well below the limit."
                )
        # All retries exhausted (should re-raise before reaching here, but mypy
        # needs an explicit terminal statement to satisfy the LLMResponse return).
        raise RuntimeError(
            "_query_llm: control flow exited retry loop without returning a response"
        )
