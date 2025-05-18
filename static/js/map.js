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
            <div class="popup-content-large">
                <b>Date:</b> ${data.date}<br>
                <b>Polymers:</b> ${data.type}<br>
                <b>Density:</b> ${data.density} pcs/cm³<br>
                <img src="${data.image}" alt="Sample" style="max-width:200px;max-height:200px;display:block;margin-top:4px;">
            </div>
        `);
        marker.addTo(map);
        markers.push(marker);
    });
}

let currentFetchController = null;

// Initialize slider
$(function () {
    // Helper to pad numbers to two digits
    const pad = n => n < 10 ? '0' + n : n;

    // Format date as YYYY-MM-DD HH:MM:SS in UTC+8, with option for end of day
    const formatDate = (timestamp, isMax = false) => {
        const date = new Date((timestamp + 8 * 3600) * 1000); // shift to UTC+8
        const time = isMax ? '23:59:59' : '00:00:00';
        return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ${time}`;
    };

    // Format date as YYYY-MM-DD in UTC+8 for display
    const formatDisplayDate = timestamp => {
        const date = new Date((timestamp + 8 * 3600) * 1000);
        return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`;
    };

    // Get today's midnight in UTC+8 as the slider's max value
    const now = new Date();
    const utc8Midnight = new Date(now.getTime() + 8 * 3600 * 1000);
    utc8Midnight.setUTCHours(0, 0, 0, 0);
    const maxSliderTimestamp = Math.floor(utc8Midnight.getTime() / 1000) - 8 * 3600;

    // Get April 1, 2025 midnight in UTC+8 as the slider's min value
    const startSliderTimestamp = Math.floor(new Date('2025-04-01T00:00:00+08:00').getTime() / 1000);

    // Initialize the slider
    $("#slider-range").slider({
        range: true,
        min: startSliderTimestamp,
        max: maxSliderTimestamp,
        step: 86400, // One day
        values: [
            startSliderTimestamp,
            maxSliderTimestamp
        ],
        slide: function (event, ui) {
            // Clamp right handle to maxSliderTimestamp
            if (ui.values[1] > maxSliderTimestamp) {
                ui.values[1] = maxSliderTimestamp;
            }
            $("#amount").text(
                formatDisplayDate(ui.values[0]) + " - " + formatDisplayDate(ui.values[1])
            );

            // Abort previous fetch if still running
            if (currentFetchController) {
                currentFetchController.abort();
            }
            currentFetchController = new AbortController();

            // Fetch filtered markers
            fetch('/filter_markers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    min_date: formatDate(ui.values[0], false),
                    max_date: formatDate(ui.values[1], true)
                }),
                signal: currentFetchController.signal
            })
            .then(response => response.json())
            .then(data => {
                addMarkers(data);
            })
            .catch(err => {
                if (err.name !== 'AbortError') {
                    console.error(err);
                }
            });
        }
    });

    // Set initial label
    const initialValues = $("#slider-range").slider("values");
    $("#amount").text(
        formatDisplayDate(initialValues[0]) + " - " + formatDisplayDate(initialValues[1])
    );

    // Fetch initial markers
    fetch('/filter_markers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            min_date: formatDate(initialValues[0], false),
            max_date: formatDate(initialValues[1], true)
        })
    })
    .then(response => response.json())
    .then(data => {
        addMarkers(data);
    });
});
