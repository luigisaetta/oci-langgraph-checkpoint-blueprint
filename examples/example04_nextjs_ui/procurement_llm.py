"""
Author: L. Saetta
Date last modified: 2026-07-23
License: MIT
Description: Uses OCI Responses API calls to extract IT procurement requests and offers.
"""

import json
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError

from examples.example04_nextjs_ui.llm_factory import (
    create_oci_responses_client,
    get_oci_model_id,
)


class ProcurementRequest(BaseModel):
    """Represents the structured product request extracted from user language."""

    requested_object: str = Field(min_length=1, max_length=120)
    quantity: int = Field(ge=1, le=99)


REQUEST_EXTRACTION_SCHEMA = {
    "type": "json_schema",
    "name": "procurement_request",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["requested_object", "quantity"],
        "properties": {
            "requested_object": {
                "type": "string",
                "description": "Concise IT product requested, preserving useful attributes.",
            },
            "quantity": {
                "type": "integer",
                "minimum": 1,
                "maximum": 99,
                "description": "Requested unit count; use 1 when omitted.",
            },
        },
    },
}

EXTRACTION_INSTRUCTIONS = """Extract an IT procurement request.
Return only the structured JSON requested by the schema. Identify one concise
requested product description, retaining relevant attributes such as wireless
or ergonomic. Extract a positive quantity; use 1 when the user omits it."""

OFFER_INSTRUCTIONS = """You are an IT procurement assistant simulating a catalogue search.
Given a structured requested object and quantity, generate a concise offer in
plain text. Include the requested item, quantity, an illustrative unit price
and total in EUR, and one short availability assumption. Do not claim to query
a real supplier, reserve inventory, or create an actual order. Do not add
products that were not requested."""


class ProcurementInferenceError(ValueError):
    """Raised when an OCI model response cannot safely drive the workflow."""


class ProcurementLlmService:
    """Coordinates the two OCI Responses API calls used by the procurement graph."""

    def __init__(
        self,
        client_factory: Callable[[], Any] = create_oci_responses_client,
        model_id: str | None = None,
    ) -> None:
        """Initialize the service without contacting OCI.

        Args:
            client_factory: Lazy OCI client factory, injectable in unit tests.
            model_id: Optional OCI model ID. Defaults to ``OCI_MODEL_ID``.
        """
        self._client_factory = client_factory
        self._client: Any | None = None
        self._model_id = get_oci_model_id(model_id)

    @property
    def _inference_client(self) -> Any:
        """Create the configured client on the first actual LLM call."""
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    def extract_request(self, message: str) -> ProcurementRequest:
        """Extract the requested IT object and quantity through structured output.

        Args:
            message: Original natural-language user request.

        Returns:
            A validated structured procurement request.

        Raises:
            ProcurementInferenceError: If the model output is absent, invalid JSON,
                or incompatible with the expected schema.
        """
        response = self._inference_client.responses.create(
            model=self._model_id,
            instructions=EXTRACTION_INSTRUCTIONS,
            input=message,
            text={"format": REQUEST_EXTRACTION_SCHEMA},
        )
        return self._parse_extraction_output(getattr(response, "output_text", ""))

    def generate_offer(self, request: ProcurementRequest) -> str:
        """Generate a concise simulated offer from structured procurement data.

        Args:
            request: Previously validated extracted procurement request.

        Returns:
            A non-empty simulated offer suitable for human approval.

        Raises:
            ProcurementInferenceError: If OCI returns no usable offer text.
        """
        response = self._inference_client.responses.create(
            model=self._model_id,
            instructions=OFFER_INSTRUCTIONS,
            input=request.model_dump_json(),
        )
        offer = str(getattr(response, "output_text", "")).strip()
        if not offer:
            raise ProcurementInferenceError("OCI returned an empty procurement offer.")
        return offer

    @staticmethod
    def _parse_extraction_output(output_text: str) -> ProcurementRequest:
        """Parse and validate structured output returned by the model.

        Args:
            output_text: JSON text returned from the Responses API.

        Returns:
            Validated request data.

        Raises:
            ProcurementInferenceError: If the output is invalid or violates schema.
        """
        try:
            payload = json.loads(output_text)
            return ProcurementRequest.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as error:
            raise ProcurementInferenceError(
                "OCI returned an invalid structured procurement request."
            ) from error
