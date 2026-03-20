from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import uuid
import yt_dlp
import static_ffmpeg

# Inicializa ffmpeg para que yt-dlp pueda usarlo
static_ffmpeg.add_paths()

app = FastAPI(title="Video Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite conexiones desde Vite (localhost:5173) o cualquier móvil en la mis red
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directorio temporal para los videos descargados
TEMP_DIR = "descargas_temporales"
os.makedirs(TEMP_DIR, exist_ok=True)

class DownloadRequest(BaseModel):
    url: str
    cookie: Optional[str] = None

def remove_file(path: str):
    """Elimina el archivo después de haberlo enviado para no llenar el servidor."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Error al eliminar archivo: {e}")

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request

@app.get("/api/download")
async def download_video_endpoint(url: str, request: Request, background_tasks: BackgroundTasks):
    cookie_str = request.headers.get('Cookie') or request.headers.get('X-Cookie')
    
    if not url:
        raise HTTPException(status_code=400, detail="Se requiere una URL válida.")
    
    # Nombre de archivo único para evitar sobreescribir otros si te conectas al mismo tiempo
    file_id = str(uuid.uuid4())
    output_template = os.path.join(TEMP_DIR, f"{file_id}.%(ext)s")
    
    ydl_opts = {
        'outtmpl': output_template,
        'format_sort': ['vcodec:h264', 'ext:mp4:m4a'],
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'postprocessor_args': [
            '-vcodec', 'libx264',
            '-acodec', 'aac',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
        ],
        'quiet': True,
        'no_warnings': True,
    }

    # Lógica invencible de Cookies
    # 1. Checar si hay un archivo cookies.txt global (el que sacamos de la PWA/Script)
    import sys
    root_cookie_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies.txt")
    
    if os.path.exists(root_cookie_file):
        ydl_opts['cookiefile'] = root_cookie_file
    elif os.name == 'nt' or sys.platform == 'darwin':
        # 2. Solo extraemos del navegador de PC si estamos corriendo en tu Windows/Mac local
        # En la Nube (Linux) los servidores no tienen Firefox instalado, y esto causaría un Error Crítico.
        ydl_opts['cookiesfrombrowser'] = ('firefox', )
        
    # 3. Aún así, mandamos las headers de la WebView móvil por si acas
    if cookie_str:
        ydl_opts['http_headers'] = {
            'Cookie': cookie_str
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extraemos info primero para saber el nombre exacto final
            info_dict = ydl.extract_info(url, download=True)
            final_filename = ydl.prepare_filename(info_dict)
            
            # yt-dlp a veces cambia la extensión en el postproceso
            if not final_filename.endswith('.mp4'):
                final_filename = final_filename.rsplit('.', 1)[0] + '.mp4'

            # Devolvemos el archivo completo. 
            # BackgroundTasks borrará el archivo justo después de que la app termine de enviarlo
            background_tasks.add_task(remove_file, final_filename)
            return FileResponse(path=final_filename, media_type='video/mp4', filename="video_descargado.mp4")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante la descarga: {str(e)}")

@app.get("/")
def read_root():
    return {"mensaje": "¡El servidor del Descargador está funcionando a la perfección!"}
