import streamlit as st
import requests
import io
import re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors

# ✅ API Setup
API_KEY = st.secrets["GROQ_API_KEY"] # NEW: Get API key from Streamlit secrets
MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"
# MAX_CHUNK_CHARS will no longer be used as chunking is removed

# ✅ Page Setup
st.set_page_config(page_title="Coursera Summarizer", layout="centered")
st.title("📘 Coursera Transcript Summarizer (Groq + LLaMA 4)")
st.markdown("Upload your transcript `.txt` file and get a revision-friendly PDF summary.")

# ✅ File Upload & PDF Naming
uploaded_file = st.file_uploader("📤 Upload transcript file (.txt)", type=["txt"])
pdf_name = st.text_input("📄 Enter output PDF file name (optional)", value="summary")

# ✅ Summarization with Groq (NO CHUNKING)
def summarize_full_text(text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""
    Summarize the following Coursera transcript into a neat, concise handout suitable for revision.
    Organize the information logically with clear headings and concise paragraphs or standard bullet points.
    Focus on key concepts, important definitions, procedures, and significant points.
    Do not use specific labels like 'Key Takeaway:', 'Example:', 'Tip:', or 'Note:'.
    Ensure the summary is easy to read and understand for a revision purpose.
    Only return the clean, summarized content. Do not repeat this prompt or add extra instructions or conversational text.

    \"\"\"\n{text}\n\"\"\"
    """

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"ERROR: {response.status_code} - {response.text}"

# ✅ PDF Creation (Simplified Styling)
def create_pdf(summary_text, pdf_filename="summary"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=40, leftMargin=40,
                            topMargin=60, bottomMargin=40)

    styles = getSampleStyleSheet()

    # Define a custom style for the main body text
    # Check if 'BodyText' style already exists before adding it
    if 'BodyText' not in styles:
        styles.add(ParagraphStyle(name='BodyText', fontSize=11, leading=14, spaceAfter=6, alignment=TA_LEFT))
    else:
        # If it exists, update it or ensure it's set correctly
        styles['BodyText'].fontSize = 11
        styles['BodyText'].leading = 14
        styles['BodyText'].spaceAfter = 6
        styles['BodyText'].alignment = TA_LEFT

    # Define a style for headings (if the LLM generates them using ## Markdown)
    if 'Heading2' not in styles:
        styles.add(ParagraphStyle(name='Heading2', fontSize=14, leading=18, spaceAfter=10, textColor=colors.black, fontName='Helvetica-Bold'))
    else:
        styles['Heading2'].fontSize = 14
        styles['Heading2'].leading = 18
        styles['Heading2'].spaceAfter = 10
        styles['Heading2'].textColor = colors.black
        styles['Heading2'].fontName = 'Helvetica-Bold'

    # Define a style for bullet points
    if 'BulletStyle' not in styles:
        styles.add(ParagraphStyle(name='BulletStyle', fontSize=11, leading=14, spaceAfter=4, leftIndent=20, bulletIndent=10, textColor=colors.black))
    else:
        styles['BulletStyle'].fontSize = 11
        styles['BulletStyle'].leading = 14
        styles['BulletStyle'].spaceAfter = 4
        styles['BulletStyle'].leftIndent = 20
        styles['BulletStyle'].bulletIndent = 10
        styles['BulletStyle'].textColor = colors.black


    story = []
    lines = summary_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.lower().startswith("please provide the transcript"):
            continue

        # Handle potential markdown headings (##)
        if line.startswith("##"):
            # Remove ## and create a heading paragraph
            story.append(Paragraph(line.replace("##", "").strip(), styles['Heading2']))
        elif line.startswith("* ") or line.startswith("- ") or line.startswith("• "):
            # Handle standard markdown bullet points
            cleaned_line = re.sub(r"^[\*\-\•]+\s*", "", line).strip()
            # Ensure bolding (if any) is kept for PDF
            cleaned_line = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", cleaned_line)
            story.append(Paragraph(f"• {cleaned_line}", styles['BulletStyle']))
        else:
            # Assume it's a regular paragraph
            # Ensure bolding (if any) is kept for PDF
            cleaned_line = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", line)
            story.append(Paragraph(cleaned_line, styles['BodyText']))

    story.append(Spacer(1, 20))
    doc.build(story)
    buffer.seek(0)
    return buffer


# ✅ Main Workflow
if uploaded_file:
    transcript = uploaded_file.read().decode("utf-8")
    
    # Removed chunking logic
    st.info("Summarizing the entire transcript...")

    if "full_summary_cached" not in st.session_state:
        st.session_state.full_summary_cached = None

    if st.session_state.full_summary_cached is None:
        with st.spinner("Generating full summary... This might take a moment for long transcripts."):
            summary = summarize_full_text(transcript)
            if summary.startswith("ERROR"):
                st.error(summary)
                st.stop()
            st.session_state.full_summary_cached = summary
    else:
        summary = st.session_state.full_summary_cached

    st.success("✅ Summary complete!")

    st.markdown("### 📝 Generated Summary")
    st.text_area("Final Notes", summary, height=400, key="final_summary_box")

    if st.button("🔁 Regenerate Full Summary"):
        st.session_state.full_summary_cached = None # Clear cached summary to force regeneration
        st.rerun()

    pdf = create_pdf(summary)
    st.download_button(
        "📥 Download Notes as PDF",
        data=pdf,
        file_name=f"{pdf_name.strip() or 'summary'}.pdf",
        mime="application/pdf"
    )
else:
    st.info("Upload a transcript to begin.")