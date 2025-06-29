import pytest
from fastapi import HTTPException

from app.utils import extract_failures, parse_junit_xml


def test_parse_junit_xml_valid():
    xml_str = """<testsuites><testsuite name="suite"><testcase classname="class" name="test" /></testsuite></testsuites>"""
    xml = parse_junit_xml(xml_str)
    assert len(xml) == 1


def test_extract_failures_returns_empty_for_no_failures():
    xml_str = """<testsuites><testsuite name="suite"><testcase classname="class" name="test" /></testsuite></testsuites>"""
    xml = parse_junit_xml(xml_str)
    failures = extract_failures(test_run_id=1, junit_xml=xml)
    assert failures == []


def test_extract_failures_returns_failures_for_failed_tests():
    xml_str = """
    <testsuites>
      <testsuite name="suite">
        <testcase classname="class1" name="test1">
          <failure>Failure message 1</failure>
        </testcase>
        <testcase classname="class2" name="test2">
          <failure>Failure message 2</failure>
        </testcase>
      </testsuite>
    </testsuites>
    """
    xml = parse_junit_xml(xml_str)
    failures = extract_failures(test_run_id=1, junit_xml=xml)

    assert len(failures) == 2

    # Check some attributes of the first failure
    f1 = failures[0]
    assert f1.test_run_id == 1
    assert f1.test_name == "class1.test1"
    assert "Failure message 1" in f1.failure_text

    # Similarly check the second failure
    f2 = failures[1]
    assert f2.test_name == "class2.test2"
    assert "Failure message 2" in f2.failure_text


def test_parse_junit_xml_invalid():
    invalid_xml_str = "<testsuites><testsuite><testcase></testsuite>"  # malformed XML

    with pytest.raises(HTTPException) as exc_info:
        parse_junit_xml(invalid_xml_str)

    assert exc_info.value.status_code == 400
    assert "Invalid JUnit XML format" in exc_info.value.detail
