import pycountry

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

def search_company_sites_osm(company_name, location=""):
    """
    Modified to search Google Places API over all countries if location is empty.
    """
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
                        "status": place.get("business_status"),
                        "source": "Google"
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


