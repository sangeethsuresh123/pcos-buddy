import numpy as np
import pandas as pd
import pytest

from backend.config import settings
from backend.ml.preprocess import FEATURE_COLUMNS, TARGET_COLUMN

TEST_EMAIL = "tester@example.com"
TEST_PASSWORD = "testpassword123"

BINARY_COLUMNS = [
    "Weight gain(Y/N)",
    "hair growth(Y/N)",
    "Skin darkening (Y/N)",
    "Hair loss(Y/N)",
    "Reg.Exercise(Y/N)",
]


@pytest.fixture
def sample_features() -> dict:
    return {
        "Age (yrs)": 28,
        "Blood Group": 11,
        "Pulse rate(bpm)": 72,
        "Hb(g/dl)": 12.5,
        "Cycle(R/I)": 4,
        "Cycle length(days)": 35,
        "Marraige Status (Yrs)": 3,
        "I   beta-HCG(mIU/mL)": 1.99,
        "II    beta-HCG(mIU/mL)": 181.23,
        "FSH(mIU/mL)": 5.71,
        "Waist:Hip Ratio": 0.88,
        "TSH (mIU/L)": 2.0,
        "PRL(ng/mL)": 21.87,
        "Vit D3 (ng/mL)": 16.9,
        "PRG(ng/mL)": 0.25,
        "RBS(mg/dl)": 110,
        "Weight gain(Y/N)": 1,
        "hair growth(Y/N)": 0,
        "Skin darkening (Y/N)": 1,
        "Hair loss(Y/N)": 1,
        "Reg.Exercise(Y/N)": 0,
        "Follicle No. (L)": 11,
        "Follicle No. (R)": 9,
    }


def make_dataframe(n_rows: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    data = {col: rng.uniform(0.5, 5.0, n_rows) for col in FEATURE_COLUMNS}
    for col in BINARY_COLUMNS:
        data[col] = rng.integers(0, 2, n_rows)
    data[TARGET_COLUMN] = rng.integers(0, 2, n_rows)
    return pd.DataFrame(data)


@pytest.fixture
def synthetic_dataset(tmp_path):
    train_path = tmp_path / "train.csv"
    test_path = tmp_path / "test.csv"
    make_dataframe(120, 1).to_csv(train_path, index=False)
    make_dataframe(40, 2).to_csv(test_path, index=False)
    return train_path, test_path


@pytest.fixture
def predictor_module(monkeypatch, tmp_path, synthetic_dataset):
    from backend.ml import predictor as predictor_module

    train_path, test_path = synthetic_dataset
    model_dir = tmp_path / "models"

    monkeypatch.setattr(predictor_module, "MODEL_DIR", model_dir)
    monkeypatch.setattr(predictor_module, "MODEL_PATH", model_dir / "pcos_model.pkl")
    monkeypatch.setattr(predictor_module, "SCALER_PATH", model_dir / "pcos_scaler.pkl")
    monkeypatch.setattr(predictor_module, "FEATURES_PATH", model_dir / "pcos_features.pkl")
    monkeypatch.setattr(predictor_module, "TRAIN_DATA_PATH", train_path)
    monkeypatch.setattr(predictor_module, "TEST_DATA_PATH", test_path)
    return predictor_module


@pytest.fixture(autouse=True)
def isolated_app_dbs(tmp_path, monkeypatch):
    """Point auth + weight SQLite files at a throwaway path and use fast hashing."""
    monkeypatch.setattr(settings, "auth_db_path", str(tmp_path / "auth.db"))
    monkeypatch.setattr(settings, "weight_db_path", str(tmp_path / "weight.db"))
    monkeypatch.setattr(settings, "auth_pbkdf2_iterations", 1000)


@pytest.fixture()
def client(isolated_app_dbs):
    """TestClient that is already registered and logged in."""
    from fastapi.testclient import TestClient

    from backend.app import app

    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        assert response.status_code == 201
        yield test_client


@pytest.fixture()
def anon_client(isolated_app_dbs):
    """Unauthenticated TestClient."""
    from fastapi.testclient import TestClient

    from backend.app import app

    with TestClient(app) as test_client:
        yield test_client
