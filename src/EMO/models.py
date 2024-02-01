import pandas as pd
import numpy as np
import os
import logging
from collections import namedtuple
from random import randint
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn import linear_model, svm, ensemble
import joblib
from sklearn.metrics import (
    explained_variance_score,
    mean_absolute_error,
    mean_tweedie_deviance,
)
from math import exp
from utils import Config
from DBAC.api import DbOperator

log = logging.getLogger("EFC")


MODEL_APPROACHES = (
    "Universal",
    "Language-Specific",
)

RECORD_COLS = [
    "TOTAL",
    "PREV_WPM",
    "TIMEDELTA_SINCE_CREATION",
    "TIMEDELTA_LAST_REV",
    "CUM_CNT_REVS",
    "PREV_SCORE",
]


m_eval = namedtuple(
    "ModelEvaluation",
    (
        "Explained_Variance",
        "Mean_Absolute_Error",
        "Mean_Tweedie_Deviance",
        "Test_Data",
        "Preds",
    ),
)


class Model:
    def __init__(self, model_name, model, approach, lng_cols: tuple, **kwargs):
        self.name = model_name
        self.model = model
        self.anc = kwargs
        self.approach = approach
        self.rec_cols = RECORD_COLS.copy()
        if self.approach == MODEL_APPROACHES[1]:
            self.__language_specific_model = True
            self.lng_cols = lng_cols
            self.rec_cols.extend(self.lng_cols)
        else:
            self.__language_specific_model = False
            self.lng_cols = tuple()
        self.discretizer = kwargs.get("discretizer")
        self.__predict = {
            "SVR": self._predict_svr,
            "LAS": self._predict_las,
            "RFR": self._predict_rfr,
            "CST": Model._predict_cst,
        }[model_name]

    def predict(self, records: list[list], lng: str = "") -> list[list]:
        if self.__language_specific_model:
            enc_lngs = [int(l == lng) for l in self.lng_cols]
            records = [r + enc_lngs for r in records]
        return self.__predict(records)

    def _predict_svr(self, records: list[list]):
        if self.discretizer:
            records = self.discretizer.transform(
                pd.DataFrame(data=records, columns=self.rec_cols)
            ).values
        return self.anc["scy_svr"].inverse_transform(
            self.model.predict(
                np.array(self.anc["scx_svr"].transform(records))
            ).reshape(-1, 1)
        )

    def _predict_las(self, records: list[list]):
        if self.discretizer:
            records = self.discretizer.transform(
                pd.DataFrame(data=records, columns=self.rec_cols)
            ).values
        return [self.model.predict([p]) for p in records]

    def _predict_rfr(self, records: list[list]):
        if self.discretizer:
            records = self.discretizer.transform(
                pd.DataFrame(data=records, columns=self.rec_cols)
            )
        return self.model.predict(np.array(records)).reshape(-1, 1)

    @staticmethod
    def _predict_cst(record: list[list]):
        preds = list()
        for r in record:
            (
                total,
                prev_wpm,
                ts_creation,
                ts_last_rev,
                repeated_times,
                prev_score,
                *_,
            ) = r
            x1, x2, x3, x4 = 2.039, -4.566, -12.495, -0.001
            s = (repeated_times**x1 + 0.01 * prev_score * x2) - (x3 * exp(total * x4))
            preds.append([100 * exp(-ts_last_rev / (24 * s))])
        return preds


class Models:
    def __init__(self):
        self.config = Config()
        self.size_test = 0.2
        self.random_state = randint(0, 2137)
        self.models = dict()
        self.evaluation = dict()

    def prep_SVR(self, data: pd.DataFrame):
        x, y = data.iloc[:, :-1], data.iloc[:, -1:]
        x_train_svr, self.x_test_svr, y_train_svr, self.y_test_svr = train_test_split(
            x.values, y.values, test_size=self.size_test, random_state=self.random_state
        )
        self.scx_svr = StandardScaler()
        self.scy_svr = StandardScaler()
        x_train_svr = self.scx_svr.fit_transform(x_train_svr)
        y_train_svr = self.scy_svr.fit_transform(y_train_svr)
        svr_model = svm.SVR(kernel="rbf")
        svr_model.fit(x_train_svr, y_train_svr.ravel())
        self.y_test_svr = np.array(self.y_test_svr).reshape(-1, 1)
        self.models["SVR"] = svr_model

    def eval_SVR(self):
        transformed_xs = self.scx_svr.transform(self.x_test_svr)
        predictions = self.scy_svr.inverse_transform(
            self.models["SVR"].predict(np.array(transformed_xs)).reshape(-1, 1)
        )
        self.evaluation["SVR"] = m_eval(
            explained_variance_score(self.y_test_svr, predictions),
            mean_absolute_error(self.y_test_svr, predictions),
            mean_tweedie_deviance(self.y_test_svr, predictions),
            self.y_test_svr,
            predictions,
        )

    def prep_LASSO(self, data: pd.DataFrame):
        x, y = data.iloc[:, :-1], data.iloc[:, -1:]
        x_train_las, self.x_test_las, y_train_las, self.y_test_las = train_test_split(
            x.values, y.values, test_size=self.size_test, random_state=self.random_state
        )
        lasso_model = linear_model.Lasso(alpha=0.1)
        lasso_model.fit(x_train_las, y_train_las)
        self.y_test_las = np.array(self.y_test_las).reshape(-1, 1)
        self.x_test_las = np.array(self.x_test_las)
        self.models["LAS"] = lasso_model

    def eval_LASSO(self):
        predictions = [
            self.models["LAS"].predict(pd.DataFrame(data=p).transpose())
            for p in self.x_test_las
        ]
        self.evaluation["LAS"] = m_eval(
            explained_variance_score(self.y_test_las, predictions),
            mean_absolute_error(self.y_test_las, predictions),
            mean_tweedie_deviance(self.y_test_las, predictions),
            self.y_test_las,
            predictions,
        )

    def prep_RFR(self, data: pd.DataFrame):
        x, y = data.iloc[:, :-1], data.iloc[:, -1:]
        x_train_rfr, self.x_test_rfr, y_train_rfr, self.y_test_rfr = train_test_split(
            x.values, y.values, test_size=self.size_test, random_state=self.random_state
        )
        regressor_rfr = ensemble.RandomForestRegressor(
            n_estimators=12, random_state=42, max_depth=8, min_samples_leaf=3
        )
        regressor_rfr.fit(x_train_rfr, y_train_rfr.ravel())
        self.y_test_rfr = np.array(self.y_test_rfr).reshape(-1, 1)
        self.models["RFR"] = regressor_rfr

    def eval_RFR(self):
        predictions = (
            self.models["RFR"].predict(np.array(self.x_test_rfr)).reshape(-1, 1)
        )
        self.evaluation["RFR"] = m_eval(
            explained_variance_score(self.y_test_rfr, predictions),
            mean_absolute_error(self.y_test_rfr, predictions),
            mean_tweedie_deviance(self.y_test_rfr, predictions),
            self.y_test_rfr,
            predictions,
        )

    def prep_CST(self, data: pd.DataFrame):
        x, y = data.iloc[:, :-1], data.iloc[:, -1:]
        _, self.x_test_cst, _, self.y_test_cst = train_test_split(
            x.values, y.values, test_size=self.size_test, random_state=self.random_state
        )
        self.models["CST"] = Model._predict_cst

    def eval_CST(self):
        predictions = Model._predict_cst(self.x_test_cst)
        self.evaluation["CST"] = m_eval(
            explained_variance_score(self.y_test_cst, predictions),
            mean_absolute_error(self.y_test_cst, predictions),
            mean_tweedie_deviance(self.y_test_cst, predictions),
            np.array(self.y_test_cst).reshape(-1, 1),
            predictions,
        )

    def save_model(self, model_name: str, lng_cols: tuple, approach: str, **kwargs):
        """Use first-class function to save selected model to a file"""
        if model_name == "SVR":
            model = Model(
                model_name,
                self.models["SVR"],
                approach=approach,
                lng_cols=lng_cols,
                scx_svr=self.scx_svr,
                scy_svr=self.scy_svr,
                **kwargs,
            )
        elif model_name in {"LAS", "RFR", "CST"}:
            model = Model(
                model_name,
                self.models[model_name],
                approach=approach,
                lng_cols=lng_cols,
                **kwargs,
            )
        else:
            return False

        joblib.dump(model, os.path.join(DbOperator().RES_PATH, f"model.pkl"))
        log.debug(
            f"Created a new {approach} {model_name} model for Languages {lng_cols}"
        )
        return True
