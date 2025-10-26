from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.deps.auth import verify_firebase_token
from datetime import datetime, timezone

router = APIRouter()

# In-memory storage for development
_IN_MEMORY_PROPERTIES: List[dict] = []

class Property(BaseModel):
    id: Optional[str] = None
    name: str
    address: str
    landlord_id: str
    tenants: Optional[List[str]] = []
    status: str = "Active"
    created_at: Optional[str] = None

@router.post("/property/create")
def create_property(property: Property, token: str = Depends(verify_firebase_token)):
    payload = property.model_dump()
    if not payload.get("id"):
        payload["id"] = f"property-{datetime.now(timezone.utc).timestamp()}"
    if not payload.get("created_at"):
        payload["created_at"] = datetime.now(timezone.utc).isoformat()

    _IN_MEMORY_PROPERTIES.append(payload)
    return {"status": "created", "property": payload}

@router.get("/property/list/{landlord_id}")
def list_properties(landlord_id: str, token: str = Depends(verify_firebase_token)):
    items = [p for p in _IN_MEMORY_PROPERTIES if p.get("landlord_id") == landlord_id]
    return {"landlord_id": landlord_id, "properties": items}

@router.get("/property/tenant/{tenant_id}")
def get_tenant_property(tenant_id: str, token: str = Depends(verify_firebase_token)):
    """Get the property where user is a tenant"""
    for prop in _IN_MEMORY_PROPERTIES:
        if tenant_id in prop.get("tenants", []):
            return {"property": prop}
    return {"property": None}

@router.put("/property/update/{property_id}")
def update_property(property_id: str, property: Property, token: str = Depends(verify_firebase_token)):
    for i, p in enumerate(_IN_MEMORY_PROPERTIES):
        if p.get("id") == property_id:
            payload = property.model_dump()
            payload["id"] = property_id
            _IN_MEMORY_PROPERTIES[i] = payload
            return {"status": "updated", "property": payload}
    return {"status": "not_found"}

@router.delete("/property/delete/{property_id}")
def delete_property(property_id: str, token: str = Depends(verify_firebase_token)):
    global _IN_MEMORY_PROPERTIES
    _IN_MEMORY_PROPERTIES = [p for p in _IN_MEMORY_PROPERTIES if p.get("id") != property_id]
    return {"status": "deleted"}

@router.post("/property/add_tenant")
def add_tenant_to_property(
    property_id: str,
    tenant_id: str,
    token: str = Depends(verify_firebase_token)
):
    """Add a tenant to a property"""
    for prop in _IN_MEMORY_PROPERTIES:
        if prop.get("id") == property_id:
            if "tenants" not in prop:
                prop["tenants"] = []
            if tenant_id not in prop["tenants"]:
                prop["tenants"].append(tenant_id)
            return {"status": "added", "property": prop}
    return {"status": "not_found"}
