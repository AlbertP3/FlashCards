# symbolic chart showing importance of features
import pandas as pd
from feature_engine.outliers import Winsorizer
from feature_engine.discretisation import DecisionTreeDiscretiser
import feature_engine.transformation as fet
from EMO.models import RECORD_COLS
from cfg import config


def cap_quantiles(df: pd.DataFrame):
    df = df.astype({k: "float" for k in RECORD_COLS}, copy=True)
    w = Winsorizer(
        capping_method="quantiles",
        tail="both",
        fold=config["EMO"]["cap_fold"],
        variables=RECORD_COLS,
    ).fit(df)
    df = w.transform(df)
    return df


def decision_tree_discretizer(
    df, scoring="r2", cols=RECORD_COLS
) -> tuple[pd.DataFrame, DecisionTreeDiscretiser]:
    x, y = df.iloc[:, :-1], df.iloc[:, -1]
    dt_discretizer = DecisionTreeDiscretiser(
        cv=12,
        scoring=scoring,
        regression=True,
        param_grid={"max_depth": range(1, 12, 2), "min_samples_leaf": range(1, 12, 2)},
        variables=cols,
    )
    dt_discretizer.fit(x, y)
    df.iloc[:, :-1] = dt_discretizer.transform(x)
    return df, dt_discretizer


def transformation_yeo_johnson(
    df, cols=RECORD_COLS
) -> tuple[pd.DataFrame, fet.YeoJohnsonTransformer]:
    yj_transformation = fet.YeoJohnsonTransformer(variables=cols)
    yj_transformation.fit(df.iloc[:, :-1])
    df.iloc[:, :-1] = yj_transformation.transform(df.iloc[:, :-1])
    return df, yj_transformation
