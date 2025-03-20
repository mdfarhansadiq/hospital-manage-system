// Initialize dashboard charts
function initDashboardCharts() {
    // Patient Statistics Chart
    const patientCtx = document.getElementById('patientStats').getContext('2d');
    new Chart(patientCtx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            datasets: [{
                label: 'Patient Admissions',
                data: [65, 59, 80, 81, 56, 55],
                borderColor: '#0d6efd',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                }
            }
        }
    });

    // Bed Occupancy Chart
    const bedCtx = document.getElementById('bedOccupancy').getContext('2d');
    new Chart(bedCtx, {
        type: 'doughnut',
        data: {
            labels: ['Occupied', 'Available'],
            datasets: [{
                data: [75, 25],
                backgroundColor: ['#dc3545', '#198754']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('patientStats')) {
        initDashboardCharts();
    }
});
