# symbolic chart showing importance of features
from feature_engine.outliers import Winsorizer
from feature_engine.discretisation import DecisionTreeDiscretiser


def cap_quantiles(df):
    variables = [i for i in df.columns.values.tolist()]
    w = Winsorizer(capping_method='quantiles', tail='both', fold=0.05, variables=variables).fit(df)
    df = w.transform(df)
    return df


def decision_tree_discretizer(df, scoring='r2'):
    x, y = df.iloc[:, :-1], df.iloc[:, -1]
    dt_discretizer = DecisionTreeDiscretiser(cv=12, scoring=scoring, regression=True,
                                             param_grid={'max_depth': range(1, 9, 3),
                                                         'min_samples_leaf': range(1, 13, 3)})
    dt_discretizer.fit(x, y)
    df.iloc[:, :-1] = dt_discretizer.transform(x)
    return df
