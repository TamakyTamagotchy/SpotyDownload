import os, eyed3, requests, re, logging
from PIL import Image
from io import BytesIO

def update_mp3_metadata(filename, title, artist, album, cover_image_url, release_date, genre):
    try:
        # Ensure the file exists and is a valid MP3
        if not os.path.exists(filename):
            logging.error(f'Archivo no encontrado: {filename}')
            return False
        
        # Load the audio file with error handling
        audio = eyed3.load(filename)
        if audio is None:
            logging.error(f'No se pudo cargar el archivo de audio: {filename}')
            return False
        
        # Initialize tag if not exists
        if audio.tag is None:
            audio.initTag()
        
        # Normalizar artista a string si es una lista
        if isinstance(artist, list):
            artist_str = ", ".join(artist)
        else:
            artist_str = artist or "Artista Desconocido"
        
        # Metadatos básicos mejorados
        audio.tag.title = title or "Titulo Desconocido"
        audio.tag.artist = artist_str
        audio.tag.album = album or "Album Desconocido"
        
        # Limpiar y mejorar nombres de artistas
        if artist_str and ', ' in artist_str:
            # Si hay múltiples artistas, usar el principal como artista y guardar colaboradores
            artists_list = [a.strip() for a in artist_str.split(', ')]
            audio.tag.artist = artists_list[0]
            if len(artists_list) > 1:
                # Guardar artistas colaboradores en el campo albumartist
                audio.tag.album_artist = artist_str
        
        logging.info(f'Metadatos básicos: {audio.tag.title} - {audio.tag.artist} - {audio.tag.album}')

        # Año: solo año simple para evitar warnings TDRL
        if release_date:
            year_match = re.search(r'\b(19|20)\d{2}\b', str(release_date))
            if year_match:
                year = int(year_match.group())
                # Solo usar el año simple, no fechas completas
                audio.tag.recording_date = year
                logging.info(f'Año de grabación establecido: {year}')
            else:
                logging.warning(f'No se pudo extraer año válido de: {release_date}')
        else:
            audio.tag.recording_date = None

        # Género: usar directamente el género de Spotify sin normalización
        if genre and isinstance(genre, str) and genre.strip():
            audio.tag.genre = genre.strip()
            logging.info(f'Género establecido desde Spotify: {genre.strip()}')
        else:
            audio.tag.genre = None
            logging.info('No se estableció género específico')

        # Portada: detectar formato y aplicar correctamente
        if cover_image_url:
            try:
                logging.info(f'Descargando portada desde: {cover_image_url}')
                response = requests.get(cover_image_url, timeout=10)
                response.raise_for_status()
                image_content = response.content
                logging.info(f'Portada descargada, tamaño: {len(image_content)} bytes')
                
                # Detectar formato de imagen
                mime = "image/jpeg"  # Default fallback
                try:
                    img = Image.open(BytesIO(image_content))
                    if img.format:
                        format_to_mime = {
                            'JPEG': 'image/jpeg',
                            'PNG': 'image/png',
                            'GIF': 'image/gif',
                            'BMP': 'image/bmp',
                            'WEBP': 'image/webp'
                        }
                        mime = format_to_mime.get(img.format, 'image/jpeg')
                        logging.info(f'Formato de imagen detectado: {img.format}, MIME: {mime}')
                    img.verify()
                except Exception as pil_error:
                    logging.warning(f'No se pudo verificar la imagen con PIL: {pil_error}, usando JPEG como fallback')
                
                # Aplicar la portada al MP3
                audio.tag.images.set(3, image_content, mime, u"Cover")
                logging.info(f'Portada aplicada exitosamente con MIME: {mime}')
                
            except Exception as img_error:
                logging.error(f'Error en el procesamiento de la imagen de portada: {img_error}')

        # Save with specific ID3v2.4 version for maximum compatibility
        audio.tag.save(version=(2,3,0))
        
        return True
    
    except Exception as e:
        logging.error(f'Error en la actualización de metadatos: {e}')
        return False
