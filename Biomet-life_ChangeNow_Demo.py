import streamlit as st
import requests
import folium
import time
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

API_KEY = "AIzaSyCBhur5E-PvIFL6jSY3PoP6UR3Ns7Qb0No"  # Replace with your actual Google Maps API key

# --- Helper function ---
def search_company_sites(company_name, location=""):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        'query': f"{company_name} {location}",
        'key': API_KEY
    }

    results = []
    while url:
        res = requests.get(url, params=params)
        data = res.json()

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
            time.sleep(2)
            params = {'pagetoken': next_page_token, 'key': API_KEY}
        else:
            break

    return results

# --- Streamlit UI ---
st.set_page_config(page_title="Company Sites via Google Maps", layout="wide")
st.title("🌍 Company Site Finder (via Google Maps API)")

company = st.text_input("Enter company name:", "Coca-Cola")
location_filter = st.text_input("Optional location (e.g., Greece):", "")

if company:
    with st.spinner(f"Searching Google Maps for '{company}' sites..."):
        try:
            locations = search_company_sites(company, location=location_filter)

            if not locations:
                st.warning("No sites found on Google Maps for that company.")
            else:
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

        except Exception as e:
            st.error(f"Error querying Google Maps API: {e}")


