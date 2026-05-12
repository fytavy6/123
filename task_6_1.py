import secrets
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
 
app = FastAPI(title="Task 6.1 — Basic Auth")
 
security = HTTPBasic()
 
VALID_USERNAME = "admin"
VALID_PASSWORD = "secret"
 
 
def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, VALID_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, VALID_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
 
 
@app.get("/login")
def login(username: str = Depends(verify_credentials)):
    return {"message": "You got my secret, welcome"}