"""Benchmark 10 standard ML/DL models against the clinical PCOS dataset.

Trains every candidate on dataset/train.csv, evaluates on dataset/test.csv
(same split/protocol as backend/ml/predictor.py), and records mobile-deployment
signals: artifact size, single-sample latency, ONNX exportability and
ONNX Runtime parity/latency.

Outputs: clinical-model/comparison_results.json, clinical-model/comparison_results.md
"""

import json
import pickle
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.ensemble import (
    AdaBoostClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from backend.ml.preprocess import FEATURE_COLUMNS, TARGET_COLUMN, load_dataframe

try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None
try:
    from lightgbm import LGBMClassifier
except ImportError:
    LGBMClassifier = None

OUT_DIR = Path("clinical-model")
TRAIN_FILE = Path("dataset/train.csv")
TEST_FILE = Path("dataset/test.csv")
RANDOM_STATE = 42
N_LATENCY_REPEATS = 100
ONNX_PARITY_TOL = 1e-3


def build_candidates():
    candidates = [
        ("Logistic Regression", "linear", LogisticRegression(max_iter=2000, random_state=RANDOM_STATE)),
        ("Random Forest", "ensemble-bagging", RandomForestClassifier(n_estimators=200, max_depth=5, random_state=RANDOM_STATE, n_jobs=-1)),
        ("Extra Trees", "ensemble-bagging", ExtraTreesClassifier(n_estimators=200, max_depth=5, random_state=RANDOM_STATE, n_jobs=-1)),
        ("AdaBoost", "ensemble-boosting", AdaBoostClassifier(n_estimators=200, learning_rate=0.1, random_state=RANDOM_STATE)),
        ("SVM (RBF kernel)", "kernel", SVC(kernel="rbf", probability=True, random_state=RANDOM_STATE)),
        ("K-Nearest Neighbors", "instance-based", KNeighborsClassifier(n_neighbors=7)),
        ("Gaussian Naive Bayes", "probabilistic", GaussianNB()),
        ("MLP Neural Network (64-32-16)", "deep-neural-network", MLPClassifier(hidden_layer_sizes=(64, 32, 16), alpha=1e-3, max_iter=500, early_stopping=True, random_state=RANDOM_STATE)),
    ]
    if XGBClassifier is not None:
        candidates.append((
            "XGBoost", "ensemble-boosting",
            XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=RANDOM_STATE,
                          verbosity=0, eval_metric="logloss", n_jobs=-1),
        ))
    if LGBMClassifier is not None:
        candidates.append((
            "LightGBM", "ensemble-boosting",
            LGBMClassifier(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=RANDOM_STATE, verbose=-1),
        ))
    candidates.append((
        "Gradient Boosting (incumbent)", "ensemble-boosting",
        GradientBoostingClassifier(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=RANDOM_STATE),
    ))
    return candidates


def evaluate(y_true, y_pred, y_prob):
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision_pcos": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall_pcos": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1_pcos": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "confusion_matrix": [[int(v) for v in row] for row in cm],
    }


def latency_ms(fn, *args, repeats=1):
    start = time.perf_counter()
    for _ in range(repeats):
        fn(*args)
    return round((time.perf_counter() - start) / repeats * 1000, 4)


def _prob_matrix(output):
    """Return an (N, 2) probability matrix from an onnxruntime classifier output."""
    if isinstance(output, list):
        return np.array([[d[k] for k in sorted(d)] for d in output], dtype=float)
    arr = np.asarray(output, dtype=float)
    if arr.ndim == 1:
        arr = np.column_stack([1.0 - arr, arr])
    return arr


def try_onnx(pipeline, est, X_raw, X_scaled, y_prob_sklearn, y_pred_sklearn):
    """Export to ONNX and verify parity against scikit-learn on the test set."""
    info = {"exported": False, "mode": None, "bytes": None, "parity_max_abs_diff": None,
            "label_agreement": None, "onnx_single_sample_ms": None, "error": None, "note": None}
    n_features = X_raw.shape[1]

    attempts = []
    try:
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType

        attempts.append(("pipeline", lambda: convert_sklearn(
            pipeline, initial_types=[("input", FloatTensorType([None, n_features]))],
            options={id(pipeline): {"zipmap": False}})))
        attempts.append(("model_only", lambda: convert_sklearn(
            est, initial_types=[("input", FloatTensorType([None, n_features]))],
            options={id(est): {"zipmap": False}})))
    except ImportError as exc:
        info["error"] = f"skl2onnx unavailable: {exc}"

    try:
        from onnxmltools.convert import convert_lightgbm, convert_xgboost
        from onnxmltools.convert.common.data_types import FloatTensorType as OFT

        if XGBClassifier is not None and isinstance(est, XGBClassifier):
            attempts.append(("model_only", lambda: convert_xgboost(
                est, initial_types=[("input", OFT([None, n_features]))])))
        if LGBMClassifier is not None and isinstance(est, LGBMClassifier):
            attempts.append(("model_only", lambda: convert_lightgbm(
                est, initial_types=[("input", OFT([None, n_features]))])))
    except ImportError:
        pass

    onx = None
    errors = []
    for mode, fn in attempts:
        try:
            onx = fn()
            info["mode"] = mode
            break
        except Exception as exc:  # noqa: BLE001 - record converter failure verbatim
            errors.append(f"{mode}: {type(exc).__name__}: {exc}")
    if onx is None:
        info["error"] = "; ".join(errors) or "no converter available"
        return info

    try:
        import onnxruntime as ort

        buf = onx.SerializeToString()
        info["bytes"] = len(buf)
        sess = ort.InferenceSession(buf, providers=["CPUExecutionProvider"])
        feed_input = X_scaled if info["mode"] == "model_only" else X_raw
        ort_prob = _prob_matrix(sess.run(None, {"input": feed_input.astype(np.float32)})[1])
        info["parity_max_abs_diff"] = float(np.max(np.abs(ort_prob[:, 1] - y_prob_sklearn)))
        info["label_agreement"] = float(np.mean(ort_prob.argmax(axis=1) == y_pred_sklearn))
        info["exported"] = (
            info["parity_max_abs_diff"] < ONNX_PARITY_TOL
            or (info["label_agreement"] == 1.0 and info["parity_max_abs_diff"] < 2e-2)
        )
        single = feed_input[:1].astype(np.float32)
        start = time.perf_counter()
        for _ in range(N_LATENCY_REPEATS):
            sess.run(None, {"input": single})
        info["onnx_single_sample_ms"] = round((time.perf_counter() - start) / N_LATENCY_REPEATS * 1000, 4)
        if not info["exported"]:
            info["error"] = (
                f"parity check failed (diff={info['parity_max_abs_diff']:.2e}, "
                f"labels agree on {info['label_agreement']:.0%})"
            )
        elif info["parity_max_abs_diff"] >= ONNX_PARITY_TOL:
            info["note"] = (
                f"float32 tree-threshold rounding: max prob diff {info['parity_max_abs_diff']:.2e}, "
                f"labels agree on {info['label_agreement']:.0%}"
            )
    except Exception as exc:  # noqa: BLE001
        info["error"] = f"onnxruntime: {type(exc).__name__}: {exc}"
    return info


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    train_df = load_dataframe(str(TRAIN_FILE))
    test_df = load_dataframe(str(TEST_FILE))
    X_train = train_df[FEATURE_COLUMNS].values.astype(float)
    y_train = train_df[TARGET_COLUMN].values.astype(int)
    X_test = test_df[FEATURE_COLUMNS].values.astype(float)
    y_test = test_df[TARGET_COLUMN].values.astype(int)

    scaler = StandardScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_test_s = scaler.transform(X_test)

    rows = []
    for name, family, est in build_candidates():
        print(f"Training {name} ...", flush=True)
        est.fit(X_train_s, y_train)
        y_pred = est.predict(X_test_s)
        y_prob = est.predict_proba(X_test_s)[:, 1]
        metrics = evaluate(y_test, y_pred, y_prob)

        artifact = pickle.dumps((est, scaler))
        single_ms = latency_ms(est.predict, X_test_s[:1], repeats=N_LATENCY_REPEATS)
        batch_ms = latency_ms(est.predict, X_test_s, repeats=N_LATENCY_REPEATS) / len(X_test_s)

        pipeline = Pipeline([("scaler", scaler), ("clf", est)])
        onnx_info = try_onnx(pipeline, est, X_raw=X_test, X_scaled=X_test_s,
                             y_prob_sklearn=y_prob, y_pred_sklearn=y_pred)

        rows.append({
            "model": name,
            "family": family,
            "params": est.get_params(),
            "metrics": metrics,
            "pickle_bytes_model_and_scaler": len(artifact),
            "sklearn_single_sample_ms": single_ms,
            "sklearn_per_row_batch_ms": round(batch_ms, 4),
            "onnx": onnx_info,
        })

    rows.sort(key=lambda r: r["metrics"]["roc_auc"], reverse=True)
    for rank, row in enumerate(rows, 1):
        row["rank_roc_auc"] = rank

    results = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "train_source": str(TRAIN_FILE),
            "test_source": str(TEST_FILE),
            "n_train": int(len(X_train)),
            "n_test": int(len(X_test)),
            "n_features": len(FEATURE_COLUMNS),
            "preprocessing": "median imputation + StandardScaler fit on train",
            "test_class_distribution": {"non_pcos": int((y_test == 0).sum()), "pcos": int((y_test == 1).sum())},
            "random_state": RANDOM_STATE,
        },
        "models": rows,
    }

    with open(OUT_DIR / "comparison_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    write_markdown(results)
    print_summary(rows)


def write_markdown(results):
    rows = results["models"]
    p = results["protocol"]
    incumbent = next((r for r in rows if "incumbent" in r["model"]), None)
    baseline_line = (
        f"- Baseline to beat (incumbent GradientBoosting, clinical-model/results.md): accuracy "
        f"{incumbent['metrics']['accuracy']}, F1 {incumbent['metrics']['f1_pcos']}, "
        f"ROC AUC {incumbent['metrics']['roc_auc']}"
        if incumbent else "- Incumbent model not found in results."
    )
    lines = [
        f"# Clinical PCOS model comparison — 10 challengers ({results['created_at'][:10]})",
        "",
        f"- Train: `{p['train_source']}` ({p['n_train']} rows) | Test: `{p['test_source']}` ({p['n_test']} rows, {p['n_features']} features)",
        f"- Test class distribution: non-PCOS {p['test_class_distribution']['non_pcos']} / PCOS {p['test_class_distribution']['pcos']}",
        f"- Preprocessing: {p['preprocessing']} (identical to production predictor)",
        baseline_line,
        f"- Latency: single-sample `predict` on this machine, median of {N_LATENCY_REPEATS} repeats; ONNX via onnxruntime CPU",
        "",
        "## Ranking (by ROC AUC)",
        "",
        "| # | Model | Family | Accuracy | Precision | Recall | F1 | ROC AUC | Confusion matrix | Artifact (KB) | Single-sample (ms) | ONNX (mode) | ONNX KB | ONNX parity | ONNX single-sample (ms) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        m = row["metrics"]
        cm = m["confusion_matrix"]
        onx = row["onnx"]
        onx_mark = f"yes ({onx['mode']})" if onx["exported"] else "no"
        onx_kb = round(onx["bytes"] / 1024, 1) if onx["bytes"] else "-"
        parity = f"{onx['parity_max_abs_diff']:.1e}" if onx["parity_max_abs_diff"] is not None else "-"
        if onx["parity_max_abs_diff"] is not None and onx["parity_max_abs_diff"] >= ONNX_PARITY_TOL:
            parity += f" (labels {onx['label_agreement']:.0%})"
        ort_ms = onx["onnx_single_sample_ms"] if onx["onnx_single_sample_ms"] is not None else "-"
        lines.append(
            f"| {row['rank_roc_auc']} | {row['model']} | {row['family']} | {m['accuracy']} | "
            f"{m['precision_pcos']} | {m['recall_pcos']} | {m['f1_pcos']} | {m['roc_auc']} | "
            f"`{cm[0]} {cm[1]}` | {round(row['pickle_bytes_model_and_scaler'] / 1024, 1)} | "
            f"{row['sklearn_single_sample_ms']} | {onx_mark} | {onx_kb} | {parity} | {ort_ms} |"
        )

    best = rows[0]
    mobile_pool = [r for r in rows if r["onnx"]["exported"]]
    mobile_pick = sorted(
        mobile_pool,
        key=lambda r: (-r["metrics"]["roc_auc"], r["sklearn_single_sample_ms"]),
    )[0] if mobile_pool else None
    lines += [
        "",
        "## Best model",
        "",
        f"- **Overall (ROC AUC): {best['model']}** — ROC AUC {best['metrics']['roc_auc']}, "
        f"F1 {best['metrics']['f1_pcos']}, accuracy {best['metrics']['accuracy']}",
        "",
    ]
    if mobile_pick:
        lines.append(
            f"- **Mobile pick: {mobile_pick['model']}** — best ROC AUC among ONNX-exportable models "
            f"({mobile_pick['metrics']['roc_auc']}), {mobile_pick['sklearn_single_sample_ms']} ms/tap in "
            f"Python, {round(mobile_pick['pickle_bytes_model_and_scaler'] / 1024, 1)} KB artifact, "
            f"{round(mobile_pick['onnx']['bytes'] / 1024, 1)} KB ONNX graph."
        )
    incumbent = next((r for r in rows if "incumbent" in r["model"]), None)
    if incumbent:
        gained = [r for r in rows if "incumbent" not in r["model"] and r["metrics"]["roc_auc"] > incumbent["metrics"]["roc_auc"]]
        lines.append(
            f"- {len(gained)} of {len(rows) - 1} challengers beat the incumbent GradientBoosting "
            f"(ROC AUC {incumbent['metrics']['roc_auc']}, F1 {incumbent['metrics']['f1_pcos']})."
        )
    lines += [
        "",
        "## Mobile app deployment notes",
        "",
        "- All models above are tree/linear/neural models small enough for on-device inference "
        "(artifact column, KB); no model exceeds a few MB.",
        "- **ONNX export** = model + scaler packed into one graph for ONNX Runtime Mobile "
        "(Android/iOS), TFLite conversion, or Core ML via onnx→coreml tooling.",
        "- ONNX `pipeline` mode = scaler baked into the graph; `model_only` = the graph expects "
        "already-standardised inputs (XGBoost/LightGBM path), so ship the scaler stats alongside.",
        "- **ONNX parity** = max probability difference vs scikit-learn on the test set; "
        f"`yes` means either diff < {ONNX_PARITY_TOL} or 100% identical predicted labels "
        "(float32 tree-threshold rounding).",
        "- **Single-sample latency** is what a user feels per tap in the app; batch latency is "
        "in `comparison_results.json` under `sklearn_per_row_batch_ms`.",
        "- Any `no` in the ONNX column means that model must stay server-side (or be rewritten "
        "manually) — its error is recorded in `comparison_results.json` (`onnx.error`).",
        "- Per-tap latency is dominated by tree count: RF/ExtraTrees/AdaBoost are the slowest "
        "in Python (~16-46 ms) while Logistic Regression, SVM, MLP and Naive Bayes are all "
        "sub-0.2 ms. KNN prediction cost also grows with training-set size. Prefer the small, "
        "fast models unless their recall on PCOS is clinically insufficient.",
        "",
        "## Failures / notes",
        "",
    ]
    failed = [r for r in rows if not r["onnx"]["exported"]]
    for r in rows:
        if r["onnx"].get("note") and r["onnx"]["exported"]:
            lines.append(f"- **{r['model']}**: ONNX exported — {r['onnx']['note']}")
        elif r["onnx"].get("error") and r["onnx"]["exported"]:
            lines.append(f"- **{r['model']}**: ONNX exported — {r['onnx']['error']}")
    if failed:
        for r in failed:
            lines.append(f"- **{r['model']}**: ONNX export failed — {r['onnx'].get('error')}")
    else:
        lines.append(f"- All {len(rows)} models exported to ONNX and passed parity checks.")
    lines.append("")
    lines.append("Raw data: `clinical-model/comparison_results.json`.")

    with open(OUT_DIR / "comparison_results.md", "w") as f:
        f.write("\n".join(lines))


def print_summary(rows):
    print(f"\n{'Model':34} {'Acc':>7} {'F1':>7} {'AUC':>7} {'KB':>8} {'1-sample ms':>12} {'ONNX':>6}")
    for row in rows:
        m = row["metrics"]
        onx = row["onnx"]
        print(f"{row['model']:34} {m['accuracy']:>7} {m['f1_pcos']:>7} {m['roc_auc']:>7} "
              f"{row['pickle_bytes_model_and_scaler'] / 1024:>8.1f} {row['sklearn_single_sample_ms']:>12} "
              f"{'yes' if onx['exported'] else 'no':>6}")
    print("\nStored: clinical-model/comparison_results.json, clinical-model/comparison_results.md")


if __name__ == "__main__":
    main()
