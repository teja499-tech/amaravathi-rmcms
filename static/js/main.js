/**
 * Amaravathi RMC - Main JavaScript File
 */

document.addEventListener('DOMContentLoaded', function() {
    // Enable Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Enable Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Handle responsive tables
    makeTableResponsive();
    
    // Handle date inputs with date pickers if available
    setupDatePickers();
});

/**
 * Make tables responsive on small screens
 */
function makeTableResponsive() {
    var tables = document.querySelectorAll('table.table-responsive-data');
    
    tables.forEach(function(table) {
        var headerCells = table.querySelectorAll('thead th');
        var headerTexts = [];
        
        // Store header text content
        headerCells.forEach(function(th) {
            headerTexts.push(th.textContent.trim());
        });
        
        // Add data-label attribute to each cell in the table body
        var bodyCells = table.querySelectorAll('tbody td');
        
        bodyCells.forEach(function(td, index) {
            var headerIndex = index % headerTexts.length;
            td.setAttribute('data-label', headerTexts[headerIndex]);
        });
    });
}

/**
 * Setup date pickers for date input fields
 */
function setupDatePickers() {
    // Check if flatpickr is available
    if (typeof flatpickr !== 'undefined') {
        flatpickr('.datepicker', {
            dateFormat: 'Y-m-d',
            allowInput: true
        });
    }
}

/**
 * Format currency
 * @param {number} amount - The amount to format
 * @param {string} currency - The currency code (default: INR)
 * @returns {string} Formatted currency amount
 */
function formatCurrency(amount, currency = 'INR') {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2
    }).format(amount);
}

/**
 * Format date
 * @param {string|Date} date - The date to format
 * @param {string} format - The format (short, medium, long)
 * @returns {string} Formatted date string
 */
function formatDate(date, format = 'medium') {
    const dateObj = date instanceof Date ? date : new Date(date);
    
    const options = {
        short: { year: 'numeric', month: 'numeric', day: 'numeric' },
        medium: { year: 'numeric', month: 'short', day: 'numeric' },
        long: { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }
    };
    
    return dateObj.toLocaleDateString('en-IN', options[format]);
} 