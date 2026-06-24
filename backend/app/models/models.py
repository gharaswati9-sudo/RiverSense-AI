from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from app.database import Base
import datetime

class Upload(Base):
    __tablename__ = "uploads"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    location = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.datetime.utcnow)

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"))
    health_score = Column(Float, nullable=False)
    species_count = Column(Integer, nullable=False)
    report_path = Column(String, nullable=True)

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analysis_results.id"))
    alert_type = Column(String, nullable=False)
    message = Column(String, nullable=False)
    sent_to = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)