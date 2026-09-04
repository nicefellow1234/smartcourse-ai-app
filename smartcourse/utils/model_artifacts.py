from __future__ import annotations

import os
from typing import Any

import joblib
import numpy as np
from joblib.numpy_pickle import NumpyUnpickler
from pandas.core.arrays.string_ import StringArray


class _CompatibleStringArray(StringArray):
    """Read Python-backed StringArrays written by newer pandas versions."""

    def __setstate__(self, state: Any) -> None:
        # pandas 3.x stores this as (StringDtype, object ndarray), while
        # pandas 2.x raises NotImplementedError for that state. The model
        # loaders only need the legacy DataFrame long enough to extract rows.
        if isinstance(state, tuple) and len(state) == 2:
            self.__init__(np.asarray(state[1], dtype=object))
            return
        super().__setstate__(state)


class _CompatibleNumpyUnpickler(NumpyUnpickler):
    def find_class(self, module: str, name: str) -> Any:
        if name == "StringArray" and module in {
            "pandas.arrays",
            "pandas.core.arrays.string_",
        }:
            return _CompatibleStringArray
        return super().find_class(module, name)


def load_joblib(path: str) -> Any:
    """Load an artifact, with a fallback for cross-pandas legacy pickles."""
    try:
        return joblib.load(path)
    except NotImplementedError as original_error:
        # Some older artifacts embed a pandas DataFrame using a state format
        # that pandas 2.x cannot read after it was written by pandas 3.x.
        # The custom unpickler preserves the model components while adapting
        # only the StringArray class used by that embedded DataFrame.
        try:
            with open(path, "rb") as handle:
                return _CompatibleNumpyUnpickler(
                    os.path.abspath(path), handle, True
                ).load()
        except Exception:
            raise original_error
