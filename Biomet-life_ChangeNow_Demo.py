import streamlit as st
import requests
import folium
import time
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# --- CONFIG ---
API_KEY = "AIzaSyCBhur5E-PvIFL6jSY3PoP6UR3Ns7Qb0No" 

# --- Function to search company sites using Google Maps API ---
def search_company_sites(company_name, location=""):
    query = f"{company_name.strip()} {location.strip()}".lower()
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        'query': query,
        'region': 'gr',  # optional: 'us', 'fr', etc.
        'key': API_KEY
    }

    results = []

    while url:
        res = requests.get(url, params=params)
        data = res.json()

        # Debug output
        st.write("🔍 Raw API response:", data)

        for place in data.get("results", []):
            site = {
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                "lon": place.get("geometry", {}).get("location", {}).get("lon"),
                "types": place.get("types"),
                "status": place.get("business_status", "N/A")
            }
            if site["lat"] and site["lon"]:
                results.append(site)

        next_page_token = data.get("next_page_token")
        if next_page_token:
            time.sleep(2)  # wait for token to become valid
            params = {'pagetoken': next_page_token, 'key': API_KEY}
        else:
            break

    return results

# --- Streamlit UI ---
st.set_page_config(page_title="Company Sites via Google Maps", layout="wide")
st.title("🌍 Company Site Finder (via Google Maps API)")

company = st.text_input("Enter company name:", "Coca-Cola")
location_filter = st.text_input("Optional location (e.g., Greece):", "")

if st.button("🔍 Search"):
    if company.strip():
        with st.spinner(f"Searching Google Maps for '{company}' sites..."):
            try:
                locations = search_company_sites(company, location=location_filter)
                st.session_state["locations"] = locations
            except Exception as e:
                st.error(f"Error querying Google Maps API: {e}")
    else:
        st.warning("Please enter a company name.")

# --- Display Results ---
if "locations" in st.session_state:
    locations = st.session_state["locations"]
    if not locations:
        st.warning("⚠️ No sites found on Google Maps for that company.")
    else:
        st.success(f"✅ Found {len(locations)} site(s)")

        m = folium.Map(location=[locations[0]['lat'], locations[0]['lon']], zoom_start=5)
        marker_cluster = MarkerCluster().add_to(m)

        for site in locations:
            folium.Marker(
                location=[site['lat'], site['lon']],
                popup=f"<b>{site['name']}</b><br>{site['address']}<br>Status: {site['status']}",
                tooltip=site['name']
            ).add_to(marker_cluster)

        st.subheader("📍 Sites Map")
        st_folium(m, width=1000, height=600)


