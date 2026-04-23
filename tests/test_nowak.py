import numpy as np
import pytest

from parasolpy.nowak import choose_analog_index, sim_single_year, sim_multi_trace


RNG = np.random.default_rng(42)


def _make_observed(n=20):
    rng = np.random.default_rng(0)
    Z = rng.uniform(50, 150, n)
    p = rng.dirichlet(np.ones(12), size=n)  # 12 monthly proportions per year
    years = np.arange(2000, 2000 + n)
    return Z, p, years


class TestChooseAnalogIndex:
    def test_returns_valid_index(self):
        Z, _, _ = _make_observed(20)
        idx = choose_analog_index(RNG, Z, sim_Z=Z.mean())
        assert 0 <= idx < len(Z)

    def test_returns_int(self):
        Z, _, _ = _make_observed(10)
        idx = choose_analog_index(RNG, Z, sim_Z=Z[0])
        assert isinstance(idx, int)

    def test_exact_match_biases_toward_nearest(self):
        # When sim_Z equals Z[3], index 3 should be most probable
        rng = np.random.default_rng(99)
        Z = np.array([10.0, 20.0, 30.0, 100.0, 110.0, 120.0])
        counts = {}
        for _ in range(500):
            idx = choose_analog_index(rng, Z, sim_Z=100.0)
            counts[idx] = counts.get(idx, 0) + 1
        # Index 3 (Z=100) should appear most often
        assert max(counts, key=counts.get) == 3


class TestSimSingleYear:
    def test_output_length_equals_num_periods(self):
        Z, p, years = _make_observed(20)
        result = sim_single_year(RNG, Z, p, years, sim_Z=Z.mean())
        assert len(result) == 12

    def test_output_sums_to_sim_Z(self):
        Z, p, years = _make_observed(20)
        sim_Z = 80.0
        result = sim_single_year(RNG, Z, p, years, sim_Z=sim_Z)
        assert np.sum(result) == pytest.approx(sim_Z, rel=1e-9)

    def test_non_negative_output(self):
        Z, p, years = _make_observed(20)
        result = sim_single_year(RNG, Z, p, years, sim_Z=Z.mean())
        assert np.all(result >= 0)


class TestSimMultiTrace:
    def test_output_shape(self):
        Z, p, years = _make_observed(20)
        num_seq, num_years, repl = 3, 5, 2
        rng = np.random.default_rng(7)
        sim_Z = rng.uniform(50, 150, (num_seq, num_years))
        result = sim_multi_trace(RNG, Z, p, years, sim_Z, repl=repl)
        assert result.shape == (12 * num_years, num_seq * repl)

    def test_single_sequence_no_repl(self):
        Z, p, years = _make_observed(10)
        sim_Z = np.array([[80.0, 90.0, 70.0]])
        result = sim_multi_trace(RNG, Z, p, years, sim_Z, repl=1)
        assert result.shape == (36, 1)
