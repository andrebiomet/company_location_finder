import streamlit as st
import requests
import folium
import time
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# Install pycountry if not already installed
try:
    import pycountry
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "pycountry"])
    import pycountry

API_KEY = "AIzaSyCBhur5E-PvIFL6jSY3PoP6UR3Ns7Qb0No"  # Replace with your key

# Dynamically fetch list of all countries
ALL_COUNTRIES = [country.name for country in pycountry.countries]

def search_company_sites(company_name, location=""):
    """Search company locations using Google Places API."""
    all_results = []

    search_targets = [location.strip()] if location.strip() else ALL_COUNTRIES

    for loc in search_targets:
        query = f"{company_name} in {loc}"
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {'query': query, 'key': API_KEY}

        while url:
            res = requests.get(url, params=params)
            data = res.json()

            for place in data.get("results", []):
                loc_data = place.get("geometry", {}).get("location")
                if loc_data:
                    site = {
                        "name": place.get("name"),
                        "address": place.get("formatted_address"),
                        "location": loc_data,
                        "types": place.get("types"),
                        "business_status": place.get("business_status")
                    }
                    all_results.append(site)

            next_page_token = data.get("next_page_token")
            if next_page_token:
                time.sleep(2)
                url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
                params = {'pagetoken': next_page_token, 'key': API_KEY}
            else:
                break

        time.sleep(1.5)  # avoid hitting rate limits

    # Deduplicate by name + address
    unique_results = {(s['name'], s['address']): s for s in all_results}
    return list(unique_results.values())

# --- Streamlit UI ---
st.set_page_config(page_title="Global Company Site Finder", layout="wide")
st.title("🌍 Company Site Finder (Worldwide via Google Maps API)")

company = st.text_input("Enter company name:", "Coca-Cola")
location = st.text_input("Optional location (e.g., France):", "")

if st.button("🔍 Search"):
    if company.strip():
        with st.spinner("Searching... (this may take a few minutes globally)"):
            try:
                sites = search_company_sites(company, location)
                st.session_state["sites"] = sites
            except Exception as e:
                st.error(f"API error: {e}")
    else:
        st.warning("Please enter a company name.")

# --- Map ---
if "sites" in st.session_state:
    sites = st.session_state["sites"]

    if not sites:
        st.warning("No sites found.")
    else:
        # Determine map center
        first_valid = next((s for s in sites if s["location"]), None)
        if first_valid:
            start_coords = [first_valid["location"]["lat"], first_valid["location"]["lng"]]
        else:
            start_coords = [48.8566, 2.3522]  # fallback to Paris

        m = folium.Map(location=start_coords, zoom_start=2)
        marker_cluster = MarkerCluster().add_to(m)

        for site in sites:
            loc = site["location"]
            folium.Marker(
                location=[loc["lat"], loc["lng"]],
                popup=folium.Popup(f"{site['name']}<br>{site['address']}<br>Status: {site['business_status']}", max_width=250),
                tooltip=site["name"],
                icon=folium.Icon(icon="info-sign")
            ).add_to(marker_cluster)

        st.subheader("📍 Map of Company Sites")
        st_folium(m, width=1000, height=600)





