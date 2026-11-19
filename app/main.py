from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_session


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # APScheduler jobs are wired in a later milestone.
    yield


app = FastAPI(title="inbox-guard", lifespan=lifespan)


@app.get("/health")
def health(session: Session = Depends(get_session)) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok"}
