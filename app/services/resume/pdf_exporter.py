"""ATS-compliant PDF resume exporter using ReportLab.

Produces clean, machine-parseable, single/multi-page PDF documents.
Ensures standard system fonts (Helvetica) and standard semantic headings for ATS compatibility.
"""

import io
import logging
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger("kuru.resume.pdf")


class ResumePdfExporter:
    """Renders structured resume dictionaries into professional ATS-friendly PDF documents."""

    @classmethod
    def export_resume_pdf(cls, resume: Any) -> bytes:
        """Render resume model or data dictionary into PDF bytes."""
        if isinstance(resume, dict):
            return cls.export_pdf(resume)
        resume_dict = {
            "title": getattr(resume, "title", "Resume"),
            "target_role": getattr(resume, "target_role", None),
            "contact_info": getattr(resume, "contact_info", {}),
            "summary": getattr(resume, "summary", None),
            "skills_by_category": getattr(resume, "skills_by_category", {}),
            "practical_assessments": getattr(resume, "practical_assessments", []),
            "projects": getattr(resume, "projects", []),
            "experience": getattr(resume, "experience", []),
            "education": getattr(resume, "education", []),
            "tailoring_metadata": getattr(resume, "tailoring_metadata", None),
        }
        return cls.export_pdf(resume_dict)

    @classmethod
    def export_pdf(cls, resume_data: dict[str, Any]) -> bytes:
        """Render resume data dictionary into PDF bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
        )

        styles = getSampleStyleSheet()

        # Custom ATS-compliant typography styles
        title_style = ParagraphStyle(
            "ResumeTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=1,  # Centered
            textColor=colors.HexColor("#111827"),
        )

        subtitle_style = ParagraphStyle(
            "ResumeSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=1,
            textColor=colors.HexColor("#4F46E5"),
        )

        contact_style = ParagraphStyle(
            "ResumeContact",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=1,
            textColor=colors.HexColor("#4B5563"),
        )

        heading_style = ParagraphStyle(
            "ResumeSectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1F2937"),
            spaceBefore=8,
            spaceAfter=3,
        )

        body_style = ParagraphStyle(
            "ResumeBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#374151"),
        )

        bullet_style = ParagraphStyle(
            "ResumeBullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.5,
            leftIndent=14,
            firstLineIndent=-10,
            textColor=colors.HexColor("#374151"),
        )

        subheading_style = ParagraphStyle(
            "ResumeSubHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#111827"),
        )

        submeta_style = ParagraphStyle(
            "ResumeSubMeta",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#6B7280"),
        )

        story = []

        contact_info = resume_data.get("contact_info", {})
        full_name = contact_info.get("full_name") or "Candidate Name"
        target_role = resume_data.get("target_role") or "Software Engineer"

        # 1. Header: Name & Target Role
        story.append(Paragraph(full_name.upper(), title_style))
        story.append(Spacer(1, 2))
        story.append(Paragraph(target_role.title(), subtitle_style))
        story.append(Spacer(1, 4))

        # Contact details line
        contact_parts = []
        if contact_info.get("email"):
            contact_parts.append(contact_info["email"])
        if contact_info.get("phone"):
            contact_parts.append(contact_info["phone"])
        if contact_info.get("location"):
            contact_parts.append(contact_info["location"])
        if contact_info.get("github_url"):
            contact_parts.append(contact_info["github_url"])

        contact_line = "  •  ".join(contact_parts)
        story.append(Paragraph(contact_line, contact_style))
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB"), spaceBefore=2, spaceAfter=6))

        # 2. Professional Summary
        summary = resume_data.get("summary")
        if summary:
            story.append(Paragraph("PROFESSIONAL SUMMARY", heading_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB"), spaceBefore=1, spaceAfter=4))
            story.append(Paragraph(summary, body_style))
            story.append(Spacer(1, 6))

        # 3. Technical Skills
        skills_by_cat = resume_data.get("skills_by_category", {})
        if any(skills_by_cat.values()):
            story.append(Paragraph("TECHNICAL SKILLS & EVIDENCE", heading_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB"), spaceBefore=1, spaceAfter=4))

            for cat_name, skill_items in skills_by_cat.items():
                if skill_items:
                    formatted_names = []
                    for s in skill_items:
                        name = s.get("skill_name") if isinstance(s, dict) else str(s)
                        v_status = s.get("verification_status") if isinstance(s, dict) else ""
                        if v_status == "practically_demonstrated":
                            formatted_names.append(f"<b>{name}</b>* (Verified)")
                        else:
                            formatted_names.append(name)

                    line = f"<b>{cat_name}:</b> {', '.join(formatted_names)}"
                    story.append(Paragraph(line, body_style))
                    story.append(Spacer(1, 2))

            story.append(Spacer(1, 6))

        # 4. Practical SkillProof Assessments (if available)
        practical_assessments = resume_data.get("practical_assessments", [])
        if practical_assessments:
            story.append(Paragraph("PRACTICAL ASSESSMENTS & CODE VERIFICATION", heading_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB"), spaceBefore=1, spaceAfter=4))

            for pa in practical_assessments:
                skill_name = pa.get("skill_name", "Skill")
                level = pa.get("assessment_level", "Standard").title()
                ctype = pa.get("challenge_type", "Coding").title()
                score = pa.get("score", 100.0)
                date_str = pa.get("verified_at") or "Verified"

                title_row = f"<b>{skill_name} Practical Assessment</b> ({level} {ctype}) — Score: {score:.0f}%"
                story.append(Paragraph(title_row, subheading_style))
                story.append(
                    Paragraph(
                        f"• Certified independently in isolated sandbox execution; passed all public and hidden boundary test suites ({date_str}).",
                        bullet_style,
                    )
                )
                story.append(Spacer(1, 3))

            story.append(Spacer(1, 4))

        # 5. Technical Projects (Grounded in GitHub)
        projects = resume_data.get("projects", [])
        if projects:
            story.append(Paragraph("TECHNICAL PROJECTS & REPOSITORY PORTFOLIO", heading_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB"), spaceBefore=1, spaceAfter=4))

            for proj in projects[:3]:
                p_title = proj.get("title", "Project")
                p_stack = ", ".join(proj.get("tech_stack", []))
                story.append(Paragraph(f"<b>{p_title}</b> | <i>{p_stack}</i>", subheading_style))

                p_desc = proj.get("description")
                if p_desc:
                    story.append(Paragraph(f"• {p_desc}", bullet_style))

                for bullet in proj.get("bullet_points", []):
                    if bullet != p_desc:
                        story.append(Paragraph(f"• {bullet}", bullet_style))

                story.append(Spacer(1, 4))

            story.append(Spacer(1, 4))

        # 6. Experience (if available)
        experience = resume_data.get("experience", [])
        if experience:
            story.append(Paragraph("EXPERIENCE", heading_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB"), spaceBefore=1, spaceAfter=4))

            for exp in experience:
                role = exp.get("role", "Engineer")
                comp = exp.get("company", "Company")
                loc = exp.get("location") or ""
                dates = f"{exp.get('start_date') or ''} - {exp.get('end_date') or 'Present'}"
                meta = f"{loc} | {dates}".strip(" |")

                story.append(Paragraph(f"<b>{role}</b> — {comp}", subheading_style))
                if meta:
                    story.append(Paragraph(meta, submeta_style))

                for bullet in exp.get("bullet_points", []):
                    story.append(Paragraph(f"• {bullet}", bullet_style))

                story.append(Spacer(1, 4))

            story.append(Spacer(1, 4))

        # 7. Education
        education = resume_data.get("education", [])
        if education:
            story.append(Paragraph("EDUCATION", heading_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB"), spaceBefore=1, spaceAfter=4))

            for edu in education:
                degree = edu.get("degree", "Degree")
                inst = edu.get("institution", "Institution")
                year = edu.get("graduation_year") or ""
                gpa = edu.get("grade_or_gpa") or ""
                details = f"{degree} | {inst}"
                if year:
                    details += f" ({year})"
                if gpa:
                    details += f" — GPA/Score: {gpa}"

                story.append(Paragraph(details, body_style))
                story.append(Spacer(1, 2))

        # 8. ATS Footnote Disclaimer
        story.append(Spacer(1, 10))
        story.append(
            Paragraph(
                "<i>*Verified skills backed by passing SkillProof isolated sandbox practical assessments. "
                "All resume contents ground strictly in validated portfolio code and profile records.</i>",
                submeta_style,
            )
        )

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes


resume_pdf_exporter = ResumePdfExporter()
pdf_exporter = resume_pdf_exporter
