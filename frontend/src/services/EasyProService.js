class EasyProService {
    
    async getUserData() {
        
        const localUrlRaw = import.meta.env.VITE_LOCAL_HOST_EASYPRO;
        const localUrl = typeof localUrlRaw === 'string' ? localUrlRaw.trim().replace(/\/$/, '') : '';
        if (!localUrl) {
            throw new Error('Missing env var: VITE_LOCAL_HOST_EASYPRO');
        }

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
        

        let datos= { id: rawId, nombre: rawNombre };
        return  datos ;

    }
}
export default EasyProService;