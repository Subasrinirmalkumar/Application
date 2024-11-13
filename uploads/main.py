import logging
from urllib import request
import uuid
from fastapi import FastAPI, HTTPException, Request, UploadFile, Depends,File
from fastapi.responses import  FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from flask import session, redirect, url_for
from starlette.middleware.sessions import SessionMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext 
import os
from pymongo import MongoClient
from data_validation import LoginInput

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Middleware to handle sessions
app.add_middleware(SessionMiddleware, secret_key="subasri")

client = MongoClient("mongodb://localhost:27017/")  
db = client["myuserdatabase"] 
users_collection = db["users"] 
files_collection = db["files"]

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Function to hash passwords
def hash_password(password: str):
    return pwd_context.hash(password)

# Function to verify password hash
def verify_password(plain_password: str, hashed_password: str):
    print(plain_password, type(plain_password))
    print(hashed_password, type(hashed_password))
    return pwd_context.verify(plain_password, hashed_password)


# Configure the upload folder
UPLOAD_FOLDER = 'uploads' 
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Endpoint to home
@app.get("/", response_class=HTMLResponse)
async def home_section(request: Request):
    if "user" not in request.session:
        return templates.TemplateResponse("login.html", {"request": request, "is_logged_in": False})
    return templates.TemplateResponse("home.html", {"request": request, "is_logged_in": True})

@app.post("/login/")
async def login(request: Request,form_data: LoginInput):
    print(form_data.username,form_data.password)
    
    user = users_collection.find_one({"name":form_data.username},{'_id':0,'name':1,'password':1,'user_id':1})
    print(user)
    if user is None:
        print("0000")
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    if not verify_password(form_data.password, user["password"]):
        print("7700")
        raise HTTPException(status_code=400, detail="Invalid credentials")

    request.session["user"] = form_data.username
    return {"message": "Login successful", "user_id": user["user_id"]}

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

    


@app.post("/register/")
async def register(request: Request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    name = data.get("name")
    dob = data.get("dob")
    
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if not dob:
        raise HTTPException(status_code=400, detail="Date of birth is required")


    if users_collection.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed_password = hash_password(password)
    
    # Generate unique user ID
    user_id = str(uuid.uuid4())
    users_collection.insert_one({
        "password": hashed_password,
        "name": name,
        "dob": dob,
        "user_id": user_id,
        
    })

    return {"message": "Registration successful","user_id": user_id}

  

# Endpoint to upload a file
@app.post("/uploadfile/")
async def upload_file(request: Request,file: UploadFile = File(...)):
    if "user" not in request.session:
        raise HTTPException(status_code=401, detail="User must be logged in")
    try:
        file_location = os.path.join(UPLOAD_FOLDER, file.filename)
        
        # Check if the file already exists
        if os.path.exists(file_location):
            return HTMLResponse(content=f"File '{file.filename}' has already been uploaded.", status_code=400)
        
        with open(file_location, "wb+") as file_object:
            file_content = await file.read()
            file_object.write(file_content)
            
        file_data = {
            "filename": file.filename,
            "size": len(file_content),
            "format": file.filename.split('.')[-1] if '.' in file.filename else "unknown",
            "uploaded_by": request.session["user"]
        }
        files_collection.insert_one(file_data)

        return templates.TemplateResponse("home.html", {
            "request": request,
            "filename": file.filename,
            "file_size": len(file_content),
            "file_format": file_data["format"]
        })    
        
    except Exception as e:
        logging.error(f"Error uploading file: {e}")
        return HTMLResponse(content="<h1>Internal Server Error</h1>", status_code=500)   


@app.get("/uploads/")
async def list_uploaded_files(request: Request):
    # Check if user is logged in
    if "user" not in request.session:
        logging.error("User is not logged in.")
        raise HTTPException(status_code=401, detail="User must be logged in")
    
    try:
        # List files in the upload directory
        files = os.listdir(UPLOAD_FOLDER)
        
        # If no files are found, return an empty list
        if not files:
            logging.warning("No files found in the upload folder.")
        
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

        logging.info(f"Files found: {files_info}")
        return {"uploaded_files": files_info}

    except Exception as e:
        logging.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
import os

UPLOAD_FOLDER = 'uploads'  # This should be the folder where files are stored

@app.get("/files/{filename}")
async def download_file(filename: str, request: Request):
    # Check if the user is logged in
    if "user" not in request.session:
        raise HTTPException(status_code=401, detail="User must be logged in")
    
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    # Log file path for debugging
    print(f"Attempting to download file from {file_path}")

    # Check if the file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        return FileResponse(file_path, media_type='application/octet-stream', headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        # Log the exception for debugging
        print(f"Error serving file: {e}")
        raise HTTPException(status_code=500, detail="Error serving the file")

    
# Endpoint to delete a file
@app.delete("/files/{filename}")
async def delete_file(filename: str, request: Request):
    if "user" not in request.session:
        raise HTTPException(status_code=401, detail="User must be logged in")

    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        # Remove file metadata from MongoDB
        files_collection.delete_one({"filename": filename})
        return {"message": f"File '{filename}' deleted successfully."}
    else:
        raise HTTPException(status_code=404, detail="File not found")
    
@app.post("/logout/")
async def logout(request: Request):
    print("Logout request received")
    print(f"Session before logout: {request.session}")
    request.session.pop('user', None)  # Remove the 'user' from session
    print(f"Session after logout: {request.session}")
    return {"message": "Logout successful"}


@app.get("/check-login-status/")
async def check_login_status(request: Request):
    if "user" in request.session:
        return {"is_logged_in": True}
    return {"is_logged_in": False}

    

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app,host="127.0.0.1",port=8000,reload = True)
 
    
    