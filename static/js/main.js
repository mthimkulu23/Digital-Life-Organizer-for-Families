document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Page Loader Interception for links
    const navLinks = document.querySelectorAll('a[href]:not([href^="#"]):not([data-bs-toggle="modal"]):not([target="_blank"]):not([download])');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
            
            const url = this.getAttribute('href');
            if (url && url.startsWith('javascript:')) return;
            if (url && url.startsWith('mailto:')) return;
            if (url && url.startsWith('tel:')) return;
            
            e.preventDefault();
            showLoaderAndNavigate(this.href);
        });
    });

    // Page Loader Interception for forms
    const forms = document.querySelectorAll('form:not([target="_blank"])');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Avoid double submission if already loading
            if (this.dataset.submitting) return;
            
            // Check HTML5 validity
            if (!this.checkValidity()) return;
            
            this.dataset.submitting = "true";
            e.preventDefault();
            showLoaderAndNavigate(null, true, this);
        });
    });
});

function showLoaderAndNavigate(url, isForm = false, formElement = null) {
    const loader = document.getElementById('page-loader');
    const progressBar = document.getElementById('loader-progress-bar');
    const percentageText = document.getElementById('loader-percentage');
    
    if (!loader) {
        if (isForm && formElement) {
            formElement.submit();
        } else if (url) {
            window.location.href = url;
        }
        return;
    }
    
    loader.classList.remove('d-none');
    
    let progress = 10;
    progressBar.style.width = '10%';
    percentageText.innerText = '10%';
    
    const interval = setInterval(() => {
        progress += Math.floor(Math.random() * 15) + 10; // add 10-24 per tick
        
        if (progress >= 100) {
            progress = 100;
            clearInterval(interval);
            
            progressBar.style.width = '100%';
            percentageText.innerText = '100%';
            
            // Wait a tiny bit at 100% then execute navigation
            setTimeout(() => {
                if (isForm && formElement) {
                    formElement.submit();
                } else if (url) {
                    window.location.href = url;
                }
            }, 100);
        } else {
            progressBar.style.width = progress + '%';
            percentageText.innerText = progress + '%';
        }
    }, 40); // 40ms interval makes the fake load fast enough not to be annoying
}


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
