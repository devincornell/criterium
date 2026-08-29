import typing

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from . import schemas


ScalarFieldType = typing.Literal["string", "integer", "number", "boolean"]


class _SuggestedLeafField(BaseModel):
    name: str
    field_type: ScalarFieldType
    description: str
    required: bool = False


class _SuggestedArrayItem(BaseModel):
    field_type: typing.Literal["string", "integer", "number", "boolean", "object"]
    description: str
    properties: list[_SuggestedLeafField] = Field(default_factory=list)


class _SuggestedField(BaseModel):
    name: str
    field_type: typing.Literal["string", "integer", "number", "boolean", "array", "object"]
    description: str
    required: bool = False
    properties: list[_SuggestedLeafField] = Field(default_factory=list)
    items: _SuggestedArrayItem | None = None


class _GeminiCollectionSuggestion(BaseModel):
    name: str
    extraction_prompt: str
    fields: list[_SuggestedField]


def _scalar_schema(
    field_type: ScalarFieldType,
    description: str,
) -> schemas.ResearchSchemaDef:
    common = {"description": description}
    if field_type == "string":
        return schemas.ResearchSchemaString(**common)
    if field_type == "integer":
        return schemas.ResearchSchemaInteger(**common)
    if field_type == "number":
        return schemas.ResearchSchemaNumber(**common)
    return schemas.ResearchSchemaBoolean(**common)


def _object_schema(
    fields: list[_SuggestedLeafField],
    description: str,
) -> schemas.ResearchSchemaObject:
    properties = {
        child.name: _scalar_schema(child.field_type, child.description)
        for child in fields
    }
    required = [child.name for child in fields if child.required]
    return schemas.ResearchSchemaObject(
        properties=properties,
        required=required or None,
        description=description,
    )


def _to_research_schema(field: _SuggestedField) -> schemas.ResearchSchemaDef:
    common = {"description": field.description}
    if field.field_type in {"string", "integer", "number", "boolean"}:
        return _scalar_schema(field.field_type, field.description)
    if field.field_type == "array":
        if field.items is None:
            raise ValueError(f"Suggested array field {field.name!r} has no item schema.")
        if field.items.field_type == "object":
            items = _object_schema(field.items.properties, field.items.description)
        else:
            items = _scalar_schema(field.items.field_type, field.items.description)
        return schemas.ResearchSchemaArray(items=items, **common)

    return _object_schema(field.properties, field.description)


class CollectionSuggester(typing.Protocol):
    def suggest(self, description: str) -> schemas.CollectionSuggestionResponse:
        """Propose a collection configuration from a plain-language description."""
        ...


class GeminiCollectionSuggester:
    def __init__(
        self,
        ai_client: genai.Client,
        model_name: str = "gemini-3.7-flash",
    ) -> None:
        self.ai_client = ai_client
        self.model_name = model_name

    def suggest(self, description: str) -> schemas.CollectionSuggestionResponse:
        response = self.ai_client.models.generate_content(
            model=self.model_name,
            contents=(
                "Design a practical starting configuration for a research collection based on "
                f"this description:\n\n{description}\n\n"
                "Choose a concise collection name, write an extraction prompt that tells a "
                "research model exactly what to find, and propose fields for a root object schema. "
                "For object fields, put nested fields in properties. For array fields, provide an "
                "items field definition. Include useful descriptions and mark only essential "
                "fields as required. Keep the schema focused enough to compare items consistently."
            ),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_GeminiCollectionSuggestion,
            ),
        )

        if isinstance(response.parsed, _GeminiCollectionSuggestion):
            suggestion = response.parsed
        elif response.parsed is not None:
            suggestion = _GeminiCollectionSuggestion.model_validate(response.parsed)
        elif response.text:
            suggestion = _GeminiCollectionSuggestion.model_validate_json(response.text)
        else:
            raise ValueError("Gemini returned no collection suggestion.")

        properties = {
            field.name: _to_research_schema(field)
            for field in suggestion.fields
        }
        required = [field.name for field in suggestion.fields if field.required]
        return schemas.CollectionSuggestionResponse(
            name=suggestion.name,
            extraction_prompt=suggestion.extraction_prompt,
            research_schema=schemas.ResearchSchemaObject(
                properties=properties,
                required=required or None,
            ),
        )
