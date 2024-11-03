from re import template
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import  FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os

from flask import logging, render_template

app = FastAPI()
templates = Jinja2Templates(directory="templates")


# Configure the upload folder
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER,exist_ok=True)

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="static"),name="static")

# Endpoint to home
@app.get("/", response_class=HTMLResponse)
async def home_section(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})  

# Endpoint to upload a file
@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    try:
       file_location = os.path.join(UPLOAD_FOLDER, file.filename)
       with open(file_location, "wb+") as file_object:
           file_content = await file.read()
           file_object.write(file_content)
       # Determine file format based on the filename extension 
       file_format = file.filename.split('.')[-1] if '.' in file.filename else "unknown"
    
       return templates.TemplateResponse("home.html", {
            "request": {"headers": {}, "path": "/"},
            "filename": file.filename,
            "file_size": len(file_content),
            "file_format": file_format  # Corrected: Added missing comma here
       })
    except Exception as e:
        logging.error(f"Error uploading file: {e}")
        return HTMLResponse(content="<h1>Internal Server Error</h1>", status_code=500)   


@app.get("/uploads/")
async def list_uploaded_files():
    files = os.listdir(UPLOAD_FOLDER)
    files_info = []

    for filename in files:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file_size = os.path.getsize(file_path)
        file_format = filename.split('.')[-1] if '.' in filename else "unknown"
        files_info.append({
            "file_name": filename,
            "file_size": file_size,
            "file_format": file_format,
        })
        
    return {"uploaded_files": files_info, "total_files": len(files)}
    
# Endpoint to download a file
@app.get("/files/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        return HTMLResponse(content="<h1>File not found</h1>", status_code=404)
    return FileResponse(file_path)

# Endpoint to delete a file
@app.delete("/files/{filename}")
async def delete_file(filename: str):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": f"File '{filename}' deleted successfully."}
    else:
        raise HTTPException(status_code=404, detail="File not found")
    

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app,host="127.0.0.1",port=8000)