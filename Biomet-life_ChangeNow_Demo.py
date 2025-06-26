import streamlit as st
import requests
import time
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import pycountry

def get_all_countries():
    return [country.name for country in pycountry.countries]

def is_affiliated(name, company):
    name_lower = name.lower()
    company_lower = company.lower().strip()

    # Ignore short, generic names
    if len(company_lower.split()) == 1 and len(company_lower) < 8:
        return False

    suffixes = ['s.a.', 'sa', 'inc', 'ltd', 'corp', 'plc', 'llc']
    for s in suffixes:
        company_lower = company_lower.replace(s, '')
    company_lower = company_lower.strip()

    return company_lower in name_lower

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
def search_company_sites_google(company_name, location="Greece"):
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

# === No location entered API ===
def search_company_sites_osm(company_name):
    """Fallback when no location is provided — search globally via Google across all countries."""
    locations_to_search = get_all_countries()
    results = []
    seen_place_ids = set()

    for loc in locations_to_search:
        query = f"{company_name} in {loc}"
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': query,
            'key': API_KEY
        }

        while url:
            try:
                res = requests.get(url, params=params)
                data = res.json()
            except Exception as e:
                print(f"Error searching in {loc}: {e}")
                break

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
                        "name": name,
                        "address": place.get("formatted_address"),
                        "location": place.get("geometry", {}).get("location"),
                        "source": "Google (Global)",
                        "types": types,
                        "status": place.get("business_status", "UNKNOWN")
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



