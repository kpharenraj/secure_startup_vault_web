function toggleAuth() {
    const subtitle = document.getElementById('auth-subtitle');
    const toggleLink = document.getElementById('toggle-msg');
    const authForm = document.getElementById('auth-form');
    const submitBtn = document.getElementById('submit-btn');
    const title = document.querySelector('.auth-header h2');
    const confirmGroup = document.getElementById('confirm-pass-group');
    const confirmInput = document.getElementById('confirm_field');

    // Check current mode based on button text
    const isLoginMode = submitBtn.innerText.trim() === "Login";

    if (isLoginMode) {
        // Switch to Register Mode
        if (title) title.innerText = "CREATE ACCOUNT";
        if (subtitle) subtitle.innerText = "Join the most secure vault for your startup.";

        // Update Link
        if (toggleLink) {
            toggleLink.innerHTML = 'Already have an account? <a href="javascript:void(0)" onclick="toggleAuth()">Login</a>';
        }

        // Update Form action
        if (authForm) authForm.action = "{{ url_for('auth.register') }}";
        if (submitBtn) submitBtn.innerText = "Create Account";

        // Show Confirm Password
        if (confirmGroup) {
            confirmGroup.style.display = "block";
            if (confirmInput) {
                confirmInput.required = true;
                confirmInput.style.display = "block";
            }
        }

    } else {
        // Switch back to Login Mode
        if (title) title.innerText = "SECURE STARTUP VAULT";
        if (subtitle) subtitle.innerText = "Welcome back! Please login to your account.";

        // Update Link
        if (toggleLink) {
            toggleLink.innerHTML = 'Don\'t have an account? <a href="javascript:void(0)" onclick="toggleAuth()">Register</a>';
        }

        // Update Form action
        if (authForm) authForm.action = "{{ url_for('auth.login') }}";
        if (submitBtn) submitBtn.innerText = "Login";

        // Hide Confirm Password
        if (confirmGroup) {
            confirmGroup.style.display = "none";
            if (confirmInput) {
                confirmInput.required = false;
                confirmInput.style.display = "none";
            }
        }
    }
}

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