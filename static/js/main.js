document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

function copyEmergencyCode() {
    const codeElement = document.getElementById('emergency-code-text');
    if (codeElement) {
        navigator.clipboard.writeText(codeElement.innerText).then(function() {
            const copyIcon = document.getElementById('copy-icon');
            copyIcon.classList.remove('fa-copy');
            copyIcon.classList.add('fa-check', 'text-success');
            setTimeout(function() {
                copyIcon.classList.remove('fa-check', 'text-success');
                copyIcon.classList.add('fa-copy');
            }, 2000);
        });
    }
}
