import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# --- Helper functions ---
def query_overpass(company_name):
    query = f"""
    [out:json][timeout:25];
    (
      node["name"~"{company_name}", i];
      way["name"~"{company_name}", i];
      relation["name"~"{company_name}", i];
      node["operator"~"{company_name}", i];
      way["operator"~"{company_name}", i];
      relation["operator"~"{company_name}", i];
      node["brand"~"{company_name}", i];
      way["brand"~"{company_name}", i];
      relation["brand"~"{company_name}", i];
    );
    out center;
    """
    url = "https://overpass-api.de/api/interpreter"
    response = requests.post(url, data={"data": query})
    response.raise_for_status()
    return response.json()

def parse_osm_results(data):
    elements = data.get("elements", [])
    sites = []
    for el in elements:
        tags = el.get("tags", {})
        site = {
            "name": tags.get("name", "Unnamed"),
            "lat": el.get("lat") or el.get("center", {}).get("lat"),
            "lon": el.get("lon") or el.get("center", {}).get("lon"),
            "type": tags.get("building") or tags.get("office") or tags.get("amenity") or tags.get("industrial") or "unspecified"
        }
        if site["lat"] and site["lon"]:
            sites.append(site)
    return sites

# --- Streamlit UI ---
st.set_page_config(page_title="Company OSM Sites Map", layout="wide")
st.title("🌍 Company Site Finder (via OpenStreetMap)")

company = st.text_input("Enter company name:", "Coca-Cola")

if company:
    with st.spinner(f"Searching OSM for '{company}' sites..."):
        try:
            osm_data = query_overpass(company)
            locations = parse_osm_results(osm_data)

            if not locations:
                st.warning("No sites found on OSM for that company.")
            else:
                m = folium.Map(location=[locations[0]['lat'], locations[0]['lon']], zoom_start=4)
                marker_cluster = MarkerCluster().add_to(m)

                for site in locations:
                    folium.Marker(
                        location=[site['lat'], site['lon']],
                        popup=f"{site['name']}<br>Type: {site['type']}",
                        tooltip=f"{site['name']} ({site['type']})"
                    ).add_to(marker_cluster)

                st.subheader("📍 Sites Map")
                st_folium(m, width=1000, height=600)

        except Exception as e:
            st.error(f"Error querying OSM: {e}")

