import streamlit as st
import requests
import folium
import time
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

API_KEY = "AIzaSyCBhur5E-PvIFL6jSY3PoP6UR3Ns7Qb0No"  # Your actual key

# --- Search Function (matches Colab version) ---
def search_company_sites(company_name, location="Greece"):
    """Search for company locations using Google Places API."""
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        query = company_name if location.strip() == "" else f"{company_name} in {location}",
        'key': API_KEY
    }

    results = []
    while url:
        res = requests.get(url, params=params)
        data = res.json()

        # Optional: Debug output
        st.write("🔍 Raw API response:", data)

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
            time.sleep(2)  # Required before using token
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

company = st.text_input("Enter company name:", "Coca-Cola")
location = st.text_input("Optional location (e.g., Greece):", "Greece")

if st.button("🔍 Search"):
    if company.strip():
        with st.spinner("Searching Google Maps..."):
            try:
                sites = search_company_sites(company, location)
                st.session_state["sites"] = sites
            except Exception as e:
                st.error(f"API request failed: {e}")
    else:
        st.warning("Please enter a company name.")

# --- Display Results ---
if "sites" in st.session_state:
    sites = st.session_state["sites"]
    if not sites:
        st.warning("No sites found.")
    else:
        st.success(f"✅ Found {len(sites)} site(s).")

        # Center map on first result
        if sites:
            first = sites[0]
            if first["location"] and "lat" in first["location"] and "lng" in first["location"]:
                start_coords = [first["location"]["lat"], first["location"]["lng"]]
            else:
                start_coords = [48.8566, 2.3522]  # fallback to Paris
        else:
            start_coords = [48.8566, 2.3522]  # fallback if no sites
            
        m = folium.Map(location=start_coords, zoom_start=4)
        marker_cluster = MarkerCluster().add_to(m)

        for site in sites:
            loc = site["location"]
            folium.Marker(
                location=[loc['lat'], loc['lng']],
                popup=folium.Popup(f"{site['name']}\n{site['address']}\n{site['business_status']}\n{site['types']}", max_width=250),
                tooltip=site['name'],
                icon=folium.Icon(icon="info-sign")  # ✅ Adds default pin
            ).add_to(marker_cluster)


        st.subheader("📍 Sites Map")
        st_folium(m, width=1000, height=600)



