// Function to update URL query parameters
function updateQueryStringParameter(uri, key, value) {
    const re = new RegExp(`([?&])${key}=.*?(&|$)`, 'i');
    const separator = uri.includes('?') ? "&" : "?";
    
    if (uri.match(re)) {
        return uri.replace(re, `$1${key}=${value}$2`);
    }
    
    return `${uri}${separator}${key}=${value}`;
}

// Initialize sortable table functionality
function initSortableTable() {
    const sortableHeaders = document.querySelectorAll('.sortable');
    if (!sortableHeaders.length) return;

    const urlParams = new URLSearchParams(window.location.search);
    const currentSortBy = urlParams.get('sort_by') || 'datetime';
    const currentSortOrder = urlParams.get('sort_order') || 'desc';

    // Update sort indicators on page load
    sortableHeaders.forEach(header => {
        const sortBy = header.dataset.sortBy;
        if (sortBy === currentSortBy) {
            header.classList.add('sorting-' + currentSortOrder);
            header.setAttribute('data-sort-order', 
                currentSortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            header.setAttribute('data-sort-order', 'desc');
        }
    });

    // Add click handlers for sortable headers
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const sortBy = this.dataset.sortBy;
            let sortOrder = this.dataset.sortOrder || 'desc';
            
            // Toggle sort order if clicking the same column
            if (sortBy === currentSortBy) {
                sortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
            }

            // Update URL with new sort parameters
            const newUrl = updateQueryStringParameter(
                window.location.href, 
                'sort_by', 
                sortBy
            );
            
            window.location.href = updateQueryStringParameter(
                newUrl,
                'sort_order',
                sortOrder
            );
        });
    });
}

// Initialize when DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    initSortableTable();
});
