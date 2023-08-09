# symbolic chart showing importance of features
from feature_engine.outliers import Winsorizer
from feature_engine.discretisation import DecisionTreeDiscretiser
import feature_engine.transformation as fet
from EMO.models import RECORD_COLS
from utils import Config

config = Config()

def cap_quantiles(df):
    variables = [i for i in df.columns.values.tolist()]
    fold = float(config['emo_cap_fold'])
    w = Winsorizer(capping_method='quantiles', tail='both', fold=fold, variables=variables).fit(df)
    df = w.transform(df)
    return df


def decision_tree_discretizer(df, scoring='r2'):
    x, y = df.iloc[:, :-1], df.iloc[:, -1]
    dt_discretizer = DecisionTreeDiscretiser(cv=12, scoring=scoring, regression=True,
                                             param_grid={'max_depth': range(1, 12, 2), 'min_samples_leaf': range(1, 12, 2)})
    dt_discretizer.fit(x, y)
    df.iloc[:, :-1] = dt_discretizer.transform(x)
    return df, dt_discretizer


def transformation_yeo_johnson(df, cols=RECORD_COLS):
    yj_transformation = fet.YeoJohnsonTransformer(variables=cols)
    yj_transformation.fit(df.iloc[:, :-1])
    df.iloc[:, :-1] = yj_transformation.transform(df.iloc[:, :-1])
    return df, yj_transformation

