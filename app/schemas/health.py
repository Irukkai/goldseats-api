"""Response models for the health endpoints."""

from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: str
    environment: str
    version: str


class ReadinessStatus(BaseModel):
    status: str
    database: bool
