# 🎵 Spotify Downloader - Versión Mejorada

Una aplicación moderna y completa para descargar música desde Spotify con integración directa a la API y mantenimiento automático de sesión.

## ✨ Características Principales

### 🔐 Autenticación Avanzada de Spotify
- **Conexión directa** con la API oficial de Spotify
- **Mantenimiento automático de sesión** - no necesitas reconectarte constantemente
- **Cache inteligente** de tokens de acceso
- **Verificación automática** de validez de sesión cada 5 minutos
- **Reconexión automática** al iniciar la aplicación

### 📋 Gestión Completa de Playlists
- **Visualización de todas tus playlists** de Spotify
- **Acceso a "Canciones que te gustan"** (Liked Songs)
- **Carga progresiva** con indicador de progreso
- **Información detallada** de cada playlist (número de canciones, propietario)
- **Navegación intuitiva** entre playlists y canciones

### 🎧 Descarga Individual y Masiva
- **Descarga individual** de canciones con un clic
- **Descarga completa de playlists** con confirmación
- **Progreso en tiempo real** para cada descarga
- **Manejo inteligente de errores** con opción de reintentar
- **Integración completa** con el sistema de descarga existente

### 🎨 Interfaz Moderna
- **Diseño moderno** con tema oscuro
- **Iconos descriptivos** para mejor usabilidad
- **Indicadores visuales** de estado de conexión
- **Botones contextuales** que cambian según el estado
- **Scrolling fluido** para listas largas de canciones

## 🚀 Instalación y Configuración

### Requisitos Previos
```bash
pip install PyQt6 spotipy yt-dlp eyed3 requests pillow
```

### Configuración de Spotify Developer

1. **Crear aplicación en Spotify:**
   - Ve a [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Haz clic en "Create an App"
   - Llena nombre y descripción
   - Acepta los términos

2. **Configurar Redirect URI:**
   - En tu aplicación, haz clic en "Settings"
   - En "Redirect URIs" agrega: `http://127.0.0.1:8080/callback`
   - Haz clic en "Add" y luego "Save"

3. **Obtener credenciales:**
   - Copia el "Client ID"
   - Haz clic en "Show client secret" y copia el "Client Secret"

### Primera Conexión

1. **Ejecutar la aplicación:**
   ```bash
   python main.py
   ```

2. **Configurar Spotify:**
   - Ve a la pestaña "🎧 Spotify"
   - Ingresa tu Client ID y Client Secret
   - Haz clic en "🔗 Conectar con Spotify"

3. **Autorizar la aplicación:**
   - Se abrirá tu navegador
   - Inicia sesión en Spotify
   - Haz clic en "AUTHORIZE"
   - Copia la URL de la página de error que aparece
   - Pégala en el campo solicitado

4. **¡Listo!** La sesión se mantendrá automáticamente

## 💡 Uso de la Aplicación

### Navegar por tus Playlists
1. Una vez conectado, verás todas tus playlists automáticamente
2. Haz clic en cualquier playlist para ver sus canciones
3. La información se carga progresivamente

### Descargar Canciones
**Individual:**
- Haz clic en "⬇️ Descargar" al lado de cualquier canción
- El botón mostrará el progreso y cambiará a "✅ Completado"

**Playlist completa:**
- Haz clic en "⬇️ Descargar Toda la Playlist"
- Confirma la descarga
- Ve el progreso en la página principal

### Gestión de Sesión
- **Reconexión automática:** Al abrir la app, se conecta automáticamente si tienes credenciales guardadas
- **Verificación de sesión:** Cada 5 minutos verifica que la sesión siga activa
- **Desconexión manual:** Usa el botón "🔌 Desconectar" para cerrar sesión

## 📁 Estructura de Archivos

```
downloads/
├── Spotify_Playlist/     # Playlists descargadas desde Spotify
├── *.mp3                 # Canciones individuales
└── ...

config/
├── spotify_settings.json        # Configuración de Spotify (guardado automático)
├── default_spotify_settings.json # Configuración por defecto
└── settings.json               # Configuración general

.spotify_cache              # Cache automático de tokens (no editar)
```

## 🔧 Funcionalidades Técnicas

### Mantenimiento de Sesión
- **Token caching:** Los tokens se guardan automáticamente en `.spotify_cache`
- **Renovación automática:** Los tokens se renuevan automáticamente cuando expiran
- **Verificación periódica:** Timer que verifica la validez cada 5 minutos
- **Reconexión inteligente:** Intenta reconectar automáticamente en caso de error

### Sistema de Descarga Mejorado
- **Workers independientes:** Cada descarga usa un worker thread separado
- **Gestión de errores:** Manejo robusto de errores con opciones de reintento
- **Progreso detallado:** Indicadores visuales de progreso para cada operación
- **Integración completa:** Usa el sistema de búsqueda y descarga existente

### Gestión de Metadatos
- **Información completa:** Título, artista, álbum, año, género, carátula
- **Carátulas HD:** Descarga automática de carátulas en alta resolución
- **Tags ID3:** Metadatos compatibles con todos los reproductores

## 🐛 Solución de Problemas

### Problemas de Conexión
- **Error "Invalid client":** Verifica que el Client ID y Secret sean correctos
- **Error "Invalid redirect URI":** Asegúrate de haber agregado exactamente `http://127.0.0.1:8080/callback`
- **Sesión expirada:** La app debería reconectar automáticamente, pero puedes usar "🔄 Reconectar"

### Problemas de Descarga
- **Canción no encontrada:** Algunas canciones pueden no estar disponibles en YouTube Music
- **Error de metadatos:** Verifica que tienes permisos de escritura en la carpeta de descarga
- **Descarga lenta:** Depende de tu conexión a internet y la disponibilidad del contenido

### Interfaz
- **Playlists no cargan:** Verifica tu conexión a internet y estado de Spotify
- **Botones no responden:** Reinicia la aplicación
- **Tema no se aplica:** Verifica que el archivo `dark_theme.qss` exista

## 📝 Changelog

### Versión 2.0 - Integración Completa de Spotify
- ✅ Autenticación directa con API de Spotify
- ✅ Mantenimiento automático de sesión
- ✅ Visualización completa de playlists
- ✅ Descarga individual y masiva desde Spotify
- ✅ Interfaz moderna y responsive
- ✅ Gestión inteligente de errores
- ✅ Cache automático de configuración
- ✅ Verificación periódica de sesión

### Próximas Funcionalidades
- 🔄 Sincronización automática de playlists
- 🎨 Temas personalizables
- 📊 Estadísticas de descarga
- 🔍 Búsqueda avanzada dentro de playlists
- 📱 Optimización para pantallas pequeñas

## 🤝 Contribuciones

Este proyecto está en constante desarrollo. Si encuentras bugs o tienes sugerencias:

1. Revisa los logs en `spotify_downloader.log`
2. Ejecuta `python test_spotify_integration.py` para diagnosticar problemas
3. Reporta issues con información detallada

## ⚖️ Disclaimer

Esta aplicación es para uso educativo y personal únicamente. Asegúrate de cumplir con los términos de servicio de Spotify y las leyes de derechos de autor de tu país.

---

**Desarrollado con ❤️ para la comunidad de música**
