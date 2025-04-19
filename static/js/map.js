// Define bounding box around Laguna de Bay area
const bounds = [
    [13.9, 120.8], // Southwest corner
    [14.9, 121.7]  // Northeast corner
];

// Initialize the map with zoom and boundary restrictions
const map = L.map('map', {
    center: [14.4, 121.25],
    zoom: 10,
    minZoom: 10,
    maxZoom: 16,
    maxBounds: bounds,
});

// Add tile layer
L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_satellite/{z}/{x}/{y}{r}.jpg', {
    attribution: '&copy; CNES, Distribution Airbus DS, © Airbus DS, © PlanetObserver (Contains Copernicus Data)'
}).addTo(map);

let markers = [];

// Function to add markers dynamically
function addMarkers(markerData) {
    // Clear existing markers
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];

    // Add new markers
    markerData.forEach(data => {
        const marker = L.circleMarker([data.lat, data.lon], {
            radius: 6,
            color: 'blue',
            fillColor: 'blue',
            fillOpacity: 0.7
        }).bindPopup(`
            <b>Type:</b> ${data.type}<br>
            <b>Density:</b> ${data.density} pcs/cm³<br>
            <b>Date:</b> ${data.date}<br>
            <b>Image:</b> ${data.image}
        `);
        marker.addTo(map);
        markers.push(marker);
    });
}

// Initialize slider
$(function () {
    const formatDate = timestamp => new Date(timestamp * 1000).toISOString().split('T')[0];

    $("#slider-range").slider({
        range: true,
        min: new Date('2025-04-01').getTime() / 1000,
        max: new Date('2025-07-01').getTime() / 1000,
        step: 86400, // One day
        values: [
            new Date('2025-05-01').getTime() / 1000,
            new Date('2025-06-01').getTime() / 1000
        ],
        slide: function (event, ui) {
            $("#amount").text(
                formatDate(ui.values[0]) + " - " + formatDate(ui.values[1])
            );

            // Fetch filtered markers
            fetch('/filter_markers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    min_date: formatDate(ui.values[0]),
                    max_date: formatDate(ui.values[1])
                })
            })
            .then(response => response.json())
            .then(data => {
                addMarkers(data);
            });
        }
    });

    const initialValues = $("#slider-range").slider("values");
    $("#amount").text(
        formatDate(initialValues[0]) + " - " + formatDate(initialValues[1])
    );

    // Fetch initial markers
    fetch('/filter_markers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            min_date: formatDate(initialValues[0]),
            max_date: formatDate(initialValues[1])
        })
    })
    .then(response => response.json())
    .then(data => {
        addMarkers(data);
    });
});
