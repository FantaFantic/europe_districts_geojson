import os
import json
import geojson
import geopandas as gpd
from shapely.geometry import shape, Point, mapping
from collections import defaultdict
from geopandas import GeoDataFrame

ZIP_CODES_GITHUB = "https://github.com/zauberware/postal-codes-json-xml-csv/tree/master/data"

fill_colors = {
    "CZ" : "#f3b554",

    "IT" : "#f4da04",
    "ES" : "#F3B455",
    "PT" : "#e2e9c2",

    "DE" : "#dbe4b5",
    "AT" : "#e2e7ea",

    "SK" : "#e0c009",

    "FR" : "#f5dfb7",

    "CH" : "#9BB5CD",
    "NL" : "#ED9C29",
    "PL" : "#f4da04",
    # SLOVENIA
    "SI" : "#EC9D27",
    # BELGIUM
    "BE" : "#f4da04",
    # HUNGARIA
    "HU" : "#C3D476",
    # LUXEMBOURG
    "LU" : "",
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


def process_country_districts_geojson(districts_data, country_code, input_zip_codes_file):

    # Load zip code data
    with open(input_zip_codes_file, 'r', encoding='utf-8') as f:
        zip_codes_data = json.load(f)

    # Convert zip code data to a GeoDataFrame
    zip_gdf : GeoDataFrame = GeoDataFrame(
        zip_codes_data,
        geometry=[Point(float(z['longitude']), float(z['latitude'])) for z in zip_codes_data]
    )
    
    # Filter to the relevant country
    zip_gdf = zip_gdf[zip_gdf['country_code'] == country_code]
    
    # Create a spatial index for ZIP code points
    zip_index = zip_gdf.sindex

    # Store the country center as the average of the centroids
    country_center = {"latitude": 0, "longitude": 0}
    district_centers = []

    # Store the number of valid centroids to calculate the country center
    valid_centroids_count = 0

    # Iterate over each district feature
    for feature in districts_data['features']:
        # Get the district geometry as a shapely object
        district_geometry = shape(feature['geometry'])

        # Check if the geometry is valid, and fix it if necessary
        if not district_geometry.is_valid:
            print(f"Invalid geometry found in district: {feature['properties'].get('name', 'Unknown District')}")
            district_geometry = district_geometry.buffer(0)  # This can fix some invalid geometries
        
        
        # Calculate the centroid of the district polygon
        centroid = district_geometry.centroid
        centroid_coords = {'latitude': centroid.y, 'longitude': centroid.x}

        # Use spatial index to find candidate points within the district's bounds
        possible_matches_index = list(zip_index.intersection(district_geometry.bounds))
        possible_matches = zip_gdf.iloc[possible_matches_index]

        # Filter the points to those actually within the district
        matching_points = possible_matches[possible_matches.geometry.within(district_geometry)]

        # Count the frequency of ZIP code prefixes
        zipcodes_count = defaultdict(int)
        for _, row in matching_points.iterrows():
            parsed_zip = row['zipcode'][0:2]
            zipcodes_count[parsed_zip] += 1

        # Determine the most frequent ZIP code prefix, if any
        most_frequent_zip = max(zipcodes_count, key=zipcodes_count.get, default=None)
        feature['properties']['zip_code'] = most_frequent_zip

        # Create a GeoJSON feature for the district center with the ZIP code as the label
        district_center_feature = geojson.Feature(
            geometry=mapping(centroid),
            properties={'label': most_frequent_zip or 'No ZIP'}
        )
        district_centers.append(district_center_feature)

        # Update the country center calculation with the centroid coordinates
        country_center['latitude'] += centroid_coords['latitude']
        country_center['longitude'] += centroid_coords['longitude']
        valid_centroids_count += 1

    # Calculate the average coordinates to determine the country center
    if valid_centroids_count > 0:
        country_center['latitude'] /= valid_centroids_count
        country_center['longitude'] /= valid_centroids_count

    # Create a GeoJSON feature for the country center
    country_center_feature = geojson.Feature(
        geometry=geojson.Point((country_center['longitude'], country_center['latitude'])),
        properties={'label': country_code}
    )

    # Convert the district centers to a GeoJSON FeatureCollection
    district_centers_geojson = geojson.FeatureCollection(district_centers)

    return districts_data['features'], country_center_feature, district_centers_geojson

# Example usage
input_geojson_dir = 'country_district_polygons'  # Change this to your input GeoJSON path
input_zip_codes_dir = 'zip_codes'  # Change this to your input GeoJSON path

output_districts_center_dir = "country_district_labels"

country_centers_geojson = "europe_country_labels.geojson"
output_country_districts_geojson = 'europe_districts.geojson'  # Change this to your desired output path

districts = []
country_centers = []

# Iterate over all files in the directory
for filename in os.listdir(input_geojson_dir):
    # Construct the full file path
    file_path = os.path.join(input_geojson_dir, filename)
    
    # Check if it's a file (not a directory)
    if os.path.isfile(file_path):

        country_code = filename.split(".geojson")[0]
        zip_code_path = input_zip_codes_dir + "/" + country_code + ".json"

        print(f"Processing: {file_path}")

        output_district_centers = output_districts_center_dir + "/" + country_code + ".geojson"


        # Load GeoJSON data for districts
        with open(file_path, 'r', encoding='utf-8') as f:
            districts_data = geojson.load(f)


        # Check if the file already exists
        if os.path.exists(output_district_centers):
            print("Already processed " + country_code)
            
            continue

        features, country_center, district_centers = process_country_districts_geojson(districts_data, country_code, zip_code_path)

        districts.extend(features)
        country_centers.append(country_center)
    

        # Save the modified data to a new GeoJSON file, ensuring ASCII encoding
        with open(output_district_centers, 'w', encoding='utf-8') as f:
            geojson.dump(district_centers, f, ensure_ascii=True)

previous_country_centers = []
previous_districts = []

# Load previously saved country centers if the file exists
if os.path.exists(country_centers_geojson):
    with open(country_centers_geojson, 'r', encoding='utf-8') as f:
        data = geojson.load(f)
        # Extract the existing features into the list
        previous_country_centers = data.get('features', [])

# Load previously saved districts if the file exists
if os.path.exists(output_country_districts_geojson):
    with open(output_country_districts_geojson, 'r', encoding='utf-8') as f:
        data = geojson.load(f)
        # Extract the existing features into the list
        previous_districts = data.get('features', [])


previous_country_centers.extend(country_centers)


with open(country_centers_geojson, 'w', encoding='utf-8') as f:
    geojson.dump(geojson.FeatureCollection(previous_country_centers), f, ensure_ascii=True)

previous_districts.extend(districts)

# Save the modified data to a new GeoJSON file, ensuring ASCII encoding
with open(output_country_districts_geojson, 'w', encoding='utf-8') as f:
    geojson.dump(geojson.FeatureCollection(previous_districts), f, ensure_ascii=True)

print(f"Europe districts geojson created and saved to {output_country_districts_geojson}")