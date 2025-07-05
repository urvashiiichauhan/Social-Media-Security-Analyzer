from flask import Flask, render_template, request
import requests
from urllib.parse import urlparse
import re
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///analysis.db'
db = SQLAlchemy(app)

class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120))
    instagram_url = db.Column(db.String(300))
    username = db.Column(db.String(100))
    breach_count = db.Column(db.Integer)
    bio_status = db.Column(db.String(300))
    is_secure = db.Column(db.String(10))

# Use email & password from .env file
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    email = request.form['email']
    insta_url = request.form['instagram']
    username = extract_username(insta_url)

    breach_count = 0  # Simulated for now

    try:
        response = requests.get(f"https://www.instagram.com/{username}/?__a=1&__d=dis", headers={"User-Agent": "Mozilla/5.0"})
        bio = response.text
    except:
        bio = ""

    suspicious = find_suspicious_links(bio)
    bio_status = "No suspicious link." if not suspicious else "⚠️ Suspicious link found!"
    secure = "Yes" if breach_count == 0 and not suspicious else "No"
    twofa_enabled = "Please make sure **Two-Factor Authentication** is enabled for added protection."

    analysis = Analysis(email=email, instagram_url=insta_url, username=username,
                        breach_count=breach_count, bio_status=bio_status, is_secure=secure)
    db.session.add(analysis)
    db.session.commit()

    send_email(email, username, breach_count, bio_status, secure)

    return render_template('result.html',
                           email=email,
                           username=username,
                           breach_count=breach_count,
                           twofa=twofa_enabled,
                           bio_status=bio_status,
                           is_secure=secure)

@app.route('/history')
def history():
    analyses = Analysis.query.order_by(Analysis.id.desc()).all()
    return render_template('history.html', analyses=analyses)

def extract_username(url):
    parsed_url = urlparse(url)
    path = parsed_url.path.strip('/')
    return path.split('/')[0]

def find_suspicious_links(bio):
    links = re.findall(r'http[s]?://\S+', bio)
    for link in links:
        if any(bad in link.lower() for bad in ['bit.ly', 'grabify', 'shady']):
            return True
    return False

def send_email(to_email, username, breach_count, bio_status, secure):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = "🔐 Social Media Security Analyzer Report"

    body = f"""Hey there 👋,

Thank you for trusting our **Social Media Security Analyzer**. Here's your personalized security report 🛡️:

________________________________________

📧 **Email**: {to_email}  
🔎 Found in: **{breach_count}** public data breach(es).

📸 **Instagram Username**: @{username}  
🔗 Bio Scan Result: {bio_status}  
🛡️ 2FA Recommendation: Please make sure **Two-Factor Authentication** is enabled for added protection.  
✅ Account Secure: {secure}
________________________________________

✨ _We highly recommend updating any old passwords and avoiding suspicious links in your profile bio._  
Your online safety is important to us.

Thank you once again for using our service.  
If you have any questions or need support, feel free to reach out!

Warm regards,  
**Urvashi Chauhan** 🦋  
_Social Media Security Analyzer Team_
"""

    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print(f"Email sent successfully to {to_email}")
    except Exception as e:
        print("Email sending failed:", e)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
