# -*- coding: utf-8 -*-
"""
SintaJournal-Scraper & Mailer
A Streamlit web application to scrape Sinta journals, extract contacts, APC submission fees, and send mass emails using SMTP Gmail.

Cara Menjalankan:
1. Pastikan library terinstall:
   pip install requests beautifulsoup4 streamlit python-dotenv pandas
2. Jalankan Streamlit:
   streamlit run app.py
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import urllib3
import html
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import time
import os
import urllib.parse
from dotenv import load_dotenv, set_key

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load env variables from .env file if it exists
ENV_PATH = ".env"
load_dotenv(ENV_PATH)

# Page Configuration
st.set_page_config(
    page_title="SintaJournal Scraper & Mailer",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Header Gradient styling */
    .header-container {
        background: linear-gradient(135deg, #4F46E5 0%, #06B6D4 100%);
        padding: 2.5rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.3), 0 8px 10px -6px rgba(6, 182, 212, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
    }
    
    .header-title {
        font-size: 2.6rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.04em;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .header-subtitle {
        font-size: 1.1rem;
        font-weight: 400;
        opacity: 0.95;
        margin-top: 0.75rem;
    }
    
    /* Card Container */
    .card-container {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(229, 231, 235, 0.8);
        padding: 1.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease;
    }
    
    .card-container:hover {
        transform: translateY(-2px);
    }
    
    /* Metrics Grid Card */
    .metric-card {
        background: linear-gradient(135deg, #F3F4F6 0%, #E5E7EB 100%);
        border-radius: 12px;
        padding: 1rem 1.5rem;
        text-align: center;
        border: 1px solid #D1D5DB;
        box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.8);
    }
    
    /* Dark Mode support for Cards */
    @media (prefers-color-scheme: dark) {
        .card-container {
            background: rgba(31, 41, 55, 0.6);
            border-color: rgba(55, 65, 81, 0.8);
        }
        .metric-card {
            background: linear-gradient(135deg, #374151 0%, #1F2937 100%);
            border-color: #4B5563;
            box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.05);
        }
    }
    
    /* Custom Button styling */
    div.stButton > button {
        background: linear-gradient(135deg, #4F46E5 0%, #06B6D4 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        border-radius: 10px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25);
        width: 100%;
    }
    
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 18px rgba(79, 70, 229, 0.35);
        background: linear-gradient(135deg, #4338CA 0%, #0891B2 100%);
        color: white;
    }
    
    /* Inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        border-radius: 10px !important;
        border: 1px solid #D1D5DB !important;
        transition: border-color 0.2s;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {
        border-color: #6366F1 !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
    }
    </style>
""", unsafe_allow_html=True)

# Helper function to decode Cloudflare Email Protection
def decode_cloudflare_email(cf_hex):
    try:
        key = int(cf_hex[:2], 16)
        email = []
        for i in range(2, len(cf_hex), 2):
            char = int(cf_hex[i:i+2], 16) ^ key
            email.append(chr(char))
        return "".join(email)
    except Exception:
        return ""

# Helper function to parse emails from HTML text and decode Cloudflare format
def extract_emails(html_text):
    valid_emails = set()
    
    # 1. Decode Cloudflare emails
    cf_matches = re.findall(r'data-cfemail="([a-f0-9]+)"', html_text)
    for cf_hex in cf_matches:
        decoded = decode_cloudflare_email(cf_hex)
        if decoded and '@' in decoded:
            valid_emails.add(decoded.lower())
            
    # 2. Extract standard emails from text
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    raw_emails = re.findall(email_pattern, html_text)
    for email in raw_emails:
        if not email.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js', '.svg', '.webp', '.pdf', '.docx')):
            valid_emails.add(email.lower())
            
    return list(valid_emails)

# Helper function to extract other contacts (Phone & WhatsApp)
def extract_other_contacts(html_text, soup):
    contacts = set()
    
    # 1. Look for tel: links
    tel_links = soup.find_all('a', href=re.compile(r'^tel:'))
    for link in tel_links:
        num = link.get('href').replace('tel:', '').strip()
        num = re.sub(r'[\s\-]', '', num)
        if num:
            contacts.add(f"Telp: {num}")
            
    # 2. Look for WhatsApp links (wa.me or api.whatsapp.com)
    wa_links = soup.find_all('a', href=re.compile(r'wa\.me|whatsapp\.com|send\?phone', re.I))
    for link in wa_links:
        href = link.get('href')
        match = re.search(r'(?:wa\.me/|phone=|send\?phone=)(\+?[0-9]+)', href)
        if match:
            num = match.group(1)
            contacts.add(f"WA: {num}")
        else:
            contacts.add("WA Link")
            
    # 3. Look for phone number patterns in page text
    text_content = soup.get_text()
    phone_pattern = r'(?:\+62|62|0)8[1-9][0-9\-\s]{7,11}'
    found_nums = re.findall(phone_pattern, text_content)
    
    for num in found_nums:
        clean_num = re.sub(r'[\s\-]', '', num)
        if 9 <= len(clean_num) <= 15:
            if clean_num.startswith('08') or clean_num.startswith('628') or clean_num.startswith('+628'):
                contacts.add(f"WA/Tel: {clean_num}")
            else:
                contacts.add(f"Tel: {clean_num}")
                
    # 4. Search in text for telephone labels
    tel_text_pattern = r'(?:telp|phone|telepon|hp|kontak|contact)[\s\:\-\+]*(\(?[0-9]{2,4}\)?[\s\-]*[0-9]{5,10})'
    text_matches = re.findall(tel_text_pattern, text_content.lower())
    for val in text_matches:
        clean_val = re.sub(r'[\s\-]', '', val)
        if len(clean_val) >= 6:
            contacts.add(f"Telp: {val.strip()}")

    result_list = list(contacts)
    result_list.sort(key=lambda s: 0 if s.startswith("WA") else 1)
    
    return "; ".join(result_list) if result_list else ""

# Helper to extract focus and scope of OJS website
def extract_scope(soup, text_content):
    scope_headers = [
        "focus and scope", "focus & scope", "aims and scope", "aims & scope", 
        "scope", "ruang lingkup", "fokus dan ruang lingkup", "fokus & ruang lingkup"
    ]
    
    # 1. Search for heading elements containing keywords
    for keyword in scope_headers:
        elements = soup.find_all(lambda tag: tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div'] and tag.text and keyword in tag.text.lower())
        for el in elements:
            siblings = el.find_next_siblings(['p', 'div', 'ul'])
            scope_text = ""
            for sib in siblings[:3]:
                txt = sib.get_text().strip()
                if txt:
                    scope_text += txt + " "
            scope_text = scope_text.strip()
            if len(scope_text) > 40:
                scope_text = re.sub(r'\s+', ' ', scope_text)
                if len(scope_text) > 300:
                    return scope_text[:300] + "..."
                return scope_text
                
    # 2. Scanner Fallback in raw text content
    for keyword in scope_headers:
        idx = text_content.lower().find(keyword)
        if idx != -1:
            start_idx = idx + len(keyword)
            snippet = text_content[start_idx:start_idx+350].strip()
            snippet = re.sub(r'\s+', ' ', snippet)
            snippet = snippet.lstrip(':-* \t\n\r')
            if len(snippet) > 40:
                if len(snippet) > 300:
                    return snippet[:300] + "..."
                return snippet
                
    return "Skope / Bidang fokus tidak terdeteksi otomatis."

# Helper to extract Publication / Submission Fee (APC)
def extract_fee(soup, html_text, journal_url, headers):
    fee_keywords = [
        "author fee", "author fees", "biaya penulisan", "biaya publikasi", 
        "publication fee", "submission fee", "article processing charge", 
        "apc", "biaya submit", "biaya pemrosesan", "processing fee", "biaya artikel"
    ]
    
    # 1. Search in main page elements
    for kw in fee_keywords:
        elements = soup.find_all(lambda tag: tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'td', 'li'] and tag.text and kw in tag.text.lower())
        for el in elements:
            parent = el.parent if el.name in ['h1','h2','h3','h4','h5','h6'] else el
            txt = parent.get_text().strip()
            match = re.search(r'(?:Rp\.?|IDR|\$|USD)\s?[\d\.\,]+|(?:free of charge|tidak dipungut biaya|tanpa biaya|no publication fee|gratis|0\s?(?:idr|usd|rp)|rp\.?\s?0)', txt, re.I)
            if match:
                clean_txt = re.sub(r'\s+', ' ', txt)
                if len(clean_txt) > 150:
                    clean_txt = clean_txt[:147] + "..."
                return clean_txt

    # 2. Pattern matching in main raw text
    fee_match = re.search(r'(?:biaya|fee|apc|publikasi|penulisan|submission)[^\.\n]{0,60}(?:Rp\.?|IDR|\$|USD)\s?[\d\.\,]+|(?:Rp\.?|IDR|\$|USD)\s?[\d\.\,]+[^\.\n]{0,60}(?:biaya|fee|publikasi|artikel|page)', html_text, re.I)
    if fee_match:
        clean_match = re.sub(r'\s+', ' ', fee_match.group(0)).strip()
        if len(clean_match) > 120:
            clean_match = clean_match[:117] + "..."
        return clean_match

    free_match = re.search(r'(?:free of charge|tidak dipungut biaya|tanpa biaya|no publication fee|0\s?(?:idr|usd|rp)|rp\.?\s?0)', html_text, re.I)
    if free_match:
        return "Gratis / Free"

    # 3. Check fee subpages
    base_url = journal_url.rstrip('/')
    fee_urls = [
        f"{base_url}/about/submissions",
        f"{base_url}/about/editorialPolicies",
        f"{base_url}/about/fees",
    ]
    if "index.php" in base_url.lower():
        fee_urls.extend([
            f"{base_url}/about/submissions#authorFees",
            f"{base_url}/about/editorialPolicies#authorFees",
        ])

    for a in soup.find_all('a', href=True):
        href = a['href']
        href_lower = href.lower()
        if any(k in href_lower for k in ['fee', 'author', 'submission', 'biaya', 'charge']):
            if not href.startswith(('http://', 'https://')):
                from urllib.parse import urljoin
                href = urljoin(journal_url, href)
            fee_urls.append(href)

    seen_fee_urls = set()
    unique_fee_urls = [x for x in fee_urls if not (x in seen_fee_urls or seen_fee_urls.add(x))]
    
    for f_url in unique_fee_urls[:2]:
        try:
            f_res = requests.get(f_url, headers=headers, timeout=6, verify=False)
            if f_res.status_code == 200:
                f_html = html.unescape(f_res.text)
                f_soup = BeautifulSoup(f_html, 'html.parser')
                f_text = f_soup.get_text()
                
                fee_elem = f_soup.find(id=re.compile(r'authorFees|fee|biaya', re.I)) or f_soup.find(class_=re.compile(r'authorFees|fee|biaya', re.I))
                if fee_elem:
                    t = re.sub(r'\s+', ' ', fee_elem.get_text()).strip()
                    if len(t) > 10:
                        if len(t) > 150:
                            t = t[:147] + "..."
                        return t
                
                m = re.search(r'(?:biaya|fee|apc|publikasi|penulisan|submission)[^\.\n]{0,60}(?:Rp\.?|IDR|\$|USD)\s?[\d\.\,]+|(?:Rp\.?|IDR|\$|USD)\s?[\d\.\,]+[^\.\n]{0,60}(?:biaya|fee|publikasi|artikel|page)', f_text, re.I)
                if m:
                    clean_m = re.sub(r'\s+', ' ', m.group(0)).strip()
                    if len(clean_m) > 120:
                        clean_m = clean_m[:117] + "..."
                    return clean_m
                    
                if any(k in f_text.lower() for k in ['free of charge', 'tidak dipungut biaya', 'tanpa biaya', 'no publication fee']):
                    return "Gratis / Free"
        except Exception:
            continue

    return "Tidak terdeteksi (Bisa diisi manual)"

# Helper function to scrape keywords from HTML text
def search_keywords(text_content):
    keywords = [
        "call for papers", "submission", "submissions", "deadline", "volume", "issue", "vol.", "no.",
        "januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus", "september", "oktober", "november", "desember",
        "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"
    ]
    
    text_lower = text_content.lower()
    found_keywords = []
    for kw in keywords:
        if kw in text_lower:
            found_keywords.append(kw)
            
    months_eng = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
    months_ind = ["januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus", "september", "oktober", "november", "desember"]
    
    months_found = []
    general_found = []
    for kw in found_keywords:
        if kw in months_eng or kw in months_ind:
            months_found.append(kw.capitalize())
        else:
            general_found.append(kw.upper() if kw in ["vol.", "no."] else kw.title())
            
    months_found = sorted(list(set(months_found)))
    general_found = sorted(list(set(general_found)))
    
    result_tags = []
    if general_found:
        result_tags.extend(general_found[:4])
    if months_found:
        result_tags.append("Bulan: " + "/".join(months_found[:3]))
        
    return ", ".join(result_tags) if result_tags else "Tidak ditemukan kata kunci spesifik"

# Helper to count articles and extract current issue title from OJS
def count_articles_in_current_issue(journal_url, headers):
    journal_url = journal_url.strip()
    if not journal_url.startswith(("http://", "https://")):
        journal_url = "https://" + journal_url
        
    base_url = journal_url.rstrip('/')
    
    current_issue_urls = [
        f"{base_url}/issue/current",
        f"{base_url}/index.php/index/issue/current",
        f"{base_url}/index.php/current",
    ]
    current_issue_urls.append(journal_url)
    
    if "index.php" in journal_url:
        parts = journal_url.split("index.php")
        journal_path = parts[1].strip('/')
        current_issue_urls.insert(0, f"{parts[0]}index.php/{journal_path}/issue/current")
        current_issue_urls.insert(1, f"{parts[0]}index.php/{journal_path}/issue/archive")
        
    seen = set()
    current_issue_urls = [x for x in current_issue_urls if not (x in seen or seen.add(x))]
    
    for url in current_issue_urls:
        try:
            res = requests.get(url, headers=headers, timeout=8, verify=False)
            if res.status_code == 200:
                html_content = html.unescape(res.text)
                soup = BeautifulSoup(html_content, 'html.parser')
                
                articles_count = 0
                articles = soup.find_all(class_=re.compile(r'article[-_]summary|obj[-_]article[-_]summary', re.I))
                if articles:
                    articles_count = len(articles)
                else:
                    toc_articles = soup.find_all(class_=re.compile(r'tocArticle|tocTitle', re.I))
                    if toc_articles:
                        articles_count = len(toc_articles)
                    else:
                        article_links = soup.find_all('a', href=re.compile(r'/article/view/\d+', re.I))
                        unique_article_hrefs = set(link.get('href') for link in article_links)
                        base_article_hrefs = set()
                        for href in unique_article_hrefs:
                            match = re.search(r'/article/view/(\d+)', href, re.I)
                            if match:
                                base_article_hrefs.add(match.group(1))
                        if base_article_hrefs:
                            articles_count = len(base_article_hrefs)
                
                if articles_count > 0:
                    issue_title = ""
                    title_elem = soup.find(class_=re.compile(r'issue[-_]title|current[-_]issue|page[-_]title', re.I))
                    if not title_elem:
                        title_elem = soup.find(['h1', 'h2', 'h3'])
                    if title_elem:
                        issue_title = title_elem.text.strip()
                        issue_title = re.sub(r'\s+', ' ', issue_title)
                        if len(issue_title) > 60:
                            issue_title = issue_title[:57] + "..."
                            
                    return {
                        "count": articles_count,
                        "issue_info": issue_title if issue_title else "Terbitan Terakhir"
                    }
        except Exception:
            continue
            
    return {
        "count": 0,
        "issue_info": "Tidak terdeteksi"
    }

# Helper function to scrape a single journal URL
def scrape_journal_website(journal_url, headers):
    journal_url = journal_url.strip()
    if not journal_url.startswith(("http://", "https://")):
        journal_url = "https://" + journal_url
        
    try:
        res = requests.get(journal_url, headers=headers, timeout=12, verify=False)
        html_content = html.unescape(res.text)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        title = soup.title.string.strip() if soup.title else "No Title"
        emails = extract_emails(html_content)
        other_contacts = extract_other_contacts(html_content, soup)
        text_content = soup.get_text()
        keywords_summary = search_keywords(text_content)
        scope_summary = extract_scope(soup, text_content)
        fee_summary = extract_fee(soup, html_content, journal_url, headers)
        
        base_url = journal_url.rstrip('/')
        contact_urls = [
            f"{base_url}/about/contact",
            f"{base_url}/about",
            f"{base_url}/contact",
            f"{base_url}/about/editorialPolicies",
        ]
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            href_lower = href.lower()
            if 'contact' in href_lower or 'about' in href_lower:
                if not href.startswith(('http://', 'https://')):
                    from urllib.parse import urljoin
                    href = urljoin(journal_url, href)
                contact_urls.append(href)
                
        if "index.php" not in base_url.lower():
            contact_urls.extend([
                f"{base_url}/index.php/about/contact",
                f"{base_url}/index.php/contact",
                f"{base_url}/index.php/about",
                f"{base_url}/index.php/about/editorialPolicies"
            ])
            
        seen_urls = set()
        unique_urls = [x for x in contact_urls if not (x in seen_urls or seen_urls.add(x))]
        
        contact_priority = []
        about_priority = []
        other_priority = []
        for url in unique_urls:
            url_lower = url.lower()
            if 'contact' in url_lower:
                contact_priority.append(url)
            elif 'about' in url_lower:
                about_priority.append(url)
            else:
                other_priority.append(url)
                
        sorted_contact_urls = contact_priority + about_priority + other_priority
        target_urls = sorted_contact_urls[:3]
        
        for c_url in target_urls:
            try:
                c_res = requests.get(c_url, headers=headers, timeout=8, verify=False)
                if c_res.status_code == 200:
                    c_html = html.unescape(c_res.text)
                    c_soup = BeautifulSoup(c_html, 'html.parser')
                    c_text = c_soup.get_text()
                    
                    c_emails = extract_emails(c_html)
                    if c_emails:
                        emails.extend(c_emails)
                        
                    c_other = extract_other_contacts(c_html, c_soup)
                    if c_other:
                        if other_contacts:
                            combined = set(other_contacts.split("; ") + c_other.split("; "))
                            other_contacts = "; ".join(list(combined))
                        else:
                            other_contacts = c_other
                            
                    if "tidak terdeteksi" in scope_summary.lower():
                        c_scope = extract_scope(c_soup, c_text)
                        if "tidak terdeteksi" not in c_scope.lower():
                            scope_summary = c_scope
                            
                    k_sum = search_keywords(c_text)
                    if k_sum != "Tidak ditemukan kata kunci spesifik" and keywords_summary == "Tidak ditemukan kata kunci spesifik":
                        keywords_summary = k_sum
            except Exception:
                continue
                
        emails = list(set(emails))
        email_str = ", ".join(emails) if emails else ""
        
        issue_data = count_articles_in_current_issue(journal_url, headers)
        if issue_data["count"] > 0:
            last_issue_str = f"{issue_data['count']} Artikel ({issue_data['issue_info']})"
        else:
            last_issue_str = "Tidak terdeteksi"
        
        return {
            "status": "Sukses",
            "title": title,
            "emails": email_str,
            "other_contacts": other_contacts,
            "scope": scope_summary,
            "fee": fee_summary,
            "keywords": keywords_summary,
            "last_issue": last_issue_str
        }
        
    except Exception as e:
        return {
            "status": f"Error: {str(e)}",
            "title": "Gagal Akses",
            "emails": "",
            "other_contacts": "",
            "scope": "Koneksi Gagal",
            "fee": "Koneksi Gagal",
            "keywords": "Koneksi Gagal",
            "last_issue": "Koneksi Gagal"
        }

# Helper to find maximum page count dynamically on Sinta list
def get_max_sinta_pages(soup):
    max_page = 1
    pagination_div = soup.find('div', class_='pagination') or soup.find('ul', class_='pagination')
    if pagination_div:
        links = pagination_div.find_all('a')
        for link in links:
            href = link.get('href') or ""
            match = re.search(r'page=(\d+)', href)
            if match:
                page_num = int(match.group(1))
                if page_num > max_page:
                    max_page = page_num
            text = link.text.strip()
            if text.isdigit():
                page_num = int(text)
                if page_num > max_page:
                    max_page = page_num
    return max_page

# Main Header
st.markdown("""
    <div class="header-container">
        <h1 class="header-title">🚀 SintaJournal-Scraper & Mailer</h1>
        <p class="header-subtitle">Pencarian Jurnal Sinta, Ekstraksi Kontak, Scope, Biaya Submit (APC), & Pengirim Email Massal.</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.markdown("### 👤 Identitas Pengirim (Anda)")
sender_name = st.sidebar.text_input("✍️ Nama Lengkap Anda:", value=os.getenv("SENDER_NAME", ""), placeholder="Contoh: Dr. Budi Santoso, M.Kom")
sender_inst = st.sidebar.text_input("🏢 Institusi/Jabatan Anda:", value=os.getenv("SENDER_INSTITUTION", ""), placeholder="Contoh: Universitas Indonesia / Dosen")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Kredensial SMTP & Pengirim")
default_email = os.getenv("SENDER_EMAIL", "")
default_password = os.getenv("SENDER_PASSWORD", "")
default_subject = os.getenv("EMAIL_SUBJECT", "Pertanyaan Mengenai Kuota Publikasi & Biaya Submit - {nama_jurnal}")

sender_email = st.sidebar.text_input("📧 Email Pengirim (Gmail):", value=default_email, placeholder="contoh@gmail.com")
app_password = st.sidebar.text_input("🔑 App Password (16-digit):", value=default_password, type="password", placeholder="abcd efgh ijkl mnop")
email_subject = st.sidebar.text_input("✉️ Subject Email:", value=default_subject)

# Auto-save credentials & identity to .env silently on change
try:
    if (sender_name != os.getenv("SENDER_NAME", "") or
        sender_inst != os.getenv("SENDER_INSTITUTION", "") or
        sender_email != os.getenv("SENDER_EMAIL", "") or
        app_password != os.getenv("SENDER_PASSWORD", "") or
        email_subject != os.getenv("EMAIL_SUBJECT", "Pertanyaan Mengenai Kuota Publikasi & Biaya Submit - {nama_jurnal}")):
        
        set_key(ENV_PATH, "SENDER_NAME", sender_name)
        set_key(ENV_PATH, "SENDER_INSTITUTION", sender_inst)
        set_key(ENV_PATH, "SENDER_EMAIL", sender_email)
        set_key(ENV_PATH, "SENDER_PASSWORD", app_password)
        set_key(ENV_PATH, "EMAIL_SUBJECT", email_subject)
except Exception:
    pass

st.sidebar.caption("🟢 Kredensial & identitas disimpan otomatis.")

st.sidebar.markdown("---")
with st.sidebar.expander("❓ Cara Mendapatkan App Password Gmail"):
    st.markdown("""
    1. Buka halaman **Akun Google** Anda ([myaccount.google.com](https://myaccount.google.com)).
    2. Pilih menu **Keamanan** (Security) di sebelah kiri.
    3. Aktifkan **Verifikasi 2 Langkah** (2-Step Verification) jika belum aktif.
    4. Setelah aktif, cari menu **Sandi Aplikasi** (App Passwords) di bagian bawah.
    5. Masukkan nama aplikasi bebas (contoh: *Sinta Mailer*), lalu klik **Buat**.
    6. Salin **16 karakter** sandi yang muncul dan masukkan ke kolom Password di atas (tanpa spasi).
    """)

# Session State Initializations
if 'scraped_df' not in st.session_state:
    st.session_state.scraped_df = None
if 'max_sinta_pages' not in st.session_state:
    st.session_state.max_sinta_pages = 5
if 'sinta_query_search' not in st.session_state:
    st.session_state.sinta_query_search = ""

# Tab Setup
tab1, tab2 = st.tabs(["🔍 Tab 1: Scraper Jurnal, Kontak & Biaya", "✉️ Tab 2: Pengirim Email Massal"])

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "id,en-US;q=0.7,en;q=0.3",
    "Connection": "keep-alive"
}

with tab1:
    st.markdown("""
    <div class="card-container">
        <h4 style="margin-top:0;">📥 Sumber Data & Pencarian Jurnal SINTA</h4>
    """, unsafe_allow_html=True)
    
    source_option = st.radio(
        "Pilih metode input data jurnal:",
        ["Ambil Otomatis dari Portal SINTA", "Input URL Jurnal Manual secara Massal", "Upload File CSV Hasil Edit (Excel)"],
        horizontal=True
    )
    
    # Render option parameters
    if source_option == "Ambil Otomatis dari Portal SINTA":
        col1, col2 = st.columns(2)
        with col1:
            sinta_rank = st.selectbox("Pilih Akreditasi Sinta:", ["Sinta 1", "Sinta 2", "Sinta 3", "Sinta 4", "Sinta 5", "Sinta 6"], index=3)
        with col2:
            subject_area = st.selectbox("Pilih Bidang Keilmuan (Sinta Area):", [
                "Semua Bidang Keilmuan",
                "Education (Edukasi)", 
                "Social (Sosial)", 
                "Humanities (Humaniora)", 
                "Science (Sains)", 
                "Economy (Ekonomi)", 
                "Engineering (Teknik)", 
                "Health (Kesehatan)", 
                "Art (Seni)", 
                "Agriculture (Pertanian)", 
                "Religion (Agama)"
            ], index=0)
            
        rank_map = {"Sinta 1": "1", "Sinta 2": "2", "Sinta 3": "3", "Sinta 4": "4", "Sinta 5": "5", "Sinta 6": "6"}
        area_map = {
            "Semua Bidang Keilmuan": "all",
            "Education (Edukasi)": "6",
            "Social (Sosial)": "9",
            "Humanities (Humaniora)": "3",
            "Science (Sains)": "5",
            "Economy (Ekonomi)": "2",
            "Engineering (Teknik)": "10",
            "Health (Kesehatan)": "4",
            "Art (Seni)": "8",
            "Agriculture (Pertanian)": "7",
            "Religion (Agama)": "1"
        }
        
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("#### 🎯 Quick Preset & Pencarian Topik Spesifik")
        st.caption("Pilih tombol bidang ilmu di bawah untuk mengisi otomatis kata kunci pencarian, atau ketik manual topik jurnal yang dicari:")
        
        # Preset Buttons
        p_col1, p_col2, p_col3, p_col4, p_col5, p_col6 = st.columns(6)
        with p_col1:
            if st.button("💻 IT & Komputer"):
                st.session_state.sinta_query_search = "informatika"
                st.rerun()
        with p_col2:
            if st.button("🎓 Pendidikan"):
                st.session_state.sinta_query_search = "pendidikan"
                st.rerun()
        with p_col3:
            if st.button("💼 Ekonomi"):
                st.session_state.sinta_query_search = "ekonomi"
                st.rerun()
        with p_col4:
            if st.button("🏥 Kesehatan"):
                st.session_state.sinta_query_search = "kesehatan"
                st.rerun()
        with p_col5:
            if st.button("⚙️ Teknik"):
                st.session_state.sinta_query_search = "teknik"
                st.rerun()
        with p_col6:
            if st.button("🌐 Reset Topik"):
                st.session_state.sinta_query_search = ""
                st.rerun()

        sinta_search_query = st.text_input(
            "🔍 Kata Kunci Topik Jurnal di SINTA:",
            value=st.session_state.sinta_query_search,
            placeholder="Contoh: informatika, komputer, sistem informasi, data science, dll."
        )

        st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
        pages_to_scrape = st.slider(
            "Jumlah Halaman SINTA yang Di-scrape (10 jurnal/hal):",
            min_value=1,
            max_value=50,
            value=3,
            help="Tentukan berapa banyak halaman daftar jurnal SINTA yang ingin di-scrape."
        )
            
    elif source_option == "Input URL Jurnal Manual secara Massal":
        st.markdown("**Masukkan URL Jurnal (Satu URL per baris):**")
        manual_urls = st.text_area(
            "Daftar URL:",
            value="https://join.if.uinsgd.ac.id/index.php/join\nhttps://journal.universitasbumigora.ac.id/index.php/matrik\nhttp://journals.ums.ac.id/index.php/khif",
            height=150,
            help="Tulis alamat website jurnal target lengkap dengan http:// atau https://"
        )
        
    else:
        st.markdown("**Unggah File CSV Jurnal Hasil Olahan Excel:**")
        uploaded_file = st.file_uploader("Pilih file CSV:", type=["csv"], help="Unggah file CSV hasil download dari aplikasi ini yang sudah Anda filter/edit di Excel.")
        if uploaded_file is not None:
            try:
                uploaded_df = pd.read_csv(uploaded_file)
                
                required_cols = ["Nama Jurnal", "Website URL", "Email Tujuan", "Kontak Lain (WA/Telp)", "Biaya Submit / APC", "Scope Jurnal"]
                # Fallback check if old format without Biaya Submit
                if "Biaya Submit / APC" not in uploaded_df.columns:
                    uploaded_df["Biaya Submit / APC"] = "Belum Diisi"

                missing_cols = [col for col in required_cols if col not in uploaded_df.columns and col != "Biaya Submit / APC"]
                
                if not missing_cols:
                    if "Pilih" not in uploaded_df.columns:
                        uploaded_df.insert(0, "Pilih", True)
                    
                    uploaded_df["Pilih"] = uploaded_df["Pilih"].astype(bool)
                    st.session_state.scraped_df = uploaded_df
                    st.toast("File CSV berhasil diunggah!", icon="✅")
                else:
                    st.error(f"Format kolom CSV tidak cocok. Pastikan file CSV memiliki kolom dasar: Nama Jurnal, Website URL, Email Tujuan, Kontak Lain, Scope Jurnal.")
            except Exception as e:
                st.error(f"Gagal membaca file CSV: {e}")
                
        if st.session_state.scraped_df is not None:
            df = st.session_state.scraped_df
            total_rows = len(df)
            
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            st.info(f"📊 File CSV terunggah berisi **{total_rows} jurnal**.")
            
            if st.button("🔄 Sinkronisasi & Validasi Ulang Semua Kontak & Biaya (Re-Scrape & Gabung)", help="Menelusuri ulang seluruh website jurnal di CSV dan menggabungkan kontak & biaya baru."):
                status_container = st.status("Memulai re-scrape dan penggabungan seluruh data kontak & biaya...")
                progress_bar = st.progress(0)
                
                updated_df = df.copy()
                start_time = time.time()
                
                def merge_emails(existing_val, new_val):
                    if not existing_val or pd.isna(existing_val):
                        return new_val if new_val else ""
                    if not new_val:
                        return existing_val
                    existing_list = [v.strip() for v in re.split(r'[,;]', str(existing_val)) if v.strip()]
                    new_list = [v.strip() for v in re.split(r'[,;]', str(new_val)) if v.strip()]
                    combined = []
                    seen = set()
                    for item in existing_list + new_list:
                        item_lower = item.lower()
                        if item_lower not in seen:
                            seen.add(item_lower)
                            combined.append(item)
                    return ", ".join(combined)

                def merge_other_contacts(existing_val, new_val):
                    if not existing_val or pd.isna(existing_val):
                        return new_val if new_val else ""
                    if not new_val:
                        return existing_val
                    existing_list = [v.strip() for v in re.split(r';', str(existing_val)) if v.strip()]
                    new_list = [v.strip() for v in re.split(r';', str(new_val)) if v.strip()]
                    combined = []
                    seen = set()
                    for item in existing_list + new_list:
                        item_lower = item.lower().replace(" ", "").replace("-", "")
                        if item_lower not in seen:
                            seen.add(item_lower)
                            combined.append(item)
                    return "; ".join(combined)

                def is_empty_val(val):
                    if val is None or pd.isna(val):
                        return True
                    s = str(val).strip().lower()
                    return s == "" or s == "nan" or s == "tidak terdeteksi" or "koneksi gagal" in s or "belum diisi" in s or "tidak terdeteksi (bisa diisi manual)" in s

                for idx in range(total_rows):
                    row = updated_df.iloc[idx]
                    j_url = row["Website URL"]
                    
                    status_container.write(f"Validasi Ulang [{idx+1}/{total_rows}]: {j_url}...")
                    
                    scrape_res = scrape_journal_website(j_url, headers)
                    
                    if scrape_res["status"] == "Sukses":
                        orig_email = row.get("Email Tujuan", "")
                        updated_df.iat[idx, updated_df.columns.get_loc("Email Tujuan")] = merge_emails(orig_email, scrape_res["emails"])
                        
                        orig_contact = row.get("Kontak Lain (WA/Telp)", "")
                        updated_df.iat[idx, updated_df.columns.get_loc("Kontak Lain (WA/Telp)")] = merge_other_contacts(orig_contact, scrape_res["other_contacts"])
                        
                        orig_fee = row.get("Biaya Submit / APC", "")
                        if "Biaya Submit / APC" in updated_df.columns:
                            if is_empty_val(orig_fee) and scrape_res["fee"]:
                                updated_df.iat[idx, updated_df.columns.get_loc("Biaya Submit / APC")] = scrape_res["fee"]
                        else:
                            updated_df["Biaya Submit / APC"] = scrape_res["fee"]
                            
                        orig_scope = row.get("Scope Jurnal", "")
                        if is_empty_val(orig_scope) and scrape_res["scope"]:
                            updated_df.iat[idx, updated_df.columns.get_loc("Scope Jurnal")] = scrape_res["scope"]
                            
                        orig_last_issue = row.get("Jumlah Terbitan Terakhir", "")
                        if "Jumlah Terbitan Terakhir" in updated_df.columns:
                            if is_empty_val(orig_last_issue) and scrape_res["last_issue"]:
                                updated_df.iat[idx, updated_df.columns.get_loc("Jumlah Terbitan Terakhir")] = scrape_res["last_issue"]
                                
                        updated_df.iat[idx, updated_df.columns.get_loc("Status Scraping")] = "Sukses"
                        if is_empty_val(row.get("Judul Web")):
                            updated_df.iat[idx, updated_df.columns.get_loc("Judul Web")] = scrape_res["title"]
                    else:
                        updated_df.iat[idx, updated_df.columns.get_loc("Status Scraping")] = scrape_res["status"]
                        
                    progress_bar.progress((idx + 1) / total_rows)
                    time.sleep(0.8)
                    
                st.session_state.scraped_df = updated_df
                duration = time.time() - start_time
                mins, secs = int(duration // 60), int(duration % 60)
                duration_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
                
                status_container.update(state="complete", label=f"Sinkronisasi selesai dalam {duration_str}!")
                st.toast("Seluruh data kontak & biaya berhasil disinkronisasi!", icon="✅")
                time.sleep(1)
                st.rerun()

    # Keyword relevance filtering options (Optional local keyword filter)
    if source_option != "Upload File CSV Hasil Edit (Excel)":
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_rel1, col_rel2 = st.columns([1, 2])
        with col_rel1:
            filter_relevance = st.checkbox("🔍 Filter Relevansi Kata Kunci Lokal", value=False, help="Centang jika ingin menyaring lagi hasil scraping secara spesifik di lokal.")
        with col_rel2:
            relevance_keywords = st.text_input("Kata Kunci Penyaring Tambahan (opsional):", value="informatika, komputer, software, sistem informasi, data science, teknologi", help="Contoh: informatika, komputer, teknologi")
    else:
        filter_relevance = False
        relevance_keywords = ""

    st.markdown("</div>", unsafe_allow_html=True)

    # Scrape Trigger
    if source_option != "Upload File CSV Hasil Edit (Excel)":
        if st.button("🚀 Mulai Scraping & Cari Kontak/Biaya"):
            start_time = time.time()
            journal_targets = []
            
            if source_option == "Ambil Otomatis dari Portal SINTA":
                status_container = st.status("Menghubungkan ke Portal SINTA...")
                
                s_rank_val = rank_map[sinta_rank]
                s_area_val = area_map[subject_area]
                q_val = sinta_search_query.strip()
                
                sinta_session = requests.Session()
                
                try:
                    for page in range(1, pages_to_scrape + 1):
                        status_container.write(f"Mengambil daftar jurnal dari SINTA - Halaman {page}...")
                        url_get = f"https://sinta.kemdiktisaintek.go.id/journals/index/?sinta={s_rank_val}&page={page}"
                        if s_area_val != "all":
                            url_get += f"&area={s_area_val}"
                        if q_val:
                            url_get += f"&q={urllib.parse.quote(q_val)}"
                            
                        get_res = sinta_session.get(url_get, headers=headers, timeout=15)
                        
                        if get_res.status_code == 200:
                            soup = BeautifulSoup(get_res.text, 'html.parser')
                            journal_divs = soup.find_all('div', class_='affil-name')
                            
                            for div in journal_divs:
                                a_tag = div.find('a')
                                if a_tag:
                                    j_name = a_tag.text.strip()
                                    parent = div.find_parent('div', class_='ar-list-item') or div.parent.parent
                                    
                                    website_url = ""
                                    publisher_name = ""
                                    if parent:
                                        abbrev_div = parent.find('div', class_='affil-abbrev')
                                        if abbrev_div:
                                            links = abbrev_div.find_all('a')
                                            for link in links:
                                                txt = link.text.strip().lower()
                                                if 'website' in txt:
                                                    website_url = link.get('href')
                                                    break
                                        loc_div = parent.find('div', class_='affil-loc')
                                        if loc_div:
                                            publisher_name = loc_div.text.strip()
                                                    
                                    if website_url:
                                        journal_targets.append({
                                            "name": j_name,
                                            "url": website_url,
                                            "publisher": publisher_name
                                        })
                    
                    status_container.write(f"Berhasil menemukan {len(journal_targets)} jurnal dari SINTA.")
                except Exception as e:
                    status_container.write(f"❌ Gagal melakukan scraping SINTA: {e}")
                    st.error(f"Terjadi kesalahan saat scrape SINTA: {e}")
                    
            else:
                urls = [u.strip() for u in manual_urls.split('\n') if u.strip()]
                for u in urls:
                    journal_targets.append({
                        "name": "Jurnal Input Manual",
                        "url": u,
                        "publisher": ""
                    })
                    
            if journal_targets:
                results = []
                status_container = st.status("Scraping detail isi website jurnal, kontak, & biaya submit...") if 'status_container' not in locals() else status_container
                
                progress_bar = st.progress(0)
                total = len(journal_targets)
                
                for idx, target in enumerate(journal_targets):
                    j_name = target["name"]
                    j_url = target["url"]
                    j_pub = target["publisher"]
                    
                    status_container.write(f"Scraping [{idx+1}/{total}]: {j_url}...")
                    
                    scrape_res = scrape_journal_website(j_url, headers)
                    
                    final_name = j_name
                    if j_name == "Jurnal Input Manual" and scrape_res["status"] == "Sukses":
                        final_name = scrape_res["title"].split('|')[0].split('-')[0].strip()
                    
                    if filter_relevance and scrape_res["status"] == "Sukses":
                        kws = [k.strip().lower() for k in relevance_keywords.split(',') if k.strip()]
                        combined_text = f"{final_name} {scrape_res['scope']} {scrape_res['keywords']} {j_pub}".lower()
                        match_found = False
                        for kw in kws:
                            if kw in combined_text:
                                match_found = True
                                break
                        if not match_found:
                            status_container.write(f"ℹ️ Dilewati (tidak relevan): {final_name}")
                            progress_bar.progress((idx + 1) / total)
                            continue
                        
                    results.append({
                        "Pilih": True,
                        "Nama Jurnal": final_name,
                        "Website URL": j_url,
                        "Email Tujuan": scrape_res["emails"],
                        "Kontak Lain (WA/Telp)": scrape_res["other_contacts"],
                        "Biaya Submit / APC": scrape_res["fee"],
                        "Scope Jurnal": scrape_res["scope"],
                        "Jumlah Terbitan Terakhir": scrape_res["last_issue"],
                        "Keywords Terdeteksi": scrape_res["keywords"],
                        "Institusi Penerbit": j_pub,
                        "Status Scraping": scrape_res["status"],
                        "Judul Web": scrape_res["title"]
                    })
                    
                    progress_bar.progress((idx + 1) / total)
                    
                st.session_state.scraped_df = pd.DataFrame(results)
                end_time = time.time()
                duration_seconds = end_time - start_time
                minutes = int(duration_seconds // 60)
                seconds = int(duration_seconds % 60)
                duration_str = f"{minutes} menit {seconds} detik" if minutes > 0 else f"{seconds} detik"
                
                status_container.update(state="complete", label=f"Scraping detail jurnal, kontak, dan biaya submit selesai dalam {duration_str}!")
                st.success(f"Selesai! Berhasil memproses {len(results)} website jurnal dalam {duration_str}.")
            else:
                st.warning("Tidak ada target jurnal yang ditemukan untuk di-scrape.")
            
    # Display table results
    if st.session_state.scraped_df is not None:
        total_found = len(st.session_state.scraped_df)
        emails_found = st.session_state.scraped_df["Email Tujuan"].apply(lambda e: 1 if e else 0).sum()
        other_contacts_found = st.session_state.scraped_df["Kontak Lain (WA/Telp)"].apply(lambda c: 1 if c else 0).sum()
        
        email_pct = int((emails_found/total_found)*100) if total_found > 0 else 0
        contact_pct = int((other_contacts_found/total_found)*100) if total_found > 0 else 0

        st.markdown("### 📊 Ringkasan Data Ditemukan")
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.markdown(f"""
                <div class="metric-card">
                    <p style="font-size:0.9rem;color:#6B7280;margin:0;font-weight:600;">Total Jurnal Terproses</p>
                    <p style="font-size:2.2rem;color:#4F46E5;margin:0;font-weight:800;">{total_found}</p>
                </div>
            """, unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"""
                <div class="metric-card">
                    <p style="font-size:0.9rem;color:#6B7280;margin:0;font-weight:600;">Email Ditemukan</p>
                    <p style="font-size:2.2rem;color:#059669;margin:0;font-weight:800;">{emails_found} <span style="font-size:1rem;font-weight:400;">({email_pct}%)</span></p>
                </div>
            """, unsafe_allow_html=True)
        with m_col3:
            st.markdown(f"""
                <div class="metric-card">
                    <p style="font-size:0.9rem;color:#6B7280;margin:0;font-weight:600;">Kontak WA/Telp Ditemukan</p>
                    <p style="font-size:2.2rem;color:#0891B2;margin:0;font-weight:800;">{other_contacts_found} <span style="font-size:1rem;font-weight:400;">({contact_pct}%)</span></p>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📋 Hasil Scraping & Konfigurasi Penerima Email")
        st.info("💡 **Tips:** Anda dapat langsung mengedit kolom **'Email Tujuan'** atau **'Biaya Submit / APC'** pada tabel di bawah ini jika ingin melengkapi data.")
        
        edited_df = st.data_editor(
            st.session_state.scraped_df,
            column_config={
                "Pilih": st.column_config.CheckboxColumn(
                    "Pilih",
                    help="Centang untuk menyertakan jurnal ini dalam pengiriman email massal",
                    default=True,
                ),
                "Nama Jurnal": st.column_config.TextColumn(
                    "Nama Jurnal",
                    disabled=True
                ),
                "Website URL": st.column_config.LinkColumn(
                    "Website URL",
                    disabled=True
                ),
                "Email Tujuan": st.column_config.TextColumn(
                    "Email Tujuan (Bisa Diedit)",
                    help="Alamat email penerima. Anda bisa mengedit kolom ini."
                ),
                "Kontak Lain (WA/Telp)": st.column_config.TextColumn(
                    "Kontak Lain (WA/Telp)",
                    help="Nomor WhatsApp atau Telepon pengelola jurnal yang terdeteksi."
                ),
                "Biaya Submit / APC": st.column_config.TextColumn(
                    "Biaya Submit / APC",
                    help="Informasi biaya submit/publikasi jurnal yang terdeteksi. Bisa diedit manual."
                ),
                "Scope Jurnal": st.column_config.TextColumn(
                    "Scope Jurnal",
                    help="Fokus dan ruang lingkup artikel jurnal."
                ),
                "Jumlah Terbitan Terakhir": st.column_config.TextColumn(
                    "Jumlah Terbitan Terakhir",
                    help="Jumlah artikel dan nama edisi terbitan terakhir dari archives."
                ),
                "Keywords Terdeteksi": st.column_config.TextColumn(
                    "Keywords Terdeteksi",
                    disabled=True
                ),
                "Institusi Penerbit": st.column_config.TextColumn(
                    "Institusi Penerbit",
                    help="Nama institusi atau penerbit jurnal."
                ),
                "Status Scraping": st.column_config.TextColumn(
                    "Status Scraper",
                    disabled=True
                ),
                "Judul Web": st.column_config.TextColumn(
                    "Judul Web",
                    disabled=True
                )
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.session_state.scraped_df = edited_df
        
        st.markdown("<br>", unsafe_allow_html=True)
        csv_data = st.session_state.scraped_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Data Jurnal ke CSV",
            data=csv_data,
            file_name="hasil_scraping_jurnal.csv",
            mime="text/csv",
            help="Unduh semua data tabel di atas ke dalam format file spreadsheet CSV"
        )

with tab2:
    st.markdown("### ✉️ Editor & Pengirim Email Massal")
    
    if not sender_email or not app_password:
        st.warning("⚠️ Kredensial SMTP Gmail belum diatur secara lengkap di Sidebar kiri. Harap isi email pengirim dan App Password sebelum mengirim.")
        
    if st.session_state.scraped_df is not None:
        selected_journals = st.session_state.scraped_df[st.session_state.scraped_df["Pilih"] == True]
    else:
        selected_journals = pd.DataFrame()
        
    if selected_journals.empty:
        st.info("Silakan lakukan scraping jurnal di **Tab 1** terlebih dahulu dan pilih jurnal yang akan dikirimi email.")
    else:
        col_left, col_right = st.columns([2, 1])
        
        default_body_template = """Yth. Tim Editor {nama_jurnal} {nama_institusi},

Perkenalkan, saya {nama_pengirim}. Saya bermaksud untuk mengirimkan artikel ilmiah ke {nama_jurnal}.

Sehubungan dengan hal tersebut, mohon informasi terkait proses publikasi artikel, antara lain:

1. Informasi rincian biaya publikasi (APC / submission fee) di {nama_jurnal}.
2. Kapan perkiraan jadwal terbit atau estimasi waktu proses review hingga publikasi.
3. Apakah saat ini masih tersedia kuota untuk terbitan edisi terdekat.

Besar harapan saya untuk memperoleh informasi tersebut sebagai bahan pertimbangan sebelum melakukan submit artikel.

Atas perhatian dan kerja samanya, saya ucapkan terima kasih.

Hormat saya,

{nama_pengirim}
{institusi_pengirim}"""

        with col_left:
            st.markdown("**Template Body Email:**")
            email_body_template = st.text_area(
                "Gunakan placeholder `{nama_jurnal}`, `{nama_institusi}`, `{nama_pengirim}`, dan `{institusi_pengirim}` secara dinamis:",
                value=default_body_template,
                height=350
            )
            
        with col_right:
            st.markdown("**Preview Email Dinamis:**")
            first_row = selected_journals.iloc[0]
            sample_journal_name = first_row["Nama Jurnal"]
            sample_email = first_row["Email Tujuan"] if first_row["Email Tujuan"] else "[Email Kosong]"
            sample_publisher = first_row["Institusi Penerbit"] if first_row["Institusi Penerbit"] else ""
            
            disp_sender_name = sender_name if sender_name else "[Nama Anda]"
            disp_sender_inst = sender_inst if sender_inst else "[Institusi Anda]"
            
            preview_subject = email_subject.replace("{nama_jurnal}", sample_journal_name)
            
            preview_body = email_body_template\
                .replace("{nama_jurnal}", sample_journal_name)\
                .replace("{nama_institusi}", sample_publisher)\
                .replace("{nama_pengirim}", disp_sender_name)\
                .replace("{institusi_pengirim}", disp_sender_inst)
            
            st.markdown(f"**Kepada:** `{sample_email}`")
            st.markdown(f"**Subject:** `{preview_subject}`")
            st.text_area("Preview Isi Email:", value=preview_body, height=270, disabled=True)
            
        st.markdown(f"### 📋 Daftar Penerima ({len(selected_journals)} Jurnal Terpilih)")
        
        display_selected = selected_journals[["Nama Jurnal", "Website URL", "Email Tujuan", "Biaya Submit / APC", "Institusi Penerbit", "Kontak Lain (WA/Telp)"]].copy()
        display_selected["Email Tujuan"] = display_selected["Email Tujuan"].apply(
            lambda e: "⚠️ [Belum Diisi - Harap Edit]" if not e else e
        )
        st.dataframe(display_selected, hide_index=True, use_container_width=True)
        
        if st.button("✈️ Kirim Email Massal"):
            has_empty_email = any(not e for e in selected_journals["Email Tujuan"])
            if has_empty_email:
                st.error("Gagal mengirim! Ada jurnal terpilih yang tidak memiliki alamat email. Silakan isi manual kolom 'Email Tujuan' di Tab 1 atau batalkan pilihan jurnal tersebut.")
            elif not sender_email or not app_password:
                st.error("Gagal mengirim! Kredensial email pengirim dan App Password tidak boleh kosong.")
            else:
                send_progress = st.progress(0)
                status_area = st.empty()
                log_container = st.container()
                
                total_emails = len(selected_journals)
                success_count = 0
                fail_count = 0
                
                with log_container:
                    st.markdown("#### 📝 Log Pengiriman Email:")
                    
                    try:
                        status_area.info("Menghubungkan ke SMTP Server Gmail...")
                        server = None
                        connected_port = None
                        
                        try:
                            status_area.info("Menghubungkan via Port 587 (TLS)...")
                            server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
                            server.starttls()
                            connected_port = 587
                        except Exception as tls_err:
                            status_area.info("Gagal terhubung via Port 587. Mencoba Port 465 (SSL)...")
                            try:
                                server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
                                connected_port = 465
                            except Exception as ssl_err:
                                raise Exception(f"Kedua port SMTP (587 & 465) diblokir oleh provider internet/ISP Anda atau koneksi tidak stabil.\nDetail TLS (587): {tls_err}\nDetail SSL (465): {ssl_err}")
                                
                        status_area.info(f"Terhubung via Port {connected_port}. Melakukan Autentikasi...")
                        server.login(sender_email, app_password)
                        
                        for i, (_, row) in enumerate(selected_journals.iterrows()):
                            j_name = row["Nama Jurnal"]
                            j_email = row["Email Tujuan"]
                            j_pub = row["Institusi Penerbit"] if row["Institusi Penerbit"] else ""
                            
                            j_emails = [e.strip() for e in re.split(r'[,;]', str(j_email)) if e.strip()]
                            
                            status_area.info(f"Mengirim email ke: {j_name} ({', '.join(j_emails)})...")
                            
                            subj = email_subject.replace("{nama_jurnal}", j_name)
                            body = email_body_template\
                                .replace("{nama_jurnal}", j_name)\
                                .replace("{nama_institusi}", j_pub)\
                                .replace("{nama_pengirim}", sender_name if sender_name else "Pengirim")\
                                .replace("{institusi_pengirim}", sender_inst if sender_inst else "")
                            
                            msg = MIMEMultipart()
                            msg['From'] = sender_email
                            msg['To'] = ", ".join(j_emails)
                            msg['Subject'] = subj
                            msg.attach(MIMEText(body, 'plain', 'utf-8'))
                            
                            try:
                                server.sendmail(sender_email, j_emails, msg.as_string())
                                success_count += 1
                                st.write(f"✅ **Sukses:** Email terkirim ke {j_name} (`{', '.join(j_emails)}`)")
                            except Exception as email_err:
                                fail_count += 1
                                st.write(f"❌ **Gagal:** Pengiriman ke {j_name} (`{', '.join(j_emails)}`) error: {email_err}")
                                
                            send_progress.progress((i + 1) / total_emails)
                            time.sleep(1.5)
                            
                        server.quit()
                        status_area.empty()
                        
                        st.markdown("---")
                        if fail_count == 0:
                            st.success(f"🎉 Sukses mengirim semua email! Total: {success_count} email terkirim.")
                        else:
                            st.warning(f"⚠️ Pengiriman selesai dengan beberapa kendala. Sukses: {success_count}, Gagal: {fail_count}.")
                            
                    except Exception as smtp_err:
                        status_area.empty()
                        st.error(f"❌ **Gagal menyambung ke SMTP server:** {smtp_err}")
                        st.info("Silakan periksa kembali apakah email pengirim dan App Password sudah benar, dan apakah koneksi internet Anda stabil.")
