import os
import smtplib
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3

def startTheAiEngine():

    envPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(envPath)
    apiKey = os.getenv("apiKey") 

    
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

    # 1. Sadece GERCEKTEN indirimde olan urunleri filtrele (indirim > 0)
    realDiscountedProducts = [p for p in allProducts if calculateDiscount(p) > 0]
    
    # 2. Indirim oranina gore buyukten kucuge sirala
    realDiscountedProducts.sort(key=calculateDiscount, reverse=True)
    
    # 3. En iyi 5 tanesini al (Eger 2 tane varsa 2'sini alir, 8 tane varsa ilk 5'ini alir)
    bestDiscountOfFive = realDiscountedProducts[:5]
    
    # GUARD CLAUSE: Eğer listede hiç ürün kalmadıysa indirim yok demektir.
    if len(bestDiscountOfFive) == 0:
        print("\n=======================================================")
        print("[CHECK] EN YUKSEK INDIRIM ORANI: %0")
        print("[INFO] Bugun hicbir urunde indirim yok. AI asamasi iptal edildi.")
        print("=======================================================\n")
        return
    else:
        highest_discount_val = int(calculateDiscount(bestDiscountOfFive[0]))
        print("\n=======================================================")
        print(f"[CHECK] HARIKA! {len(bestDiscountOfFive)} ADET INDIRIMLI URUN BULUNDU!")
        print(f"[CHECK] EN YUKSEK INDIRIM ORANI: %{highest_discount_val}")
        print("[INFO] Yapay Zeka bulteni hazirlaniyor...")
        print("=======================================================\n")
    
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

    print("[INFO] Sending data to Google Gemini AI. Waiting for research and analysis...")

    aiJobDescription = f"""
    You are a professional Hardware Analyst.
    Below is a list of the top products with the highest discount rates that I scraped from Amazon.
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

    try:
        from google import genai
        import time
        # We reuse the "apiKey" env var so you don't have to change GitHub Actions YAML
        client = genai.Client(api_key=apiKey)
        
        models_to_try = ['gemini-3.5-flash']
        answer_text = None
        
        for model in models_to_try:
            print(f"[INFO] Trying Google Gemini Model: {model}...")
            
            # 503 hatalarina karsi 3 kere tekrar deneme (Retry) mekanizmasi
            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=aiJobDescription,
                    )
                    answer_text = response.text
                    print(f"[SUCCESS] Gemini ({model}) responded successfully on attempt {attempt+1}!")
                    break # Basarili olursa retry dongusunden cik
                except Exception as e:
                    if "503" in str(e) or "UNAVAILABLE" in str(e):
                        print(f"[WARNING] {model} is busy (503). Retrying in 5 seconds... (Attempt {attempt+1}/3)")
                        time.sleep(5)
                    else:
                        print(f"[ERROR] Gemini {model} failed with non-503 error: {e}")
                        break # Baska bir hataysa (orn: yanlis sifre) tekrar deneme, diger modele gec
            
            if answer_text:
                break # Eger cevap geldiyse model dongusunden de tamamen cik
                
        if not answer_text:
            raise Exception("All Gemini models and retries failed.")
            
    except Exception as e:
        print(f"[ERROR] AI Engine completely failed: {e}")
        print("[INFO] Skipping Email phase to prevent pipeline crash.")
        return 

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