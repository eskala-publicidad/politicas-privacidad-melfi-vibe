from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import hashlib
import os
from pathlib import Path
from typing import List, Optional
import shutil
import subprocess

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / 'uploads'
DERIVED_DIR = UPLOAD_DIR / 'derived'
UPLOAD_DIR.mkdir(exist_ok=True)
DERIVED_DIR.mkdir(exist_ok=True)

app = FastAPI(title='Servidor de subida')

# Allow local development from file:// or localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def find_imagemagick() -> Optional[str]:
    # Try common commands on Windows and Unix
    for cmd in ("magick", "convert"):
        try:
            subprocess.run([cmd, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return cmd
        except Exception:
            continue
    return None


IMAGEMAGICK_CMD = find_imagemagick()


def is_image_mime(mime: str) -> bool:
    return mime.startswith('image/')


def generate_image_derivatives(src: Path, derived_dir: Path, cmd: str) -> List[dict]:
    """Genera un thumbnail y una versión webp (si es posible) usando ImageMagick.
    Devuelve lista de metadatos de archivos generados.
    """
    metas = []
    base, ext = os.path.splitext(src.name)

    # thumbnail: limitar a 800x800 manteniendo aspect ratio
    thumb_name = f"{base}_thumb{ext}"
    thumb_path = derived_dir / thumb_name
    try:
        # magick convert syntax: magick input -resize 800x800\> output
        if cmd == 'magick':
            subprocess.run([cmd, str(src), '-resize', '800x800>', str(thumb_path)], check=True)
        else:
            subprocess.run([cmd, str(src), '-resize', '800x800>', str(thumb_path)], check=True)
        metas.append({
            'type': 'thumbnail',
            'filename': thumb_path.name,
            'size_bytes': thumb_path.stat().st_size,
            'sha256': sha256_file(thumb_path),
        })
    except Exception as e:
        # no bloquear el flujo si falla ImageMagick
        metas.append({'type': 'thumbnail', 'error': str(e)})

    # webp conversion
    webp_name = f"{base}.webp"
    webp_path = derived_dir / webp_name
    try:
        if cmd == 'magick':
            subprocess.run([cmd, str(src), str(webp_path)], check=True)
        else:
            subprocess.run([cmd, str(src), str(webp_path)], check=True)
        metas.append({
            'type': 'webp',
            'filename': webp_path.name,
            'size_bytes': webp_path.stat().st_size,
            'sha256': sha256_file(webp_path),
        })
    except Exception as e:
        metas.append({'type': 'webp', 'error': str(e)})

    return metas


@app.post('/upload')
async def upload(phone: str = Form(...), files: List[UploadFile] = File(...)):
    phone_clean = ''.join(c for c in phone if c.isdigit())
    if len(phone_clean) < 8 or len(phone_clean) > 15:
        raise HTTPException(status_code=400, detail='Número de teléfono inválido')

    if not files:
        raise HTTPException(status_code=400, detail='No se recibieron archivos')

    results = []
    for up in files:
        # Sanitize filename
        filename = os.path.basename(up.filename)
        dest = UPLOAD_DIR / filename
        # Avoid overwriting: if exists, append incremental suffix
        base, ext = os.path.splitext(filename)
        counter = 1
        while dest.exists():
            dest = UPLOAD_DIR / f"{base}_{counter}{ext}"
            counter += 1

        # Save file
        with dest.open('wb') as f:
            content = await up.read()
            f.write(content)

        # Compute metadata
        sha = sha256_file(dest)
        size = dest.stat().st_size
        file_meta = {
            'original_filename': up.filename,
            'stored_filename': dest.name,
            'mime_type': up.content_type,
            'size_bytes': size,
            'sha256': sha,
            'derived': []
        }

        # If it's an image and ImageMagick is available, generate derivatives
        if IMAGEMAGICK_CMD and is_image_mime(up.content_type):
            try:
                derived = generate_image_derivatives(dest, DERIVED_DIR, IMAGEMAGICK_CMD)
                file_meta['derived'] = derived
            except Exception as e:
                file_meta['derived_error'] = str(e)

        results.append(file_meta)

    return JSONResponse({'phone': phone_clean, 'files': results, 'imagemagick': bool(IMAGEMAGICK_CMD)})
