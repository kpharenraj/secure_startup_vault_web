function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const btn = event.currentTarget || event.target; // handle both click targets

    if (input.type === "password") {
        input.type = "text";
        btn.innerText = "HIDE";
    } else {
        input.type = "password";
        btn.innerText = "SHOW";
    }
}

// Log form submission details for debugging
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('auth-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const tokenInput = form.querySelector('input[name=csrf_token]');
            const token = tokenInput ? tokenInput.value : 'MISSING';
            console.log('[AUTH] Form submitting to:', form.action);
            console.log('[AUTH] CSRF token present:', !!tokenInput);
            console.log('[AUTH] CSRF token value sample:', token.substring(0, 20));
            console.log('[AUTH] All form fields:', Array.from(form.elements).map(el => el.name).filter(Boolean));
        });
    }
});
