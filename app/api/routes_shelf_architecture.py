"""Authenticated, read-only Sovereign Shelf Architecture discovery."""
from fastapi import APIRouter, Depends, HTTPException
from app.security.auth import require_api_key
from app.shelf.architecture import load_architecture_catalog, get_architecture_card

router = APIRouter(prefix="/v1/shelf/architecture", tags=["shelf"])

@router.get("", dependencies=[Depends(require_api_key)])
def architecture_shelf():
    return load_architecture_catalog()

@router.get("/{slug}", dependencies=[Depends(require_api_key)])
def architecture_card(slug: str):
    card = get_architecture_card(slug)
    if card is None:
        raise HTTPException(status_code=404, detail="Unknown architecture card")
    return card
