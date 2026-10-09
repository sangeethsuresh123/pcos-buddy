from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.weight import store

router = APIRouter(prefix="/api/weight", tags=["weight"])


class ProfileIn(BaseModel):
    height_cm: float = Field(..., ge=120, le=230)


class ProfileOut(BaseModel):
    height_cm: float | None = None


class EntryIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entry_date: date = Field(..., alias="date")
    weight_kg: float = Field(..., ge=25, le=400)
    waist_cm: float | None = Field(None, ge=40, le=250)
    hip_cm: float | None = Field(None, ge=40, le=280)
    notes: str | None = Field(None, max_length=200)

    @field_validator("entry_date")
    @classmethod
    def not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("entry date cannot be in the future")
        return value


class EntryOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    entry_date: date = Field(..., alias="date")
    weight_kg: float
    waist_cm: float | None = None
    hip_cm: float | None = None
    notes: str | None = None


class DeleteResponse(BaseModel):
    deleted: bool


@router.get("/profile", response_model=ProfileOut)
async def get_profile():
    return ProfileOut(height_cm=store.get_profile_height())


@router.put("/profile", response_model=ProfileOut)
async def put_profile(request: ProfileIn):
    return ProfileOut(height_cm=store.set_profile_height(request.height_cm))


@router.get("/entries", response_model=list[EntryOut])
async def get_entries(days: int | None = Query(None, ge=1, le=1095)):
    return [EntryOut(**e) for e in store.list_entries(days)]


@router.post("/entries", response_model=EntryOut)
async def create_entry(request: EntryIn):
    payload = request.model_dump()
    payload["entry_date"] = payload["entry_date"].isoformat()
    return EntryOut(**store.upsert_entry(payload))


@router.delete("/entries/{entry_id}", response_model=DeleteResponse)
async def remove_entry(entry_id: int):
    if store.delete_entry(entry_id):
        return DeleteResponse(deleted=True)
    raise HTTPException(status_code=404, detail="Entry not found")


@router.get("/analytics")
async def analytics():
    height = store.get_profile_height()
    entries = store.list_entries()
    data = store.compute_analytics(entries, height)
    for key in ("latest", "baseline"):
        item = data.get(key)
        if item and "entry_date" in item:
            data[key] = {**item, "date": item["entry_date"]}
            data[key].pop("entry_date", None)
    return data
