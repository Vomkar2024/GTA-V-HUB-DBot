from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from gta_hub.database import Database


class DatabaseIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_hub.sqlite3"
        self.db = Database(self.db_path)
        await self.db.initialize()

    async def asyncTearDown(self) -> None:
        await self.db.close()
        self.temp_dir.cleanup()

    async def test_garage_lifecycle(self) -> None:
        user_id = 99901
        await self.db.add_garage(user_id, "Krieger")
        await self.db.add_garage(user_id, "Emerus")

        garage = await self.db.get_garage(user_id)
        self.assertEqual(len(garage), 2)
        names = [row[0] for row in garage]
        self.assertIn("Krieger", names)
        self.assertIn("Emerus", names)

        removed = await self.db.remove_garage(user_id, "krieger")
        self.assertTrue(removed)

        garage_after = await self.db.get_garage(user_id)
        self.assertEqual(len(garage_after), 1)
        self.assertEqual(garage_after[0][0], "Emerus")

        removed_again = await self.db.remove_garage(user_id, "krieger")
        self.assertFalse(removed_again)

    async def test_profile_lifecycle(self) -> None:
        user_id = 99902
        none_profile = await self.db.get_profile(user_id)
        self.assertIsNone(none_profile)

        await self.db.set_profile(user_id, "RacerX", "PC")
        profile = await self.db.get_profile(user_id)
        self.assertIsNotNone(profile)
        self.assertEqual(profile, ("RacerX", "PC"))

        # Update profile
        await self.db.set_profile(user_id, "RacerX_PlayStation", "PlayStation")
        updated = await self.db.get_profile(user_id)
        self.assertEqual(updated, ("RacerX_PlayStation", "PlayStation"))

    async def test_claim_daily_and_leaderboard(self) -> None:
        user1 = 1001
        user2 = 1002

        # Link profiles
        await self.db.set_profile(user1, "PlayerOne", "PC")
        await self.db.set_profile(user2, "PlayerTwo", "Xbox")

        # Claim daily
        res1 = await self.db.claim_daily(user1)
        self.assertTrue(res1["claimed"])
        self.assertGreaterEqual(res1["reward"], 100)

        res2 = await self.db.claim_daily(user2)
        self.assertTrue(res2["claimed"])

        # Second claim on same day is rejected
        res1_dup = await self.db.claim_daily(user1)
        self.assertFalse(res1_dup["claimed"])
        self.assertGreaterEqual(res1_dup["hours_left"], 1)

        # Leaderboard check
        board = await self.db.get_leaderboard("credits", limit=5)
        self.assertEqual(len(board), 2)
        self.assertEqual(board[0]["discord_user_id"], str(user1) if board[0]["total_credits"] >= board[1]["total_credits"] else str(user2))
        self.assertIn(board[0]["rockstar_name"], ["PlayerOne", "PlayerTwo"])

        stats1 = await self.db.get_community_stats(user1)
        self.assertIsNotNone(stats1)
        self.assertEqual(stats1["streak"], 1)
        self.assertEqual(stats1["claim_count"], 1)


if __name__ == "__main__":
    unittest.main()
