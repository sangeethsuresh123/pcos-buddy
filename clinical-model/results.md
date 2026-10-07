# Clinical PCOS model results (2026-09-22)

- Source: `dataset/test.csv` (82 rows, 23 features)
- Class distribution (test): non-PCOS 55 / PCOS 27
- Model: GradientBoostingClassifier{'ccp_alpha': 0.0, 'criterion': 'deprecated', 'init': None, 'learning_rate': 0.1, 'loss': 'log_loss', 'max_depth': 5, 'max_features': None, 'max_leaf_nodes': None, 'min_impurity_decrease': 0.0, 'min_samples_leaf': 1, 'min_samples_split': 2, 'min_weight_fraction_leaf': 0.0, 'n_estimators': 200, 'n_iter_no_change': None, 'random_state': 42, 'subsample': 1.0, 'tol': 0.0001, 'validation_fraction': 0.1, 'verbose': 0, 'warm_start': False}

| Metric | Value |
|---|---|
| Accuracy | 0.9024 |
| Precision (PCOS) | 0.88 |
| Recall (PCOS) | 0.8148 |
| F1 (PCOS) | 0.8462 |
| ROC AUC | 0.9037 |
| Confusion matrix | `[[52, 3], [5, 22]]` |