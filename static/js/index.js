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
    maxZoom: 22,
    maxBounds: bounds,
    zoomControl: false,
});

// Add zoom control to the bottom right of the map
const zoomControl = L.control.zoom({
    position: 'bottomright'
});
zoomControl.addTo(map);

// Define Jawg Light and Jawg Terrain tile layers
const jawgLight = L.tileLayer('https://tile.jawg.io/jawg-light/{z}/{x}/{y}{r}.png?access-token=BD2lZDhbcFkhEdIcvlN4uXNTuX5eb21icj9H78VAp4GEA27N0j8B96s6rTWjnNSx', {
    attribution: '<a href="https://www.jawg.io?utm_medium=map&utm_source=attribution" target="_blank">&copy; Jawg</a> - <a href="https://www.openstreetmap.org?utm_medium=map-attribution&utm_source=jawg" target="_blank">&copy; OpenStreetMap</a> contributors',
    maxZoom: 22
});
const jawgTerrain = L.tileLayer('https://tile.jawg.io/jawg-terrain/{z}/{x}/{y}{r}.png?access-token=BD2lZDhbcFkhEdIcvlN4uXNTuX5eb21icj9H78VAp4GEA27N0j8B96s6rTWjnNSx', {
    attribution: '<a href="https://www.jawg.io?utm_medium=map&utm_source=attribution" target="_blank">&copy; Jawg</a> - <a href="https://www.openstreetmap.org?utm_medium=map-attribution&utm_source=jawg" target="_blank">&copy; OpenStreetMap</a> contributors',
    maxZoom: 22
});

// Add the default tile layer to the map
jawgLight.addTo(map);

// Custom toggle button for tile layers
const TileToggleControl = L.Control.extend({
    options: { position: 'bottomleft' },
    onAdd: function(map) {
        const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
        container.style.backgroundColor = 'white';
        container.style.cursor = 'pointer';
        container.style.padding = '4px 10px';
        container.style.fontWeight = 'bold';
        container.style.fontSize = '14px';
        container.style.borderRadius = '4px';
        container.style.boxShadow = '0 1px 5px rgba(0,0,0,0.3)';
        container.innerHTML = 'Terrain'; // Show the next layer to switch to
        let currentLayer = jawgLight;
        let nextLayer = jawgTerrain;
        container.onclick = function(e) {
            e.stopPropagation();
            if (map.hasLayer(currentLayer)) {
                map.removeLayer(currentLayer);
                nextLayer.addTo(map);
                // Swap layers
                const temp = currentLayer;
                currentLayer = nextLayer;
                nextLayer = temp;
                container.innerHTML = (currentLayer === jawgLight) ? 'Terrain' : 'Light';
            }
        };
        return container;
    }
});
map.addControl(new TileToggleControl());

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
        { value: 0.0,  color: '#8a2be2' },  // Violet (lowest)
        { value: 0.025, color: '#4b0082' },  // Indigo
        { value: 0.05,  color: '#0000ff' },  // Blue
        { value: 0.075, color: '#00ff00' },  // Green
        { value: 0.1,  color: '#ffff00' },  // Yellow
        { value: 0.125, color: '#ff8000' },  // Orange
        { value: 0.15,  color: '#ff0000' }   // Red (highest)
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
                <b>Density:</b> ${data.density} pcs/cm³<br>
                <b>Polymer Composition:</b><br>
                &nbsp;&nbsp;• Polystyrene (PS): <b>${data.percentPS}%</b><br>
                &nbsp;&nbsp;• Polypropylene (PP): <b>${data.percentPP}%</b><br>
                &nbsp;&nbsp;• Polyethylene (PE): <b>${data.percentPE}%</b><br>
                <img src="${data.image}" alt="Sample" class="sample-image" style="max-width:200px;max-height:200px;display:block;margin:8px auto;border-radius:8px;cursor:zoom-in;"><br>
                ${data.annotatedimageurl ? `<a href="${data.annotatedimageurl}" target="_blank">Annotated</a>` : ''}
            </div>
        `);
        
        // Add click handler to marker for opening popup
        marker.on('click', function() {
            // Close any open popups before opening a new one
            markers.forEach(m => {
                if (m !== marker) {
                    m.closePopup();
                }
            });
            // Open the popup for the clicked marker
            marker.getPopup().setLatLng(marker.getLatLng()).openOn(map);
        });
        
        // Add click handler for image preview when popup opens
        function handlePopupOpen(e) {
            const popup = e.popup;
            const content = popup.getElement();
            const img = content ? content.querySelector('.sample-image') : null;
            
            if (!img) return;
            
            // Store the current popup reference
            const currentPopup = popup;
            
            // Single click handler function
            function handleImageClick() {
                const overlay = document.getElementById('image-preview-overlay');
                const previewImg = document.getElementById('preview-image');
                const closeBtn = document.querySelector('.image-preview-close');
                
                if (!overlay || !previewImg) return;
                
                // Set the image source and show overlay
                previewImg.src = this.src;
                overlay.style.display = 'flex';
                document.body.style.overflow = 'hidden';
                
                // Clean up any existing handlers to prevent duplicates
                overlay.removeEventListener('click', handleOverlayClick);
                document.removeEventListener('keydown', handleEscapeKey);
                
                // Add new handlers
                overlay.addEventListener('click', handleOverlayClick);
                document.addEventListener('keydown', handleEscapeKey);
                
                // Stop propagation to prevent closing when clicking the image
                if (previewImg.parentNode) {
                    previewImg.parentNode.onclick = function(e) {
                        e.stopPropagation();
                    };
                }
            }
            
            // Handle overlay click (close when clicking outside the image or on close button)
            function handleOverlayClick(e) {
                const overlay = document.getElementById('image-preview-overlay');
                const closeBtn = document.querySelector('.image-preview-close');
                
                // Check if click is on overlay background or close button
                if (e.target === overlay || (closeBtn && closeBtn.contains(e.target))) {
                    overlay.style.display = 'none';
                    document.body.style.overflow = '';
                    
                    // Remove the event listeners to prevent memory leaks
                    overlay.removeEventListener('click', handleOverlayClick);
                    document.removeEventListener('keydown', handleEscapeKey);
                }
            }
            
            // Handle escape key press
            function handleEscapeKey(e) {
                if (e.key === 'Escape') {
                    const overlay = document.getElementById('image-preview-overlay');
                    if (overlay) {
                        overlay.style.display = 'none';
                        document.body.style.overflow = '';
                    }
                }
            }
            
            // Clean up previous handlers and add new one
            img.removeEventListener('click', handleImageClick);
            img.addEventListener('click', handleImageClick);
            
            // Clean up when popup is closed
            function cleanupPreview() {
                const overlay = document.getElementById('image-preview-overlay');
                if (overlay) {
                    overlay.style.display = 'none';
                    overlay.removeEventListener('click', handleOverlayClick);
                }
                document.removeEventListener('keydown', handleEscapeKey);
                document.body.style.overflow = '';
            }
            
            // Add close button click handler
            const closeBtn = document.querySelector('.image-preview-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', cleanupPreview);
            }
            
            // Clean up when popup is closed
            popup._closeButton = popup._closeButton || (popup._container && popup._container.querySelector('.leaflet-popup-close-button'));
            if (popup._closeButton) {
                function popupCloseHandler() {
                    cleanupPreview();
                    if (currentPopup && currentPopup._closeButton) {
                        currentPopup._closeButton.removeEventListener('click', popupCloseHandler);
                    }
                }
                popup._closeButton.addEventListener('click', popupCloseHandler);
            }
        }
        
        // Remove any existing popupopen handler to prevent duplicates
        marker.off('popupopen', handlePopupOpen);
        // Add the popupopen handler
        marker.on('popupopen', handlePopupOpen);
        
        // Add marker to map and array
        marker.addTo(map);
        markers.push(marker);
    });
    
    // No legend added
}

let currentFetchController = null;
let latestMaxDate = null; // Store the latest max date globally

// Function to fetch markers with current controller
function fetchMarkers(minDate, maxDate) {
    if (currentFetchController) {
        currentFetchController.abort();
    }
    currentFetchController = new AbortController();

    return fetch('/filter_markers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ min_date: minDate, max_date: maxDate }),
        signal: currentFetchController.signal
    })
    .then(response => response.json())
    .then(data => {
        addMarkers(data);
        return data;
    });
}

// Function to initialize the slider with dynamic date range
function initializeSlider(minDate, maxDate) {
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

    // Convert date strings to timestamps
    const minTimestamp = Math.floor(new Date(minDate).getTime() / 1000);
    const maxTimestamp = Math.floor(new Date(maxDate).getTime() / 1000);

    // Initialize the slider with the date range
    $("#slider-range").slider({
        range: true,
        min: minTimestamp,
        max: maxTimestamp,
        step: 86400, // One day
        values: [minTimestamp, maxTimestamp],
        slide: function (event, ui) {
            // Clamp right handle to max timestamp
            if (ui.values[1] > maxTimestamp) {
                ui.values[1] = maxTimestamp;
            }
            // Only update the displayed date range during slide
            $("#amount").text(
                formatDisplayDate(ui.values[0]) + " - " + formatDisplayDate(ui.values[1])
            );
        },
        stop: function(event, ui) {
            // Only fetch data when user stops dragging
            const minDate = formatDate(ui.values[0], false);
            const maxDate = formatDate(ui.values[1], true);
            
            // Update markers and sidebar immediately after slider stops
            fetchMarkers(minDate, maxDate).then(() => {
                updateSidebarStats(minDate, maxDate);
            });
        }
    });

    // Set initial label
    const initialValues = $("#slider-range").slider("values");
    $("#amount").text(
        formatDisplayDate(initialValues[0]) + " - " + formatDisplayDate(initialValues[1])
    );

    // On initial load
    const initialMinDate = formatDate(initialValues[0], false);
    const initialMaxDate = formatDate(initialValues[1], true);
    
    // Fetch initial markers and update sidebar
    fetchMarkers(initialMinDate, initialMaxDate).then(() => {
        updateSidebarStats(initialMinDate, initialMaxDate);
    });
}

// Initialize the application
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

    // Function to fetch date range and store the max date
    function fetchDateRange() {
        return fetch('/date_range')
            .then(response => response.json())
            .then(data => {
                if (data.min_date && data.max_date) {
                    // Store the max date for the "Last Updated" section
                    latestMaxDate = data.max_date;
                    return data;
                }
                throw new Error('Invalid date range data');
            });
    }

    // Fetch the date range from the server, initialize the slider, and update the last updated display
    fetchDateRange()
        .then(data => {
            initializeSlider(data.min_date, data.max_date);
            // Update the last updated display with the stored max date
            updateLastUpdated();
        })
        .catch(error => {
            console.error('Error fetching date range:', error);
            // Fallback to default dates on error
            const defaultMinDate = '2025-04-01T00:00:00+08:00';
            const defaultMaxDate = new Date();
            defaultMaxDate.setUTCHours(0, 0, 0, 0);
            latestMaxDate = defaultMaxDate.toISOString().replace('T', ' ').split('.')[0];
            initializeSlider(defaultMinDate, latestMaxDate);
            updateLastUpdated();
        });
});

// Function to update the "Last Updated" section using the stored max date
function updateLastUpdated() {
    const lastUpdatedElement = document.getElementById('last-updated');
    if (latestMaxDate) {
        // Extract only the date part (YYYY-MM-DD)
        const dateOnly = latestMaxDate.split(' ')[0];
        lastUpdatedElement.textContent = `Last Updated: ${dateOnly}`;
    } else {
        // If we don't have the max date yet, fetch it
        fetchDateRange()
            .then(() => {
                if (latestMaxDate) {
                    const dateOnly = latestMaxDate.split(' ')[0];
                    lastUpdatedElement.textContent = `Last Updated: ${dateOnly}`;
                } else {
                    lastUpdatedElement.textContent = 'Last Updated: Data unavailable';
                }
            })
            .catch(err => {
                console.error('Error fetching date range:', err);
                lastUpdatedElement.textContent = 'Last Updated: Error fetching data';
            });
    }
}

// Fetch total samples from DynamoDB with date range filter and update the sidebar
function updateTotalSamples(minDate, maxDate) {
    fetch('/total_samples', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ min_date: minDate, max_date: maxDate })
    })
    .then(response => response.json())
    .then(data => {
        const totalSamplesElement = document.getElementById('sidebar-sample-count');
        if (data && data.total_samples) {
            totalSamplesElement.textContent = data.total_samples;
        } else {
            totalSamplesElement.textContent = '0';
        }
    })
    .catch(err => {
        console.error('Error fetching total samples:', err);
        const totalSamplesElement = document.getElementById('sidebar-sample-count');
        totalSamplesElement.textContent = 'Error fetching data';
    });
}

// Fetch average density from DynamoDB with date range filter and update the sidebar
function updateAverageDensity(minDate, maxDate) {
    fetch('/average_density', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ min_date: minDate, max_date: maxDate })
    })
    .then(response => response.json())
    .then(data => {
        const avgDensityElement = document.getElementById('sidebar-average-density');
        if (data && typeof data.average_density === 'number') {
            avgDensityElement.textContent = data.average_density.toFixed(2);
        } else {
            avgDensityElement.textContent = '0';
        }
    })
    .catch(err => {
        console.error('Error fetching average density:', err);
        const avgDensityElement = document.getElementById('sidebar-average-density');
        avgDensityElement.textContent = 'Error';
    });
}

// Update both total samples and average density when slider changes or on load
function updateSidebarStats(minDate, maxDate) {
    updateTotalSamples(minDate, maxDate);
    updateAverageDensity(minDate, maxDate);
}

// Call updateLastUpdated and updateSidebarStats on page load
document.addEventListener('DOMContentLoaded', () => {
    updateLastUpdated();
    
    // Get the initial slider values
    const slider = $("#slider-range");
    if (slider.length) {
        const values = slider.slider("values");
        const formatDate = timestamp => {
            const date = new Date((timestamp + 8 * 3600) * 1000);
            const pad = n => n < 10 ? '0' + n : n;
            return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ` + 
                   (timestamp === slider.slider("option", "max") ? '23:59:59' : '00:00:00');
        };
        
        const minDate = formatDate(values[0]);
        const maxDate = formatDate(values[1]);
        updateSidebarStats(minDate, maxDate);
    }
});
