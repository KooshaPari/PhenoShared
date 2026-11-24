"""
Provider configuration helpers for pheno.config.
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field


class RetryConfig(BaseModel):
    """
    Retry configuration for providers.
    """

    max_retries: int = 3
    backoff_factor: float = 1.0


class AzureOpenAIConfig(BaseModel):
    """
    Azure OpenAI provider configuration.
    """

    retry: RetryConfig = Field(default_factory=RetryConfig)
    api_key: str | None = None
    endpoint: str | None = None


class ProviderConfigs(BaseModel):
    """
    Container for all provider configurations.
    """

    azure_openai: AzureOpenAIConfig = Field(default_factory=AzureOpenAIConfig)


def load_provider_configs_from_env() -> ProviderConfigs:
    """
    Load provider configurations from environment variables.
    """
    azure_config = AzureOpenAIConfig(
        retry=RetryConfig(
            max_retries=int(os.getenv("AZURE_OPENAI_MAX_RETRIES", "3")),
            backoff_factor=float(os.getenv("AZURE_OPENAI_BACKOFF_FACTOR", "1.0")),
        ),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )
    return ProviderConfigs(azure_openai=azure_config)


__all__ = ["AzureOpenAIConfig", "ProviderConfigs", "RetryConfig", "load_provider_configs_from_env"]
