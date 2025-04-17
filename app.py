import folium

# Define boundary limits around Laguna de Bay
min_lat, max_lat = 14.1700, 14.5300
min_lon, max_lon = 121, 121.4500

# Center of the lake
center_lat, center_lon = 14.4000, 121.2500

# Stadia Alidade Satellite tile layer setup
tiles_url = "https://tiles.stadiamaps.com/tiles/alidade_satellite/{z}/{x}/{y}{r}.jpg"
tiles_attr = (
    '&copy; CNES, Distribution Airbus DS, © Airbus DS, © PlanetObserver '
    '(Contains Copernicus Data) | '
    '&copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> '
    '&copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> '
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
)

# Create the map with limits
m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=12,
    max_bounds=True,
    tiles=tiles_url,
    attr=tiles_attr,
    min_lat=min_lat,
    max_lat=max_lat,
    min_lon=min_lon,
    max_lon=max_lon
)

# Optional: Show boundary corners
folium.CircleMarker([max_lat, min_lon], tooltip="Upper Left").add_to(m)
folium.CircleMarker([min_lat, min_lon], tooltip="Lower Left").add_to(m)
folium.CircleMarker([min_lat, max_lon], tooltip="Lower Right").add_to(m)
folium.CircleMarker([max_lat, max_lon], tooltip="Upper Right").add_to(m)

# Save to HTML
m.save("map.html")
