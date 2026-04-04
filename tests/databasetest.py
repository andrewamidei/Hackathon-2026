import unittest
import os
import pandas as pd
from src.database import DatabaseManager as db


class TestYourModule(unittest.TestCase):

    def setUp(self):
        # Corrected (Lat, Lon) coordinates
        self.coordinates = [
            (40.748441, -73.985654),  # 0: NYC
            (37.7749, -122.4194),    # 1: SF
            (40.7128, -74.006),      # 2: Staten Island
            (48.8566, 2.3522),       # 3: Paris
            (51.5074, -0.1276),      # 4: London
            (-33.8568, 151.2153),    # 5: Sydney
            (35.217, 34.0522),       # 6: Haifa
            (34.0522, -118.2437),    # 7: LA
            (41.8902, 12.4964),      # 8: Rome
            (51.5074, -0.1278),      # 9: London 2
            (-33.8597, 151.2139),    # 10: Sydney 2
            (35.218, 34.0522),       # 11: Haifa 2
            (34.0513, -118.2451),    # 12: LA 2
            (41.8903, 12.4964),      # 13: Rome 2
            (40.7484, -73.9856),     # 14: NYC 2
            (37.7749, -122.4194),    # 15: SF 2
            (48.8566, 2.3522),       # 16: Paris 2
            (51.5074, -0.1276),      # 17: London 3
            (-33.8568, 151.2153),    # 18: Sydney 3
            (35.217, 34.0522)        # 19: Haifa 3
        ]
        url = os.getenv("DATABASE_URL", "postgresql+psycopg://myuser:mypassword@db:5432/mydatabase")
        self.dbm = db(url=url)

        # Clean the table before every test to ensure isolation
        self.dbm.execute_raw("DELETE FROM sessions")

    def test_radius_logic(self):
        """Tests the mathematical distance calculation."""
        # SF and NYC are thousands of km apart
        is_close = self.dbm.is_within_radius(self.coordinates[1], self.coordinates[0], 100.00)
        # These two NYC points are very close (~5 meters)
        is_very_close = self.dbm.is_within_radius(self.coordinates[0], self.coordinates[14], 100.00)

        self.assertFalse(is_close)
        self.assertTrue(is_very_close)

    def test_session_lifecycle(self):
        """Tests Save, Null Update, and Remove."""
        session_id = "test_user_123"

        # 1. Save initial location
        self.dbm.save_data((session_id, self.coordinates[0]))
        df = self.dbm.query_to_df(f"SELECT * FROM sessions WHERE session_id='{session_id}'")
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['latitude'], self.coordinates[0][0])

        # 2. Update to NULL (User hides location)
        self.dbm.save_data((session_id, None))
        df_null = self.dbm.query_to_df(f"SELECT * FROM sessions WHERE session_id='{session_id}'")
        self.assertTrue(pd.isna(df_null.iloc[0]['latitude']))

        # 3. Remove session
        self.dbm.remove_session(session_id)
        df_empty = self.dbm.query_to_df(f"SELECT * FROM sessions WHERE session_id='{session_id}'")
        self.assertTrue(df_empty.empty)

    def test_query_nearest(self):
        """Tests the N-nearest neighbor sorting logic."""
        # Insert 3 points: NYC, Staten Island (Close), and Paris (Far)
        self.dbm.save_data(("nyc", self.coordinates[0]))
        self.dbm.save_data(("staten_island", self.coordinates[2]))
        self.dbm.save_data(("paris", self.coordinates[3]))

        # Query from NYC point
        nearest = self.dbm.query_nearest(self.coordinates[0], n=2)

        self.assertEqual(len(nearest), 2)
        self.assertEqual(nearest[0], "nyc")           # Nearest is itself
        self.assertEqual(nearest[1], "staten_island")  # Second nearest
        self.assertNotIn("paris", nearest)


if __name__ == '__main__':
    unittest.main()

