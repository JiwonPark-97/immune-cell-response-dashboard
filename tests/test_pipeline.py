"""Regression tests for the required analysis outputs."""

import unittest

from analysis import (
    get_baseline_subset,
    get_form_answer,
    get_population_frequencies,
    get_responder_comparison,
)


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = get_population_frequencies()

    def test_population_frequency_table(self):
        self.assertEqual(len(self.summary), 52_500)
        self.assertTrue(self.summary.groupby("sample").size().eq(5).all())
        totals = self.summary.groupby("sample")["percentage"].sum()
        self.assertTrue(((totals - 100).abs() < 1e-9).all())

    def test_responder_analysis(self):
        subject_frequencies, statistics = get_responder_comparison(self.summary)
        self.assertEqual(len(subject_frequencies), 3_280)
        self.assertEqual(len(statistics), 5)
        self.assertFalse(statistics["significant"].any())

    def test_baseline_subset(self):
        subset, counts = get_baseline_subset()
        self.assertEqual(len(subset), 656)
        observed = {
            (row.breakdown, row.group): row.count
            for row in counts.itertuples(index=False)
        }
        self.assertEqual(observed[("project", "prj1")], 384)
        self.assertEqual(observed[("project", "prj3")], 272)
        self.assertEqual(observed[("response", "yes")], 331)
        self.assertEqual(observed[("response", "no")], 325)
        self.assertEqual(observed[("sex", "F")], 312)
        self.assertEqual(observed[("sex", "M")], 344)

    def test_form_calculation(self):
        average, sample_count = get_form_answer()
        self.assertEqual(sample_count, 485)
        self.assertAlmostEqual(average, 10_206.15, places=2)


if __name__ == "__main__":
    unittest.main()
