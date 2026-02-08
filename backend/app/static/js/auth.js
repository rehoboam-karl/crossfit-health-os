// CrossFit Health OS - Authentication JavaScript

// Check if already authenticated and redirect to dashboard
$(document).ready(function() {
    const currentPath = window.location.pathname;
    const authPages = ['/login', '/register', '/forgot-password'];
    
    if (authPages.includes(currentPath) && Utils.isAuthenticated()) {
        window.location.href = '/dashboard';
    }
});

// Password strength indicator
function checkPasswordStrength(password) {
    let strength = 0;
    const checks = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        number: /\d/.test(password),
        special: /[!@#$%^&*]/.test(password)
    };
    
    for (let key in checks) {
        if (checks[key]) strength++;
    }
    
    if (strength < 3) return { level: 'weak', color: 'danger' };
    if (strength < 4) return { level: 'medium', color: 'warning' };
    return { level: 'strong', color: 'success' };
}

// Add password strength indicator on register page
if (window.location.pathname === '/register') {
    $(document).ready(function() {
        $('#password').on('input', function() {
            const password = $(this).val();
            if (password.length > 0) {
                const strength = checkPasswordStrength(password);
                
                // Remove existing indicator
                $('#password-strength').remove();
                
                // Add new indicator
                const indicator = `
                    <div id="password-strength" class="mt-1">
                        <small class="text-${strength.color}">
                            Password strength: <strong>${strength.level}</strong>
                        </small>
                    </div>
                `;
                $(this).after(indicator);
            } else {
                $('#password-strength').remove();
            }
        });
        
        // Check password match
        $('#confirm_password').on('input', function() {
            const password = $('#password').val();
            const confirm = $(this).val();
            
            $('#password-match').remove();
            
            if (confirm.length > 0) {
                if (password === confirm) {
                    $(this).after('<div id="password-match" class="mt-1"><small class="text-success"><i class="fas fa-check-circle me-1"></i> Passwords match</small></div>');
                } else {
                    $(this).after('<div id="password-match" class="mt-1"><small class="text-danger"><i class="fas fa-times-circle me-1"></i> Passwords do not match</small></div>');
                }
            }
        });
    });
}
