"""Operational/API contract tests; fixtures do not measure lunar accuracy."""

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.jobs import JobRepository
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    for name, value in {
        "UPLOAD_DIR": tmp_path / "uploads",
        "RESULTS_DIR": tmp_path / "results",
        "CACHE_DIR": tmp_path / "cache",
        "RAW_DIR": tmp_path / "raw",
        "JOB_DB_PATH": tmp_path / "jobs.sqlite3",
    }.items():
        monkeypatch.setattr(settings, name, value)
    settings.RAW_DIR.mkdir()
    monkeypatch.setattr("app.api.routes.registration.submit_job", lambda *args: None)
    with TestClient(app) as client:
        yield client


def test_persistent_jobs_queue_bound_and_restart_recovery(tmp_path):
    repo = JobRepository(tmp_path / "jobs.sqlite3")
    repo.create({"job_id": "one", "status": "pending"}, max_pending=1)
    assert JobRepository(repo.path).get("one")["status"] == "pending"
    with pytest.raises(RuntimeError, match="full"):
        repo.create({"job_id": "two", "status": "pending"}, max_pending=1)
    repo.recover()
    assert repo.get("one")["status"] == "failed"


def test_upload_create_poll_cancel_and_reject_glob_ids(client):
    image = np.random.default_rng(5).integers(0, 255, (64, 64), dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    ids = [
        client.post(
            "/api/v1/upload",
            files={"file": ("unit.png", encoded.tobytes(), "image/png")},
        ).json()["file_id"]
        for _ in range(2)
    ]
    request = {"source_image_id": ids[0], "reference_image_id": ids[1]}
    response = client.post("/api/v1/register", json=request)
    assert response.status_code == 200, response.text
    job = response.json()["job_id"]
    assert client.get(f"/api/v1/jobs/{job}").json()["status"] == "pending"
    assert client.delete(f"/api/v1/jobs/{job}").json()["cancel_requested"]
    assert (
        client.post(
            "/api/v1/register", json={**request, "matcher": "invalid"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/register", json={**request, "source_image_id": "../*"}
        ).status_code
        == 422
    )


def test_corrupt_upload_is_rejected(client):
    assert (
        client.post(
            "/api/v1/upload", files={"file": ("bad.png", b"invalid", "image/png")}
        ).status_code
        == 400
    )


def test_authentication_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-key")
    assert client.get("/api/v1/images").status_code == 401
    assert (
        client.get("/api/v1/images", headers={"X-API-Key": "test-key"}).status_code
        == 200
    )
    assert client.get("/api/v1/health").status_code == 200


def test_actual_configuration_and_result_path_containment(client):
    config = client.get("/api/v1/config/processing").json()
    assert config["engine_config"]["features"] == "aliked"
    assert config["subpixel"]["method"] == "fractional_gradient_ncc_bidirectional"
    assert client.get("/api/v1/files/%2e%2e/jobs.sqlite3").status_code != 200


def test_scale_divisors_must_be_positive_finite(client):
    response = client.post(
        "/api/v1/register",
        json={
            "source_image_id": "a",
            "reference_image_id": "b",
            "source_scale_xy": [0, 1],
        },
    )
    assert response.status_code == 422


def test_historical_demo_never_reports_current_acceptance_or_invented_dates(
    client, tmp_path, monkeypatch
):
    import json

    monkeypatch.setattr(settings, "BASE_DIR", tmp_path)
    directory = tmp_path / "outputs/submission"
    directory.mkdir(parents=True)
    (directory / "metrics.json").write_text(
        json.dumps({"evaluation_metrics": {"quality_decision": "ACCEPT"}})
    )
    result = client.get("/api/v1/jobs/showcase_submission/results").json()["metrics"]
    assert result["evaluation_metrics"]["quality_decision"] == "HISTORICAL_UNVALIDATED"
    assert result["evaluation_metrics"]["historical_quality_decision"] == "ACCEPT"
    status = client.get("/api/v1/jobs/showcase_submission").json()
    assert status["created_at"] is None
    assert status["completed_at"] is None


def test_public_mode_refuses_start_without_api_key(client, monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_MODE", True)
    monkeypatch.setattr(settings, "API_KEY", None)
    with (
        pytest.raises(RuntimeError, match="PUBLIC_MODE requires API_KEY"),
        TestClient(app),
    ):
        pass


def test_workspace_history_metadata_and_visualization(client):
    import json
    import uuid

    job_id = str(uuid.uuid4())
    repo = JobRepository()
    repo.create(
        {
            "job_id": job_id,
            "status": "completed",
            "source_path": "/private/source.img",
            "metrics": {"quality_decision": "REJECT"},
        }
    )
    directory = settings.RESULTS_DIR / job_id
    directory.mkdir()
    (directory / "transform.json").write_text(
        json.dumps({"direction": "native_source_pixels_to_native_reference_pixels"})
    )
    (directory / "correspondence_points.csv").write_text(
        "point_id,source_x,source_y,reference_x,reference_y,primary_confidence,secondary_agreement,refined,fit_residual_reference_px\n1,100.25,201.5,4.5,9.25,0.8,True,False,1.2\n"
    )
    history = client.get("/api/v1/jobs").json()
    assert history[0]["quality_decision"] == "REJECT"
    assert "/private/" not in str(history)
    result = client.get(f"/api/v1/jobs/{job_id}/visualization").json()
    assert result["points"][0]["source"] == [100.25, 201.5]
    assert result["points"][0]["secondary_agreement"] is True
    assert result["points"][0]["refined"] is False
    assert result["artifacts"]["transform.json"].endswith("/transform.json")
    assert client.get("/api/v1/jobs?limit=101").status_code == 422
    repo.update(job_id, status="processing")
    assert client.get(f"/api/v1/jobs/{job_id}/visualization").status_code == 409


def test_invalid_crop_rejected_before_queueing(client):
    image = np.arange(64 * 64, dtype=np.uint8).reshape(64, 64)
    _, encoded = cv2.imencode(".png", image)
    ids = [
        client.post(
            "/api/v1/upload",
            files={"file": ("unit.png", encoded.tobytes(), "image/png")},
        ).json()["file_id"]
        for _ in range(2)
    ]
    metadata = client.get(f"/api/v1/images/{ids[0]}/metadata").json()
    assert metadata["shape"] == [64, 64]
    response = client.post(
        "/api/v1/register",
        json={
            "source_image_id": ids[0],
            "reference_image_id": ids[1],
            "source_bounds": [0, 0, 100, 10],
        },
    )
    assert response.status_code == 400
    assert client.get("/api/v1/jobs").json() == []
