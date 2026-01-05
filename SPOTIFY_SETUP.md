# Configuración de Spotify para el Downloader

## Pasos para configurar la integración con Spotify:

### 1. Crear una aplicación en Spotify

1. Ve a [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Inicia sesión con tu cuenta de Spotify
3. Haz clic en "Create an App"
4. Completa los campos:
   - **App name**: Spotify Downloader (o el nombre que prefieras)
   - **App description**: Aplicación para descargar música de Spotify
   - **Redirect URI**: `http://localhost:8080/callback`
5. Acepta los términos de servicio
6. Haz clic en "Create"

### 2. Obtener las credenciales

1. Una vez creada la aplicación, ve al dashboard de tu app
2. Haz clic en "Settings"
3. Copia el **Client ID**
4. Haz clic en "View client secret" y copia el **Client Secret**

### 3. Configurar la aplicación

1. Abre la aplicación Spotify Downloader
2. Ve a la pestaña "🎧 Spotify"
3. Pega el **Client ID** en el campo correspondiente
4. Pega el **Client Secret** en el campo correspondiente
5. Verifica que el **Redirect URI** sea: `http://localhost:8080/callback`
6. Haz clic en "Conectar con Spotify"

### 4. Autorizar la aplicación

1. Se abrirá tu navegador web con la página de autorización de Spotify
2. Inicia sesión en Spotify si no lo has hecho
3. Autoriza la aplicación haciendo clic en "Authorize"
4. Serás redirigido a `localhost:8080/callback` - esto es normal
5. Regresa a la aplicación, donde deberías ver "Conectado exitosamente"

### 5. Usar la funcionalidad

Una vez conectado, podrás:
- Ver todas tus playlists
- Ver tus canciones guardadas ("Canciones que te gustan")
- Descargar canciones individuales
- Descargar playlists completas

## Notas importantes:

- Las credenciales se guardan localmente en `config/spotify_config.json`
- La aplicación solo lee tus playlists y canciones, no modifica nada
- Las descargas se realizan buscando las canciones en YouTube y otras fuentes públicas
- Spotify no permite descargar directamente los archivos de audio por razones de copyright

## Solución de problemas:

### Error "Invalid client secret"
- Verifica que hayas copiado correctamente el Client Secret
- Asegúrate de que no haya espacios extra al principio o final

### Error "Invalid redirect URI"
- En el dashboard de Spotify, asegúrate de que el Redirect URI sea exactamente: `http://localhost:8080/callback`
- Verifica que el puerto 8080 no esté siendo usado por otra aplicación

### Error "Insufficient client scope"
- Esto puede ocurrir si la aplicación de Spotify no tiene los permisos correctos
- Intenta desconectar y volver a conectar

### No se muestran las playlists
- Verifica tu conexión a internet
- Asegúrate de que tu cuenta de Spotify tenga playlists creadas
- Intenta hacer clic en "Actualizar"
