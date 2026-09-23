import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import google.generativeai as genai

# 1. Read Environment Variables
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

def fetch_pubmed_articles():
    """Fetch top 10 recent PubMed articles on calcium & osteoporosis management"""
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": "calcium osteoporosis management",
        "retmode": "json",
        "retmax": 10,
        "sort": "pub_date"
    }
    res = requests.get(search_url, params=search_params).json()
    id_list = res.get('esearchresult', {}).get('idlist', [])

    if not id_list:
        return []

    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    summary_params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "json"
    }
    details = requests.get(summary_url, params=summary_params).json().get('result', {})

    articles = []
    for uid in id_list:
        title = details.get(uid, {}).get('title', 'No Title Available')
        pub_date = details.get(uid, {}).get('pubdate', 'N/A')
        link = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
        articles.append({"title": title, "date": pub_date, "link": link})

    return articles

def generate_email_html(articles):
    """Summarize articles using Gemini into clean HTML"""
    articles_text = "\n".join([f"- Title: {a['title']}\n  Date: {a['date']}\n  Link: {a['link']}" for a in articles])

    prompt = f"""
    You are an expert medical research assistant. Format a daily digest of these 10 articles on Calcium & Osteoporosis Management.

    Articles list:
    {articles_text}

    Create an HTML-formatted email body containing:
    1. An introduction paragraph summarizing current clinical trends.
    2. An ordered HTML list (`<ol>`) of all 10 articles. For each item include:
       - Article title as a hyperlinked text (`<a href="...">`) pointing to its link.
       - Publication date in muted text.
       - A concise 2-sentence key clinical takeaway.

    Return ONLY raw valid HTML code without backticks or ```html markers.
    """
    response = model.generate_content(prompt)
    return response.text.strip()

def send_gmail(html_body):
    """Send formatted email via Gmail SMTP"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = " Daily Digest: Calcium & Osteoporosis Management Research"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

if __name__ == "__main__":
    print("Fetching PubMed articles...")
    articles = fetch_pubmed_articles()
    
    if articles:
        print("Generating AI summary...")
        html_digest = generate_email_html(articles)
        
        print("Sending email via Gmail...")
        send_gmail(html_digest)
        print("Digest successfully sent!")
    else:
        print("No articles retrieved.")