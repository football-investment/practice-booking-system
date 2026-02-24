"""
Payload Factory for API Smoke Tests

Generates minimally valid request payloads based on OpenAPI schemas.
This module extracts schemas from FastAPI's OpenAPI spec and creates
valid payloads for POST/PUT/PATCH endpoints.

Phase 1 Goal: Eliminate 422 validation errors by providing real, schema-compliant data.
"""

from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional
import json


class PayloadFactory:
    """Factory for generating valid API request payloads from OpenAPI schemas."""

    def __init__(self, openapi_schema: Dict):
        """
        Initialize factory with OpenAPI schema.

        Args:
            openapi_schema: Full OpenAPI schema from app.openapi()
        """
        self.openapi_schema = openapi_schema
        self.components = openapi_schema.get("components", {}).get("schemas", {})
        self.paths = openapi_schema.get("paths", {})

    def resolve_ref(self, ref_path: str) -> Dict:
        """Resolve $ref pointer to actual schema."""
        if ref_path.startswith("#/components/schemas/"):
            schema_name = ref_path.replace("#/components/schemas/", "")
            return self.components.get(schema_name, {})
        return {}

    def get_endpoint_schema(self, method: str, path: str) -> Optional[Dict]:
        """Get request body schema for a specific endpoint."""
        endpoint_data = self.paths.get(path, {}).get(method.lower(), {})
        request_body = endpoint_data.get("requestBody", {})
        content = request_body.get("content", {}).get("application/json", {})
        schema = content.get("schema", {})

        if "$ref" in schema:
            return self.resolve_ref(schema["$ref"])
        return schema if schema else None

    def generate_value(self, field_name: str, field_schema: Dict, context: Dict = None) -> Any:
        """
        Generate a valid value for a field based on its schema.

        Args:
            field_name: Name of the field
            field_schema: OpenAPI schema for the field
            context: Optional context with fixture values (tournament_id, student_id, etc.)

        Returns:
            A valid value for the field
        """
        context = context or {}

        # Handle $ref at the top level - resolve first
        if "$ref" in field_schema:
            resolved_schema = self.resolve_ref(field_schema["$ref"])
            return self.generate_value(field_name, resolved_schema, context)

        field_type = field_schema.get("type")
        field_format = field_schema.get("format")

        # Handle enums
        if "enum" in field_schema:
            return field_schema["enum"][0]

        # Handle anyOf (union types)
        if "anyOf" in field_schema:
            # Use first option
            return self.generate_value(field_name, field_schema["anyOf"][0], context)

        # Handle allOf (combined schemas)
        if "allOf" in field_schema:
            # Merge all schemas and generate value
            merged = {}
            for schema in field_schema["allOf"]:
                if "$ref" in schema:
                    resolved = self.resolve_ref(schema["$ref"])
                    merged.update(resolved)
                else:
                    merged.update(schema)
            return self.generate_value(field_name, merged, context)

        # Type-specific generation
        if field_type == "string":
            return self._generate_string(field_name, field_schema, context)
        elif field_type == "integer":
            return self._generate_integer(field_name, field_schema, context)
        elif field_type == "number":
            return self._generate_number(field_name, field_schema, context)
        elif field_type == "boolean":
            return self._generate_boolean(field_name, field_schema, context)
        elif field_type == "array":
            return self._generate_array(field_name, field_schema, context)
        elif field_type == "object":
            return self._generate_object(field_name, field_schema, context)

        # Default fallback
        return None

    def _generate_string(self, field_name: str, schema: Dict, context: Dict) -> str:
        """Generate string value."""
        # Check for context values (fixture IDs)
        field_lower = field_name.lower()

        # Date/datetime handling
        field_format = schema.get("format")
        if field_format == "date":
            return date.today().isoformat()
        elif field_format == "date-time":
            return datetime.now(timezone.utc).isoformat()

        # Enum values
        if "enum" in schema:
            return schema["enum"][0]

        # Pattern-based generation
        min_length = schema.get("minLength", 1)
        max_length = schema.get("maxLength", 100)

        # Field-specific defaults
        if "email" in field_lower:
            return "test@example.com"
        elif "password" in field_lower:
            return "TestPass123!"
        elif "phone" in field_lower:
            return "+36301234567"
        elif "code" in field_lower:
            timestamp = int(datetime.now(timezone.utc).timestamp())
            return f"TEST_{timestamp}"
        elif "name" in field_lower:
            return "Test Name"
        elif "description" in field_lower or "reason" in field_lower:
            return "Test description"
        elif "status" in field_lower:
            return "ACTIVE"
        elif "type" in field_lower:
            return "TEST"

        # Generic string of appropriate length
        value = "test_value"
        if len(value) < min_length:
            value = value * ((min_length // len(value)) + 1)
        return value[:max_length]

    def _generate_integer(self, field_name: str, schema: Dict, context: Dict) -> int:
        """Generate integer value."""
        field_lower = field_name.lower()

        # Context-based IDs
        if "tournament_id" in field_lower and "tournament_id" in context:
            return context["tournament_id"]
        elif "semester_id" in field_lower and "semester_id" in context:
            return context["semester_id"]
        elif "student_id" in field_lower and "student_id" in context:
            return context["student_id"]
        elif "instructor_id" in field_lower and "instructor_id" in context:
            return context["instructor_id"]
        elif "campus_id" in field_lower and "campus_id" in context:
            return context["campus_id"]

        # Respect min/max
        minimum = schema.get("minimum", 0)
        maximum = schema.get("maximum", 100)

        # Field-specific defaults
        if "player" in field_lower or "max" in field_lower:
            return max(minimum, min(10, maximum))
        elif "cost" in field_lower or "price" in field_lower:
            return max(minimum, 0)

        return max(minimum, 1)

    def _generate_number(self, field_name: str, schema: Dict, context: Dict) -> float:
        """Generate number value."""
        minimum = schema.get("minimum", 0.0)
        maximum = schema.get("maximum", 100.0)
        return max(minimum, 1.0)

    def _generate_boolean(self, field_name: str, schema: Dict, context: Dict) -> bool:
        """Generate boolean value."""
        # Default to True for most cases
        if "active" in field_name.lower() or "enabled" in field_name.lower():
            return True
        return False

    def _generate_array(self, field_name: str, schema: Dict, context: Dict) -> List:
        """Generate array value."""
        items_schema = schema.get("items", {})
        min_items = schema.get("minItems", 0)

        # If minimum is 0, return empty array for minimal payload
        if min_items == 0:
            return []

        # Generate minimum required items
        return [
            self.generate_value(f"{field_name}_item", items_schema, context)
            for _ in range(min_items)
        ]

    def _generate_object(self, field_name: str, schema: Dict, context: Dict) -> Dict:
        """Generate object value."""
        # Recursively generate nested object
        return self.generate_payload(schema, context)

    def generate_payload(self, schema: Dict, context: Dict = None) -> Dict:
        """
        Generate a complete payload from schema.

        Args:
            schema: OpenAPI schema definition
            context: Context with fixture values

        Returns:
            Valid payload dictionary
        """
        context = context or {}
        payload = {}

        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])

        # Generate only required fields for minimal payload
        for field_name in required_fields:
            if field_name in properties:
                field_schema = properties[field_name]

                # Resolve $ref if present
                if "$ref" in field_schema:
                    field_schema = self.resolve_ref(field_schema["$ref"])

                value = self.generate_value(field_name, field_schema, context)
                payload[field_name] = value

        return payload

    def create_payload(self, method: str, path: str, context: Dict = None) -> Dict:
        """
        Create payload for a specific endpoint.

        Args:
            method: HTTP method (POST, PUT, PATCH)
            path: API path
            context: Context with fixture values

        Returns:
            Valid payload dictionary
        """
        schema = self.get_endpoint_schema(method, path)
        if not schema:
            return {}

        return self.generate_payload(schema, context)


# Convenience functions for tournament endpoints
def create_tournament_payload(factory: PayloadFactory, context: Dict = None) -> Dict:
    """Generate payload for POST /api/v1/tournaments/"""
    return factory.create_payload("POST", "/api/v1/tournaments/", context)


def create_tournament_v2_payload(factory: PayloadFactory, context: Dict = None) -> Dict:
    """Generate payload for POST /api/v1/tournaments/create"""
    return factory.create_payload("POST", "/api/v1/tournaments/create", context)


def update_tournament_payload(factory: PayloadFactory, context: Dict = None) -> Dict:
    """Generate payload for PATCH /api/v1/tournaments/{tournament_id}"""
    return factory.create_payload("PATCH", "/api/v1/tournaments/{tournament_id}", context)


def cancel_tournament_payload(factory: PayloadFactory, context: Dict = None) -> Dict:
    """Generate payload for POST /api/v1/tournaments/{tournament_id}/cancel"""
    return factory.create_payload("POST", "/api/v1/tournaments/{tournament_id}/cancel", context)


def assign_instructor_payload(factory: PayloadFactory, context: Dict = None) -> Dict:
    """Generate payload for POST /api/v1/tournaments/{tournament_id}/assign-instructor"""
    return factory.create_payload("POST", "/api/v1/tournaments/{tournament_id}/assign-instructor", context)


def batch_enroll_payload(factory: PayloadFactory, context: Dict = None) -> Dict:
    """Generate payload for POST /api/v1/tournaments/{tournament_id}/admin/batch-enroll"""
    return factory.create_payload("POST", "/api/v1/tournaments/{tournament_id}/admin/batch-enroll", context)


def create_skill_mapping_payload(factory: PayloadFactory, context: Dict = None) -> Dict:
    """Generate payload for POST /api/v1/tournaments/{tournament_id}/skill-mappings"""
    return factory.create_payload("POST", "/api/v1/tournaments/{tournament_id}/skill-mappings", context)


def submit_session_results_payload(factory: PayloadFactory, context: Dict = None) -> Dict:
    """Generate payload for POST /api/v1/tournaments/{tournament_id}/sessions/{session_id}/submit-results"""
    return factory.create_payload("POST", "/api/v1/tournaments/{tournament_id}/sessions/{session_id}/submit-results", context)


def generate_sessions_payload(factory: PayloadFactory, context: Dict = None) -> Dict:
    """Generate payload for POST /api/v1/tournaments/{tournament_id}/generate-sessions"""
    return factory.create_payload("POST", "/api/v1/tournaments/{tournament_id}/generate-sessions", context)
