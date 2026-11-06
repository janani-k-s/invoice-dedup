from django.test import TestCase

# Create your tests here.

from datetime import date

from django.test import SimpleTestCase

from .matching import calculate_similarity, get_status_from_score


class InvoiceMatchingTests(SimpleTestCase):

    def test_same_invoice_details_and_date(self):
        score = calculate_similarity(
            "INV-100", "INV-100",
            1000, 1000,
            "ABC Traders", "ABC Traders",
            date(2026, 10, 1), date(2026, 10, 1),
        )
        self.assertEqual(score, 100)
        self.assertEqual(get_status_from_score(score), "duplicate")

    def test_different_dates_need_review(self):
        score = calculate_similarity(
            "INV-100", "INV-100",
            1000, 1000,
            "ABC Traders", "ABC Traders",
            date(2026, 10, 1), date(2026, 10, 2),
        )
        self.assertLess(score, 95)
        self.assertEqual(get_status_from_score(score), "review")

    def test_different_vendors_are_unrelated(self):
        score = calculate_similarity(
            "INV-100", "INV-100",
            1000, 1000,
            "ABC Traders", "XYZ Supplies",
            date(2026, 10, 1), date(2026, 10, 1),
        )
        self.assertEqual(score, 0)
        self.assertEqual(get_status_from_score(score), "new")

    def test_missing_date_needs_review(self):
        score = calculate_similarity(
            "INV-100", "INV-100",
            1000, 1000,
            "ABC Traders", "ABC Traders",
            None, date(2026, 10, 1),
        )
        self.assertLess(score, 95)
        self.assertEqual(get_status_from_score(score), "review")

    def test_missing_vendor_cannot_be_auto_duplicate(self):
        score = calculate_similarity(
            "INV-100", "INV-100",
            1000, 1000,
            "", "ABC Traders",
            date(2026, 10, 1), date(2026, 10, 1),
        )
        self.assertLess(score, 95)
        self.assertEqual(get_status_from_score(score), "review")
