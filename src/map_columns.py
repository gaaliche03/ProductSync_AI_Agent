import json
import os
from groq import Groq
from dotenv import load_dotenv
import time

load_dotenv()
client = Groq(api_key=os.getenv("API_KEY"))
schema_cible = ["product_name","brand","category","quantity","price","stock","description","extra_info","country","labels","status"]

#ft permet d'envoyer les col names to llm pour les mapper pour avoir schema cible et leurs score de confience
def map_columns(columns_info):
    cols_summary = ""
    # Nettoyer les noms de colonnes problématiques
    clean_info = {}
    for col, info in columns_info.items():
        clean_col = col.replace("(€)", "(EUR)").replace("€", "EUR")
        clean_info[clean_col] = info
    columns_info = clean_info

    cols_summary = ""
    for col, info in columns_info.items():
        sample = ", ".join(str(s) for s in info["sample"][:2])
        cols_summary += f'- "{col}": type={info["type"]}, examples=[{sample}]\n'

    prompt = f"""You are a data engineering expert specialized in product catalog normalization.
    Below are the columns from a raw product Excel file:
    {cols_summary}
    Target schema to map toward:
    {schema_cible}
    Rules:
    - Every raw column must have exactly one target field
    - If a column does not match any target, use "ignore" as target
    - If two columns map to the same target, keep both but lower the confidence of the less reliable one

    - confidence = your certainty from 0 to 100
    - Columns related to nutrition, specs, materials, or any product-specific attributes → map to "extra_info"
    - Return ONLY a valid JSON object, no text before or after, no markdown
    Expected format:
    {{
    "raw_column_name": {{"target": "target_field", "confidence": score}},
    ...
    }}
"""

    for attempt in range(3):
        try:
            #model="llama-3.3-70b-versatile",
            #pour avoir les models dispo : https://console.groq.com/docs/deprecations
            response=client.chat.completions.create(model="openai/gpt-oss-120b",messages=[{"role": "user", "content": prompt}],
                                                    max_tokens=1500,temperature=0)
            raw = response.choices[0].message.content.strip()
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()

            start = raw.find("{")
            end   = raw.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found in response")
            raw = raw[start:end]

            return json.loads(raw)

        except Exception as e:
            if attempt < 2:
                print(f"***Attempt {attempt+1} failed retrying in 5s***")
                time.sleep(5)
            else:
                raise


if __name__ == "__main__":
    columns_info = {
        "Prod Name":{"type": "text","null_%": 0.0,  "sample": ["pinto bean", "KETO GRANOLA"]},
        "Brand":{"type": "text","null_%": 42.6, "sample": ["central bean", "Danone"]},
        "Cat":{"type": "text","null_%": 77.8, "sample": ["boissons", "Bvrg"]},
        "Main Cat":{"type": "text","null_%": 77.8, "sample": ["Asian", "sce"]},
        "Qty/Vol":{"type": "mixed","null_%": 74.1, "sample": ["250g", "3000ml"]},
        "Labels":{"type": "text","null_%": 83.3, "sample": ["Organic", "No GMOs"]},
        "Country":{"type": "text","null_%": 0.0,  "sample": ["France", "Germany"]},
        "Desc":{"type": "text","null_%": 90.7, "sample": ["Wheat Flour, Sugar..."]},
        "Kcal":{"type": "numeric","null_%": 0.0,  "sample": ["261,4", "580.6"]},
        "Fat":{"type": "numeric","null_%": 2.8,  "sample": ["10.2", "54.8 g"]},
        "Sugar":{"type": "numeric","null_%": 11.1, "sample": ["4.9", "3.2 g"]},
        "Prot":{"type": "numeric","null_%": 2.8,  "sample": ["17.5", "5.9"]},
        "Salt":{"type": "numeric","null_%": 29.6, "sample": ["0,7", "0.27"]},
        "Prix (€)":{"type": "numeric","null_%": 12.0, "sample": ["EUR 3.49", "$33.37"]},
        "Qty Avail":{"type": "numeric","null_%": 0.0,  "sample": ["5", "274"]},
    }

    result = map_columns(columns_info)
    print(json.dumps(result, indent=2, ensure_ascii=False))
