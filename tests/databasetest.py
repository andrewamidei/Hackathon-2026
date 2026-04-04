# tests/test_your_module.py
import unittest
from src.database import DatabaseManager as db
import os


class TestYourModule(unittest.TestCase):

    def setUp(self):
        self.coordinates = [
            (40.748441, -73.985654),  # New York City
            (37.7749, -122.4194),    # San Francisco
            (40.7128, -74.006),      # Staten Island
            (48.8566, 2.3522),       # Paris
            (51.5074, -0.1276),      # London
            (-33.8568, 151.2153),    # Sydney
            (35.217, 34.0522),       # Haifa
            (34.0522, -118.2437),    # Los Angeles
            (41.8902, 12.4964),      # Rome
            (51.5074, -0.1278),      # London again
            (-33.8597, 151.2139),    # Sydney again
            (35.218, 34.0522),       # Haifa again
            (34.0513, -118.2451),    # Los Angeles again
            (41.8903, 12.4964),      # Rome again
            (40.7484, -73.9856),     # New York City another point
            (37.7749, -122.4194),    # San Francisco another point
            (48.8566, 2.3522),       # Paris another point
            (51.5074, -0.1276),      # London another point
            (-33.8568, 151.2153),    # Sydney another point
            (35.217, 34.0522)        # Haifa another point
        ]
        url = os.getenv("DATABASE_URL", "postgresql+psycopg://myuser:mypassword@db:5432/mydatabase")
        self.dbm = db(url=url)
        pass

    def test_method1(self):
        test: bool = self.dbm.is_within_radius(self.coordinates[1], self.coordinates[0], 100.00)
        test2: bool = self.dbm.is_within_radius(self.coordinates[0], self.coordinates[14], 100.00)
        self.assertEqual(test, False)
        self.assertEqual(test2, True)

    def test_method2(self):


