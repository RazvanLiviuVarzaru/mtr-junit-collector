from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import TestFailure, TestRun


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}


def test_upload_test_results_success(client):
    # Example minimal valid XML with one failure
    xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="suite">
    <testcase classname="classA" name="test1">
      <failure>Failure message here</failure>
    </testcase>
  </testsuite>
</testsuites>"""

    response = client.post(
        "/upload-test-results/",
        data={
            "branch": "main",
            "revision": "rev123",
            "platform": "linux",
            "bbnum": "42",
            "typ": "test",
        },
        files={"file": ("test-results.xml", xml_content, "application/xml")},
    )
    assert response.status_code == 200
    assert "Results were stored successfully" in response.json()["detail"]


def test_upload_test_results_bad_extension(client):
    response = client.post(
        "/upload-test-results/",
        data={
            "branch": "main",
            "revision": "rev123",
            "platform": "linux",
            "bbnum": "42",
            "typ": "test",
        },
        files={"file": ("badfile.txt", b"some text", "text/plain")},
    )
    assert response.status_code == 400
    assert "Only .xml files are supported" in response.json()["detail"]


def test_upload_real_test_results(client, session):
    xml_path = Path("tests/integration/sample/mtr_01.xml")
    with open(xml_path, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/upload-test-results/",
        data={
            "branch": "main",
            "revision": "rev123",
            "platform": "linux",
            "bbnum": "42",
            "typ": "test",
        },
        files={"file": ("real_test_results.xml", file_bytes, "application/xml")},
    )

    assert response.status_code == 200
    assert "Results were stored successfully" in response.json()["detail"]

    # Verify DB entries
    # Example: Verify a test run was created
    test_runs = session.exec(select(TestRun)).all()
    assert len(test_runs) == 1
    assert test_runs[0].branch == "main"

    # Verify test cases (adjust to your actual schema logic)
    test_cases = session.exec(select(TestFailure)).all()
    assert any(tc.test_name == "archive" for tc in test_cases)

def test_nothing_to_upload(client, session):
    xml_path = Path("tests/integration/sample/mtr_02.xml")
    with open(xml_path, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/upload-test-results/",
        data={
            "branch": "main",
            "revision": "rev123",
            "platform": "linux",
            "bbnum": "42",
            "typ": "test",
        },
        files={"file": ("real_test_results.xml", file_bytes, "application/xml")},
    )

    assert response.status_code == 200
    assert "No test failures to store" in response.json()["detail"]

def test_duplicate_key_on_test_failure(client):
    """
    I've modified the mtr_03.xml to have the archive test failed with combinations="" on both instances.
    This should raise a duplicate key error on the database level.
    """
    xml_path = Path("tests/integration/sample/mtr_03.xml")
    with open(xml_path, "rb") as f:
        file_bytes = f.read()
    response = client.post(
        "/upload-test-results/",
        data={
            "branch": "main",
            "revision": "rev123",
            "platform": "linux",
            "bbnum": "42",
            "typ": "test",
        },
        files={"file": ("real_test_results.xml", file_bytes, "application/xml")},
    )
    assert response.status_code == 500
    assert "UNIQUE constraint failed" in response.json()["detail"]