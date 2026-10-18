from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.auth.deps import get_current_user
from backend.symptoms import store

router = APIRouter(prefix="/api/symptoms", tags=["symptoms"])


class ProfileIn(BaseModel):
    typical_cycle_length: Optional[int] = Field(None, ge=15, le=60)
    typical_period_length: Optional[int] = Field(None, ge=1, le=14)
    last_period_start: Optional[date] = None


class ProfileOut(BaseModel):
    typical_cycle_length: Optional[int] = None
    typical_period_length: Optional[int] = None
    last_period_start: Optional[date] = None


class EntryIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entry_date: date = Field(..., alias="date")
    period_flow: Optional[int] = Field(None, ge=0, le=4)
    period_day: Optional[int] = Field(None, ge=1, le=60)
    cycle_length: Optional[int] = Field(None, ge=15, le=60)
    abdominal_pain: Optional[int] = Field(None, ge=0, le=10)
    breast_tenderness: Optional[int] = Field(None, ge=0, le=10)
    bloating: Optional[int] = Field(None, ge=0, le=10)
    headache: Optional[int] = Field(None, ge=0, le=10)
    fatigue: Optional[int] = Field(None, ge=0, le=10)
    acne: Optional[int] = Field(None, ge=0, le=10)
    hair_loss: Optional[int] = Field(None, ge=0, le=10)
    hirsutism: Optional[int] = Field(None, ge=0, le=10)
    skin_darkening: Optional[int] = Field(None, ge=0, le=10)
    mood_swings: Optional[int] = Field(None, ge=0, le=10)
    anxiety: Optional[int] = Field(None, ge=0, le=10)
    depression: Optional[int] = Field(None, ge=0, le=10)
    irritability: Optional[int] = Field(None, ge=0, le=10)
    exercise_minutes: Optional[int] = Field(None, ge=0, le=300)
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    stress_level: Optional[int] = Field(None, ge=1, le=10)
    diet_quality: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = Field(None, max_length=500)

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
    period_flow: Optional[int] = None
    period_day: Optional[int] = None
    cycle_length: Optional[int] = None
    abdominal_pain: Optional[int] = None
    breast_tenderness: Optional[int] = None
    bloating: Optional[int] = None
    headache: Optional[int] = None
    fatigue: Optional[int] = None
    acne: Optional[int] = None
    hair_loss: Optional[int] = None
    hirsutism: Optional[int] = None
    skin_darkening: Optional[int] = None
    mood_swings: Optional[int] = None
    anxiety: Optional[int] = None
    depression: Optional[int] = None
    irritability: Optional[int] = None
    exercise_minutes: Optional[int] = None
    sleep_hours: Optional[float] = None
    stress_level: Optional[int] = None
    diet_quality: Optional[int] = None
    notes: Optional[str] = None


class CycleEventIn(BaseModel):
    start_date: date
    end_date: Optional[date] = None
    cycle_length: Optional[int] = Field(None, ge=15, le=60)
    flow_pattern: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)


class CycleEventOut(BaseModel):
    id: int
    start_date: date
    end_date: Optional[date] = None
    cycle_length: Optional[int] = None
    flow_pattern: Optional[str] = None
    notes: Optional[str] = None
    created_at: str


class AnalysisOut(BaseModel):
    cycles: list[dict]
    avg_cycle_length: Optional[float] = None
    avg_period_length: Optional[float] = None
    next_period_estimate: Optional[str] = None
    phase: str
    days_since_last_period: Optional[int] = None
    symptom_patterns: dict


class MlFeaturesOut(BaseModel):
    features: dict
    entry_date: Optional[date] = None


@router.get("/profile", response_model=ProfileOut)
async def get_profile(user: dict = Depends(get_current_user)):
    profile = store.get_profile(user["id"])
    if profile and profile.get("last_period_start"):
        profile["last_period_start"] = date.fromisoformat(profile["last_period_start"])
    return ProfileOut(**profile) if profile else ProfileOut()


@router.put("/profile", response_model=ProfileOut)
async def put_profile(request: ProfileIn, user: dict = Depends(get_current_user)):
    data = request.model_dump()
    if data.get("last_period_start"):
        data["last_period_start"] = data["last_period_start"].isoformat()
    profile = store.upsert_profile(user["id"], data)
    if profile and profile.get("last_period_start"):
        profile["last_period_start"] = date.fromisoformat(profile["last_period_start"])
    return ProfileOut(**profile)


@router.get("/entries", response_model=list[EntryOut])
async def get_entries(
    days: int | None = Query(None, ge=1, le=1095),
    user: dict = Depends(get_current_user),
):
    return [EntryOut(**e) for e in store.list_entries(user["id"], days)]


@router.get("/entries/{entry_date}", response_model=EntryOut)
async def get_entry(entry_date: date, user: dict = Depends(get_current_user)):
    entry = store.get_entry(user["id"], entry_date.isoformat())
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return EntryOut(**entry)


@router.post("/entries", response_model=EntryOut)
async def create_entry(request: EntryIn, user: dict = Depends(get_current_user)):
    payload = request.model_dump(by_alias=True)
    # The alias for entry_date is "date", so we need to get it by the alias
    entry_date = payload.pop("date")
    payload["entry_date"] = entry_date.isoformat()
    return EntryOut(**store.upsert_entry(user["id"], payload))


@router.delete("/entries/{entry_id}")
async def remove_entry(entry_id: int, user: dict = Depends(get_current_user)):
    if store.delete_entry(user["id"], entry_id):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Entry not found")


@router.get("/cycle-events", response_model=list[CycleEventOut])
async def get_cycle_events(
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    return [CycleEventOut(**e) for e in store.list_cycle_events(user["id"], limit)]


@router.post("/cycle-events", response_model=CycleEventOut)
async def create_cycle_event(request: CycleEventIn, user: dict = Depends(get_current_user)):
    data = request.model_dump()
    data["start_date"] = data["start_date"].isoformat()
    if data.get("end_date"):
        data["end_date"] = data["end_date"].isoformat()
    return CycleEventOut(**store.add_cycle_event(user["id"], data))


@router.get("/analysis", response_model=AnalysisOut)
async def get_analysis(user: dict = Depends(get_current_user)):
    entries = store.list_entries(user["id"])
    profile = store.get_profile(user["id"])
    return AnalysisOut(**store.compute_cycle_analysis(user["id"], entries, profile))


@router.get("/ml-features", response_model=MlFeaturesOut)
async def get_ml_features(user: dict = Depends(get_current_user)):
    entries = store.list_entries(user["id"], days=30)
    features = store.get_latest_symptoms_for_ml(user["id"])
    entry_date = date.fromisoformat(entries[-1]["entry_date"]) if entries else None
    return MlFeaturesOut(features=features, entry_date=entry_date)