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


class _SuggestedArrayItem(BaseModel):
    field_type: typing.Literal["string", "integer", "number", "boolean", "object"]
    description: str
    properties: list[_SuggestedLeafField] = Field(default_factory=list)


class _SuggestedField(BaseModel):
    name: str
    field_type: typing.Literal["string", "integer", "number", "boolean", "array", "object"]
    description: str
    properties: list[_SuggestedLeafField] = Field(default_factory=list)
    items: _SuggestedArrayItem | None = None


class _GeminiCollectionSuggestion(BaseModel):
    name: str
    research_instructions: str | None = None
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
    return schemas.ResearchSchemaObject(
        properties=properties,
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
                "Choose a concise collection name and propose fields for a root object schema. "
                "For object fields, put nested fields in properties. For array fields, provide an "
                "items field definition. Include useful descriptions. Every proposed field will be "
                "required, so keep the schema focused enough to compare items consistently and tell "
                "the research model to use null when reliable evidence is unavailable. Only provide "
                "research_instructions when the description includes cross-cutting scope, source, "
                "methodology, or interpretation rules that cannot be captured by field descriptions."
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
        return schemas.CollectionSuggestionResponse(
            name=suggestion.name,
            research_instructions=suggestion.research_instructions,
            research_schema=schemas.ResearchSchemaObject(
                properties=properties,
            ),
        )
