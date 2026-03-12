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

// remaining functions removed since mode is now handled by server-side
