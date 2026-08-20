import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django.setup()

import base64
import json
from PIL import Image
from django.utils import timezone
from pos.models import *

from google import genai
from google.genai import types

client = genai.Client(api_key="AIzaSyDpajyAe-vTUBLuPBdhPdzgFLmGszDvkLU")  # never hardcode the key


def process_ai_image():
    img = Image.open("saved_image.jpg")
    img.thumbnail((1024, 1024))
    img.save("resized.jpg", quality=80, optimize=True)
    with open("resized.jpg", "rb") as f:
        image_data = f.read()

    product_names = list(Product.objects.values_list("name", flat=True))

    prompt = f"""Products: {json.dumps(product_names)}

Match each item on the scanned list to the closest product name (handle typos, abbreviations, Cyrillic→Uzbek Latin). If no reasonable match exists, set "name" to null.

Output ONLY this JSON array, no other text:
[{{"name": "matched catalog name or null", "quantity": 3}}]"""

    response = client.models.generate_content(
        model="gemini-3.7-flash",  # cheap + fast; use gemini-3.1-pro-preview if accuracy needs a bump
        contents=[
            types.Part.from_bytes(data=image_data, mime_type="image/jpeg"),
            prompt,
        ],
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="low"),  # keep cost/latency down
            response_mime_type="application/json",  # forces valid JSON output, no markdown fences
            max_output_tokens=1800,
        ),
    )

    raw_text = response.text
    if not raw_text:
        print("No text in response:", response)
        return "❌ AI javobida matn topilmadi."

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        print("Failed to parse:", raw_text)
        return "❌ AI javobini o'qib bo'lmadi, qaytadan urinib ko'ring."

    message = "Qo'shildi:\n"
    for item in data:
        if item["name"]:
            product = Product.objects.filter(name=item["name"]).first()
            if product:
                Stock.objects.create(product=product, qty=item["quantity"], created_at=timezone.now())
                product.qty += item["quantity"]
                product.save()
                message += f"✅ {item['name']} — {item['quantity']}\n"
        else:
            message += f"❌ Noma'lum mahsulot — {item['quantity']}\n"
    return message