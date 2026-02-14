class EasyProService {

    async getUserData() {
        // 1. Check for token in URL
        const params = new URLSearchParams(window.location.search);
        const token = params.get('token');

        if (token) {
            // Store token for ChatService to use
            localStorage.setItem('chat_token', token);

            // Clean URL
            window.history.replaceState({}, document.title, window.location.pathname);

            // Decode token to get user data
            try {
                const payload = this.parseJwt(token);
                return {
                    id: payload.id,
                    nombre: payload.nombre
                };
            } catch (e) {
                console.error("Invalid token:", e);
                // Fallback to existing logic or throw
            }
        }

        // Check if we have a stored token
        const storedToken = localStorage.getItem('chat_token');
        if (storedToken) {
            try {
                const payload = this.parseJwt(storedToken);
                // Optional: Check expiration
                if (payload.exp * 1000 > Date.now()) {
                    return {
                        id: payload.id,
                        nombre: payload.nombre
                    };
                } else {
                    localStorage.removeItem('chat_token');
                }
            } catch (e) {
                localStorage.removeItem('chat_token');
            }
        }

        // Fallback to original logic (fetching from local easypro)
        // CHECK: Is this still needed? The user asked for "intranet user -> easychat".
        // If the old way is irrelevant, we could remove it, but for backward compat might be safe to keep if ENV is set.

        const localUrlRaw = import.meta.env.VITE_LOCAL_HOST_EASYPRO;
        if (!localUrlRaw) {
            // If no fetching configured and no token, we can't do much.
            // Maybe return null or throw.
            throw new Error('No authentication token found and VITE_LOCAL_HOST_EASYPRO not set');
        }

        const localUrl = typeof localUrlRaw === 'string' ? localUrlRaw.trim().replace(/\/$/, '') : '';

        const response = await fetch(`${localUrl}/api/user`, {
            method: 'GET',
            credentials: 'include',
            headers: { 'Accept': 'application/json' }
        });

        if (!response.ok) {
            const bodyText = await response.text().catch(() => '');
            throw new Error(`EasyPro /api/user failed: ${response.status} ${response.statusText}${bodyText ? ` - ${bodyText.slice(0, 200)}` : ''}`);
        }

        const data = await response.json();
        const rawId = data?.id ?? data?.user?.id ?? data?.data?.id;
        const rawNombre = data?.nombre ?? data?.name ?? data?.user?.nombre ?? data?.user?.name;

        if (rawId == null || (typeof rawId === 'string' && rawId.trim() === '')) {
            throw new Error('EasyPro /api/user: missing id in response');
        }
        if (rawNombre == null || (typeof rawNombre === 'string' && rawNombre.trim() === '')) {
            throw new Error('EasyPro /api/user: missing nombre/name in response');
        }

        return { id: rawId, nombre: rawNombre };
    }

    parseJwt(token) {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function (c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
            return JSON.parse(jsonPayload);
        } catch (e) {
            return {};
        }
    }
}
export default EasyProService;