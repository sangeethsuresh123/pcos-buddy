import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score

from backend.ml.preprocess import FEATURE_COLUMNS, TARGET_COLUMN, load_dataframe

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "pcos_model.pkl"
SCALER_PATH = MODEL_DIR / "pcos_scaler.pkl"
FEATURES_PATH = MODEL_DIR / "pcos_features.pkl"
TRAIN_DATA_PATH = PROJECT_ROOT / "dataset" / "train.csv"
TEST_DATA_PATH = PROJECT_ROOT / "dataset" / "test.csv"


class PCOSPredictor:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names: list[str] = []
        self.is_loaded = False

    def load(self) -> bool:
        if all(p.exists() for p in (MODEL_PATH, SCALER_PATH, FEATURES_PATH)):
            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)
            with open(SCALER_PATH, "rb") as f:
                self.scaler = pickle.load(f)
            with open(FEATURES_PATH, "rb") as f:
                self.feature_names = pickle.load(f)
            self.is_loaded = True
            return True
        return False

    def save(self):
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(self.model, f)
        with open(SCALER_PATH, "wb") as f:
            pickle.dump(self.scaler, f)
        with open(FEATURES_PATH, "wb") as f:
            pickle.dump(self.feature_names, f)

    def train(self) -> dict:
        if not TRAIN_DATA_PATH.exists() or not TEST_DATA_PATH.exists():
            raise FileNotFoundError(
                f"Datasets not found. Expected {TRAIN_DATA_PATH} and {TEST_DATA_PATH}."
                " Place the PCOS train.csv and test.csv in the dataset/ folder."
            )

        train_df = load_dataframe(str(TRAIN_DATA_PATH))
        test_df = load_dataframe(str(TEST_DATA_PATH))

        X_train = train_df[FEATURE_COLUMNS].values.astype(float)
        y_train = train_df[TARGET_COLUMN].values.astype(int)
        X_test = test_df[FEATURE_COLUMNS].values.astype(float)
        y_test = test_df[TARGET_COLUMN].values.astype(int)

        scaler = self._fit_scaler(X_train)

        model = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
        )
        model.fit(scaler.transform(X_train), y_train)

        y_pred = model.predict(scaler.transform(X_test))
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        try:
            auc = roc_auc_score(y_test, model.predict_proba(scaler.transform(X_test))[:, 1])
        except ValueError:
            auc = 0.0

        self.model = model
        self.scaler = scaler
        self.feature_names = FEATURE_COLUMNS.copy()
        self.save()
        self.is_loaded = True

        return {
            "accuracy": round(accuracy, 4),
            "precision": round(report["weighted avg"]["precision"], 4),
            "recall": round(report["weighted avg"]["recall"], 4),
            "f1_score": round(report["weighted avg"]["f1-score"], 4),
            "roc_auc": round(auc, 4),
            "n_training_samples": len(X_train),
            "n_test_samples": len(X_test),
            "feature_importance": dict(zip(
                self.feature_names,
                [round(float(v), 4) for v in model.feature_importances_],
            )),
        }

    def predict(self, features: dict) -> dict:
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Train or load a model first.")

        feature_values = []
        for fname in self.feature_names:
            val = features.get(fname, 0)
            feature_values.append(float(val))

        X = np.array(feature_values).reshape(1, -1)
        X_scaled = self.scaler.transform(X)

        prediction = int(self.model.predict(X_scaled)[0])
        probability = self.model.predict_proba(X_scaled)[0]

        risk_level = "low"
        if probability[1] > 0.7:
            risk_level = "high"
        elif probability[1] > 0.4:
            risk_level = "moderate"

        return {
            "prediction": prediction,
            "diagnosis": "Likely PCOS" if prediction == 1 else "Unlikely PCOS",
            "probability_pcos": round(float(probability[1]), 4),
            "probability_no_pcos": round(float(probability[0]), 4),
            "risk_level": risk_level,
            "recommendations": self._get_recommendations(risk_level, features),
        }

    def _get_recommendations(self, risk_level: str, features: dict) -> list[str]:
        recs = []

        if risk_level == "high":
            recs.append("Consult a gynecologist or endocrinologist for a comprehensive evaluation.")
            recs.append("Get blood work done: hormone panel, fasting glucose, insulin, and lipid profile.")
        elif risk_level == "moderate":
            recs.append("Consider scheduling a check-up with your healthcare provider.")
            recs.append("Track your menstrual cycle and note any irregularities.")

        cycle = features.get("Cycle(R/I)", 0)
        cycle_len = features.get("Cycle length(days)", 0)
        if cycle == 1 or 0 < cycle_len < 21 or cycle_len > 35:
            recs.append("Irregular or long cycles are common in PCOS — keep a cycle diary and discuss it with your doctor.")

        rbs = features.get("RBS(mg/dl)", 0)
        if rbs > 100:
            recs.append("Monitor blood sugar levels regularly and consider an anti-inflammatory, low-glycemic diet.")

        follicle_l = features.get("Follicle No. (L)", 0)
        follicle_r = features.get("Follicle No. (R)", 0)
        if follicle_l > 10 or follicle_r > 10:
            recs.append("Elevated follicle counts on the ovaries are consistent with PCOS — verify with your clinician.")

        vitd = features.get("Vit D3 (ng/mL)", 0)
        if 0 < vitd < 20:
            recs.append("Low vitamin D levels are common in PCOS — consider testing and supplementation with your provider.")

        weight_gain = features.get("Weight gain(Y/N)", 0)
        if weight_gain == 1:
            recs.append("Gradual weight loss (5-10% of body weight) through diet and exercise can improve symptoms.")

        if features.get("hair growth(Y/N)") == 1 or features.get("Skin darkening (Y/N)") == 1:
            recs.append("Hirsutism and skin changes may reflect hormonal imbalance — discuss management options with your doctor.")

        hair_loss = features.get("Hair loss(Y/N)", 0)
        if hair_loss == 1:
            recs.append("Hair loss can be distressing — a dermatologist can help address it alongside hormonal treatment.")

        if features.get("Reg.Exercise(Y/N)") == 0:
            recs.append("Regular exercise (aerobic + resistance) improves insulin sensitivity — aim for 150 minutes weekly.")

        if not recs:
            recs.append("Continue maintaining a healthy lifestyle. Regular check-ups are recommended.")

        return recs

    @staticmethod
    def _fit_scaler(X_train: np.ndarray):
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        scaler.fit(np.asarray(X_train, dtype=float))
        return scaler


_predictor: PCOSPredictor | None = None


def get_predictor() -> PCOSPredictor:
    global _predictor
    if _predictor is None:
        _predictor = PCOSPredictor()
        _predictor.load()
    return _predictor