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

// Use Jawg Terrain tile layer
// L.tileLayer('https://tile.jawg.io/jawg-terrain/{z}/{x}/{y}{r}.png?access-token=BD2lZDhbcFkhEdIcvlN4uXNTuX5eb21icj9H78VAp4GEA27N0j8B96s6rTWjnNSx', {
//     attribution: '<a href="https://www.jawg.io?utm_medium=map&utm_source=attribution" target="_blank">&copy; Jawg</a> - <a href="https://www.openstreetmap.org?utm_medium=map-attribution&utm_source=jawg" target="_blank">&copy; OpenStreetMap</a> contributors',
// }).addTo(map);

// Use Jawg Light tile layer
L.tileLayer('https://tile.jawg.io/jawg-light/{z}/{x}/{y}{r}.png?access-token=BD2lZDhbcFkhEdIcvlN4uXNTuX5eb21icj9H78VAp4GEA27N0j8B96s6rTWjnNSx', {
    attribution: '<a href="https://www.jawg.io?utm_medium=map&utm_source=attribution" target="_blank">&copy; Jawg</a> - <a href="https://www.openstreetmap.org?utm_medium=map-attribution&utm_source=jawg" target="_blank">&copy; OpenStreetMap</a> contributors',
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
    const formatDate = timestamp => {
        const date = new Date(timestamp * 1000); // Convert seconds to milliseconds
        return date.toISOString().split('T')[0]; // Format as YYYY-MM-DD
    };

    // Get the user's local timezone offset in seconds
    const timezoneOffset = new Date().getTimezoneOffset() * 60;

    // Calculate current date in the user's local timezone
    const currentDate = Math.floor(new Date().getTime() / 1000) - timezoneOffset;

    // Start date (April 1, 2025) adjusted to the user's local timezone
    const startDate = new Date('2025-04-01T00:00:00Z').getTime() / 1000 - timezoneOffset;

    $("#slider-range").slider({
        range: true,
        min: startDate,
        max: currentDate, // Set max to the current date in the user's local timezone
        step: 86400, // One day
        values: [
            startDate,
            currentDate
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
