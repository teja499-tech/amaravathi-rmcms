/**
 * Responsive Tables JS
 * 
 * Makes standard HTML tables responsive on mobile devices by
 * adding data attributes to help with mobile display
 */

function makeTablesResponsive() {
    // Target tables with .table class that don't have .table-responsive-off class
    const tables = document.querySelectorAll('table.table:not(.table-responsive-off)');
    
    tables.forEach(table => {
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
        
        // Skip tables that already have data-labels
        if (table.querySelector('td[data-label]')) {
            return;
        }
        
        // Add data-label attributes to all td elements based on their corresponding th
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                if (headers[index]) {
                    cell.setAttribute('data-label', headers[index]);
                }
            });
        });
        
        // Add responsive class to the table
        table.classList.add('table-responsive-custom');
    });
}

// Call on page load
document.addEventListener('DOMContentLoaded', makeTablesResponsive);

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { makeTablesResponsive };
} 