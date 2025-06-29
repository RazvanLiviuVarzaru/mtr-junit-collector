import logging
from typing import List, Set, Tuple

from fastapi import HTTPException, status
from junitparser import JUnitXml
from sqlmodel import Session

from app.models import TestFailure, TestRun

logger = logging.getLogger(__name__)


def parse_junit_xml(xml_string: str) -> JUnitXml:
    try:
        return JUnitXml.fromstring(xml_string)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JUnit XML format"
        )


def insert_test_run(session: Session, **kwargs) -> TestRun:
    test_run = TestRun(**kwargs)
    try:
        session.add(test_run)
        session.commit()
        session.refresh(test_run)
    except Exception as e:
        logger.error(f"Failed to insert test run: {str(e)}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to insert test run: {str(e)}",
        )
    return test_run


def extract_failures(test_run_id: int, junit_xml: JUnitXml) -> List[TestFailure]:
    failures = []
    seen: Set[Tuple[int, str, str]] = (
        set()
    )  # To track (test_run_id, test_name, test_variant)

    for suite in junit_xml:
        for case in suite:
            if case.is_failure:
                for result in case:
                    test_suite = case.classname
                    test_name = case.name
                    test_variant = case._elem.attrib.get("combinations", "N/A")
                    key = (test_run_id, test_name, test_variant)

                    if key not in seen:
                        seen.add(key)
                        failures.append(
                            TestFailure(
                                test_run_id=test_run_id,
                                test_name=test_suite + "." + test_name,
                                test_variant=test_variant,
                                failure_text=result.text,
                            )
                        )
    return failures
