import concurrent.futures
import threading

from criterium.database import ResearchDB
from criterium.jobs import ResearchJobWorker
from criterium.research import ResearchResult
from criterium.schemas import ResearchSchemaObject, ResearchSchemaString


class ConcurrentResearcher:
    def __init__(self) -> None:
        self.barrier = threading.Barrier(2)

    def research(self, product_info, collection) -> ResearchResult:
        self.barrier.wait(timeout=2)
        return ResearchResult(
            source_url=f"https://example.com/{product_info.lower()}",
            raw_source_text=f"Evidence for {product_info}",
            extracted_data={"title": product_info},
        )


def test_worker_researches_multiple_jobs_concurrently(tmp_path) -> None:
    db = ResearchDB.from_connection_string(
        f"sqlite:///{tmp_path / 'jobs.db'}",
        create_if_not_exists=True,
    )
    collection = db.add_collection(
        "Books",
        "Extract title",
        ResearchSchemaObject(properties={"title": ResearchSchemaString()}),
    )
    db.add_research_jobs(collection.id, ["First", "Second"])
    worker = ResearchJobWorker(db=db, researcher=ConcurrentResearcher())

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        first_result = executor.submit(worker.run_once)
        second_result = executor.submit(worker.run_once)
        assert first_result.result() is True
        assert second_result.result() is True

    assert {job.status for job in db.get_research_jobs()} == {"succeeded"}
    assert len(db.get_products_by_collection(collection.id)) == 2
    db.engine.dispose()
