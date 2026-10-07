import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.preprocessing import StandardScaler

RAW_FILE = Path("home-based-dataset/pcos-gform-dataset.csv")
OUT_DIR = Path("home-based-model")

TARGET_COL = "diagnosed_pcos"

COLUMNS = {
    "Age (in Years)": "age",
    "Weight (in Kg)": "weight_kg",
    "Height (in Cm / Feet)": "height_cm",
    "Can you tell us your blood group ?": "blood_group",
    "After how many months do you get your periods?\n(select 1- if every month/regular)": "period_freq_months",
    "Have you gained weight recently?": "weight_gain",
    "Do you have excessive body/facial hair growth ?": "hair_growth",
    "Are you noticing skin darkening recently?": "skin_darkening",
    "Do have hair loss/hair thinning/baldness ?": "hair_loss",
    "Do you have pimples/acne on your face/jawline ?": "acne",
    "Do you eat fast food regularly ?": "fast_food",
    "Do you exercise on a regular basis ?": "exercise",
    "Have you been diagnosed with PCOS/PCOD?": TARGET_COL,
    "Do you experience mood swings ?": "mood_swings",
    "Are your periods regular ?": "periods_regular",
    "How long does your period last ? (in Days)\nexample- 1,2,3,4.....": "period_length_days",
}

MODEL_KWARGS = dict(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42)


def load_data():
    df = pd.read_csv(RAW_FILE).rename(columns=COLUMNS)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[TARGET_COL])
    features = [c for c in COLUMNS.values() if c != TARGET_COL]
    X = df[features].values.astype(float)
    y = df[TARGET_COL].values.astype(int)
    return df, features, X, y


def evaluate(model, scaler, X_test, y_test):
    X_s = scaler.transform(X_test)
    y_pred = model.predict(X_s)
    y_prob = model.predict_proba(X_s)[:, 1]
    return {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision_pcos": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall_pcos": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1_pcos": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
        "confusion_matrix": np.asarray(
            [[int(v) for v in row] for row in np.bincount(y_test * 2 + y_pred, minlength=4).reshape(2, 2)]
        ).tolist(),
    }


def save_artifacts(name, model, scaler, features, metrics, metadata, extra):
    with open(OUT_DIR / f"{name}_model.pkl", "wb") as f:
        pickle.dump(model, f)
    with open(OUT_DIR / f"{name}_scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    with open(OUT_DIR / "features.pkl", "wb") as f:
        pickle.dump(features, f)
    record = {
        "created_at": metadata["created_at"],
        "name": name,
        **extra,
        "metrics": metrics,
    }
    return record


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df, features, X, y = load_data()

    split = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(split.split(X, y))
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(RAW_FILE),
        "n_rows": len(df),
        "n_features": len(features),
        "class_distribution_total": {"non_pcos": int((y == 0).sum()), "pcos": int((y == 1).sum())},
        "train_rows": int(len(y_train)),
        "test_rows": int(len(y_test)),
        "test_class_distribution": {"non_pcos": int((y_test == 0).sum()), "pcos": int((y_test == 1).sum())},
        "model_params": MODEL_KWARGS,
    }

    # ---- baseline (no resampling)
    scaler_b = StandardScaler().fit(X_train)
    model_b = GradientBoostingClassifier(**MODEL_KWARGS).fit(scaler_b.transform(X_train), y_train)
    metrics_b = evaluate(model_b, scaler_b, X_test, y_test)
    record_b = save_artifacts(
        "baseline", model_b, scaler_b, features, metrics_b, metadata,
        extra={"resampling": "none", "train_class_distribution": {
            "non_pcos": int((y_train == 0).sum()), "pcos": int((y_train == 1).sum())}},
    )

    # ---- SMOTE on training set
    smote = SMOTE(random_state=42)
    X_train_sm, y_train_sm = smote.fit_resample(X_train, y_train)
    scaler_s = StandardScaler().fit(X_train_sm)
    model_s = GradientBoostingClassifier(**MODEL_KWARGS).fit(scaler_s.transform(X_train_sm), y_train_sm)
    metrics_s = evaluate(model_s, scaler_s, X_test, y_test)
    record_s = save_artifacts(
        "smote", model_s, scaler_s, features, metrics_s, metadata,
        extra={"resampling": "smote", "smote_neighbors": smote.k_neighbors,
               "train_class_distribution": {"non_pcos": int((y_train_sm == 0).sum()), "pcos": int((y_train_sm == 1).sum())}},
    )

    # ---- store combined results
    results = {
        "metadata": metadata,
        "runs": [record_b, record_s],
        "feature_importances": {
            "baseline": dict(sorted(zip(features, [round(float(v), 4) for v in model_b.feature_importances_]), key=lambda kv: kv[1], reverse=True)),
            "smote": dict(sorted(zip(features, [round(float(v), 4) for v in model_s.feature_importances_]), key=lambda kv: kv[1], reverse=True)),
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    # ---- human-readable summary
    lines = [
        f"# Home-based PCOS model results ({metadata['created_at'][:10]})",
        "",
        f"- Source: `{metadata['source']}` ({metadata['n_rows']} rows, {metadata['n_features']} features)",
        f"- Split: stratified 80/20 (train={metadata['train_rows']}, test={metadata['test_rows']})",
        f"- Target imbalance (total): non-PCOS {metadata['class_distribution_total']['non_pcos']} / PCOS {metadata['class_distribution_total']['pcos']}",
        f"- Model: GradientBoostingClassifier{metadata['model_params']}",
        "",
        "## Baseline (no resampling)",
        "", _fmt_table(record_b),
        "## SMOTE (resampled training set)",
        "", _fmt_table(record_s),
    ]
    with open(OUT_DIR / "results.md", "w") as f:
        f.write("\n".join(lines))

    for rec in results["runs"]:
        print(f"\n=== {rec['name']} | resampling: {rec['resampling']}")
        print(json.dumps(rec["metrics"], indent=2))


def _fmt_table(record):
    m = record["metrics"]
    cm = m["confusion_matrix"]
    return "\n".join([
        "| Metric | Value |",
        "|---|---|",
        f"| Accuracy | {m['accuracy']} |",
        f"| Precision (PCOS) | {m['precision_pcos']} |",
        f"| Recall (PCOS) | {m['recall_pcos']} |",
        f"| F1 (PCOS) | {m['f1_pcos']} |",
        f"| ROC AUC | {m['roc_auc']} |",
        f"| Confusion matrix | `[[{cm[0][0]} {cm[0][1]}] [{cm[1][0]} {cm[1][1]}]]` |",
        f"| Train class counts | {record['train_class_distribution']} |",
    ])


if __name__ == "__main__":
    main()