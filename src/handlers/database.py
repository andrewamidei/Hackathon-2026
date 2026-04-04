import pandas as pd
from geopy.distance import geodesic
from sqlalchemy import create_engine, text
from typing import Optional, Tuple, Union

# Result is "Positive", "Negative", or "Zero"


class DatabaseManager:
    def __init__(self, url=None):
        if (url is None):
            self.url = "postgresql+psycopg://myuser:mypassword@localhost:5432/mydatabase"
        else:
            self.url = url
        try:
            self.engine = create_engine(self.url)
            self.execute_raw("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION
            );
        """)

        except Exception as e:
            print(f"An error with the database occurred; using localhost {e}")
            self.url = "postgresql+psycopg://myuser:mypassword@localhost:5432/mydatabase"
            self.engine = create_engine(self.url)  # You'll likely want to retry the connection here

    def add_host(self, entry: Tuple[str, Optional[Tuple[float, float]]], table_name: str = "sessions"):
        """
        Saves or updates a session.
        entry example: ("session_123", (40.7, -74.0)) or ("session_123", None)
        """
        session_id, coords = entry

        # Unpack coordinates if they exist, otherwise set to None (SQL NULL)
        lat = coords[0] if coords else None
        lon = coords[1] if coords else None

        # The dictionary keys must match the :placeholders in the SQL string
        data = {
            "session_id": session_id,
            "latitude": lat,
            "longitude": lon
        }

        # PostgreSQL 'UPSERT' logic:
        # INSERT the row; if 'session_id' exists, UPDATE the latitude/longitude.
        sql = text(f"""
            INSERT INTO {table_name} (session_id, latitude, longitude)
            VALUES (:session_id, :latitude, :longitude)
            ON CONFLICT (session_id)
            DO UPDATE SET
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude;
        """)

        try:
            with self.engine.begin() as conn:
                conn.execute(sql, data)
            print(f"Successfully updated session: {session_id}")
        except Exception as e:
            print(f"Error saving session data to {table_name}: {e}")

    def query_to_df(self, sql_query: str):
        """Runs a SELECT query and returns a DataFrame using an explicit connection."""
        try:
            # 'connect()' creates a context manager that closes the connection automatically
            with self.engine.connect() as conn:
                return pd.read_sql(sql_query, conn)
        except Exception as e:
            print(f"Error reading data: {e}")
            return pd.DataFrame()

    def query_nearest(self, location: tuple[float, float], n: int = 5) -> list[str]:
        """
        Queries the database for all sessions, calculates their distance to
        the provided location, and returns the top N nearest session IDs.
        """
        # 1. Fetch all sessions that actually have a location (skip NULLs)
        query = "SELECT session_id, latitude, longitude FROM sessions WHERE latitude IS NOT NULL"
        df = self.query_to_df(query)

        if df.empty:
            return []

        # 2. Calculate distance for every row
        # We use a lambda to apply your existing geodesic logic
        def get_distance(row):
            session_coords = (row['latitude'], row['longitude'])
            # We use the raw geodesic().meters here to get the actual value for sorting
            return geodesic(location, session_coords).meters

        df['distance'] = df.apply(get_distance, axis=1)

        # 3. Sort by distance (ascending) and take the top N
        nearest_df = df.sort_values(by='distance').head(n)

        # 4. Return just the list of session IDs
        return nearest_df['session_id'].tolist()

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

    # ... (init and other methods)

    def remove_session(self, session_id: str):
        """
        Deletes a session from the database and then closes the connection pool.
        """
        sql = text("DELETE FROM sessions WHERE session_id = :session_id")

        try:

            # Use 'begin' to handle the transaction for the delete
            with self.engine.begin() as conn:
                result = conn.execute(sql, {"session_id": session_id})
                self.close_connection()
                if result.rowcount > 0:
                    print(f"Successfully removed session: {session_id}")
                else:
                    print(f"No session found with ID: {session_id}")

            # Call the closing logic immediately after the transaction finishes

        except Exception as e:
            print(f"Error during remove_session for {session_id}: {e}")
            # Still attempt to close if an error occurs to prevent hanging connections

    def close_connection(self):
        """
        Disposes of the engine and clears the connection pool.
        """
        try:
            self.engine.dispose()
            print("Database connection pool disposed.")
        except Exception as e:
            print(f"Error disposing engine: {e}")


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


