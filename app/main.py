from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
import os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(
    title="GrowFi API",
    openapi_url=None,  # отключаем OpenAPI для продакшена
    docs_url=None,     # отключаем Swagger UI для продакшена
    redoc_url=None     # отключаем ReDoc для продакшена
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    return {"message": "Welcome to GrowFi API"}
