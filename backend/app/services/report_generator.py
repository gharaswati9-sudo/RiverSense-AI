import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime

# Create a directory to hold the generated reports
REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

def generate_txt_report(analysis_id: int, score: float, alerts: list) -> str:
    """Generates a plain text summary of the biological analysis."""
    file_path = os.path.join(REPORTS_DIR, f"report_{analysis_id}.txt")
    with open(file_path, "w") as f:
        f.write("=== RiverSense AI Conservation Report ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Analysis ID: {analysis_id}\n")
        f.write(f"Biodiversity Health Score: {score}/100\n\n")
        f.write("Triggered Alerts:\n")
        if not alerts:
            f.write("- None (Healthy Ecosystem)\n")
        for alert in alerts:
            f.write(f"- {alert}\n")
    return file_path

def generate_pdf_report(analysis_id: int, score: float, alerts: list) -> str:
    """Generates a formatted PDF document using ReportLab."""
    file_path = os.path.join(REPORTS_DIR, f"report_{analysis_id}.pdf")
    c = canvas.Canvas(file_path, pagesize=letter)

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "RiverSense AI - Official Conservation Report")

    # Metadata
    c.setFont("Helvetica", 12)
    c.drawString(50, 720, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(50, 700, f"Analysis ID: {analysis_id}")

    # Color the score (Red for danger, Green for safe)
    if score < 30:
        c.setFillColorRGB(0.8, 0.1, 0.1) # Red text
    else:
        c.setFillColorRGB(0.1, 0.6, 0.1) # Green text

    c.drawString(50, 670, f"Biodiversity Health Score: {score}/100")

    # Alert Section
    c.setFillColorRGB(0, 0, 0) # Back to Black
    c.drawString(50, 630, "Triggered Critical Alerts:")

    y_position = 600
    if not alerts:
        c.drawString(70, y_position, "- None. System Healthy.")
    else:
        for alert in alerts:
            c.drawString(70, y_position, f"- {alert}")
            y_position -= 20 # Move down the page for the next line

    # Save and close the PDF
    c.save()
    return file_path