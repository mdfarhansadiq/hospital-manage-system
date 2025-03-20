// Show loading indicator
function showLoading() {
    document.querySelector('.loading').style.display = 'block';
}

// Hide loading indicator
function hideLoading() {
    document.querySelector('.loading').style.display = 'none';
}

// Form validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
    }
    form.classList.add('was-validated');
}

// Search functionality
function searchTable(inputId, tableId) {
    const input = document.getElementById(inputId);
    const filter = input.value.toLowerCase();
    const table = document.getElementById(tableId);
    const rows = table.getElementsByTagName('tr');

    for (let i = 1; i < rows.length; i++) {
        const cells = rows[i].getElementsByTagName('td');
        let found = false;

        for (let j = 0; j < cells.length; j++) {
            const cell = cells[j];
            if (cell) {
                const text = cell.textContent || cell.innerText;
                if (text.toLowerCase().indexOf(filter) > -1) {
                    found = true;
                    break;
                }
            }
        }

        rows[i].style.display = found ? '' : 'none';
    }
}

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Handle appointment form
function handleAppointmentForm(event) {
    event.preventDefault();
    showLoading();

    // Simulate form submission
    setTimeout(() => {
        hideLoading();
        alert('Appointment scheduled successfully!');
        event.target.reset();
    }, 1000);
}

function addMedicationEntry() {
    const container = document.querySelector('.medications-container');
    const template = document.querySelector('.medication-entry').cloneNode(true);

    // Clear the values
    template.querySelectorAll('input').forEach(input => input.value = '');

    container.appendChild(template);
}

function viewPrescription(id) {
    fetch(`/prescriptions/${id}`)
        .then(response => response.json())
        .then(data => {
            // Create a modal to display prescription details
            const modalHTML = `
                <div class="modal fade" id="viewPrescriptionModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Prescription Details</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <strong>Patient:</strong> ${data.patient}
                                    </div>
                                    <div class="col-md-6">
                                        <strong>Doctor:</strong> ${data.doctor}
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <strong>Date:</strong> ${data.date}
                                </div>
                                <div class="mb-3">
                                    <strong>Diagnosis:</strong>
                                    <p>${data.diagnosis}</p>
                                </div>
                                <div class="mb-3">
                                    <strong>Medications:</strong>
                                    <table class="table table-bordered mt-2">
                                        <thead>
                                            <tr>
                                                <th>Medication</th>
                                                <th>Dosage</th>
                                                <th>Frequency</th>
                                                <th>Duration</th>
                                                <th>Instructions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${data.medications.map(med => `
                                                <tr>
                                                    <td>${med.name}</td>
                                                    <td>${med.dosage}</td>
                                                    <td>${med.frequency}</td>
                                                    <td>${med.duration}</td>
                                                    <td>${med.instructions || ''}</td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                                ${data.notes ? `
                                    <div class="mb-3">
                                        <strong>Notes:</strong>
                                        <p>${data.notes}</p>
                                    </div>
                                ` : ''}
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                                <button type="button" class="btn btn-primary" onclick="printPrescription(${data.id})">
                                    <i class="fas fa-print"></i> Print
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Remove any existing modal
            const existingModal = document.getElementById('viewPrescriptionModal');
            if (existingModal) {
                existingModal.remove();
            }

            // Add the new modal to the document
            document.body.insertAdjacentHTML('beforeend', modalHTML);

            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById('viewPrescriptionModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error loading prescription details');
        });
}

function printPrescription(id) {
    fetch(`/prescriptions/${id}`)
        .then(response => response.json())
        .then(data => {
            const printWindow = window.open('', '_blank');
            printWindow.document.write(`
                <html>
                <head>
                    <title>Prescription #${id}</title>
                    <style>
                        body { font-family: Arial, sans-serif; padding: 20px; }
                        .header { text-align: center; margin-bottom: 30px; }
                        .prescription-details { margin-bottom: 20px; }
                        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                        th { background-color: #f8f9fa; }
                        @media print {
                            body { margin: 0; padding: 20px; }
                        }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h2>Hospital Management System</h2>
                        <h3>Prescription #${id}</h3>
                    </div>
                    <div class="prescription-details">
                        <p><strong>Date:</strong> ${data.date}</p>
                        <p><strong>Patient:</strong> ${data.patient}</p>
                        <p><strong>Doctor:</strong> ${data.doctor}</p>
                    </div>
                    <div class="diagnosis">
                        <h4>Diagnosis:</h4>
                        <p>${data.diagnosis}</p>
                    </div>
                    <div class="medications">
                        <h4>Medications:</h4>
                        <table>
                            <thead>
                                <tr>
                                    <th>Medication</th>
                                    <th>Dosage</th>
                                    <th>Frequency</th>
                                    <th>Duration</th>
                                    <th>Instructions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.medications.map(med => `
                                    <tr>
                                        <td>${med.name}</td>
                                        <td>${med.dosage}</td>
                                        <td>${med.frequency}</td>
                                        <td>${med.duration}</td>
                                        <td>${med.instructions || ''}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    ${data.notes ? `
                        <div class="notes">
                            <h4>Notes:</h4>
                            <p>${data.notes}</p>
                        </div>
                    ` : ''}
                    <div class="footer" style="margin-top: 50px;">
                        <p>Doctor's Signature: _____________________</p>
                    </div>
                </body>
                </html>
            `);
            printWindow.document.close();
            printWindow.print();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error printing prescription');
        });
}

// Edit Role Modal Functionality
document.addEventListener('DOMContentLoaded', function() {
    const editRoleModal = document.getElementById('editRoleModal');
    if (editRoleModal) {
        editRoleModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const userId = button.getAttribute('data-user-id');
            const userName = button.getAttribute('data-user-name');
            const userRole = button.getAttribute('data-user-role');

            const modal = this;
            modal.querySelector('#editUserId').value = userId;
            modal.querySelector('#editUserName').value = userName;
            modal.querySelector('select[name="role"]').value = userRole;
        });
    }
});

// Ward and Bed Selection Logic
document.addEventListener('DOMContentLoaded', function() {
    const wardSelect = document.getElementById('wardSelect');
    const bedSelect = document.getElementById('bedSelect');

    if (wardSelect && bedSelect) {
        wardSelect.addEventListener('change', function() {
            const wardId = this.value;

            // Clear bed select
            bedSelect.innerHTML = '<option value="">Select Bed</option>';

            if (wardId) {
                // Show loading state
                bedSelect.disabled = true;

                // Fetch available beds for selected ward
                fetch(`/api/wards/${wardId}/available-beds`)
                    .then(response => response.json())
                    .then(beds => {
                        beds.forEach(bed => {
                            const option = document.createElement('option');
                            option.value = bed.id;
                            option.textContent = `Bed ${bed.number}`;
                            bedSelect.appendChild(option);
                        });
                        bedSelect.disabled = false;
                    })
                    .catch(error => {
                        console.error('Error fetching beds:', error);
                        bedSelect.disabled = false;
                    });
            }
        });
    }
});