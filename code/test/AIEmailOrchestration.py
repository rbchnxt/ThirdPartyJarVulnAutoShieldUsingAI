import openai
import pandas as pd
import numpy as np
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
import os
import re
from pdfminer.high_level import extract_text
import pytesseract
from PIL import Image

# Initialize OpenAI API
openai.api_key = 'your-openai-api-key'

# Predefined request types and subtypes
REQUEST_TYPES = {
    "Closing Notice": ["Reallocation Fees", "Amendment Fees", "Reallocation Principal"],
    "Fee Payment": ["Ongoing Fee", "Letter of Credit Fee"],
    "Money Movement - Outbound": ["Timebound", "Foreign Currency"]
}

# Function to classify email using LLM (GPT)
def classify_email(email_text):
    prompt = f"Classify the following email into one of the predefined request types and sub request types. Extract the relevant request type and sub request type.\n\nEmail:\n{email_text}\n\nRequest Type:"
    response = openai.Completion.create(
        engine="text-davinci-003",  # Using Davinci model for better results
        prompt=prompt,
        max_tokens=150,
        temperature=0.7
    )
    return response['choices'][0]['text'].strip()

# Function to extract fields from email body and attachments
def extract_data_from_email(email_text, attachments):
    # Extract fields like deal name, amount, expiration date
    fields = {
        "deal_name": re.search(r"deal name: (\w+)", email_text, re.IGNORECASE),
        "amount": re.search(r"amount: \$?([\d,]+)", email_text),
        "expiration_date": re.search(r"expiration date: (\d{2}/\d{2}/\d{4})", email_text)
    }
   
    extracted_fields = {key: value.group(1) if value else None for key, value in fields.items()}
   
    # Process attachments using OCR for text extraction
    for attachment in attachments:
        if attachment.endswith('.pdf'):
            text = extract_text(attachment)
        elif attachment.endswith('.docx'):
            text = extract_text_from_docx(attachment)
        elif attachment.endswith('.jpg') or attachment.endswith('.png'):
            text = pytesseract.image_to_string(Image.open(attachment))
       
        # Further extraction of fields from attachment text
        extracted_fields.update(extract_data_from_email(text, []))  # Recurse for further extraction
   
    return extracted_fields

# Function to extract text from DOCX files (using python-docx)
def extract_text_from_docx(docx_file):
    from docx import Document
    doc = Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

# Function to detect duplicate emails
def detect_duplicates(email_text, email_thread, past_emails_df):
    email_content = email_text + " " + email_thread  # Combine email content with thread context
    similarities = []
   
    for past_email in past_emails_df['email_content']:
        similarity = cosine_similarity([email_content], [past_email])
        similarities.append(similarity[0][0])
   
    max_similarity = max(similarities) if similarities else 0
    if max_similarity > 0.8:  # Threshold for duplicates
        return True, "Duplicate email detected"
    else:
        return False, "No duplicate"

# Main function for processing emails
def process_email(email_text, attachments, email_thread, past_emails_df):
    # Classify the request
    classified_request = classify_email(email_text)
   
    # Extract relevant fields
    extracted_fields = extract_data_from_email(email_text, attachments)
   
    # Check for duplicates
    is_duplicate, duplicate_reason = detect_duplicates(email_text, email_thread, past_emails_df)
   
    # Output the results
    return {
        "classified_request": classified_request,
        "extracted_fields": extracted_fields,
        "is_duplicate": is_duplicate,
        "duplicate_reason": duplicate_reason
    }

# Example email text and attachments
email_text = "We would like to request a closing notice for deal ABC123, with an amount of $100,000 and an expiration date of 12/31/2025."
attachments = ['deal_details.pdf', 'payment_terms.docx']  # Sample attachments (PDF, DOCX)
email_thread = "Re: Closing Notice Request"
past_emails_df = pd.DataFrame({'email_content': ["We would like to request a closing notice for deal ABC123"]})

# Processing the email
result = process_email(email_text, attachments, email_thread, past_emails_df)
print(result)
