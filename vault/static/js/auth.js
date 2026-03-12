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

// Initialize the correct mode based on current URL
window.onload = function() {
    const currentPath = window.location.pathname;
    const submitBtn = document.getElementById('submit-btn');
    if (!submitBtn) return; // Safety check

    const isLoginPage = currentPath === '/login' || currentPath === '/';
    const isRegisterPage = currentPath === '/register';

    if (isLoginPage && submitBtn.innerText.trim() !== "Login") {
        // Force to login mode
        setLoginMode();
    } else if (isRegisterPage && submitBtn.innerText.trim() !== "Create Account") {
        // Force to register mode
        setRegisterMode();
    }
}

function setLoginMode() {
    const subtitle = document.getElementById('auth-subtitle');
    const toggleLink = document.getElementById('toggle-msg');
    const authForm = document.getElementById('auth-form');
    const title = document.querySelector('.auth-header h2');
    const confirmGroup = document.getElementById('confirm-pass-group');
    const confirmInput = document.getElementById('confirm_field');
    const submitBtn = document.getElementById('submit-btn');

    if (title) title.innerText = "SECURE STARTUP VAULT";
    if (subtitle) subtitle.innerText = "Welcome back! Please login to your account.";
    if (toggleLink) toggleLink.innerHTML = 'Don\'t have an account? <a href="javascript:void(0)" onclick="toggleAuth()">Register</a>';
    if (authForm) authForm.action = "/login";
    if (submitBtn) submitBtn.innerText = "Login";
    if (confirmGroup) confirmGroup.style.display = "none";
    if (confirmInput) {
        confirmInput.required = false;
        confirmInput.style.display = "none";
    }
}

function setRegisterMode() {
    const subtitle = document.getElementById('auth-subtitle');
    const toggleLink = document.getElementById('toggle-msg');
    const authForm = document.getElementById('auth-form');
    const title = document.querySelector('.auth-header h2');
    const confirmGroup = document.getElementById('confirm-pass-group');
    const confirmInput = document.getElementById('confirm_field');
    const submitBtn = document.getElementById('submit-btn');

    if (title) title.innerText = "CREATE ACCOUNT";
    if (subtitle) subtitle.innerText = "Join the most secure vault for your startup.";
    if (toggleLink) toggleLink.innerHTML = 'Already have an account? <a href="javascript:void(0)" onclick="toggleAuth()">Login</a>';
    if (authForm) authForm.action = "/register";
    if (submitBtn) submitBtn.innerText = "Create Account";
    if (confirmGroup) confirmGroup.style.display = "block";
    if (confirmInput) {
        confirmInput.required = true;
        confirmInput.style.display = "block";
    }
}

function toggleAuth() {
    const submitBtn = document.getElementById('submit-btn');
    const isLoginMode = submitBtn.innerText.trim() === "Login";

    if (isLoginMode) {
        setRegisterMode();
    } else {
        setLoginMode();
    }
}