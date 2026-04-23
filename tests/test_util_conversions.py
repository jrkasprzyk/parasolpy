import numpy as np
import pandas as pd
import pytest

from parasolpy.util import (
    convert_cfs_to_af,
    convert_cfs_to_cms,
    convert_cms_to_mcm,
)

# Known conversion factors
_CFS_TO_AF = 1.98347
_CFS_TO_CMS = 0.028316831998814504
_CMS_TO_MCM = 24 * 60 * 60 / 1e6


class TestConvertCfsToAf:
    def test_scalar(self):
        assert convert_cfs_to_af(1.0) == pytest.approx(_CFS_TO_AF)

    def test_zero(self):
        assert convert_cfs_to_af(0.0) == 0.0

    def test_list(self):
        result = convert_cfs_to_af([1.0, 2.0])
        assert result == pytest.approx([_CFS_TO_AF, 2 * _CFS_TO_AF])

    def test_numpy_array(self):
        arr = np.array([1.0, 2.0])
        result = convert_cfs_to_af(arr)
        np.testing.assert_allclose(result, arr * _CFS_TO_AF)

    def test_pandas_series(self):
        s = pd.Series([1.0, 3.0])
        result = convert_cfs_to_af(s)
        pd.testing.assert_series_equal(result, s * _CFS_TO_AF)

    def test_rejects_bool(self):
        with pytest.raises(TypeError):
            convert_cfs_to_af(True)

    def test_rejects_string(self):
        with pytest.raises(TypeError):
            convert_cfs_to_af("1.0")


class TestConvertCfsToCms:
    def test_scalar(self):
        assert convert_cfs_to_cms(1.0) == pytest.approx(_CFS_TO_CMS)

    def test_list(self):
        result = convert_cfs_to_cms([1.0])
        assert result == pytest.approx([_CFS_TO_CMS])


class TestConvertCmsToMcm:
    def test_scalar(self):
        assert convert_cms_to_mcm(1.0) == pytest.approx(_CMS_TO_MCM)

    def test_numpy_array(self):
        arr = np.array([1.0, 2.0])
        result = convert_cms_to_mcm(arr)
        np.testing.assert_allclose(result, arr * _CMS_TO_MCM)
