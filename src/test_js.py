import streamlit as st
from streamlit_geolocation import streamlit_geolocation

st.title("Geolocation test")

location = streamlit_geolocation()
if location and location.get("latitude"):
    st.write(f"Latitude: {location['latitude']}, Longitude: {location['longitude']}")
