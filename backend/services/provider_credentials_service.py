import json
from typing import Dict, Optional

from databases import Database
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ..models.provider_credential import provider_credentials
from ..schemas import ProviderCredentialPayload, ProviderOverride
from ..security import decrypt_secret, encrypt_secret


async def get_credentials_map(db: Database, user_id: int) -> Dict[str, ProviderCredentialPayload]:
    rows = await db.fetch_all(
        select(provider_credentials).where(provider_credentials.c.user_id == user_id)
    )
    result: Dict[str, ProviderCredentialPayload] = {}
    for row in rows:
        default_models = None
        if row["default_models"]:
            try:
                default_models = json.loads(row["default_models"])
            except json.JSONDecodeError:
                default_models = None
        result[row["provider_id"]] = ProviderCredentialPayload(
            apiKey=decrypt_secret(row["api_key_encrypted"]),
            baseUrl=row["base_url"],
            defaultModels=default_models,
        )
    return result


async def upsert_credentials(
    db: Database,
    user_id: int,
    payload: Dict[str, ProviderCredentialPayload],
) -> Dict[str, ProviderCredentialPayload]:
    for provider_id, data in payload.items():
        encoded_models = json.dumps(data.defaultModels) if data.defaultModels else None
        encrypted = encrypt_secret(data.apiKey)
        query = (
            sqlite_insert(provider_credentials)
            .values(
                user_id=user_id,
                provider_id=provider_id,
                api_key_encrypted=encrypted,
                base_url=data.baseUrl,
                default_models=encoded_models,
            )
            .on_conflict_do_update(
                index_elements=[provider_credentials.c.user_id, provider_credentials.c.provider_id],
                set_=dict(
                    api_key_encrypted=encrypted,
                    base_url=data.baseUrl,
                    default_models=encoded_models,
                ),
            )
        )
        await db.execute(query)

    # reload to ensure decrypted values are returned fresh
    return await get_credentials_map(db, user_id)


async def delete_missing_credentials(db: Database, user_id: int, keep_providers: set[str]) -> None:
    if not keep_providers:
        await db.execute(
            provider_credentials.delete().where(provider_credentials.c.user_id == user_id)
        )
        return
    await db.execute(
        provider_credentials.delete().where(provider_credentials.c.user_id == user_id).where(
            provider_credentials.c.provider_id.notin_(keep_providers)
        )
    )


def credential_payloads_to_overrides(payload: Dict[str, ProviderCredentialPayload]) -> Dict[str, ProviderOverride]:
    overrides: Dict[str, ProviderOverride] = {}
    for provider_id, data in payload.items():
        overrides[provider_id] = ProviderOverride(
            api_key=data.apiKey,
            base_url=data.baseUrl,
            default_models=data.defaultModels,
        )
    return overrides


def merge_overrides(
    stored: Optional[ProviderOverride], request: Optional[ProviderOverride]
) -> Optional[ProviderOverride]:
    if stored is None and request is None:
        return None
    stored = stored or ProviderOverride()
    request = request or ProviderOverride()
    return ProviderOverride(
        api_key=request.api_key or stored.api_key,
        base_url=request.base_url or stored.base_url,
        default_models=request.default_models or stored.default_models,
    )
