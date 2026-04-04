import pandas as pd
from geopy.distance import geodesic
from sqlalchemy import create_engine, text


# Result is "Positive", "Negative", or "Zero"


class DatabaseManager:
    def __init__(self, url=None):
        if (len(url) < 1):

            self.url = "postgresql+psycopg://myuser:mypassword@localhost:5432/mydatabase"
        else:
            self.url = url

        try:
            self.engine = create_engine(self.url)
        except Exception as e:
            print(f"An error with the database occurred; using localhost {e}")
            self.url = "postgresql+psycopg://myuser:mypassword@localhost:5432/mydatabase"
            self.engine = create_engine(self.url)  # You'll likely want to retry the connection here

    def save_data(self, df: {str: [str]}, table_name: [int], mode='append'):
        """Saves a Pandas DataFrame to the database."""
        try:
            df.to_sql(table_name, self.engine, if_exists=mode, index=False, method='multi')
            print(f"Successfully saved to {table_name}")
        except Exception as e:
            print(f"Error saving data: {e}")

    def query_to_df(self, sql_query: str):
        """Runs a SELECT query and returns a DataFrame."""
        try:
            return pd.read_sql(sql_query, self.engine)
        except Exception as e:
            print(f"Error reading data: {e}")
            return pd.DataFrame()
    # DO NOT USE

    def execute_raw(self, sql_command: str):
        """Executes raw SQL (like CREATE TABLE or DELETE) without returning data."""
        with self.engine.begin() as conn:
            conn.execute(text(sql_command))
            print("Command executed successfully.")

    def is_within_radius(self, latlon1: tuple, latlon2: tuple, radius_meters: float) -> bool:
        """
        Determines if two points are within a specific distance in meters.

        Args:
            latlon1 (tuple): (latitude, longitude)
            latlon2 (tuple): (latitude, longitude)
            radius_meters (float): The maximum allowed distance in meters.

        Returns:
            bool: True if distance <= radius_meters, False otherwise.
        """
        # Validate inputs
        if not isinstance(latlon1, tuple) or len(latlon1) != 2:
            raise ValueError(f"latlon1 must be a (lat, lon) tuple, got {latlon1}")
        if not isinstance(latlon2, tuple) or len(latlon2) != 2:
            raise ValueError(f"latlon2 must be a (lat, lon) tuple, got {latlon2}")

        if radius_meters < 0:
            raise ValueError("Radius cannot be negative.")

        # Calculate distance in meters
        # geodesic uses the WGS-84 ellipsoid (very accurate)
        distance = geodesic(latlon1, latlon2).meters

        return distance <= radius_meters


# --- Example Usage ---
if __name__ == "__main__":
    db = DatabaseManager()

    # 1. Save data
    sample_df = pd.DataFrame({'name': ['Alice', 'Bob'], 'score': [95, 88]})
    db.save_data(sample_df, 'students', mode='replace')

    # 2. Read data back
    results = db.query_to_df("SELECT * FROM students WHERE score > 90")
    print(results)
# Example usage:
    point_a = (51.5074, -0.1278)  # Latitude and longitude for London
    point_b = (48.8566, 2.3522)   # Latitude and longitude for Paris
    radius = 200  # Radius in kilometers

    if db.is_within_radius(point_a, point_b, radius):
        print("Points are within the radius.")
    else:
        print("Points are not within the radius.")


