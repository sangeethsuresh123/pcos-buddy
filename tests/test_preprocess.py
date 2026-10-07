import numpy as np
import pandas as pd

from backend.ml.preprocess import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    get_feature_names,
    load_dataframe,
)


def test_feature_columns_are_unique_and_complete():
    assert len(FEATURE_COLUMNS) == 23
    assert len(set(FEATURE_COLUMNS)) == len(FEATURE_COLUMNS)
    assert TARGET_COLUMN not in FEATURE_COLUMNS


def test_get_feature_names_returns_defensive_copy():
    names = get_feature_names()
    names.append("bogus")
    assert names != FEATURE_COLUMNS


def test_load_dataframe_coerces_and_fills_missing(tmp_path):
    data = {col: [1.0, np.nan, 3.0] for col in FEATURE_COLUMNS}
    data[TARGET_COLUMN] = [1, 0, np.nan]
    df = pd.DataFrame(data)
    df[FEATURE_COLUMNS[0]] = ["not-a-number", "1.0", "3.0"]

    path = tmp_path / "data.csv"
    df.to_csv(path, index=False)

    loaded = load_dataframe(str(path))

    assert len(loaded) == 2
    assert loaded[FEATURE_COLUMNS].dtypes.apply(np.issubdtype, args=(np.number,)).all()
    assert not loaded[FEATURE_COLUMNS].isna().any().any()
    assert "not-a-number" not in loaded.astype(str).values


def test_load_dataframe_keeps_all_rows_with_valid_target(tmp_path):
    df = pd.DataFrame(
        {
            **{col: [1.0, 2.0, 3.0] for col in FEATURE_COLUMNS},
            TARGET_COLUMN: [0, 1, 0],
        }
    )
    path = tmp_path / "data.csv"
    df.to_csv(path, index=False)

    loaded = load_dataframe(str(path))

    assert len(loaded) == 3
    assert loaded[TARGET_COLUMN].tolist() == [0, 1, 0]
