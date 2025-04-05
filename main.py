from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import shutil
import os

app = FastAPI()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "Welcome to Smart Waste Segregator API!"}

@app.post("/classify-image/")
async def classify_image(file: UploadFile = File(...)):
    # Save uploaded image to disk
    file_location = f"{UPLOAD_FOLDER}/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Placeholder - ML Model to be added here

    return JSONResponse(content={
        "filename": file.filename,
        "status": "Received",
        "message": "File uploaded successfully. Classification pending ML integration."
    })
