from contextlib import asynccontextmanager

from fastapi import FastAPI

from personal_intelligence.auth.oauth import create_oauth_tables
from personal_intelligence.auth.routes import router as auth_router
from personal_intelligence.memory.mcp_server import mcp
from personal_intelligence.memory.routes import router as memory_router

# Build the MCP sub-app eagerly so the session manager is created before the
# lifespan runs. Starlette does not propagate sub-app lifespans to the parent,
# so we start the session manager's task group here instead.
_mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_oauth_tables()
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Personal Intelligence API", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(memory_router)

app.mount("/mcp", _mcp_app)
