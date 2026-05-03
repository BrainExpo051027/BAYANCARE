from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime

def generate_referral_pdf(referral, assessment, user, health_profile):
    """
    Generate a PDF referral slip matching the medical referral form format.
    Returns PDF as BytesIO.
    """
    buffer = BytesIO()
    # Add proper margins to prevent content from overflowing page edges
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=0.6*inch,
        leftMargin=0.6*inch,
        topMargin=0.6*inch,
        bottomMargin=0.6*inch
    )
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=14,
        spaceAfter=16,
        alignment=1  # center
    )
    story.append(Paragraph("BAYANCARE REFERRAL SLIP", title_style))
    story.append(Spacer(1, 10))

    # Helper function to create bordered sections with wrapping text
    def create_section(rows, bg_color=colors.white):
        # Convert text to Paragraphs for word wrapping
        data = []
        for row in rows:
            label_cell = Paragraph(f"<b>{row[0]}</b>", ParagraphStyle(
                "LabelStyle",
                parent=styles["Normal"],
                fontSize=9,
                fontName="Helvetica-Bold",
                leading=12
            ))
            value_cell = Paragraph(str(row[1]), ParagraphStyle(
                "ValueStyle",
                parent=styles["Normal"],
                fontSize=9,
                fontName="Helvetica",
                leading=12
            ))
            data.append([label_cell, value_cell])
        
        table = Table(data, colWidths=[2.2*inch, 4.2*inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_color),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ]))
        return table

    # Reference Number Section
    ref_data = [["Reference Number:", referral.referral_code]]
    story.append(create_section(ref_data))
    story.append(Spacer(1, 8))

    # Referring Facility Section
    facility_data = [
        ["Name of Referring Facility:", referral.barangay or "Barangay Health Center"],
        ["Address:", f"{referral.barangay or 'N/A'}, Polomolok, South Cotabato"],
        ["Tel No./Cp No.:", getattr(health_profile, 'contact_number', 'N/A') or 'N/A']
    ]
    story.append(create_section(facility_data))
    story.append(Spacer(1, 8))

    # Service Provider Section
    provider_data = [
        ["Name/Position of Service Provider Referring:", "BHW/Barangay Health Worker"],
        ["Date of Referral:", referral.created_at.strftime("%Y-%m-%d") if referral.created_at else datetime.now().strftime("%Y-%m-%d")]
    ]
    story.append(create_section(provider_data))
    story.append(Spacer(1, 8))

    # Referred Facility Section
    referred_data = [["Name of the facility to which the client is being referred:", 
                      referral.referred_to_center or "Barangay Health Center"]]
    story.append(create_section(referred_data))
    story.append(Spacer(1, 8))

    # Client Information Section
    client_name = getattr(health_profile, 'full_name', None) or getattr(user, 'full_name', None) or getattr(user, 'username', 'N/A')
    client_age = str(health_profile.age) if health_profile and health_profile.age else "N/A"
    client_address = f"{getattr(health_profile, 'barangay', 'N/A') or 'N/A'}, Polomolok, South Cotabato"
    
    client_data = [
        ["Name of client:", client_name],
        ["Age:", client_age],
        ["Address:", client_address]
    ]
    story.append(create_section(client_data))
    story.append(Spacer(1, 8))

    # Reason for Referral Section
    reason_text = "High-risk symptoms identified through BAYANCARE symptom assessment requiring immediate medical evaluation and treatment."
    if assessment and assessment.assessment_summary:
        reason_text = f"{assessment.assessment_summary}"
    
    reason_data = [["Reason for Referral:", reason_text]]
    story.append(create_section(reason_data))
    story.append(Spacer(1, 8))

    # Brief History Section (taller for writing)
    history_text = "Patient presented with symptoms assessed through the BAYANCARE digital health system."
    if assessment and assessment.symptoms:
        symptoms_list = ", ".join([s.symptom_name for s in assessment.symptoms])
        history_text += f" Symptoms: {symptoms_list}."
    if assessment and assessment.risk_level:
        history_text += f" Risk classification: {assessment.risk_level.value}."
    history_text += " Immediate referral recommended for further evaluation and management."
    
    # Use proper width accounting for margins
    history_label = Paragraph(
        "<b>Brief History (include pertinent PE and laboratory findings and actions taken, if any):</b>",
        ParagraphStyle("HistoryLabel", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold", leading=12)
    )
    history_value = Paragraph(
        history_text,
        ParagraphStyle("HistoryValue", parent=styles["Normal"], fontSize=9, fontName="Helvetica", leading=12)
    )
    history_data = [[history_label], [history_value]]
    history_table = Table(history_data, colWidths=[6.4*inch])
    history_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(history_table)
    story.append(Spacer(1, 8))

    # Clinical Impression Section
    impression_text = "High-risk condition requiring immediate medical attention and intervention."
    if assessment and assessment.predicted_condition:
        impression_text = assessment.predicted_condition
    
    impression_data = [["Clinical Impression:", impression_text]]
    story.append(create_section(impression_data))
    story.append(Spacer(1, 8))

    # Signature Section
    sig_label1 = Paragraph("<b>Signature of Person Referring:</b>", ParagraphStyle(
        "SigLabel", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold", leading=12
    ))
    sig_label2 = Paragraph("<b>Signature over printed name of client/guardian:</b>", ParagraphStyle(
        "SigLabel2", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold", leading=12
    ))
    signature_data = [
        [sig_label1, ""],
        [sig_label2, ""]
    ]
    signature_table = Table(signature_data, colWidths=[3.2*inch, 3.2*inch])
    signature_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(signature_table)
    story.append(Spacer(1, 8))

    # Referral Return Slip Section
    return_title = ParagraphStyle(
        "ReturnTitle",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
        alignment=1  # center
    )
    return_note = ParagraphStyle(
        "ReturnNote",
        parent=styles["Italic"],
        fontSize=8,
        alignment=1  # center
    )
    story.append(Paragraph("<b>REFERRAL RETURN SLIP</b>", return_title))
    story.append(Paragraph("(Please cut and instruct patient/guardian to deliver back to referring facility)", return_note))
    story.append(Spacer(1, 4))
    
    return_data = [
        ["Date Seen: _______________", f"Status: {referral.status or 'PENDING'}"]
    ]
    return_table = Table(return_data, colWidths=[3.2*inch, 3.2*inch])
    return_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(return_table)
    story.append(Spacer(1, 8))

    # Footer
    story.append(Spacer(1, 20))
    story.append(Paragraph("This is an official barangay-assisted referral. Please present this to the health center.", styles["Normal"]))
    story.append(Paragraph("Generated by BAYANCARE System.", styles["Italic"]))

    doc.build(story)
    buffer.seek(0)
    return buffer
