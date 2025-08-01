import logging

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlmodel import Session

from app.database import get_session
from app.utils import extract_failures, insert_test_run, parse_junit_xml

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health(session: Session = Depends(get_session)):
    try:
        # Execute raw SQL properly with text()
        session.exec(text("SELECT 1")).one()
        return {"status": "ok", "database": "reachable"}
    except Exception:
        logger.error("Healthcheck failed. Database not reachable")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not reachable",
        )


@router.post("/upload-test-results/")
async def upload_test_results(
    branch: str = Form(None),
    revision: str = Form(None),
    platform: str = Form(...),
    bbnum: int = Form(...),
    typ: str = Form(...),
    file: UploadFile = Form(...),
    session: Session = Depends(get_session),
):
    if not file.filename.endswith(".xml"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .xml files are supported",
        )

    content = await file.read()
    junit_xml = parse_junit_xml(content.decode("utf-8"))
    test_run = insert_test_run(
        session,
        branch=branch,
        revision=revision,
        platform=platform,
        bbnum=bbnum,
        typ=typ,
    )
    failures = extract_failures(test_run.id, junit_xml)
    if failures:
        try:
            session.add_all(failures)
            session.commit()
            logger.info(f"Stored test results for {platform}:{bbnum}")
            return {"detail": f"Results were stored successfully."}
        except Exception as e:
            logger.error(f"Failed to store test results for {platform}:{bbnum}")
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store test results: {str(e)}",
            )
    return {"detail": f"No test failures to store."}
