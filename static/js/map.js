// Define bounding box around Laguna de Bay area
const bounds = [
    [13.9, 120.8], // Southwest corner
    [14.9, 121.7]  // Northeast corner
];

// Initialize the map with zoom and boundary restrictions
const map = L.map('map', {
    center: [14.37, 121.25],
    zoom: 11,
    minZoom: 10,
    maxZoom: 16,
    maxBounds: bounds,
    zoomControl: false,
});

// Add zoom control to the bottom right of the map
const zoomControl = L.control.zoom({
    position: 'bottomright'
});
zoomControl.addTo(map);

// Use Jawg Terrain tile layer
// L.tileLayer('https://tile.jawg.io/jawg-terrain/{z}/{x}/{y}{r}.png?access-token=BD2lZDhbcFkhEdIcvlN4uXNTuX5eb21icj9H78VAp4GEA27N0j8B96s6rTWjnNSx', {
//     attribution: '<a href="https://www.jawg.io?utm_medium=map&utm_source=attribution" target="_blank">&copy; Jawg</a> - <a href="https://www.openstreetmap.org?utm_medium=map-attribution&utm_source=jawg" target="_blank">&copy; OpenStreetMap</a> contributors',
// }).addTo(map);

// Use Jawg Light tile layer
L.tileLayer('https://tile.jawg.io/jawg-light/{z}/{x}/{y}{r}.png?access-token=BD2lZDhbcFkhEdIcvlN4uXNTuX5eb21icj9H78VAp4GEA27N0j8B96s6rTWjnNSx', {
    attribution: '<a href="https://www.jawg.io?utm_medium=map&utm_source=attribution" target="_blank">&copy; Jawg</a> - <a href="https://www.openstreetmap.org?utm_medium=map-attribution&utm_source=jawg" target="_blank">&copy; OpenStreetMap</a> contributors',
}).addTo(map);

let markers = [];

// Helper function to interpolate between two colors
function interpolateColor(color1, color2, factor) {
    // Convert hex colors to RGB
    const r1 = parseInt(color1.substring(1, 3), 16);
    const g1 = parseInt(color1.substring(3, 5), 16);
    const b1 = parseInt(color1.substring(5, 7), 16);
    
    const r2 = parseInt(color2.substring(1, 3), 16);
    const g2 = parseInt(color2.substring(3, 5), 16);
    const b2 = parseInt(color2.substring(5, 7), 16);
    
    // Interpolate RGB values
    const r = Math.round(r1 + factor * (r2 - r1));
    const g = Math.round(g1 + factor * (g2 - g1));
    const b = Math.round(b1 + factor * (b2 - b1));
    
    // Convert back to hex
    return `#${(r << 16 | g << 8 | b).toString(16).padStart(6, '0')}`;
}

// Function to get color based on density with smooth gradient
function getDensityColor(density) {
    // Extract numeric value from the density string (e.g., '0.5 pcs/cm³' -> 0.5)
    const densityValue = parseFloat(density);
    
    // Define color stops for the gradient
    const colorStops = [
        { value: 0.0, color: '#8a2be2' },  // Violet (lowest)
        { value: 0.5, color: '#4b0082' },  // Indigo
        { value: 1.0, color: '#0000ff' },  // Blue
        { value: 2.0, color: '#00ff00' },  // Green
        { value: 3.0, color: '#ffff00' },  // Yellow
        { value: 4.0, color: '#ff8000' },  // Orange
        { value: 5.0, color: '#ff0000' }   // Red (highest)
    ];
    
    // Cap the value at the highest color stop
    if (densityValue >= colorStops[colorStops.length - 1].value) {
        return colorStops[colorStops.length - 1].color;
    }
    
    // Find the two color stops to interpolate between
    for (let i = 0; i < colorStops.length - 1; i++) {
        if (densityValue >= colorStops[i].value && densityValue < colorStops[i + 1].value) {
            const lowerStop = colorStops[i];
            const upperStop = colorStops[i + 1];
            
            // Calculate interpolation factor (0-1)
            const range = upperStop.value - lowerStop.value;
            const factor = (densityValue - lowerStop.value) / range;
            
            // Return interpolated color
            return interpolateColor(lowerStop.color, upperStop.color, factor);
        }
    }
    
    // Fallback
    return colorStops[0].color;
}

// Function to add markers dynamically
function addMarkers(markerData) {
    // Clear existing markers
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];

    // Find min and max density for relative scaling (if needed)
    const densities = markerData.map(data => {
        // Extract numeric value from the density string (e.g., '0.5 pcs/cm³' -> 0.5)
        return parseFloat(data.density) || 0;
    });
    const minDensity = Math.min(...densities);
    const maxDensity = Math.max(...densities);
    const densityRange = maxDensity - minDensity;

    // Add new markers
    markerData.forEach(data => {
        // Extract numeric density value
        const densityValue = parseFloat(data.density) || 0;
        
        // Calculate marker size based on density (optional)
        const baseRadius = 6;
        const sizeMultiplier = 1 + (densityValue / (maxDensity || 1)) * 2; // Scale up to 3x base size
        const radius = Math.min(baseRadius * sizeMultiplier, 15); // Cap max size
        
        // Get color based on density
        const markerColor = getDensityColor(densityValue);
        
        // Create marker with dynamic styling
        const marker = L.circleMarker([data.lat, data.lon], {
            radius: radius,
            color: '#fff',  // White border
            weight: 1,     // Border width
            fillColor: markerColor,
            fillOpacity: 0.8,
            opacity: 0.8
        }).bindPopup(`
            <div class="popup-content-large">
                <b>Date:</b> ${data.date}<br>
                <b>Polymers:</b> ${data.type}<br>
                <b>Density:</b> ${data.density} pcs/cm³<br>
                <img src="${data.image}" alt="Sample" style="max-width:200px;max-height:200px;display:block;margin:8px auto;border-radius:8px;">
            </div>
        `);
        
        // Add marker to map and array
        marker.addTo(map);
        markers.push(marker);
    });
    
    // No legend added
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

// Function to update the "Last Updated" section dynamically
function updateLastUpdated() {
    fetch('/latest_date')
        .then(response => response.json())
        .then(data => {
            const lastUpdatedElement = document.getElementById('last-updated');
            if (data && data.latest_date) {
                // Extract only the date part (YYYY-MM-DD)
                const dateOnly = data.latest_date.split(' ')[0];
                lastUpdatedElement.textContent = `Last Updated: ${dateOnly}`;
            } else {
                lastUpdatedElement.textContent = 'Last Updated: Data unavailable';
            }
        })
        .catch(err => {
            console.error('Error fetching latest date:', err);
            const lastUpdatedElement = document.getElementById('last-updated');
            lastUpdatedElement.textContent = 'Last Updated: Error fetching data';
        });
}

// Fetch total samples from DynamoDB and update the sidebar
function updateTotalSamples() {
    fetch('/total_samples')
        .then(response => response.json())
        .then(data => {
            const totalSamplesElement = document.getElementById('sidebar-sample-count');
            if (data && data.total_samples) {
                totalSamplesElement.textContent = data.total_samples;
            } else {
                totalSamplesElement.textContent = 'Data unavailable';
            }
        })
        .catch(err => {
            console.error('Error fetching total samples:', err);
            const totalSamplesElement = document.getElementById('sidebar-sample-count');
            totalSamplesElement.textContent = 'Error fetching data';
        });
}

// Call updateLastUpdated and updateTotalSamples on page load
document.addEventListener('DOMContentLoaded', () => {
    updateLastUpdated();
    updateTotalSamples();
});
