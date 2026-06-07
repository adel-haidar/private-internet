import hashlib
import io
import datetime
import os

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel

from personal_intelligence.auth.oauth import validate_token
from personal_intelligence.config import get_settings
from personal_intelligence.memory.service import (
    delete_memory,
    list_memories,
    save_memory,
    update_memory,
)

router = APIRouter(prefix="/api")


async def require_auth(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    token = auth[7:]
    client_id = validate_token(token)
    if not client_id:
        raise HTTPException(status_code=401, detail="invalid token")
    return client_id


class SaveTextRequest(BaseModel):
    title: str
    content: str
    tags: list[str] = []


class UpdateMemoryRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    append_content: bool = False


@router.post("/memory/text")
async def save_text_memory(
    body: SaveTextRequest,
    client_id: str = Depends(require_auth),
):
    memory = save_memory(title=body.title, content=body.content, tags=body.tags)
    return {"memory_id": memory.memory_id}


@router.get("/memory")
async def list_memory(
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    client_id: str = Depends(require_auth),
):
    items, total = list_memories(page=page, page_size=page_size, query=q)
    pages = max(1, (total + page_size - 1) // page_size)
    return {"items": items, "total": total, "page": page, "pages": pages}


@router.patch("/memory/{memory_id}")
async def update_memory_endpoint(
    memory_id: str,
    body: UpdateMemoryRequest,
    client_id: str = Depends(require_auth),
):
    memory = update_memory(
        memory_id,
        title=body.title,
        content=body.content,
        tags=body.tags,
        append_content=body.append_content,
    )
    if memory is None:
        raise HTTPException(status_code=404, detail="memory not found")
    return {
        "memory_id": memory.memory_id,
        "title": memory.title,
        "content": memory.content,
        "tags": memory.tags,
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
    }


@router.delete("/memory/{memory_id}")
async def delete_memory_endpoint(
    memory_id: str,
    client_id: str = Depends(require_auth),
):
    deleted = delete_memory(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="memory not found")
    return {"deleted": True, "memory_id": memory_id}


_PDF_CHUNK_SIZE = 4000


def _extract_pdf_text(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _chunk_text(text: str) -> list[str]:
    if len(text) <= _PDF_CHUNK_SIZE:
        return [text]
    chunks = []
    while text:
        if len(text) <= _PDF_CHUNK_SIZE:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, _PDF_CHUNK_SIZE)
        if split_at <= 0:
            split_at = _PDF_CHUNK_SIZE
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    return chunks


@router.post("/file")
async def upload_file(file: UploadFile, client_id: str = Depends(require_auth)):
    upload_dir = get_settings().upload_dir
    os.makedirs(upload_dir, exist_ok=True)

    content = await file.read()

    if not content:
        return {"error": "Empty file"}

    file_hash = hashlib.sha256(content).hexdigest()[:12]
    timestamp = datetime.datetime.now().isoformat()
    filename = f"{file_hash}_{file.filename}"
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    if ext == "pdf":
        text = _extract_pdf_text(content)
        chunks = _chunk_text(text)
        total = len(chunks)
        first_saved = None
        for i, chunk in enumerate(chunks):
            title = file.filename if total == 1 else f"{file.filename} ({i + 1}/{total})"
            saved = save_memory(title=title, content=chunk, tags=["file-upload", "pdf"])
            if first_saved is None:
                first_saved = saved
    else:
        first_saved = save_memory(
            title=f"Uploaded file: {file.filename}",
            content=(
                f"File uploaded at {timestamp}. "
                f"Path: {filepath}. Size: {len(content)} bytes. "
                f"Hash: {file_hash}."
            ),
            tags=["file-upload", ext],
        )

    return {
        "status": "ok",
        "memory_id": first_saved.memory_id,
        "filename": filename,
        "size": len(content),
    }
