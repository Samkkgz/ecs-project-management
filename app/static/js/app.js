(function() {
    'use strict';
    document.addEventListener('DOMContentLoaded', function() {
        // Sync horizontal scroll across all right-row-wrap elements
        var rows = document.querySelectorAll('.right-row-wrap');
        var hdr = document.querySelector('.right-header-scroll');
        
        rows.forEach(function(row) {
            row.addEventListener('scroll', function() {
                // Sync all rows to the same scrollLeft
                rows.forEach(function(r) {
                    if (r !== row) r.scrollLeft = row.scrollLeft;
                });
                // Sync header
                if (hdr) hdr.scrollLeft = row.scrollLeft;
            });
        });
        
        // Also sync from header to rows
        if (hdr) {
            hdr.addEventListener('scroll', function() {
                rows.forEach(function(r) {
                    r.scrollLeft = hdr.scrollLeft;
                });
            });
        }
    });
})();
