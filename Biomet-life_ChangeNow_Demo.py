import streamlit as st
import requests
import time
import pycountry
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# === API Key ===
API_KEY = 'YOUR_GOOGLE_API_KEY'  # Replace with your actual key

# === Utility Functions ===
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
    search_url = "https://www.wikidata.org/w/api.php"
    search_params = {
        "action": "wbsearchentities",
        "language": "en",
        "format": "json",
        "search": company_name
    }
    search_response = requests.get(search_url, params=search_params).json()
    
    if not search_response["search"]:
        return []

    entity_id = None
    for result in search_response["search"]:
        if "company" in result.get("description", "").lower():
            entity_id = result["id"]
            break
    if not entity_id:
        entity_id = search_response["search"][0]["id"]

    sparql_url = "https://query.wikidata.org/sparql"
    query = f"""
    SELECT ?subsidiaryLabel WHERE {{
      wd:{entity_id} wdt:P355 ?subsidiary .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    """
    headers = {"Accept": "application/sparql-results+json"}
    r = requests.get(sparql_url, params={"query": query}, headers=headers)
    data = r.json()

    subsidiaries = [result["subsidiaryLabel"]["value"] for result in data["results"]["bindings"]]
    return subsidiaries

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

                if (
                    place_id
                    and place_id not in seen_place_ids
                    and is_affiliated(name, company_name)
                    and any(t in types for t in ['establishment', 'point_of_interest', 'store', 'gas_station', 'office', 'industrial'])
                ):
                    seen_place_ids.add(place_id)
                    site = {
                        "company": company_name,
                        "name": name,
                        "address": place.get("formatted_address"),
                        "location": place.get("geometry", {}).get("location"),
                        "types": types,
                        "business_status": place.get("business_status")
                    }
                    results.append(site)

            next_page_token = data.get("next_page_token")
            if next_page_token:
                time.sleep(2)
                params = {'pagetoken': next_page_token, 'key': API_KEY}
                url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            else:
                break

    return results

# === Streamlit UI ===
st.set_page_config(page_title="Company Sites & Subsidiaries", layout="wide")
st.title("🏢 Company Subsidiaries & Site Locator")

company = st.text_input("Enter Company Name", "Motor Oil Hellas")
location = st.text_input("Limit Search to Country (optional)", "Greece")

if "subsidiaries" not in st.session_state:
    st.session_state.subsidiaries = []
if "results" not in st.session_state:
    st.session_state.results = []

# 🔘 Button 1: Get Subsidiaries
col1, col2 = st.columns(2)
with col1:
    if st.button("🔎 Get Subsidiaries"):
        with st.spinner("Querying Wikidata..."):
            st.session_state.subsidiaries = get_subsidiaries_from_wikidata(company)
            st.success(f"Found {len(st.session_state.subsidiaries)} subsidiaries.")
            st.write(st.session_state.subsidiaries)

# 🔘 Button 2: Get All Sites
with col2:
    if st.button("🌍 Get Company + Subsidiary Sites"):
        with st.spinner("Searching Google Places..."):
            all_names = [company] + st.session_state.subsidiaries
            all_sites = []
            for name in all_names:
                st.info(f"Searching: {name}")
                sites = search_company_sites(name, location)
                all_sites.extend(sites)
            st.session_state.results = all_sites
            st.success(f"Found {len(all_sites)} site(s).")

# 🌐 Display Results on Map
if st.session_state.results:
    st.markdown("### 📍 Mapped Locations")
    first_loc = st.session_state.results[0]["location"]
    m = folium.Map(location=[first_loc["lat"], first_loc["lng"]], zoom_start=5)
    cluster = MarkerCluster().add_to(m)

    for site in st.session_state.results:
        loc = site["location"]
        popup = f"<b>{site['company']}</b><br>{site['name']}<br>{site['address']}<br>Status: {site['business_status']}"
        folium.Marker(location=[loc["lat"], loc["lng"]], tooltip=site["name"], popup=popup).add_to(cluster)

    st_folium(m, width=3000, height=600)
