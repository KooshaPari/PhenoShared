"""Model Restriction Service.

This module provides centralized management of model usage restrictions
based on environment variables. It allows organizations to limit which
models can be used from each provider for cost control, compliance, or
standardization purposes.

Environment Variables:
- OPENAI_ALLOWED_MODELS: Comma-separated list of allowed OpenAI models
- GOOGLE_ALLOWED_MODELS: Comma-separated list of allowed Gemini models
- XAI_ALLOWED_MODELS: Comma-separated list of allowed X.AI GROK models
- OPENROUTER_ALLOWED_MODELS: Comma-separated list of allowed OpenRouter models
- DIAL_ALLOWED_MODELS: Comma-separated list of allowed DIAL models
"""

from __future__ import annotations

import logging
from collections import defaultdict

from pheno.providers.shared import ProviderType

logger = logging.getLogger(__name__)


class ModelRestrictionService:
    """Central authority for environment-driven model allowlists.

    Role
        Interpret ``*_ALLOWED_MODELS`` environment variables, keep their
        entries normalised (lowercase), and answer whether a provider/model
        pairing is permitted.

    Responsibilities
        * Parse, cache, and expose per-provider restriction sets
        * Validate configuration by cross-checking each entry against the
          provider's alias-aware model list
        * Offer helper methods such as ``is_allowed`` and ``filter_models`` to
          enforce policy everywhere model names appear (tool selection, CLI
          commands, etc.).
    """

    # Environment variable names
    ENV_VARS = {
        ProviderType.OPENAI: "OPENAI_ALLOWED_MODELS",
        ProviderType.GOOGLE: "GOOGLE_ALLOWED_MODELS",
        ProviderType.XAI: "XAI_ALLOWED_MODELS",
        ProviderType.OPENROUTER: "OPENROUTER_ALLOWED_MODELS",
        ProviderType.DIAL: "DIAL_ALLOWED_MODELS",
    }

    def __init__(self):
        """
        Initialize the restriction service by loading from environment.
        """
        self.restrictions: dict[ProviderType, set[str]] = {}
        self._alias_resolution_cache: dict[ProviderType, dict[str, str]] = defaultdict(dict)
        self._load_from_env()

    def _load_from_env(self) -> None:
        """
        Load restrictions from environment variables.
        """
        import os

        for provider_type, env_var in self.ENV_VARS.items():
            env_value = os.environ.get(env_var)

            if env_value is None or env_value == "":
                # Not set or empty - no restrictions (allow all models)
                logger.debug(
                    f"{env_var} not set or empty - all {provider_type.value} models allowed",
                )
                continue

            # Parse comma-separated list
            models = set()
            for model in env_value.split(","):
                cleaned = model.strip().lower()
                if cleaned:
                    models.add(cleaned)

            if models:
                self.restrictions[provider_type] = models
                self._alias_resolution_cache[provider_type] = {}
                logger.info(f"{provider_type.value} allowed models: {sorted(models)}")
            else:
                # All entries were empty after cleaning - treat as no restrictions
                logger.debug(
                    f"{env_var} contains only whitespace - all {provider_type.value} models allowed",
                )

    def is_allowed(self, provider_type: ProviderType, model_name: str) -> bool:
        """Check if a model is allowed for a given provider.

        Args:
            provider_type: The provider type
            model_name: The model name to check

        Returns:
            True if the model is allowed, False otherwise
        """
        # If no restrictions are set for this provider, allow all models
        if provider_type not in self.restrictions:
            return True

        # Check if the model (case-insensitive) is in the allowed set
        return model_name.lower() in self.restrictions[provider_type]

    def filter_models(self, provider_type: ProviderType, models: list[str]) -> list[str]:
        """Filter a list of models to only those allowed for the provider.

        Args:
            provider_type: The provider type
            models: List of model names to filter

        Returns:
            List of allowed model names
        """
        if provider_type not in self.restrictions:
            return models  # No restrictions

        allowed_models = self.restrictions[provider_type]
        return [model for model in models if model.lower() in allowed_models]

    def get_restricted_models(self, provider_type: ProviderType) -> set[str]:
        """Get the set of restricted (allowed) models for a provider.

        Args:
            provider_type: The provider type

        Returns:
            Set of allowed model names, or empty set if no restrictions
        """
        return self.restrictions.get(provider_type, set())

    def has_restrictions(self, provider_type: ProviderType) -> bool:
        """Check if there are any restrictions for a provider.

        Args:
            provider_type: The provider type

        Returns:
            True if there are restrictions, False otherwise
        """
        return provider_type in self.restrictions


# Global singleton instance
_restriction_service: ModelRestrictionService | None = None


def get_restriction_service() -> ModelRestrictionService:
    """
    Get the global restriction service instance.
    """
    global _restriction_service
    if _restriction_service is None:
        _restriction_service = ModelRestrictionService()
    return _restriction_service
