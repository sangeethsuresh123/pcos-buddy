import pytest

from backend.ml.predictor import PCOSPredictor


def test_predictor_starts_unloaded():
    predictor = PCOSPredictor()
    assert predictor.is_loaded is False
    assert predictor.model is None
    assert predictor.scaler is None


def test_load_returns_false_when_artifacts_missing(predictor_module):
    predictor = PCOSPredictor()
    assert predictor.load() is False
    assert predictor.is_loaded is False


def test_train_returns_metrics_and_saves_artifacts(predictor_module):
    predictor = PCOSPredictor()
    result = predictor.train()

    assert predictor.is_loaded is True
    assert predictor.model is not None
    assert predictor.scaler is not None

    for key in ("accuracy", "precision", "recall", "f1_score", "roc_auc"):
        assert key in result

    assert result["n_training_samples"] == 120
    assert result["n_test_samples"] == 40
    assert set(result["feature_importance"]) == set(predictor_module.FEATURE_COLUMNS)

    assert predictor_module.MODEL_PATH.exists()
    assert predictor_module.SCALER_PATH.exists()
    assert predictor_module.FEATURES_PATH.exists()


def test_train_writes_artifacts_that_reload(predictor_module):
    predictor = PCOSPredictor()
    assert predictor.load() is False

    PCOSPredictor().train()

    reloaded = PCOSPredictor()
    assert reloaded.load() is True
    assert reloaded.is_loaded is True


def test_train_raises_when_datasets_missing(predictor_module, monkeypatch):
    monkeypatch.setattr(predictor_module, "TRAIN_DATA_PATH", predictor_module.MODEL_DIR / "nope.csv")
    monkeypatch.setattr(predictor_module, "TEST_DATA_PATH", predictor_module.MODEL_DIR / "nope2.csv")

    with pytest.raises(FileNotFoundError):
        PCOSPredictor().train()


def test_predict_requires_loaded_model():
    predictor = PCOSPredictor()
    with pytest.raises(RuntimeError, match="not loaded"):
        predictor.predict({})


def test_predict_returns_expected_shape(predictor_module, sample_features):
    predictor = PCOSPredictor()
    predictor.train()

    result = predictor.predict(sample_features)

    assert set(result) == {
        "prediction",
        "diagnosis",
        "probability_pcos",
        "probability_no_pcos",
        "risk_level",
        "recommendations",
    }
    assert result["prediction"] in (0, 1)
    assert result["diagnosis"] in ("Likely PCOS", "Unlikely PCOS")
    assert 0.0 <= result["probability_pcos"] <= 1.0
    assert abs(result["probability_pcos"] + result["probability_no_pcos"] - 1.0) < 0.01
    assert result["risk_level"] in ("low", "moderate", "high")
    assert isinstance(result["recommendations"], list)
    assert result["recommendations"]


def test_predict_tolerates_missing_feature_keys(predictor_module):
    predictor = PCOSPredictor()
    predictor.train()

    result = predictor.predict({"Age (yrs)": 30})
    assert "prediction" in result
    assert result["risk_level"] in ("low", "moderate", "high")


def test_high_risk_recommendations_advise_gynecologist():
    predictor = PCOSPredictor()
    features = {
        "Cycle(R/I)": 1,
        "RBS(mg/dl)": 140,
        "Vit D3 (ng/mL)": 12,
        "Follicle No. (L)": 14,
        "Weight gain(Y/N)": 1,
        "Reg.Exercise(Y/N)": 0,
        "hair growth(Y/N)": 1,
    }
    recs = predictor._get_recommendations("high", features)

    assert any("gynecologist" in r.lower() for r in recs)
    assert any("blood work" in r.lower() for r in recs)


def test_low_risk_recommendations_default_to_lifestyle():
    predictor = PCOSPredictor()
    recs = predictor._get_recommendations("low", {})

    assert any("healthy lifestyle" in r.lower() for r in recs)