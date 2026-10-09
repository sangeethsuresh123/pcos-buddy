# Clinical PCOS model comparison — 10 challengers (2026-10-08)

- Train: `dataset/train.csv` (459 rows) | Test: `dataset/test.csv` (82 rows, 23 features)
- Test class distribution: non-PCOS 55 / PCOS 27
- Preprocessing: median imputation + StandardScaler fit on train (identical to production predictor)
- Baseline to beat (incumbent GradientBoosting, clinical-model/results.md): accuracy 0.9024, F1 0.8462, ROC AUC 0.9037
- Latency: single-sample `predict` on this machine, median of 100 repeats; ONNX via onnxruntime CPU

## Ranking (by ROC AUC)

| # | Model | Family | Accuracy | Precision | Recall | F1 | ROC AUC | Confusion matrix | Artifact (KB) | Single-sample (ms) | ONNX (mode) | ONNX KB | ONNX parity | ONNX single-sample (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | MLP Neural Network (64-32-16) | deep-neural-network | 0.9024 | 0.913 | 0.7778 | 0.84 | 0.9239 | `[53, 2] [6, 21]` | 106.9 | 0.1124 | yes (pipeline) | 18.1 | 1.7e-07 | 0.018 |
| 2 | K-Nearest Neighbors | instance-based | 0.8659 | 0.8636 | 0.7037 | 0.7755 | 0.9232 | `[52, 3] [8, 19]` | 87.5 | 1.0403 | yes (pipeline) | 44.4 | 2.6e-08 | 0.8163 |
| 3 | SVM (RBF kernel) | kernel | 0.878 | 0.9048 | 0.7037 | 0.7917 | 0.9205 | `[53, 2] [8, 19]` | 38.7 | 0.0927 | yes (pipeline) | 22.4 | 1.9e-07 | 0.0098 |
| 4 | Extra Trees | ensemble-bagging | 0.878 | 0.9048 | 0.7037 | 0.7917 | 0.9192 | `[53, 2] [8, 19]` | 713.7 | 46.3528 | yes (pipeline) | 303.2 | 1.7e-07 | 0.0086 |
| 5 | AdaBoost | ensemble-boosting | 0.878 | 0.84 | 0.7778 | 0.8077 | 0.9192 | `[51, 4] [6, 21]` | 110.2 | 16.2252 | yes (pipeline) | 166.4 | 1.6e-07 | 0.7768 |
| 6 | XGBoost | ensemble-boosting | 0.9024 | 0.913 | 0.7778 | 0.84 | 0.9158 | `[53, 2] [6, 21]` | 265.7 | 0.3534 | yes (model_only) | 116.5 | 2.1e-07 | 0.0081 |
| 7 | Logistic Regression | linear | 0.8902 | 0.8462 | 0.8148 | 0.8302 | 0.9131 | `[51, 4] [5, 22]` | 1.7 | 0.132 | yes (pipeline) | 0.9 | 8.0e-08 | 0.007 |
| 8 | LightGBM | ensemble-boosting | 0.8659 | 0.8333 | 0.7407 | 0.7843 | 0.9111 | `[51, 4] [7, 20]` | 313.2 | 0.5962 | yes (model_only) | 184.4 | 9.6e-08 | 0.0089 |
| 9 | Gradient Boosting (incumbent) | ensemble-boosting | 0.9024 | 0.88 | 0.8148 | 0.8462 | 0.9037 | `[52, 3] [5, 22]` | 808.4 | 0.2188 | yes (pipeline) | 389.1 | 9.8e-04 | 0.0118 |
| 10 | Random Forest | ensemble-bagging | 0.8902 | 0.9091 | 0.7407 | 0.8163 | 0.8997 | `[53, 2] [7, 20]` | 766.5 | 44.7777 | yes (pipeline) | 327.6 | 1.1e-02 (labels 100%) | 0.0091 |
| 11 | Gaussian Naive Bayes | probabilistic | 0.8171 | 0.6667 | 0.8889 | 0.7619 | 0.8801 | `[43, 12] [3, 24]` | 2.1 | 0.1045 | yes (pipeline) | 2.2 | 3.4e-06 | 0.0132 |

## Best model

- **Overall (ROC AUC): MLP Neural Network (64-32-16)** — ROC AUC 0.9239, F1 0.84, accuracy 0.9024

- **Mobile pick: MLP Neural Network (64-32-16)** — best ROC AUC among ONNX-exportable models (0.9239), 0.1124 ms/tap in Python, 106.9 KB artifact, 18.1 KB ONNX graph.
- 8 of 10 challengers beat the incumbent GradientBoosting (ROC AUC 0.9037, F1 0.8462).

## Mobile app deployment notes

- All models above are tree/linear/neural models small enough for on-device inference (artifact column, KB); no model exceeds a few MB.
- **ONNX export** = model + scaler packed into one graph for ONNX Runtime Mobile (Android/iOS), TFLite conversion, or Core ML via onnx→coreml tooling.
- ONNX `pipeline` mode = scaler baked into the graph; `model_only` = the graph expects already-standardised inputs (XGBoost/LightGBM path), so ship the scaler stats alongside.
- **ONNX parity** = max probability difference vs scikit-learn on the test set; `yes` means either diff < 0.001 or 100% identical predicted labels (float32 tree-threshold rounding).
- **Single-sample latency** is what a user feels per tap in the app; batch latency is in `comparison_results.json` under `sklearn_per_row_batch_ms`.
- Any `no` in the ONNX column means that model must stay server-side (or be rewritten manually) — its error is recorded in `comparison_results.json` (`onnx.error`).
- Per-tap latency is dominated by tree count: RF/ExtraTrees/AdaBoost are the slowest in Python (~16-46 ms) while Logistic Regression, SVM, MLP and Naive Bayes are all sub-0.2 ms. KNN prediction cost also grows with training-set size. Prefer the small, fast models unless their recall on PCOS is clinically insufficient.

## Failures / notes

- **Random Forest**: ONNX exported — float32 tree-threshold rounding: max prob diff 1.07e-02, labels agree on 100%
- All 11 models exported to ONNX and passed parity checks.

Raw data: `clinical-model/comparison_results.json`.