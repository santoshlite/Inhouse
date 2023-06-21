<script>
    // @ts-nocheck

    import { onMount } from 'svelte';
    let url="empty";
    function getURL(){
        url = window.location.href;
    }
    getURL();
    function validateEmail(event) {
        const input = event.target;
        if (!input.checkValidity()) {
            input.setCustomValidity('Please enter a valid email address.');
        } else {
            input.setCustomValidity('');
        }
    }

    function validatePassword(event) {
        const input = event.target;
        if (!input.checkValidity()) {
            input.setCustomValidity('Password must be at least 4 characters long.');
        } else {
            input.setCustomValidity('');
        }
    }
</script>


<svelte:head>
    <title>Inhouse | Authentification</title>
    <meta name="description" content="About this app" />
</svelte:head>

<style>
    @import '/src/routes/styles.css';
</style>

<div class="auth-container">
    <div class='wrapper-form'>
        <h3 class="welcome">Welcome to inhouse 🏠</h3>
        <p>URL: {url}</p>
        <p class="subtext">Create an account with your email address and password, or use your existing credentials if you already have an account.</p>
        <form action={import.meta.env.VITE_API_DOMAIN+"login"} method="POST" class="form">
            <input class="input-auth" type="email" id="email" name="email" placeholder="Email" oninput={validateEmail} required>
            <input class="input-auth" type="password" id="password" name="password" placeholder="Password" minlength="4" oninput={validatePassword} required>
            <button type="submit">Access</button>
        </form>
    </div>
</div>
