import streamlit as st
import requests
import time
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

API_KEY = 'AIzaSyCBhur5E-PvIFL6jSY3PoP6UR3Ns7Qb0No'

def search_company_sites(company_name, location="Greece"):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        'query': company_name + " in " + location,
        'key': API_KEY
    }

    results = []
    while True:
        res = requests.get(url, params=params)
        data = res.json()

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
        if not next_page_token:
            break

        time.sleep(2)
        params = {
            'pagetoken': next_page_token,
            'key': API_KEY
        }

    return results

# Streamlit UI
st.set_page_config(page_title="Company Sites", layout="wide")
st.title("📍 Google Maps Company Site Finder")

company = st.text_input("Company Name", "Coca Cola")
location = st.text_input("Location", "Greece")

if st.button("🔍 Search"):
    with st.spinner("Fetching data..."):
        results = search_company_sites(company, location)
        st.session_state["results"] = results

if "results" in st.session_state:
    results = st.session_state["results"]
    st.success(f"Found {len(results)} site(s).")

    if results:
        first_loc = results[0]["location"]
        m = folium.Map(location=[first_loc["lat"], first_loc["lng"]], zoom_start=6)
        cluster = MarkerCluster().add_to(m)

        for site in results:
            loc = site["location"]
            folium.Marker(
                location=[loc["lat"], loc["lng"]],
                tooltip=site["name"],
                popup=f"{site['name']}<br>{site['address']}<br>Status: {site['business_status']}"
            ).add_to(cluster)

        st_folium(m, width=1000, height=600)









