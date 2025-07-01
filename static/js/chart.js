// Chart configuration
let chart;
let currentTimeframe = 'daily';

// Format date based on timeframe
function formatDate(dateStr, timeframe) {
    const date = new Date(dateStr);
    if (timeframe === 'weekly') {
        // Show week range (e.g., "Mar 1 - 7")
        const weekStart = new Date(date);
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekStart.getDate() + 6);
        
        const formatShortDate = (d) => {
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        };
        
        return `${formatShortDate(weekStart)} - ${formatShortDate(weekEnd)}`;
    } else {
        // Daily format (e.g., "Mar 1, 2023")
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
    }
}

// Format tooltip value
function formatValue(value) {
    return `${parseFloat(value).toFixed(2)} pcs/cm³`;
}

// Show loading state
function setLoading(isLoading) {
    const loader = document.getElementById('loading-indicator');
    loader.style.display = isLoading ? 'flex' : 'none';
}

// Fetch data from server
async function fetchData(timeframe) {
    setLoading(true);
    try {
        const res = await fetch(`/timeseries_data?mode=${timeframe}`);
        if (!res.ok) throw new Error('Failed to fetch data');
        return await res.json();
    } catch (error) {
        console.error('Error fetching data:', error);
        return [];
    } finally {
        setLoading(false);
    }
}

// Open detailed data for a specific date
function openDetailedData(date, mode) {
    const url = `/detailed_data?date=${date}&mode=${mode}`;
    window.location.href = url;
}

// Initialize and render chart
async function renderChart() {
    const data = await fetchData(currentTimeframe);
    if (!data || data.length === 0) return;
    
    const ctx = document.getElementById('densityChart').getContext('2d');
    const labels = data.map(d => formatDate(d.date, currentTimeframe));
    const densities = data.map(d => d.average_density);
    const dates = data.map(d => d.date); // Store original dates for click handling
    
    // Destroy previous chart instance if exists
    if (chart) chart.destroy();
    
    // Create new chart
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Density',
                data: densities,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                tension: 0.3,
                pointRadius: 3,
                pointHoverRadius: 6,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#3b82f6',
                pointHoverBackgroundColor: '#2563eb',
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 2,
                pointHitRadius: 20,
                pointBorderWidth: 1.5,
                spanGaps: true,
                cursor: 'pointer'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 750,
                easing: 'easeInOutQuart'
            },
            layout: {
                padding: {
                    top: 5,
                    right: 5,
                    bottom: 5,
                    left: 5
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        color: '#6b7280',
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 12,
                        padding: 10
                    }
                },
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.04)',
                        drawBorder: false,
                        drawTicks: false
                    },
                    ticks: {
                        color: '#6b7280',
                        padding: 10,
                        callback: function(value) {
                            return value + ' pcs/cm³';
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    titleColor: '#f9fafb',
                    bodyColor: '#e5e7eb',
                    titleFont: {
                        weight: '500',
                        size: 13
                    },
                    bodyFont: {
                        size: 14,
                        weight: '600'
                    },
                    padding: 10,
                    displayColors: false,
                    callbacks: {
                        title: function(context) {
                            return context[0].label;
                        },
                        label: function(context) {
                            return formatValue(context.parsed.y);
                        }
                    },
                    cornerRadius: 6,
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            },
            onHover: (event, chartElements) => {
                const target = event.native?.target;
                if (target) {
                    const points = chart.getElementsAtEventForMode(
                        event,
                        'nearest',
                        { intersect: false, axis: 'x' },
                        false
                    );
                    target.style.cursor = points.length > 0 ? 'pointer' : 'default';
                }
            },
            onClick: (e) => {
                const points = chart.getElementsAtEventForMode(
                    e,
                    'nearest',
                    { intersect: false, axis: 'x' },
                    false
                );
                
                if (points.length > 0) {
                    const point = points[0];
                    const date = dates[point.index];
                    
                    if (date) {
                        // Visual feedback
                        const activePoint = chart.getDatasetMeta(0).data[point.index];
                        const originalRadius = activePoint.options.radius;
                        activePoint.options.radius = 8;
                        chart.update();
                        
                        // Reset and navigate
                        setTimeout(() => {
                            activePoint.options.radius = originalRadius;
                            chart.update();
                            openDetailedData(date, currentTimeframe);
                        }, 150);
                    }
                }
            }
        }
    });
}

// Initialize the chart when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Handle timeframe tab clicks
    document.querySelectorAll('.timeframe-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            if (this.classList.contains('active')) return;
            
            // Update active tab
            document.querySelectorAll('.timeframe-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Update chart with new timeframe
            currentTimeframe = this.dataset.timeframe;
            renderChart();
        });
    });

    // Initial render
    renderChart();
});

// Handle window resize with debounce
let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        if (chart) chart.resize();
    }, 200);
});
