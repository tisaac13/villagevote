"""
Admin endpoints - connector management and manual ingestion
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.models import User, Connector, IngestionRun
from app.schemas import (
    Connector as ConnectorSchema,
    ConnectorCreate,
    IngestionRunRequest,
    IngestionRunResponse
)

router = APIRouter()

# Admin emails — loaded from ADMIN_EMAILS env var (comma-separated)
ADMIN_EMAILS = set(
    e.strip().lower()
    for e in getattr(settings, "ADMIN_EMAILS", "").split(",")
    if e.strip()
)


async def require_admin(current_user: User = Depends(get_current_user)):
    """
    Dependency to require admin privileges.
    Validates JWT then checks email against allowlist.
    """
    if not current_user.email or current_user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


@router.get("/connectors", response_model=List[ConnectorSchema])
async def list_connectors(
    _admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all data connectors"""
    stmt = select(Connector).order_by(Connector.name)
    result = await db.execute(stmt)
    connectors = result.scalars().all()
    
    return [
        ConnectorSchema(
            id=c.id,
            name=c.name,
            source=c.source,
            enabled=c.enabled,
            config=c.config,
            updated_at=c.updated_at
        )
        for c in connectors
    ]


@router.post("/connectors", response_model=ConnectorSchema, status_code=status.HTTP_201_CREATED)
async def create_connector(
    connector_data: ConnectorCreate,
    _admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create new data connector"""
    # Check if connector with same name exists
    stmt = select(Connector).where(Connector.name == connector_data.name)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Connector with name '{connector_data.name}' already exists"
        )
    
    # Create connector
    connector = Connector(
        name=connector_data.name,
        source=connector_data.source,
        enabled=connector_data.enabled,
        config=connector_data.config
    )
    
    db.add(connector)
    await db.commit()
    await db.refresh(connector)
    
    return ConnectorSchema(
        id=connector.id,
        name=connector.name,
        source=connector.source,
        enabled=connector.enabled,
        config=connector.config,
        updated_at=connector.updated_at
    )


@router.post("/ingest/run", response_model=IngestionRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_ingestion(
    request: IngestionRunRequest,
    _admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger manual ingestion run for a connector
    Returns immediately - ingestion happens asynchronously
    """
    # Find connector
    stmt = select(Connector).where(Connector.name == request.connector_name)
    result = await db.execute(stmt)
    connector = result.scalar_one_or_none()
    
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector '{request.connector_name}' not found"
        )
    
    if not connector.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connector '{request.connector_name}' is disabled"
        )
    
    # Create ingestion run record
    run = IngestionRun(
        connector_id=connector.id,
        status="running"
    )
    
    db.add(run)
    await db.commit()
    await db.refresh(run)
    
    # TODO: Trigger async task to run connector
    # celery_app.send_task('run_connector', args=[str(run.id)])
    
    return IngestionRunResponse(
        run_id=run.id,
        status=run.status
    )
