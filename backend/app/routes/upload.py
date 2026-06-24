from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session
from Bio import SeqIO
import os
from app.database import get_db
from app.models.models import Upload

# creates a grouping for our endpoints
router = APIRouter(prefix="/upload", tags=["Upload"])

# Creates a folder to store the uploaded DNA files
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def generate_6_mers(sequence: str) -> list:
    """Converts a raw DNA sequence string into overlapping 6-mer tokens."""
    return [sequence[i:i+6] for i in range(len(sequence) - 5)]

@router.post("")
async def upload_edna_file(
    location: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Reject invalid file extensions
    if not file.filename.endswith(('.fastq', '.fasta', '.fa', '.fq', '.pdf' , '.txt')):
        return {"error": "Invalid file format. Please upload a valid sequence or report file."}
    
    # 2. Save the file to your computer using its original filename
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    # 3. Save the record into your database
    db_upload = Upload(filename=file.filename, location=location)
    db.add(db_upload)
    db.commit()
    db.refresh(db_upload)
    
    # 4. Use BioPython safely ONLY if it's a sequence file
    parsed_reads = []
    if file.filename.endswith(('.fastq', '.fasta', '.fa', '.fq')):
        file_format = "fastq" if file.filename.endswith((".fastq", ".fq")) else "fasta"
        try:
            with open(file_path, "r") as handle:
                for i, record in enumerate(SeqIO.parse(handle, file_format)):
                    if i >= 100: # Hackathon performance trick
                        break
                    raw_seq = str(record.seq).upper()
                    k_mers = generate_6_mers(raw_seq)
                    parsed_reads.append({"id": record.id, "kmers": k_mers})
        except Exception as e:
            print(f"BioPython parsing bypassed or failed: {e}")
            
    return {
        "message": "File processed and metadata saved successfully.",
        "upload_id": db_upload.id, # Next.js receives this database ID
        "location": db_upload.location,
        "total_parsed_reads": len(parsed_reads),
        "preview_tokens": parsed_reads[0]["kmers"][:5] if parsed_reads else []
    }