import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from backend.ml.preprocess import FEATURE_COLUMNS, TARGET_COLUMN, load_dataframe
from backend.ml.predictor import get_predictor

OUT_DIR = Path("clinical-model")
TEST_FILE = Path("dataset/test.csv")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pred = get_predictor()
    if not pred.is_loaded:
        raise SystemExit("Clinical model not loaded from backend/ml/models.")

    test_df = load_dataframe(str(TEST_FILE))
    X = test_df[FEATURE_COLUMNS].values.astype(float)
    y_true = test_df[TARGET_COLUMN].values.astype(int)
    X_scaled = pred.scaler.transform(X)

    y_pred = pred.model.predict(X_scaled)
    y_prob = pred.model.predict_proba(X_scaled)[:, 1]
    cm = np.bincount(y_true * 2 + y_pred, minlength=4).reshape(2, 2)

    metrics = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision_pcos": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall_pcos": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1_pcos": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "confusion_matrix": [[int(v) for v in row] for row in cm],
    }

    results = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(TEST_FILE),
        "n_rows": int(len(y_true)),
        "n_features": len(FEATURE_COLUMNS),
        "class_distribution": {"non_pcos": int((y_true == 0).sum()), "pcos": int((y_true == 1).sum())},
        "model_loaded_from": "backend/ml/models/pcos_model.pkl",
        "model_params": pred.model.get_params(),
        "metrics": metrics,
    }

    with open(OUT_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    with open(OUT_DIR / "results.md", "w") as f:
        f.write(
            "\n".join([
                f"# Clinical PCOS model results ({results['created_at'][:10]})",
                "",
                f"- Source: `{results['source']}` ({results['n_rows']} rows, {results['n_features']} features)",
                f"- Class distribution (test): non-PCOS {results['class_distribution']['non_pcos']} / PCOS {results['class_distribution']['pcos']}",
                f"- Model: GradientBoostingClassifier{results['model_params']}",
                "",
                "| Metric | Value |",
                "|---|---|",
                f"| Accuracy | {metrics['accuracy']} |",
                f"| Precision (PCOS) | {metrics['precision_pcos']} |",
                f"| Recall (PCOS) | {metrics['recall_pcos']} |",
                f"| F1 (PCOS) | {metrics['f1_pcos']} |",
                f"| ROC AUC | {metrics['roc_auc']} |",
                f"| Confusion matrix | `{metrics['confusion_matrix']}` |",
            ])
        )

    print("Stored: clinical-model/results.json, clinical-model/results.md")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()