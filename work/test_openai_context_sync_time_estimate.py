import unittest

from app.context_sync.jobs.progress import estimate_remaining_seconds


class OpenAIContextSyncTimeEstimateTests(unittest.TestCase):
    def test_estimate_uses_observed_item_and_file_throughput(self):
        estimate = estimate_remaining_seconds(
            processed_items=25,
            total_items=125,
            elapsed_seconds=10,
            recent_throughput=5,
            remaining_file_bytes=2_000,
            average_file_bytes_per_second=100,
        )
        self.assertEqual(20, estimate)

    def test_estimate_is_unknown_without_observed_work(self):
        self.assertIsNone(estimate_remaining_seconds(0, 100, 0, 0, 0, 0))
        self.assertIsNone(estimate_remaining_seconds(10, 100, 2, 5, 1000, 0))

    def test_estimate_finishes_at_zero(self):
        self.assertEqual(0, estimate_remaining_seconds(10, 10, 2, 5, 0, 0))


if __name__ == "__main__":
    unittest.main()

