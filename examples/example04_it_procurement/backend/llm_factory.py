"""
Author: L. Saetta
Date last modified: 2026-07-23
License: MIT
Description: Creates the OCI OpenAI-compatible Responses API client for Example 04.
"""

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

OCI_OPENAI_BASE_URL_TEMPLATE = (
    "https://inference.generativeai.{region}.oci.oraclecloud.com/openai/v1"
)
DEFAULT_OCI_MODEL_ID = "openai.gpt-5.5"


def build_oci_openai_base_url(region: str) -> str:
    """Build the OCI OpenAI-compatible inference base URL for a region.

    Args:
        region: OCI region identifier, for example ``eu-frankfurt-1``.

    Returns:
        The OCI Generative AI OpenAI-compatible base URL.

    Raises:
        ValueError: If the region is blank.
    """
    normalized_region = region.strip()
    if not normalized_region:
        raise ValueError("REGION must not be blank.")
    return OCI_OPENAI_BASE_URL_TEMPLATE.format(region=normalized_region)


def create_oci_responses_client(
    api_key: str | None = None,
    region: str | None = None,
    timeout: float | None = 30.0,
) -> OpenAI:
    """Create an OCI Responses API client from local safe configuration.

    Args:
        api_key: OCI Generative AI API key. When omitted, reads ``GENAI_API_KEY``.
        region: OCI region. When omitted, reads ``REGION``.
        timeout: Optional SDK request timeout in seconds.

    Returns:
        A configured OpenAI-compatible OCI client.

    Raises:
        RuntimeError: If the required key or region is missing.
    """
    load_dotenv()
    resolved_api_key = api_key or os.getenv("GENAI_API_KEY")
    resolved_region = (region or os.getenv("REGION") or "").strip()
    if not resolved_api_key:
        raise RuntimeError("GENAI_API_KEY must be set to call OCI Generative AI.")
    if not resolved_region:
        raise RuntimeError("REGION must be set to call OCI Generative AI.")
    client_options: dict[str, Any] = {
        "api_key": resolved_api_key,
        "base_url": build_oci_openai_base_url(resolved_region),
        "max_retries": 2,
    }
    if timeout is not None:
        client_options["timeout"] = timeout
    return OpenAI(**client_options)


def get_oci_model_id(model_id: str | None = None) -> str:
    """Return the configured OCI hosted model identifier.

    Args:
        model_id: Explicit model ID that takes precedence over configuration.

    Returns:
        The explicit ID, configured ``OCI_MODEL_ID``, or a safe default.
    """
    return model_id or os.getenv("OCI_MODEL_ID", DEFAULT_OCI_MODEL_ID)
