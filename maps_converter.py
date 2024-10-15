import geojson
import json

ZIP_CODES_GITHUB = "https://github.com/zauberware/postal-codes-json-xml-csv/tree/master/data"

fill_colors = {
    "CZ" : "#f3b554",

    "IT" : "#f4da04",
    "ES" : "#f3b554",
    "PT" : "#e2e9c2",

    "DE" : "#dbe4b5",
    "AT" : "#e2e7ea",

    "SK" : "#e0c009",

    "FR" : "#f5dfb7",
}


def get_zip_codes_by_province(input_file) -> dict:

    zip_codes_by_province : dict[str, str] = {}

    with open(input_file, 'r', encoding='utf-8') as f:

        file_data = f.read()
        data = json.loads(file_data)
        for entry in data:
            zip_code = entry["zipcode"][0:2]
            province = entry["province"]
            country_code = entry["country_code"]
            if province not in zip_codes_by_province:
                zip_codes_by_province[province] = country_code + zip_code

    return zip_codes_by_province


def create_labels_from_geojson(input_file, country_code):
    # Load GeoJSON data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = geojson.load(f)

    # zip_codes_by_province = get_zip_codes_by_province(input_zip_codes_dir + "/" + country_code + ".json")

    # Loop through each feature and create a label
    for feature in data['features']:
        # Add the label to the feature properties, converting to ASCII if necessary
        # label = zip_codes_by_province.get(feature["name"], "")
        # feature['properties']['label'] = label
        #feature['properties']['fill'] = fill_colors[country_code]
        feature['properties']['color'] = fill_colors[country_code]

    return data['features']

# Example usage
input_geojson_dir = 'country_district_polygons'  # Change this to your input GeoJSON path
input_zip_codes_dir = 'zip_codes'  # Change this to your input GeoJSON path

output_geojson = 'europe_districts.geojson'  # Change this to your desired output path

# TODO iterate over all countries

features = []

features.extend(create_labels_from_geojson(input_geojson_dir + "/" + "CZ.geojson", "CZ")) 
features.extend(create_labels_from_geojson(input_geojson_dir + "/" + "DE.geojson", "DE")) 
features.extend(create_labels_from_geojson(input_geojson_dir + "/" + "IT.geojson", "IT")) 

data = {
    "type": "FeatureCollection",
    "features": features
}  

# Save the modified data to a new GeoJSON file, ensuring ASCII encoding
with open(output_geojson, 'w', encoding='utf-8') as f:
    geojson.dump(data, f, ensure_ascii=True)

print(f"Europe districts geojson created and saved to {output_geojson}")