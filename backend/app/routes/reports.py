import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

# Database Core Mappings
from app.database import get_db
from app.models.models import Upload, AnalysisResult, Alert
from app.services.report_generator import generate_txt_report
from app.services.email_service import send_alert_email

# ReportLab Visual Layout Machinery
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

router = APIRouter(prefix="/report", tags=["Report Generation"])

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

@router.post("/generate/{analysis_id}")
def create_reports(analysis_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # 1. Gather all linked database records for authentic report logs
    result = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Analysis records not found")

    upload_record = db.query(Upload).filter(Upload.id == result.upload_id).first()
    alerts = db.query(Alert).filter(Alert.analysis_id == analysis_id).all()
    alert_messages = [a.alert_type for a in alerts]

    # Use your exact original filename layout to maintain downstream alignment
    pdf_path = f"{REPORTS_DIR}/report_{analysis_id}.pdf"

    # 2. ADVANCED REPORTLAB INFRASTRUCTURE GENERATION
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    story = []
    base_styles = getSampleStyleSheet()

    # Typography Design Sheet
    title_style = ParagraphStyle(
        'DocTitle', parent=base_styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=22, leading=26,
        textColor=colors.HexColor('#0f172a'), spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle', parent=base_styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9, leading=12,
        textColor=colors.HexColor('#3b82f6'), textTransform='uppercase', spaceAfter=15
    )
    section_heading = ParagraphStyle(
        'SectionHeading', parent=base_styles['Heading2'],
        fontName='Helvetica-Bold', fontSize=12, leading=16,
        textColor=colors.HexColor('#1e293b'), spaceBefore=15, spaceAfter=8
    )
    meta_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.HexColor('#475569'))
    meta_val = ParagraphStyle('MetaValue', fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor('#0f172a'))

    # HEADER: Professional Government/Agency Style Letterhead
    story.append(Paragraph("RIVERSENSE AI • NATIONAL BIODIVERSITY INFRASTRUCTURE", subtitle_style))
    story.append(Paragraph("Ecosystem Health & Taxonomic Audit Report", title_style))
    
    # Decorative Horizontal Rule Line
    divider = Table([[""]], colWidths=[532], rowHeights=[2])
    divider.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#3b82f6'))]))
    story.append(divider)
    story.append(Spacer(1, 12))

    # SECTION A: METADATA INFORMATION LEDGER
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta_data = [
        [Paragraph("Analysis ID:", meta_label), Paragraph(str(analysis_id), meta_val),
         Paragraph("Generated On:", meta_label), Paragraph(timestamp_str, meta_val)],
        [Paragraph("Target Waterway:", meta_label), Paragraph(upload_record.location.title() if upload_record else "Unknown Stretch", meta_val),
         Paragraph("Source Datafile:", meta_label), Paragraph(upload_record.filename if upload_record else "eDNA_Sequence.txt", meta_val)]
    ]
    meta_table = Table(meta_data, colWidths=[100, 166, 100, 166])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # SECTION B: VISUAL HEALTH CALLOUT CARD BLOCK
    story.append(Paragraph("Ecosystem Diagnostics Baseline", section_heading))
    score_value = result.health_score
    
    # Dynamic styling theme based on deep learning model scoring scales
    if score_value < 30:
        status_text, theme_color, bg_color = "CRITICAL COLLAPSE", colors.HexColor('#991b1b'), colors.HexColor('#fee2e2')
    elif score_value < 60:
        status_text, theme_color, bg_color = "WARNING STATE", colors.HexColor('#9a3412'), colors.HexColor('#ffedd5')
    else:
        status_text, theme_color, bg_color = "HEALTHY ENVIRONMENT", colors.HexColor('#065f46'), colors.HexColor('#d1fae5')

    score_num_style = ParagraphStyle('ScoreNum', fontName='Helvetica-Bold', fontSize=32, leading=34, textColor=theme_color, alignment=TA_CENTER)
    score_lbl_style = ParagraphStyle('ScoreLbl', fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=colors.HexColor('#475569'), alignment=TA_CENTER)
    status_style = ParagraphStyle('StatusStyle', fontName='Helvetica-Bold', fontSize=14, leading=16, textColor=theme_color, alignment=TA_CENTER)

    card_data = [
        [Paragraph(f"{score_value:.1f} / 100", score_num_style), Paragraph(status_text, status_style)],
        [Paragraph("Calculated Health Index", score_lbl_style), Paragraph("Ecosystem Security Classification", score_lbl_style)]
    ]
    card_table = Table(card_data, colWidths=[266, 266])
    card_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_color),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 12),
        ('LINEVERTICAL', (0,0), (0,-1), 1, colors.white),
    ]))
    story.append(card_table)
    story.append(Spacer(1, 15))

    # SECTION C: TABLE PATTERN DATA STRUCTURE LOOKUP
    story.append(Paragraph("Taxonomic Structure Breakdown", section_heading))
    th_style = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=colors.white)
    td_style = ParagraphStyle('TD', fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor('#1e293b'))
    
    metrics_data = [
        [Paragraph("Observed Indicator Dimension", th_style), Paragraph("Evaluated Structural Metric Data", th_style)],
        [Paragraph("Identified Species Richness Count", td_style), Paragraph(f"{result.species_count} Distinct Taxa Cataloged", td_style)],
        [Paragraph("Ecosystem Bio-Complexity State", td_style), Paragraph("Stable Profile Base" if score_value >= 60 else "Compromised Genetic Sequence Trail", td_style)],
        [Paragraph("Classification Framework Precision", td_style), Paragraph("Fine-Tuned DNABERT Multi-Class Array Inference Core", td_style)]
    ]
    metrics_table = Table(metrics_data, colWidths=[240, 292])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f1f5f9')]),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 15))

    # SECTION D: REGULATORY WARNING DISPATCH CARD CONTAINERS
    story.append(Paragraph("Automated Policy Action Framework Dispatches", section_heading))
    if not alerts:
        ok_style = ParagraphStyle('OKBox', fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor('#065f46'))
        alert_box = Table([[Paragraph("✓ Verification Check Complete: No threshold alerts triggered. Waterway segment conforms to current biological baseline metrics.", ok_style)]], colWidths=[532])
        alert_box.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
            ('PADDING', (0,0), (-1,-1), 10),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#bbf7d0'))
        ]))
        story.append(alert_box)
    else:
        alert_story_elements = []
        alert_title_style = ParagraphStyle('AlertTitle', fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=colors.HexColor('#991b1b'))
        alert_text_style = ParagraphStyle('AlertText', fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor('#7f1d1d'))
        
        for idx, alert in enumerate(alerts):
            alert_cell = [
                Paragraph(f"⚠️ Dispatch Incident #{idx+1}: {alert.alert_type}", alert_title_style),
                Paragraph(f"<b>Target Endpoint Vector:</b> {alert.sent_to}", alert_text_style),
                Paragraph(f"<b>Telemetry Log Summary:</b> {alert.message}", alert_text_style)
            ]
            alert_table = Table([[alert_cell]], colWidths=[532])
            alert_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fef2f2')),
                ('PADDING', (0,0), (-1,-1), 8),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#fca5a5')),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8)
            ]))
            alert_story_elements.append(alert_table)
            alert_story_elements.append(Spacer(1, 6))
        story.append(KeepTogether(alert_story_elements))

    story.append(Spacer(1, 25))
    footer_style = ParagraphStyle('FooterText', fontName='Helvetica-Oblique', fontSize=8, leading=10, textColor=colors.HexColor('#94a3b8'), alignment=TA_CENTER)
    story.append(Paragraph("This is an automated biological analytics document processed securely via Next.js and FastAPI infrastructure.", footer_style))
    
    # Render the styled PDF
    doc.build(story)

    # 3. Generate backup plain text report tracking log
    txt_path = generate_txt_report(analysis_id, result.health_score, alert_messages)

    # Commit layout paths to tracking DB record fields
    result.report_path = pdf_path
    db.commit()

    # 4. BACKGROUND EMAIL SERVICE TRANSMISSION PIPELINE
    test_recipient = "your.email@gmail.com"  # Replace this with your test account string
    background_tasks.add_task(
        send_alert_email, 
        target_department="Central Pollution Control Board", 
        recipient_email=test_recipient, 
        analysis_id=analysis_id, 
        pdf_path=pdf_path, 
        score=result.health_score
    )

    return {
        "message": "Reports successfully generated and alert email dispatched.",
        "download_pdf_url": f"/report/download/{analysis_id}?file_format=pdf",
        "download_txt_url": f"/report/download/{analysis_id}?file_format=txt"
    }

@router.get("/download/{analysis_id}")
def download_report(analysis_id: int, file_format: str = "pdf"):
    extension = "pdf" if file_format.lower() == "pdf" else "txt"
    file_path = f"reports/report_{analysis_id}.{extension}"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found. Generate it first.")

    return FileResponse(path=file_path, filename=f"RiverSense_Report_{analysis_id}.{extension}")