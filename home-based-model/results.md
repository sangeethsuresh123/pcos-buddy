# Home-based PCOS model results (2026-09-22)

- Source: `home-based-dataset/pcos-gform-dataset.csv` (465 rows, 15 features)
- Split: stratified 80/20 (train=372, test=93)
- Target imbalance (total): non-PCOS 363 / PCOS 102
- Model: GradientBoostingClassifier{'n_estimators': 200, 'max_depth': 5, 'learning_rate': 0.1, 'random_state': 42}

## Baseline (no resampling)

| Metric | Value |
|---|---|
| Accuracy | 0.7849 |
| Precision (PCOS) | 0.5 |
| Recall (PCOS) | 0.5 |
| F1 (PCOS) | 0.5 |
| ROC AUC | 0.6781 |
| Confusion matrix | `[[63 10] [10 10]]` |
| Train class counts | {'non_pcos': 290, 'pcos': 82} |
## SMOTE (resampled training set)

| Metric | Value |
|---|---|
| Accuracy | 0.8065 |
| Precision (PCOS) | 0.55 |
| Recall (PCOS) | 0.55 |
| F1 (PCOS) | 0.55 |
| ROC AUC | 0.6644 |
| Confusion matrix | `[[64 9] [9 11]]` |
| Train class counts | {'non_pcos': 290, 'pcos': 290} |