from fastapi import APIRouter, Depends, File, UploadFile

from api.deps import get_settings
from api.config import Settings
from api.models import IngestResponse
from ingestion.pipeline import ingest_text

router = APIRouter(tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> IngestResponse:
    raw = await file.read()
    text = raw.decode("utf-8")
    source = file.filename or "upload.txt"
    result = ingest_text(text, source=source, settings=settings)
    return IngestResponse(
        doc_id=result.doc_id,
        source=result.source,
        chunk_count=result.chunk_count,
    )
