from backend.ml.predictor import get_predictor


def main():
    print("Training PCOS prediction model on dataset/train.csv ...")
    predictor = get_predictor()

    if predictor.is_loaded:
        print("A model already exists. Retraining...")

    results = predictor.train()

    print(f"\nTraining Complete!")
    print(f"Accuracy:    {results['accuracy']}")
    print(f"Precision:   {results['precision']}")
    print(f"Recall:      {results['recall']}")
    print(f"F1 Score:    {results['f1_score']}")
    print(f"ROC AUC:     {results['roc_auc']}")
    print(f"Train rows:  {results['n_training_samples']}")
    print(f"Test rows:   {results['n_test_samples']}")
    print(f"\nTop features by importance (tested on dataset/test.csv):")
    sorted_features = sorted(
        results["feature_importance"].items(), key=lambda x: x[1], reverse=True
    )
    for fname, imp in sorted_features[:10]:
        print(f"  {fname}: {imp}")


if __name__ == "__main__":
    main()