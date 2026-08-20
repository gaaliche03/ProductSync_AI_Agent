import pandas as pd
import numpy as np
import json
import time
from groq import Groq
from dotenv import load_dotenv
import os

from analyze_file import analyze_file
from map_columns import map_columns
from clean_data import clean_data
from detect_anomalies import detect_anomalies

load_dotenv()
client = Groq(api_key=os.getenv("API_KEY"))

def enrich_row(row):
    prompt = f"""You are a product catalog expert specialized in any type of products.

Given this product information:
- Name: {row.get("product_name", "Unknown")}
- Brand: {row.get("brand", "Unknown")}
- Extra info: {row.get("extra_info", "Unknown")}
- Country: {row.get("country", "Unknown")}
- Current category: {row.get("category", "missing")}
- Current description: {row.get("description", "missing")}
- Current labels: {row.get("labels", "missing")}

Return ONLY this JSON, nothing else, no explanation, no markdown:
{{"category": "inferred category or null", "description": "short description max 80 chars or null", "labels": "relevant label or null"}}"""

    for attempt in range(3):
        try:
            response = client.chat.completions.create(model="openai/gpt-oss-120b",messages=[{"role": "user", "content": prompt}],
                                                      max_tokens=300,temperature=0)
            raw = response.choices[0].message.content.strip()
            if not raw:
                raise ValueError("Empty response")
            raw = raw.replace("```json", "").replace("```", "").strip()
            start = raw.find("{")
            end   = raw.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found")
            raw = raw[start:end]
            return json.loads(raw)

        except Exception as e:
            if attempt < 2:
                time.sleep(5)
                continue

            # Au lieu de raise, retourner un dict vide pour ne pas bloquer
            return {"category": None, "description": None, "labels": None}
        
#permet d'enrechir rowq avec missing category, decript or label avec LLM
#return:enriched DataFrame+enrichment report
def enrich_products(df):
    df = df.copy()
    #identifier les lignes qui ont besoin d'enrichissement
    needs_enrichment = df[df["category"].isna() |df["description"].isna() |df["labels"].isna()].index.tolist()
    print(f"{len(needs_enrichment)} rows need enrichment...")

    enriched_count= 0
    failed_count= 0
    enrichment_log= []

    for idx in needs_enrichment:
        row = df.loc[idx]
        try:
            suggestions = enrich_row(row)
            changes = []
            # Appliquer uniquement les suggestions non-null
            if suggestions.get("category") and pd.isna(df.loc[idx, "category"]):
                df.loc[idx, "category"] = suggestions["category"]
                changes.append(f"category->{suggestions['category']}")

            if suggestions.get("description") and pd.isna(df.loc[idx, "description"]):
                df.loc[idx, "description"] = suggestions["description"]
                changes.append(f"description added")

            if suggestions.get("labels") and pd.isna(df.loc[idx, "labels"]):
                df.loc[idx, "labels"] = suggestions["labels"]
                changes.append(f"labels->{suggestions['labels']}")

            if changes:
                enriched_count += 1
                enrichment_log.append({"row":int(idx),"product": str(row.get("product_name", "")),"changes": changes})

            #pause pour éviter rate limit Groq
            time.sleep(0.5)

        except Exception as e:
            failed_count += 1
            print(f"Row {idx} failed: {e}")
            continue

    #recalculer status après enrichissement
    if "status" in df.columns:
        def assign_status(row):
            for col in ["product_name", "price", "category"]:
                if col in df.columns and pd.isna(row.get(col)):
                    return "needs_review"
            return "ready"
        df["status"] = df.apply(assign_status, axis=1)

    report = {
        "rows_processed":len(needs_enrichment),
        "rows_enriched":enriched_count,
        "rows_failed":failed_count,
        "enrichment_log": enrichment_log[:10]  # premiers 10 pour lisibilité
    }

    print(f" enrich_products done : {enriched_count} enriched, "
          f"{failed_count} failed")

    return df, report


#
if __name__ == "__main__":

    df= pd.read_excel(r"C:\Users\MSI\Documents\ProductSync\data\input\products_raw.xlsx")
    analysis = analyze_file(r"C:\Users\MSI\Documents\ProductSync\data\input\products_raw.xlsx")
    mapping  = map_columns(analysis["columns"])
    df_clean = clean_data(df, mapping)
    _, df_clean = detect_anomalies(df_clean)

    df_enriched, report = enrich_products(df_clean)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nStatus final:\n{df_enriched['status'].value_counts()}")
    print(f"\nCategory remplissage: {df_enriched['category'].notna().sum()}/{ len(df_enriched)}")