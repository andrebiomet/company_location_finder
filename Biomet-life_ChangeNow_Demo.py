import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# === Subsidiaries from Wikidata ===
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

# === OSM Company Search ===
def search_osm(company_name, location=None):
    base_url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "Streamlit OSM App"}
    query = f"{company_name} {location}" if location else company_name

    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": 50
    }

    r = requests.get(base_url, params=params, headers=headers)
    results = []
    for item in r.json():
        if "lat" in item and "lon" in item:
            site = {
                "name": item.get("display_name", "Unnamed"),
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "type": item.get("type", "unknown"),
                "category": item.get("class", "unknown"),
                "address": item.get("address", {})
            }
            results.append(site)
    return results

# === Streamlit UI ===
st.set_page_config(page_title="Company Sites via OSM", layout="wide")
st.title("🏢 Company Subsidiaries & Site Locator (OpenStreetMap)")

company = st.text_input("Enter Company Name", "Motor Oil Hellas")
location = st.text_input("Optional Location Filter", "Greece")

if "subsidiaries" not in st.session_state:
    st.session_state.subsidiaries = []
if "results" not in st.session_state:
    st.session_state.results = []

col1, col2 = st.columns(2)

with col1:
    if st.button("🔎 Get Subsidiaries"):
        with st.spinner("Querying Wikidata..."):
            st.session_state.subsidiaries = get_subsidiaries_from_wikidata(company)
            st.success(f"Found {len(st.session_state.subsidiaries)} subsidiaries.")
            st.write(st.session_state.subsidiaries)

with col2:
    if st.button("🌍 Search Sites via OpenStreetMap"):
        with st.spinner("Searching Nominatim (OSM)..."):
            all_names = [company] + st.session_state.subsidiaries
            all_sites = []
            for name in all_names:
                st.info(f"Searching: {name}")
                sites = search_osm(name, location)
                all_sites.extend(sites)
            st.session_state.results = all_sites
            st.success(f"Found {len(all_sites)} site(s).")

# === Display Map ===
if st.session_state.results:
    st.markdown("### 📍 Mapped Locations")
    first_loc = st.session_state.results[0]
    m = folium.Map(location=[first_loc["lat"], first_loc["lon"]], zoom_start=5)
    cluster = MarkerCluster().add_to(m)

    for site in st.session_state.results:
        popup = f"<b>{site['name']}</b><br>Type: {site['type']}<br>Category: {site['category']}"
        folium.Marker(
            location=[site["lat"], site["lon"]],
            tooltip=site["name"],
            popup=popup
        ).add_to(cluster)

    st_folium(m, width=3000, height=600)

