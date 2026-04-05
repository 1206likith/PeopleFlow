import json

from app.services.experiment_job_service import ExperimentJobService


def test_experiment_job_service_runs_job_to_completion():
    service = ExperimentJobService(max_workers=1)

    queued = service.submit_job(
        execution_type="benchmark",
        requested_by="tester",
        runner=lambda: {"execution_type": "benchmark", "benchmark": "corridor", "description": "done"},
        input_summary={"benchmark": "corridor"},
    )

    assert queued["job_id"].startswith("expjob-")
    assert queued["status"] in {"queued", "running", "completed"}

    completed = service.wait_for_completion(queued["job_id"], timeout=2.0)
    assert completed["status"] == "completed"
    assert completed["result"]["benchmark"] == "corridor"
    assert completed["result_summary"]["title"] == "Benchmark corridor"


def test_experiment_job_service_records_failures():
    service = ExperimentJobService(max_workers=1)

    queued = service.submit_job(
        execution_type="optimization",
        requested_by="tester",
        runner=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        input_summary={"name": "opt-suite"},
    )

    failed = service.wait_for_completion(queued["job_id"], timeout=2.0)
    assert failed["status"] == "failed"
    assert failed["error"]["type"] == "RuntimeError"
    assert failed["error"]["message"] == "boom"

    listing = service.list_jobs(limit=5)
    assert listing["job_count"] == 1
    assert listing["jobs"][0]["job_id"] == queued["job_id"]
    assert "result" not in listing["jobs"][0]


def test_experiment_job_service_persists_completed_jobs(tmp_path):
    storage_path = tmp_path / "experiment_jobs.json"
    service = ExperimentJobService(max_workers=1, storage_path=storage_path)

    queued = service.submit_job(
        execution_type="benchmark",
        requested_by="tester",
        runner=lambda: {"execution_type": "benchmark", "benchmark": "corridor", "description": "done"},
        input_summary={"benchmark": "corridor"},
    )

    completed = service.wait_for_completion(queued["job_id"], timeout=2.0)
    assert completed["status"] == "completed"
    assert storage_path.exists()

    reloaded = ExperimentJobService(max_workers=1, storage_path=storage_path)
    recovered = reloaded.get_job(queued["job_id"])
    assert recovered["status"] == "completed"
    assert recovered["result"]["benchmark"] == "corridor"


def test_experiment_job_service_marks_active_jobs_failed_after_restart(tmp_path):
    storage_path = tmp_path / "experiment_jobs.json"
    storage_path.write_text(
        json.dumps(
            {
                "job_schema_version": "peopleflow-experiment-job-v1",
                "persisted_at": "2026-04-03T00:00:00Z",
                "job_count": 1,
                "jobs": [
                    {
                        "job_schema_version": "peopleflow-experiment-job-v1",
                        "job_id": "expjob-restart",
                        "execution_type": "optimization",
                        "status": "running",
                        "background": True,
                        "requested_by": "tester",
                        "input_summary": {"name": "opt-suite"},
                        "submitted_at": "2026-04-03T00:00:00Z",
                        "updated_at": "2026-04-03T00:00:00Z",
                        "started_at": "2026-04-03T00:00:01Z",
                        "completed_at": None,
                        "result_summary": None,
                        "result": None,
                        "error": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    service = ExperimentJobService(max_workers=1, storage_path=storage_path)
    recovered = service.get_job("expjob-restart")
    assert recovered["status"] == "failed"
    assert recovered["error"]["type"] == "ProcessRestartInterrupted"
    assert "relaunched" in recovered["error"]["message"]
