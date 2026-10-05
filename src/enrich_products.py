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
#timeout et max_retries : un appel bloqué ne fige plus l'agent
client = Groq(api_key=os.getenv("API_KEY"), timeout=60, max_retries=2)

#nbre de ligne par lot envoyé à chaque appel llm
batch_size=10

#nan/none valeur par défaut lisible pour le prompt
def clean_val(val,default):
    return default if pd.isna(val) else val

#enrichir lot de ligne en un seul appel llm pour corriger probleme de latence du llm(trop appels)
def enrich_batch(rows):
    items = []
    for idx, row in rows:
        items.append({"id": int(idx),"name": clean_val(row.get("product_name"),"Unknown"),"brand": clean_val(row.get("brand"),"Unknown"),
                      "extra_info": clean_val(row.get("extra_info"),"Unknown"),"country": clean_val(row.get("country"),"Unknown"),
                      "category": clean_val(row.get("category"),"missing"),"description": clean_val(row.get("description"),"missing"),"labels": clean_val(row.get("labels"),"missing")})

    prompt = f"""You are a product catalog expert specialized in any type of products.
    Given this list of products (JSON):
    {json.dumps(items, ensure_ascii=False)}
    
    For EACH product, infer the missing information.
    Return ONLY a JSON list with exactly one object per product, same "id" as the input, nothing else, no explanation, no markdown:
    [{{"id": 0, "category": "inferred category or null", "description": "short description max 80 chars or null", "labels": "relevant label or null"}}]
    
    Use null for "labels" and "description" if you are not sure. Never invent certifications such as Organic or No GMOs."""



    for attempt in range(3):
        try:
            response = client.chat.completions.create(model="openai/gpt-oss-120b",messages=[{"role": "user", "content": prompt}],max_tokens=2000,temperature=0)
            raw = response.choices[0].message.content.strip()
            if not raw:
                raise ValueError("Empty response")
            raw = raw.replace("```json", "").replace("```", "").strip()
            start = raw.find("[")
            end= raw.rfind("]") +1
            if start == -1 or end == 0:
                raise ValueError("No JSON found")
            raw = raw[start:end]
            data = json.loads(raw)
            return {str(d["id"]): d for d in data if isinstance(d, dict) and "id" in d}

        except Exception as e:
            if attempt < 2:
                time.sleep(5)
                continue
            # Au lieu de raise, retourner un dict vide pour ne pas bloquer
            return {}
        
#permet d'enrechir rowq avec missing category, decript or label avec LLM
#return:enriched DataFrame+enrichment report
def enrich_products(df):
    df = df.copy()
    #identifier les lignes qui ont besoin d'enrichissement
    needs_enrichment= df[df["category"].isna() |df["description"].isna() |df["labels"].isna()].index.tolist()
    print(f"{len(needs_enrichment)} rows need enrichment")

    enriched_count= 0
    failed_count= 0
    enrichment_log= []
    
    for i in range(0, len(needs_enrichment), batch_size):
        batch_idx = needs_enrichment[i:i+batch_size]
        batch = [(idx, df.loc[idx]) for idx in batch_idx]
        print(f"Batch {i//batch_size +1}/{(len(needs_enrichment)-1)//batch_size + 1}")        
        results =enrich_batch(batch)
 
        #CAS EXCEPTIONNELLE si le lot échoue: retente ligne par ligne pour ce lot seulement
        if not results and len(batch) >1:
            for idx,row in batch:
                results.update(enrich_batch([(idx,row)]))
 
        for idx,row in batch:
            try:
                suggestions= results.get(str(int(idx)))
                if not suggestions:
                    failed_count= failed_count+1
                    continue

                changes =[]
                #appliquer uniquement les suggestions non-null
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
                    enriched_count= enriched_count+1
                    enrichment_log.append({"row":int(idx),"product": str(row.get("product_name", "")),"changes": changes})

            except Exception as e:
                failed_count += 1
                print(f"Row {idx} failed: {e}")
                continue

        #pause pour éviter rate limit Groq
        time.sleep(0.5)

    #recalculer status après enrichissement
    if "status" in df.columns:
        def assign_status(row):
            for col in ["product_name", "price", "category"]:
                if col in df.columns and pd.isna(row.get(col)):
                    return "needs_review"
            return "ready"
        df["status"] = df.apply(assign_status, axis=1)

    report = {"rows_processed":len(needs_enrichment),"rows_enriched":enriched_count,
              "rows_failed":failed_count,"enrichment_log": enrichment_log[:10]  # premiers 10 pour lisibilité 
              }

    print(f" enrich_products done : {enriched_count} enriched,"
          f"{failed_count} failed")

    return df,report

#
if __name__ == "__main__":
    df= pd.read_excel(r"C:\Users\MSI\Documents\ProductSync\data\input\products_raw.xlsx")
    analysis= analyze_file(r"C:\Users\MSI\Documents\ProductSync\data\input\products_raw.xlsx")
    mapping = map_columns(analysis["columns"])
    df_clean= clean_data(df, mapping)
    report,df_clean = detect_anomalies(df_clean)

    df_enriched, report = enrich_products(df_clean)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nStatus final:\n{df_enriched['status'].value_counts()}")
    print(f"\nCategory remplissage: {df_enriched['category'].notna().sum()}/{ len(df_enriched)}")