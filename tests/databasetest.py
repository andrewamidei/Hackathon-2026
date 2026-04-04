# tests/test_your_module.py
import unittest
from src.database import DatabaseManager as db
import os


class TestYourModule(unittest.TestCase):

    def setUp(self):
        self.coordinates = [
            (-73.985654, 40.748441),  # New York City
            (-122.4194, 37.7749),   # San Francisco
            (-74.006, 40.7128),    # Staten Island
            (2.3522, 48.8566),     # Paris
            (-0.1276, 51.5074),    # London
            (151.2153, -33.8568),  # Sydney
            (34.0522, 35.217),     # Haifa
            (-118.2437, 34.0522),  # Los Angeles
            (12.4964, 41.8902),    # Rome
            (-0.1278, 51.5074),    # London again
            (151.2139, -33.8597),  # Sydney again
            (34.0522, 35.218),     # Haifa again
            (-118.2451, 34.0513),  # Los Angeles again
            (12.4964, 41.8903),    # Rome again
            (-73.9856, 40.7484),   # New York City another point
            (-122.4194, 37.7749),  # San Francisco another point
            (2.3522, 48.8566),     # Paris another point
            (-0.1276, 51.5074),    # London another point
            (151.2153, -33.8568),  # Sydney another point
            (34.0522, 35.217)      # Haifa another point
        ]
        url = os.getenv("DATABASE_URL", "postgresql+psycopg://myuser:mypassword@db:5432/mydatabase")
        self.dbm = db(url=url)
        pass

    def test_method1(self):
        test: bool = self.dbm.is_within_radius(self.coordinates[1], self.coordinates[0], 100.00)

        test2: bool = self.dbm.is_within_radius(self.coordinates[0], self.coordinates[12], 100.00)
        self.assertEqual(test, False)
        self.assertEqual(test2, True)

