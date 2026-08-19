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
            dataText += f"  🔥 REAL DISCOUNT: {discount}% (According to our memory, price actually dropped!)\n"
        else:
            dataText += f"  ❌ No Discount (Price remains the same or increased)\n"
            
        dataText += f"  Link: {url}\n"
        dataText += f"  Image: {img}\n\n"

    print("[INFO] Sending data to AI. Waiting for research and analysis...")

    aiJobDescription = f"""
    You are a professional Hardware Analyst and Price/Performance expert.
    Below is a list of the top 5 products with the highest discount rates that I scraped from Amazon.
    Your task is to analyze the hardware and quality of these devices and comment on whether they are worth their price.

    PLEASE OUTPUT AS A STYLISH HTML NEWSLETTER (Email) FORMAT.
    Create a very professional, modern, dark mode, and visually appealing design using inline CSS within the HTML.
    Select only the "TOP 5" devices that truly have a good discount rate or high-quality hardware. Review them in detail and provide comments based on your research.
    Include price information and discount rates.
    Create clickable, simple, and stylish buttons using the Device Images (img src) and Purchase links (a href).
    ABSOLUTELY avoid complex nested blocks and tables so it can be read easily on mobile devices.
    Use a minimalist card design arranged vertically, wide, spacious, and single-column.
    Do not use large, filled, differently colored boxes; ensure box borders match the main theme and do not strain the eyes.
    Do not output any markdown ticks like ```html, just output the raw HTML code.

    Here is the List of the Top 5 Products:
    {dataText}
    """

    messages = [
        {"role": "user", "content": aiJobDescription}
    ]

    response = client.chat_completion(
        model="Qwen/Qwen2.5-72B-Instruct",
        messages=messages,
        max_tokens=2500
    )
    
    answer_text = response.choices[0].message.content

    print("[INFO] Preparing the Email Newsletter...")

    sender = os.getenv("fromAdress") 
    password = os.getenv("gmailPassword")    
    receiver = os.getenv("toAdress")        

    message = MIMEMultipart()
    message["From"] = sender
    message["To"] = receiver
    message["Subject"] = "🔥 Amazon Discount Report"

    clearHtml = answer_text.replace("```html", "").replace("```", "").strip()
    message.attach(MIMEText(clearHtml, "html"))

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