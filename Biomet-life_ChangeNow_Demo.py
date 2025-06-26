import streamlit as st
import requests
import time
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import pycountry

# === API Key ===
API_KEY = 'AIzaSyCBhur5E-PvIFL6jSY3PoP6UR3Ns7Qb0No'  # Your Google API Key

# === Get Subsidiaries from Wikidata ===
def get_subsidiaries_from_wikidata(company_name):
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "language": "en",
        "format": "json",
        "search": company_name
    }
    search = requests.get(url, params=params).json()
    if not search["search"]:
        return []

    entity_id = next((r["id"] for r in search["search"] if "company" in r.get("description", "").lower()), search["search"][0]["id"])
    query = f"""
    SELECT ?subsidiaryLabel WHERE {{
      wd:{entity_id} wdt:P355 ?subsidiary .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    """
    sparql = "https://query.wikidata.org/sparql"
    headers = {"Accept": "application/sparql-results+json"}
    data = requests.get(sparql, params={"query": query}, headers=headers).json()
    return [r["subsidiaryLabel"]["value"] for r in data["results"]["bindings"]]

# === Google Maps Places API ===
def search_company_sites_google(company_name, location):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {'query': company_name + " in " + location, 'key': API_KEY}
    results = []

    while url:
        r = requests.get(url, params=params)
        data = r.json()

        for place in data.get("results", []):
            results.append({
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "location": place.get("geometry", {}).get("location"),
                "source": "Google",
                "types": place.get("types"),
                "status": place.get("business_status", "UNKNOWN")
            })

        if "next_page_token" in data:
            time.sleep(2)
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            params = {'pagetoken': data["next_page_token"], 'key': API_KEY}
        else:
            break

    return results

# === OSM Overpass API ===
def search_company_sites_global_google(company_name):
    """Global fallback when no location is provided — search across key countries using Google Places API."""
    global_regions = [
        "United States", "Canada", "Mexico", "Brazil", "Argentina",
        "United Kingdom", "France", "Germany", "Italy", "Spain", "Netherlands", "Russia",
        "South Africa", "Nigeria", "Egypt", "India", "China", "Japan", "South Korea",
        "Australia", "New Zealand", "Indonesia", "Saudi Arabia", "Turkey", "Greece"
    ]

    results = []
    seen_places = set()

    for loc in global_regions:
        query = f"{company_name} in {loc}"
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': query,
            'key': API_KEY
        }

        while url:
            res = requests.get(url, params=params)
            data = res.json()

            for place in data.get("results", []):
                place_id = place.get("place_id")
                if place_id and place_id not in seen_places:
                    seen_places.add(place_id)
                    site = {
                        "name": place.get("name"),
                        "address": place.get("formatted_address"),
                        "location": place.get("geometry", {}).get("location"),
                        "source": "Google (Global)",
                        "types": place.get("types"),
                        "status": place.get("business_status", "UNKNOWN")
                    }
                    results.append(site)

            next_page_token = data.get("next_page_token")
            if next_page_token:
                time.sleep(2)  # Required delay
                params = {'pagetoken': next_page_token, 'key': API_KEY}
                url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            else:
                break

    return results

# === Streamlit UI ===
st.set_page_config(page_title="Company Locator", layout="wide")
st.title("🏢 Company Subsidiaries & Site Locator")

company = st.text_input("Enter Company Name", "Coca Cola HBC")
location = st.text_input("Optional Location Filter (uses Google API if specified)", "Greece")

if "subsidiaries" not in st.session_state:
    st.session_state.subsidiaries = []
if "results" not in st.session_state:
    st.session_state.results = []

# 🔘 Button 1
# 🔘 Buttons: Subsidiaries, Full Search, Company Only
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔎 Get Subsidiaries"):
        with st.spinner("Querying Wikidata..."):
            st.session_state.subsidiaries = get_subsidiaries_from_wikidata(company)
            st.success(f"Found {len(st.session_state.subsidiaries)} subsidiaries.")
            st.write(st.session_state.subsidiaries)

with col2:
    if st.button("🌍 Locate Company + Subsidiaries"):
        with st.spinner("Searching..."):
            names = [company] + st.session_state.subsidiaries
            all_sites = []
            for name in names:
                st.info(f"Searching: {name} using {'Google Maps' if location.strip() else 'OpenStreetMap'}")
                if location.strip():
                    sites = search_company_sites_google(name, location)
                else:
                    sites = search_company_sites_osm(name)
                all_sites.extend(sites)
            st.session_state.results = all_sites
            st.success(f"Found {len(all_sites)} locations.")

with col3:
    if st.button("🔍 Locate Company Only (No Subsidiaries)"):
        with st.spinner("Searching..."):
            if location.strip():
                sites = search_company_sites_google(company, location)
            else:
                sites = search_company_sites_osm(company)
            st.session_state.results = sites
            st.success(f"Found {len(sites)} location(s).")



# === Map Results ===
if st.session_state.results:
    st.markdown("### 📍 Locations Map")
    first = st.session_state.results[0]
    m = folium.Map(location=[first["location"]["lat"], first["location"]["lng"]], zoom_start=5)
    cluster = MarkerCluster().add_to(m)

    for site in st.session_state.results:
        loc = site["location"]
        popup = f"<b>{site['name']}</b><br>{site['address']}<br><i>Source: {site['source']}</i><br>Status: {site['status']}"
        folium.Marker([loc["lat"], loc["lng"]], tooltip=site["name"], popup=popup).add_to(cluster)

    st_folium(m, width=3000, height=600)




