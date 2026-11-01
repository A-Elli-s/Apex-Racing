"""Regression tests for championship-season calendar accounting."""
import unittest
from scripts.calendar_rules import championship_events, championship_round


class CalendarRulesTests(unittest.TestCase):
    def test_formula_e_season_does_not_include_next_december(self):
        events = [
            {"date": "2025-12-06", "name": "São Paulo"},
            {"date": "2026-08-16", "name": "London"},
            {"date": "2026-12-18", "name": "Jeddah", "season": "2026/27"},
        ]
        self.assertEqual(len(championship_events("Formula E", events, 2026)), 2)

    def test_nascar_exhibitions_and_duels_not_counted(self):
        events = [
            {"date": "2026-02-01", "name": "CUP — Cook Out Clash at Bowman Gray"},
            {"date": "2026-02-12", "name": "CUP — America 250 Florida Duel at DAYTONA"},
            {"date": "2026-02-12", "name": "CUP — America 250 Florida Duel at DAYTONA"},
            {"date": "2026-05-17", "name": "CUP — NASCAR All-Star Race"},
            {"date": "2026-02-15", "name": "CUP — DAYTONA 500"},
        ]
        self.assertEqual([e["name"] for e in championship_events("NASCAR Cup", events, 2026)], ["CUP — DAYTONA 500"])

    def test_dakar_2027_not_in_2026(self):
        self.assertFalse(championship_round("Dakar Rally", {"date": "2027-01-01", "season": "2027"}, 2026))

    def test_invalid_and_unrelated_year_excluded(self):
        self.assertFalse(championship_round("IMSA", {"date": "bad"}, 2026))
        self.assertFalse(championship_round("WEC", {"date": "2025-08-01"}, 2026))
        self.assertTrue(championship_round("WEC", {"date": "2026-08-01"}, 2026))


if __name__ == "__main__":
    unittest.main()
