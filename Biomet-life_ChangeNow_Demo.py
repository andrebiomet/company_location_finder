import streamlit as st
import requests
import time
import pycountry
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

API_KEY = 'AIzaSyCBhur5E-PvIFL6jSY3PoP6UR3Ns7Qb0No'

def get_all_countries():
    return [country.name for country in pycountry.countries]

def is_affiliated(name, company):
    name_lower = name.lower()
    company_lower = company.lower().strip()
    if len(company_lower.split()) == 1 and len(company_lower) < 8:
        return False
    suffixes = ['s.a.', 'sa', 'inc', 'ltd', 'corp', 'plc', 'llc']
    for s in suffixes:
        company_lower = company_lower.replace(s, '')
    company_lower = company_lower.strip()
    return company_lower in name_lower

def get_subsidiaries_from_wikidata(company_name):
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "language": "en",
        "format": "json",
        "search": company_name
    }
    res = requests.get(url, params=params).json()
    if not res["search"]:
        return []
    entity_id = next((r["id"] for r in res["search"] if "company" in r.get("description", "").lower()), res["search"][0]["id"])
    query = f"""
    SELECT ?subsidiaryLabel WHERE {{
      wd:{entity_id} wdt:P355 ?subsidiary .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    headers = {"Accept": "application/sparql-results+json"}
    data = requests.get("https://query.wikidata.org/sparql", params={"query": query}, headers=headers).json()
    return [r["subsidiaryLabel"]["value"] for r in data["results"]["bindings"]]

def search_company_sites(company_name, location=""):
    locations_to_search = [location] if location.strip() else get_all_countries()
    results = []
    seen_place_ids = set()
    for loc in locations_to_search:
        query = f"{company_name} in {loc}"
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {'query': query, 'key': API_KEY}
        while url:
            res = requests.get(url, params=params)
            data = res.json()
            for place in data.get("results", []):
                place_id = place.get("place_id")
                name = place.get("name", "")
                types = place.get("types", [])
                if (place_id and place_id not in seen_place_ids
                    and is_affiliated(name, company_name)
                    and any(t in types for t in ['establishment', 'point_of_interest', 'store', 'gas_station', 'office', 'industrial'])):
                    seen_place_ids.add(place_id)
                    results.append({
                        "company": company_name,
                        "name": name,
                        "address": place.get("formatted_address"),
                        "location": place.get("geometry", {}).get("location"),
                        "types": types,
                        "status": place.get("business_status", "UNKNOWN"),
                        "source": "Google"
                    })
            next_page_token = data.get("next_page_token")
            if next_page_token:
                time.sleep(2)
                params = {'pagetoken': next_page_token, 'key': API_KEY}
            else:
                break
    return results

# === Streamlit UI ===
st.set_page_config(page_title="Company Locator", layout="wide")
st.title("🏢 Company Subsidiaries & Site Locator")

company = st.text_input("Enter Company Name", "Amazon")
location = st.text_input("Optional Location Filter (leave blank for global search)", "")

if "subsidiaries" not in st.session_state:
    st.session_state.subsidiaries = []
if "results" not in st.session_state:
    st.session_state.results = []

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
                st.info(f"Searching: {name}")
                all_sites.extend(search_company_sites(name, location))
            st.session_state.results = all_sites
            st.success(f"Found {len(all_sites)} locations.")

with col3:
    if st.button("🔍 Locate Company Only (No Subsidiaries)"):
        with st.spinner("Searching..."):
            st.session_state.results = search_company_sites(company, location)
            st.success(f"Found {len(st.session_state.results)} location(s).")

# === Map Results ===
if st.session_state.results:
    st.markdown("### 📍 Locations Map")
    first = st.session_state.results[0]
    m = folium.Map(location=[first["location"]["lat"], first["location"]["lng"]], zoom_start=4)
    cluster = MarkerCluster().add_to(m)

    for site in st.session_state.results:
        loc = site["location"]
        popup = f"<b>{site['company']}</b><br>{site['name']}<br>{site['address']}<br>Status: {site['status']}"
        folium.Marker([loc["lat"], loc["lng"]], tooltip=site["name"], popup=popup).add_to(cluster)

    st_folium(m, width=3000, height=600)



