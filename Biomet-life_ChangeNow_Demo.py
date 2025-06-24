import streamlit as st
import requests
import folium
import time
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

API_KEY = 'AIzaSyCBhur5E-PvIFL6jSY3PoP6UR3Ns7Qb0No'  # Replace with your actual Google Maps API key

def search_company_sites(company_name, location="Greece"):
    """Search for company locations using Google Places API."""
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        'query': company_name + " in " + location,
        'key': API_KEY
    }

    results = []
    while url:
        res = requests.get(url, params=params)
        data = res.json()
        st.write("📦 API Response:", data)  # Optional debug

        for place in data.get("results", []):
            site = {
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "location": place.get("geometry", {}).get("location"),
                "types": place.get("types"),
                "business_status": place.get("business_status")
            }
            results.append(site)

        next_page_token = data.get("next_page_token")
        if next_page_token:
            time.sleep(2)  # Required delay before using the token
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            params = {
                'pagetoken': next_page_token,
                'key': API_KEY
            }
        else:
            break

    return results

# --- Streamlit UI ---
st.set_page_config(page_title="Company Site Finder", layout="wide")
st.title("🌍 Company Site Finder (via Google Maps API)")

company = st.text_input("Enter company name:", "Coca Cola")
location = st.text_input("Location (e.g., Greece):", "Greece")

if st.button("🔍 Search"):
    if company.strip():
        with st.spinner("Searching..."):
            try:
                sites = search_company_sites(company, location)
                st.session_state["sites"] = sites
                st.success(f"✅ Found {len(sites)} site(s).")
            except Exception as e:
                st.error(f"API error: {e}")
    else:
        st.warning("Please enter a company name.")

# --- Display map ---
if "sites" in st.session_state:
    sites = st.session_state["sites"]

    if not sites:
        st.warning("No sites found.")
    else:
        center = next((s["location"] for s in sites if s["location"]), {"lat": 48.8566, "lng": 2.3522})
        m = folium.Map(location=[center["lat"], center["lng"]], zoom_start=5)
        cluster = MarkerCluster().add_to(m)

        for site in sites:
            loc = site["location"]
            folium.Marker(
                location=[loc["lat"], loc["lng"]],
                popup=f"{site['name']}<br>{site['address']}<br>Status: {site['business_status']}",
                tooltip=site["name"]
            ).add_to(cluster)

        st.subheader("📍 Map of Sites")
        st_folium(m, width=1000, height=600)








