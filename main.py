from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
import os
import smtplib
from email.message import EmailMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate


# ─────────────── SETUP ───────────────
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Set your Google Gemini API key
os.environ["GOOGLE_API_KEY"] = "AIzaSyAyiQL-meKJYMEOi-dqjrngwHSQnpmOrH4" 

campaign_data = {"name": None, "donors": []}
donation_file = "donations.xlsx"

# Initialize donations Excel if not exists
if not os.path.exists(donation_file):
    df_init = pd.DataFrame(columns=["Name", "Amount", "Email"])
    df_init.to_excel(donation_file, index=False)

# ─────────────── HOMEPAGE ───────────────
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "campaign": campaign_data}
    )

# ─────────────── CREATE FUNDRAISING CAMPAIGN ───────────────
@app.post("/create_campaign")
async def create_campaign(
    request: Request,
    name: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
    file: UploadFile = File(...)
):
    df = pd.read_excel(file.file)
    campaign_data["name"] = name

    # 🧠 Generate AI message using Gemini
    template = PromptTemplate.from_template(
        "Write a short, warm, and inspiring fundraising email for alumni encouraging them to donate for the campaign: {campaign_name}. Keep it friendly and motivating."
    )
    prompt_text = template.format(campaign_name=name)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.7,
        api_key=os.environ["GOOGLE_API_KEY"]
    )
    ai_response = llm.invoke(prompt_text)
    ai_message = ai_response.content

    sender = "221fa04337@gmail.com"
    password = "omtf qrng uwdc zoyi"  # App Password

    for idx, row in df.iterrows():
        # Replace placeholders dynamically
        personalized_message = ai_message
        personalized_message = personalized_message.replace("[Alumni Name]", row.get("Name", "Alumni"))
        personalized_message = personalized_message.replace("[University Name]", "Vignan University")
        personalized_message = personalized_message.replace("[Link to Donation Page]", "https://donate.example.com")
        personalized_message = personalized_message.replace("[Mailing Address]", "123 University St, Vadlamudi")

        final_message = f"{message}\n\n---\nAI Suggested Message:\n{personalized_message}"

        # Send email (UTF-8 safe)
        msg = EmailMessage()
        msg['From'] = sender
        msg['To'] = row["Email"]
        msg['Subject'] = subject
        msg.set_content(final_message)

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender, password)
                server.send_message(msg)
        except Exception as e:
            print(f"Failed to send email to {row['Email']}: {e}")

    return RedirectResponse("/", status_code=303)
@app.post("/delete_campaign")
async def delete_campaign():
    campaign_data["name"] = None
    campaign_data["donors"] = []
    return RedirectResponse("/", status_code=303)

# ─────────────── DONATION HANDLER ───────────────
@app.post("/donate")
async def donate(name: str = Form(...), amount: float = Form(...), email: str = Form(...)):
    campaign_data["donors"].append({"name": name, "amount": amount, "email": email})

    # Save to Excel
    try:
        df = pd.read_excel(donation_file)
    except:
        df = pd.DataFrame(columns=["Name", "Amount", "Email"])

    df = pd.concat([df, pd.DataFrame([{"Name": name, "Amount": amount, "Email": email}])], ignore_index=True)
    df.to_excel(donation_file, index=False)

    return RedirectResponse("/", status_code=303)
