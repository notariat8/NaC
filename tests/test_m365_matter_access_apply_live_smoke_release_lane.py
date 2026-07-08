from __future__ import annotations

import unittest

from scripts import validate_m365_matter_access_apply_live_smoke_release_lane as validator


class M365MatterAccessApplyLiveSmokeReleaseLaneTests(unittest.TestCase):
    def test_release_lane_validator_passes(self) -> None:
        self.assertEqual([], validator.validate())


if __name__ == "__main__":
    unittest.main()
