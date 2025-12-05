# Servidor de subida (FastAPI)

Este servidor en Python (FastAPI) recibe un campo `phone` y múltiples archivos vía `multipart/form-data`, los guarda en la carpeta `uploads/` y devuelve un JSON con metadatos (nombre almacenado, tamaño, mime, sha256).

Requisitos
- Python 3.9+
- Dependencias en `requirements.txt`

Instalación y ejecución (PowerShell):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Endpoint
- POST /upload
  - Form fields: `phone` (string), `files` (archivos, multiple)
  - Respuesta: JSON con `phone` limpio y arreglo `files` con metadatos.

Notas
- El servidor permite CORS desde cualquier origen para facilitar desarrollo local. Para producción, restringe `allow_origins`.
- El servicio guarda archivos en `uploads/`. Asegúrate de gestionar espacio y permisos en producción.

ImageMagick (opcional)
--
El servidor detecta ImageMagick en la máquina y, si está disponible, genera derivadas para imágenes:
- Thumbnail (max 800x800) y versión WebP (si la conversión es posible).

Instalación en Windows
1. Descarga ImageMagick desde https://imagemagick.org/script/download.php#windows (elige una versión portátil o instalador con "Install legacy utilities (e.g., convert)" si necesitas `convert`).
2. Asegúrate de marcar la opción "Add application directory to your system path" durante la instalación para que `magick` o `convert` estén disponibles en PATH.

Comprobación rápida (PowerShell):

```powershell
magick -version
# o
convert -version
```

Si el comando devuelve versión, el servidor usará ImageMagick cuando procese imágenes.
