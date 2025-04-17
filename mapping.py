import folium
from folium.plugins import HeatMap

# Example microplastic dataset
microplastic_data = [
    {'lat': 14.35, 'lon': 121.22, 'density': 15, 'type': 'Polyethylene'},
    {'lat': 14.38, 'lon': 121.28, 'density': 30, 'type': 'Polypropylene'},
    {'lat': 14.42, 'lon': 121.26, 'density': 50, 'type': 'Polystyrene'},
    {'lat': 14.45, 'lon': 121.30, 'density': 22, 'type': 'Nylon'},
]

# Color map based on type
type_color_map = {
    'Polyethylene': 'red',
    'Polypropylene': 'green',
    'Polystyrene': 'orange',
    'Nylon': 'purple'
}

def create_marker(folium_map, lat, lon, density, type_):
    """
    Adds a color-coded circle marker based on microplastic type.
    """
    popup_text = f"<b>Type:</b> {type_}<br><b>Density:</b> {density} pcs/cm³"
    color = type_color_map.get(type_, 'blue')  # fallback color

    folium.CircleMarker(
        location=(lat, lon),
        radius=6,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        popup=folium.Popup(popup_text, max_width=250)
    ).add_to(folium_map)

def main():
    # Define boundary limits around Laguna de Bay
    min_lat, max_lat = 14.1700, 14.5300
    min_lon, max_lon = 121.0000, 121.4500
    center_lat, center_lon = 14.4000, 121.2500

    # Stadia Alidade Satellite tile layer
    tiles_url = "https://tiles.stadiamaps.com/tiles/alidade_satellite/{z}/{x}/{y}{r}.jpg"
    tiles_attr = (
        '&copy; CNES, Distribution Airbus DS, © Airbus DS, © PlanetObserver '
        '(Contains Copernicus Data) | '
        '&copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> '
        '&copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> '
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    )

    # Create the map
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

    # Optional boundary corner markers
    folium.CircleMarker([max_lat, min_lon], tooltip="Upper Left").add_to(m)
    folium.CircleMarker([min_lat, min_lon], tooltip="Lower Left").add_to(m)
    folium.CircleMarker([min_lat, max_lon], tooltip="Lower Right").add_to(m)
    folium.CircleMarker([max_lat, max_lon], tooltip="Upper Right").add_to(m)

    # Heatmap layer
    heat_data = [[d['lat'], d['lon'], d['density']] for d in microplastic_data]
    HeatMap(heat_data, radius=15, blur=10, max_zoom=13).add_to(m)

    # Color-coded markers
    for data in microplastic_data:
        create_marker(m, data['lat'], data['lon'], data['density'], data['type'])

    m.save("map.html")

if __name__ == "__main__":
    main()
