import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import analysis, auth, budget, transactions
from app.core.database import async_session_local, close_db, init_db
from app.core.db import crud
from app.core.logging_config import IndentFormatter

IndentFormatter.setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@mavrodi.ru"
DEFAULT_ADMIN_PASSWORD = "admin"


async def create_default_admin():
    async with async_session_local() as db:
        existing_admin = await crud.get_user_by_username(db, DEFAULT_ADMIN_USERNAME)
        if not existing_admin:
            logger.info("Creating default admin user...")
            admin = await crud.create_user(
                db,
                username=DEFAULT_ADMIN_USERNAME,
                email=DEFAULT_ADMIN_EMAIL,
                password=DEFAULT_ADMIN_PASSWORD,
                is_admin=True,
            )
            await crud.create_user_profile(db, user_id=admin.id)
            logger.info(f"Default admin created: {DEFAULT_ADMIN_USERNAME}")
        else:
            logger.info("Default admin already exists")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Personal Finance Manager API...")

    await init_db()
    logger.info("Database initialized successfully")

    await create_default_admin()

    async with async_session_local() as db:
        from app.core.db.crud.finance.budget import CategoryCRUD

        await CategoryCRUD.init_default_categories(db)
        logger.info("Default categories initialized")

    yield

    logger.info("Shutting down Personal Finance Manager API...")
    await close_db()
    logger.info("Database connection closed")


app = FastAPI(
    title="Personal Finance Manager API",
    description="api for managing personal finances",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(budget.router)
app.include_router(transactions.router)
app.include_router(analysis.router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Personal Finance Manager API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "auth": "/auth",
            "budget": "/finance/budget",
            "transactions": "/finance/transactions",
            "analysis": "/finance/analysis",
        },
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.core.main:app", host="0.0.0.0", port=8000, reload=True)
