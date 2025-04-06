from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException
import shutil
import os
import logging
from typing import Tuple
from PIL import Image
import io
import uuid
import re

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
TARGET_SIZE = (640, 640)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helpers
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_filename(filename: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)

def resize_image(image_data: bytes, size: Tuple[int, int] = TARGET_SIZE) -> bytes:
    try:
        img = Image.open(io.BytesIO(image_data))
        if img.mode == "RGBA":
            img = img.convert("RGB")

        aspect_ratio = img.width / img.height
        if aspect_ratio > 1:
            new_w = size[0]
            new_h = int(new_w / aspect_ratio)
        else:
            new_h = size[1]
            new_w = int(new_h * aspect_ratio)

        img_resized = img.resize((new_w, new_h), Image.LANCZOS)
        final_img = Image.new("RGB", size, (255, 255, 255))
        final_img.paste(img_resized, ((size[0] - new_w) // 2, (size[1] - new_h) // 2))

        buffer = io.BytesIO()
        final_img.save(buffer, format="JPEG", quality=90)
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"Resizing failed: {str(e)}")
        raise

# Routes
@app.get("/")
def read_root():
    return {"message": "Welcome to Smart Waste Segregator API!"}

@app.post("/classify-image/")
async def classify_image(file: UploadFile = File(...)):
    try:
        if not allowed_file(file.filename):
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPG, JPEG, PNG allowed.")

        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large. Limit: 5MB.")

        safe_name = secure_filename(file.filename)
        file_ext = safe_name.rsplit(".", 1)[-1]
        unique_name = f"{uuid.uuid4()}.{file_ext}"
        original_path = os.path.join(UPLOAD_FOLDER, unique_name)

        with open(original_path, "wb") as f:
            f.write(contents)

        try:
            resized_data = resize_image(contents)
            resized_name = f"resized_{unique_name}"
            resized_path = os.path.join(UPLOAD_FOLDER, resized_name)
            with open(resized_path, "wb") as f:
                f.write(resized_data)

            original_size = os.path.getsize(original_path)
            resized_size = os.path.getsize(resized_path)

            logger.info(f"{file.filename} uploaded and resized")

            return JSONResponse(content={
                "status": "success",
                "filename": file.filename,
                "resized_filename": resized_name,
                "resized_dimensions": f"{TARGET_SIZE[0]}x{TARGET_SIZE[1]}",
                "original_size_kb": round(original_size / 1024, 2),
                "resized_size_kb": round(resized_size / 1024, 2),
                "message": "File uploaded and resized successfully. ML prediction pending."
            })

        except Exception:
            return JSONResponse(content={
                "status": "partial_success",
                "filename": file.filename,
                "message": "File uploaded but image resizing failed."
            })

    except HTTPException as he:
        logger.warning(f"Client error: {he.detail}")
        return JSONResponse(status_code=he.status_code, content={"status": "error", "message": he.detail})

    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return JSONResponse(status_code=500, content={"status": "error", "message": "Internal server error."})
