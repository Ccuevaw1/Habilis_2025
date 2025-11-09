const CONFIG = {

    API_URL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://localhost:8000'
        : 'https://habilis2025-production.up.railway.app'
};
