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

    def is_within_radius(self, latlon1, latlon2, radius: float):
        """
        Check if two latitude-longitude points are within a specified radius of each other.
        Args:
        latlon1 (tuple): Latitude and longitude as a tuple, e.g., (latitude1, longitude1)
        latlon2 (tuple): Latitude and longitude as a tuple, e.g., (latitude2, longitude2)
        radius (float): Radius in kilometers

        Returns:
        bool: True if the points are within the radius, False otherwise
        """
        # Ensure inputs are valid latitude-longitude tuples
        if not isinstance(latlon1, tuple) or len(latlon1) != 2:
            raise ValueError("Invalid latitude-longitude tuple for latlon1")
        if not isinstance(latlon2, tuple) or len(latlon2) != 2:
            raise ValueError("Invalid latitude-longitude tuple for latlon2")

        # Calculate the distance between the two points using the Haversine formula
        distance = geodesic(latlon1, latlon2).meters

        # Return True if the distance is within the radius, False otherwise
        return distance <= radius


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


