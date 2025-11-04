from typing import Dict

from fastapi import APIRouter, Body, Depends

from ..api.dependencies import get_current_user_id, get_database
from ..schemas import ProviderCredentialPayload
from ..services import provider_credentials_service

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/credentials", response_model=Dict[str, ProviderCredentialPayload])
async def get_provider_credentials(
    db=Depends(get_database), user_id: int = Depends(get_current_user_id)
) -> Dict[str, ProviderCredentialPayload]:
    return await provider_credentials_service.get_credentials_map(db, user_id)


@router.put("/credentials", response_model=Dict[str, ProviderCredentialPayload])
async def update_provider_credentials(
    payload: Dict[str, ProviderCredentialPayload] = Body(...),
    db=Depends(get_database),
    user_id: int = Depends(get_current_user_id),
) -> Dict[str, ProviderCredentialPayload]:
    keep = set(payload.keys())
    updated = await provider_credentials_service.upsert_credentials(db, user_id, payload)
    await provider_credentials_service.delete_missing_credentials(db, user_id, keep)
    return updated
