import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Upload, AnalysisResult, Alert
from app.ml_predictor import predict_from_report

# Grouping for our analysis endpoints
router = APIRouter(prefix="/analyze", tags=["Analysis Engine"])

@router.post("/{upload_id}")
def run_analysis(upload_id: int, db: Session = Depends(get_db)):
    # 1. Verify the uploaded file actually exists in the database record
    upload_record = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload_record:
        raise HTTPException(status_code=404, detail="Upload ID not found")

    # 2. RESOLVE FILEPATH ON SERVER DISK
    file_path = os.path.join("uploads", upload_record.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail=f"Physical file missing from server upload directory: {file_path}")

    # 3. RUN REAL AI INFERENCE VIA DNABERT PIPELINE
    try:
        ml_results = predict_from_report(
            kraken_report_path=file_path,
            location=upload_record.location,
            lat=25.3176,  # Default geospatial tracking metrics for mapping visualization
            lng=83.0062
        )
    except Exception as e:
        print(f"🧠 ML Inference Execution Engine Failure: {e}")
        raise HTTPException(status_code=500, detail=f"Machine learning model crashed during evaluation: {str(e)}")

    # 4. EXTRACT VALUES FROM MACHINE LEARNING CORE
    health_score = float(ml_results["biodiversity_score"])
    species_detected = int(ml_results["species_diversity"])
    
    # 5. SAVE REAL RESULTS TO DATABASE
    result = AnalysisResult(
        upload_id=upload_id, 
        health_score=health_score, 
        species_count=species_detected
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    
    # 6. DECISION ENGINE (Automated Alerts wired directly into Live ML Metrics)
    alerts_triggered = []
    
    # Alert Type A: Critical Health Drop
    if ml_results["alert_level"] == "CRITICAL" or health_score < 30:
        alert = Alert(
            analysis_id=result.id, 
            alert_type="Critical Biodiversity Collapse", 
            message=f"Ecosystem health score plummeted to {health_score:.2f} via genomic trail inspection.", 
            sent_to="Jal Shakti Ministry"
        )
        db.add(alert)
        alerts_triggered.append(alert.alert_type)
        
    # Alert Type B: Industrial/Bacterial Contamination Flag
    if ml_results["heavy_pollution"]:
        alert = Alert(
            analysis_id=result.id, 
            alert_type="Heavy Biological Contamination", 
            message=f"Severe concentration of toxic bacterial signatures observed. Dominant organism flagged: {ml_results['dominant_organism']}.", 
            sent_to="CPCB"
        )
        db.add(alert)
        alerts_triggered.append(alert.alert_type)
        
    # Alert Type C: Species Vulnerability Context
    if health_score < 50:
        alert = Alert(
            analysis_id=result.id, 
            alert_type="Species Extinction Risk",  
            message="Critical habitat breakdown registered. Key indicator species (e.g., Platanista gangetica profiles) flagged under immediate localized threat.", 
            sent_to="Wildlife Crime Control Bureau"
        )
        db.add(alert)
        alerts_triggered.append(alert.alert_type)
        
    db.commit()
    
    # Spy log output verification channel directly in your terminal instance
    print("\n" + "="*40)
    print("🧠 REAL DNABERT ML MODEL LIVE OUTPUT LOGGED TO DB:")
    print(ml_results)
    print("="*40 + "\n")
    
    # 7. RETURN FINAL COMPREHENSIVE JSON TO FRONTEND NEXT.JS APP
    return {
        "message": "Analysis complete",
        "upload_id": upload_id,
        "analysis_id": result.id,
        "calculated_health_score": round(health_score, 2),
        "status": "Critical Alerts Triggered" if alerts_triggered else "System Healthy",
        "active_alerts": alerts_triggered,
        "ml_summary_payload": ml_results  # Appends the raw details for extended UI visualization
    }