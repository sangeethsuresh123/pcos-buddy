from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.ml.predictor import get_predictor

router = APIRouter(prefix="/api/ml", tags=["ml"])


_PREDICTION_RANGES = {
    "Age (yrs)": (10, 60),
    "Blood Group": (1, 20),
    "Pulse rate(bpm)": (40, 150),
    "Hb(g/dl)": (5, 20),
    "Cycle(R/I)": (0, 5),
    "Cycle length(days)": (1, 120),
    "Marraige Status (Yrs)": (0, 40),
    "I   beta-HCG(mIU/mL)": (0, 1000),
    "II    beta-HCG(mIU/mL)": (0, 1000),
    "FSH(mIU/mL)": (0, 50),
    "Waist:Hip Ratio": (0.5, 1.5),
    "TSH (mIU/L)": (0, 50),
    "PRL(ng/mL)": (0, 150),
    "Vit D3 (ng/mL)": (0, 100),
    "PRG(ng/mL)": (0, 60),
    "RBS(mg/dl)": (30, 400),
    "Weight gain(Y/N)": (0, 1),
    "hair growth(Y/N)": (0, 1),
    "Skin darkening (Y/N)": (0, 1),
    "Hair loss(Y/N)": (0, 1),
    "Reg.Exercise(Y/N)": (0, 1),
    "Follicle No. (L)": (0, 50),
    "Follicle No. (R)": (0, 50),
}


def _feature_field(*, alias: str, ge: float, le: float):
    return Field(..., alias=alias, ge=ge, le=le)


class PredictionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    age: float = _feature_field(alias="Age (yrs)", ge=10, le=60)
    blood_group: float = _feature_field(alias="Blood Group", ge=1, le=20)
    pulse_rate: float = _feature_field(alias="Pulse rate(bpm)", ge=40, le=150)
    hb: float = _feature_field(alias="Hb(g/dl)", ge=5, le=20)
    cycle_ri: float = _feature_field(alias="Cycle(R/I)", ge=0, le=5)
    cycle_length: float = _feature_field(alias="Cycle length(days)", ge=1, le=120)
    marriage_status: float = _feature_field(alias="Marraige Status (Yrs)", ge=0, le=40)
    i_beta_hcg: float = _feature_field(alias="I   beta-HCG(mIU/mL)", ge=0, le=1000)
    ii_beta_hcg: float = _feature_field(alias="II    beta-HCG(mIU/mL)", ge=0, le=1000)
    fsh: float = _feature_field(alias="FSH(mIU/mL)", ge=0, le=50)
    waist_hip_ratio: float = _feature_field(alias="Waist:Hip Ratio", ge=0.5, le=1.5)
    tsh: float = _feature_field(alias="TSH (mIU/L)", ge=0, le=50)
    prl: float = _feature_field(alias="PRL(ng/mL)", ge=0, le=150)
    vit_d3: float = _feature_field(alias="Vit D3 (ng/mL)", ge=0, le=100)
    prg: float = _feature_field(alias="PRG(ng/mL)", ge=0, le=60)
    rbs: float = _feature_field(alias="RBS(mg/dl)", ge=30, le=400)
    weight_gain: float = _feature_field(alias="Weight gain(Y/N)", ge=0, le=1)
    hair_growth: float = _feature_field(alias="hair growth(Y/N)", ge=0, le=1)
    skin_darkening: float = _feature_field(alias="Skin darkening (Y/N)", ge=0, le=1)
    hair_loss: float = _feature_field(alias="Hair loss(Y/N)", ge=0, le=1)
    reg_exercise: float = _feature_field(alias="Reg.Exercise(Y/N)", ge=0, le=1)
    follicle_no_l: float = _feature_field(alias="Follicle No. (L)", ge=0, le=50)
    follicle_no_r: float = _feature_field(alias="Follicle No. (R)", ge=0, le=50)


class PredictionResponse(BaseModel):
    prediction: int
    diagnosis: str
    probability_pcos: float
    probability_no_pcos: float
    risk_level: str
    recommendations: list[str]


class TrainResponse(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    n_training_samples: int
    n_test_samples: int


@router.post("/predict", response_model=PredictionResponse)
async def predict_pcos(request: PredictionRequest):
    predictor = get_predictor()
    if not predictor.is_loaded:
        raise HTTPException(
            status_code=400,
            detail="Model not trained. Run 'python train_model.py' first.",
        )

    features = request.model_dump(by_alias=True)
    result = predictor.predict(features)
    return PredictionResponse(**result)


@router.post("/train", response_model=TrainResponse)
async def train_model():
    predictor = get_predictor()
    try:
        results = predictor.train()
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return TrainResponse(
        accuracy=results["accuracy"],
        precision=results["precision"],
        recall=results["recall"],
        f1_score=results["f1_score"],
        roc_auc=results["roc_auc"],
        n_training_samples=results["n_training_samples"],
        n_test_samples=results["n_test_samples"],
    )