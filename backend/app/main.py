from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.models import models
from app.routes import upload
from app.routes import analysis
from app.routes import reports

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RiverSense AI API",
    description="Automated eDNA biodiversity monitoring and alert system for Indian riverways.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # The default Next.js port
    allow_credentials=True,
    allow_methods=["*"], # Allows all HTTP methods (POST, GET, etc.)
    allow_headers=["*"], # Allows all headers
)
app.include_router(upload.router)
app.include_router(analysis.router)
app.include_router(reports.router)

@app.get("/")
def home():
    return {
        "status": "online", 
        "message": "RiverSense API is LIVE and ready for DNA data."
    }