import dataclasses
import threading

import jsonschema

from .database import ResearchDB
from .research import Researcher


@dataclasses.dataclass(frozen=True)
class ResearchJobWorker:
    db: ResearchDB
    researcher: Researcher
    poll_interval: float = 0.5

    def run_once(self) -> bool:
        job = self.db.claim_next_research_job()
        if job is None:
            return False

        try:
            collection = self.db.get_collection(job.collection_id)
            result = self.researcher.research(job.product_info, collection)
            validation_schema = collection.research_schema.model_dump(exclude_none=True)
            _convert_nullable(validation_schema)
            jsonschema.validate(result.extracted_data, validation_schema)
            self.db.update_research_job_stage(job.id, "storing")
            self.db.complete_research_job(
                job_id=job.id,
                source_url=result.source_url,
                raw_source_text=result.raw_source_text,
                extracted_data=result.extracted_data,
                references=result.references,
            )
        except Exception as error:
            self.db.fail_research_job(job.id, str(error))
        return True

    def run_forever(self, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            if not self.run_once():
                stop_event.wait(self.poll_interval)


def _convert_nullable(schema: dict) -> None:
    if schema.pop("nullable", False):
        schema["type"] = [schema["type"], "null"]
    for property_schema in schema.get("properties", {}).values():
        _convert_nullable(property_schema)
    if isinstance(schema.get("items"), dict):
        _convert_nullable(schema["items"])