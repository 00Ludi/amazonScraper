import os
import smtplib
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3

def startTheAiEngine():

    envPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(envPath)
    apiKey = os.getenv("apiKey") 
    client = InferenceClient(api_key=apiKey)
    
    print("[INFO] Reading Amazon data from the Database (amazonData.db)...")
    
    dbPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "amazonData.db")
    conn = sqlite3.connect(dbPath)
    cursor = conn.cursor()
    
    cursor.execute("SELECT productName, currentPrice, highestPrice, productUrl, imageUrl FROM products")
    allProducts = cursor.fetchall()
    
    # Calculate real discount mathematically
    def calculateDiscount(product):
        current = product[1]
        highest = product[2]
        
        if highest > 0 and current < highest:
            return 100 - ((current * 100) / highest)
        return 0

    # 1. Sort the list descending by real discount
    allProducts.sort(key=calculateDiscount, reverse=True)
    
    # 2. Get top 5 champions
    bestDiscountOfFive = allProducts[:5]
    
    dataText = ""
    # 3. Format these 5 products into an AI Prompt
    for product in bestDiscountOfFive:
        name, current, highest, url, img = product
        discount = int(calculateDiscount(product))
        
        dataText += f"- Product: {name}\n"
        dataText += f"  Current Price: ${current} | Highest Seen Price: ${highest}\n"
        
        if discount > 0:
            dataText += f"  [REAL DISCOUNT]: {discount}% (According to our memory, price actually dropped!)\n"
        else:
            dataText += f"  [NO DISCOUNT] (Price remains the same or increased)\n"
            
        dataText += f"  Link: {url}\n"
        dataText += f"  Image: {img}\n\n"

    print("[INFO] Sending data to Hugging Face AI (Qwen). Waiting for research and analysis...")

    aiJobDescription = f"""
    You are a professional Hardware Analyst.
    Below is a list of the top 5 products with the highest discount rates that I scraped from Amazon.
    Your task is to analyze the hardware of these devices and comment on whether they are worth their price.

    PLEASE OUTPUT AS A STYLISH HTML NEWSLETTER FORMAT. Follow these STRICT rules:
    1. Background must be dark (#1a1a1a).
    2. ALL TEXT (h1, h2, h3, p, span) MUST BE EXPLICITLY WHITE (#ffffff). Add 'color: #ffffff;' to every text tag.
    3. For the purchase link, YOU MUST USE A PROPER HTML BUTTON. Do NOT output raw text links. 
       Example: <a href="THE_LINK_HERE" style="display:inline-block; padding:10px 20px; background:#007bff; color:#ffffff; text-decoration:none; border-radius:5px;">Purchase Now</a>
    4. Keep the analysis for each device CONCISE (maximum 2 short sentences per device).
    5. Do not output any markdown ticks like ```html, just output the raw HTML code.

    Here is the List of the Top Products:
    {dataText}
    """

    messages = [
        {"role": "user", "content": aiJobDescription}
    ]

    models_to_try = [
        "Qwen/Qwen2.5-72B-Instruct",
        "meta-llama/Meta-Llama-3-8B-Instruct",
        "mistralai/Mistral-7B-Instruct-v0.2"
    ]
    
    answer_text = None
    
    for model_name in models_to_try:
        try:
            print(f"[INFO] Trying Hugging Face Model: {model_name}...")
            response = client.chat_completion(
                model=model_name,
                messages=messages,
                max_tokens=4000
            )
            answer_text = response.choices[0].message.content
            print(f"[SUCCESS] Model {model_name} responded successfully!")
            break # Başarılı olduysa döngüden (diğer modelleri denemekten) çık
        except Exception as e:
            print(f"[WARNING] Model {model_name} failed: {e}. Switching to fallback...")

    if not answer_text:
        print("[ERROR] All Hugging Face models failed today.")
        print("[INFO] Skipping Email phase to prevent pipeline crash.")
        return # Hiçbiri çalışmazsa güvenli çıkış yap

    print("[INFO] Preparing the Email Newsletter...")

    sender = os.getenv("fromAdress") 
    password = os.getenv("gmailPassword")    
    receiver = os.getenv("toAdress")        

    message = MIMEMultipart()
    message["From"] = sender
    message["To"] = receiver
    message["Subject"] = "Amazon Discount Report"

    clearHtml = answer_text.replace("```html", "").replace("```", "").strip()
    message.attach(MIMEText(clearHtml, "html", "utf-8"))

    try:
        print("[INFO] Connecting to Google SMTP Servers...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        
        print("[INFO] Sending Newsletter...")
        server.sendmail(sender, receiver, message.as_string())
        server.quit()
        print("[SUCCESS] NEWSLETTER SENT SUCCESSFULLY! Please check your Inbox.")
    except Exception as e:
        print(f"[ERROR] A problem occurred while sending the Email: {e}")