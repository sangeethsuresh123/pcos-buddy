import numpy as np
import pandas as pd

TARGET_COLUMN = "PCOS (Y/N)"

FEATURE_COLUMNS = [
    "Age (yrs)",
    "Blood Group",
    "Pulse rate(bpm)",
    "Hb(g/dl)",
    "Cycle(R/I)",
    "Cycle length(days)",
    "Marraige Status (Yrs)",
    "I   beta-HCG(mIU/mL)",
    "II    beta-HCG(mIU/mL)",
    "FSH(mIU/mL)",
    "Waist:Hip Ratio",
    "TSH (mIU/L)",
    "PRL(ng/mL)",
    "Vit D3 (ng/mL)",
    "PRG(ng/mL)",
    "RBS(mg/dl)",
    "Weight gain(Y/N)",
    "hair growth(Y/N)",
    "Skin darkening (Y/N)",
    "Hair loss(Y/N)",
    "Reg.Exercise(Y/N)",
    "Follicle No. (L)",
    "Follicle No. (R)",
]


def get_feature_names() -> list[str]:
    return FEATURE_COLUMNS.copy()


def load_dataframe(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    for col in FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].fillna(df[FEATURE_COLUMNS].median())

    df[TARGET_COLUMN] = pd.to_numeric(df[TARGET_COLUMN], errors="coerce")
    df = df.dropna(subset=[TARGET_COLUMN])
    return df