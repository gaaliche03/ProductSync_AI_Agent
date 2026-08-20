#une fois dataframe est nettoyé par clean_data, le role de detect_anomalies est de détecter les pbs non résolus automatiquement
#et à la fin il produit un rapport structuré que l'agent ai utilisera si une ligne est ready ou needs_review(another code)(cols status)
#return :dict with anomaly report + updated DataFrame

import pandas as pd
import numpy as np
import json

from analyze_file import analyze_file
from map_columns  import map_columns
from clean_data   import clean_data

def detect_anomalies(df):
    df=df.copy()
    anomalies=[]
    flagged_rows=set()

    #prix aberrants
    if "price" in df.columns:
        too_low=df[df["price"]<0.5].index.tolist()
        too_high=df[df["price"]>500].index.tolist()

        if too_low:
            anomalies.append({"type":"price_too_low","count":len(too_low),"rows":too_low,
                              "message":f"{len(too_low)} products with price < 0.5€"})
            flagged_rows.update(too_low)

        if too_high:
            anomalies.append({"type":"price_too_high","count":len(too_high),"rows":too_high,
                              "message":f"{len(too_high)} products with price > 500€"})
            flagged_rows.update(too_high)

    #stock négatif
    if "stock" in df.columns:
        negative=df[df["stock"] < 0].index.tolist()
        if negative:
            anomalies.append({"type":"negative_stock","count":   len(negative),
                              "rows":negative,"message": f"{len(negative)} products with negative stock"})
            flagged_rows.update(negative)

    #names trop courts
    if "product_name" in df.columns:
        short_names= df[df["product_name"].notna() & (df["product_name"].str.len() < 3)].index.tolist()
        if short_names:
            anomalies.append({"type":"name_too_short","count":len(short_names),"rows":short_names,
                              "message":f"{len(short_names)} products with name < 3 chars"})
            flagged_rows.update(short_names)

    #cat manquantes
    if "category" in df.columns:
        missing_cat = df[df["category"].isna()].index.tolist()
        if missing_cat:
            anomalies.append({"type":"missing_category","count":len(missing_cat),"rows":missing_cat,
                              "message":f"{len(missing_cat)} products with no category"})
            flagged_rows.update(missing_cat)

    #prix manquants
    if "price" in df.columns:
        missing_price = df[df["price"].isna()].index.tolist()
        if missing_price:
            anomalies.append({"type":"missing_price","count":len(missing_price),"rows":missing_price,
                              "message":f"{len(missing_price)} products with no price"})
            flagged_rows.update(missing_price)

    #sane names (doublons)
    if "product_name" in df.columns:
        name_counts = df["product_name"].value_counts()
        dup_names=name_counts[name_counts > 1].index.tolist()
        dup_rows= df[df["product_name"].isin(dup_names)].index.tolist()
        if dup_rows:
            anomalies.append({"type":"duplicate_names","count":len(dup_rows),"rows":dup_rows,
                "message":f"{len(dup_rows)} rows with duplicate product names"})
            flagged_rows.update(dup_rows)

    #update status
    if "status" in df.columns:
        df.loc[list(flagged_rows), "status"] = "needs_review"

    #final rapport
    report = {"total_rows":len(df),
              "total_anomalies":len(anomalies),
              "flagged_rows":len(flagged_rows),
              "ready_rows":int((df["status"] == "ready").sum()),
              "needs_review_rows":int((df["status"] == "needs_review").sum()),
              "anomalies":anomalies}

    print(f" detect_anomalies done : {len(flagged_rows)} flagged rows, "
          f"{report['ready_rows']} ready")

    return report, df


#
if __name__ == "__main__":
    df= pd.read_excel(r"C:\Users\MSI\Documents\ProductSync\data\input\products_raw.xlsx")
    analysis=analyze_file(r"C:\Users\MSI\Documents\ProductSync\data\input\products_raw.xlsx")
    mapping=map_columns(analysis["columns"])
    df_clean=clean_data(df, mapping)
    report,df_final=detect_anomalies(df_clean)
    print(json.dumps(report,indent=2))
    print(f"\nStatus:\n{df_final['status'].value_counts()}")

    

#explication du reslt du test 

#anomalie1: missing_category : 103 lignes: pb déjà connu 
#Cat était vide à 77% dans le dataset brut. 103 produits n'ont pas de catégorie après nettoyage.
#L'agent les marque needs_review pour intervention humaine ou enrichissement LLM 

#anomalie2:missing_price : 15 lignes:
# 15 produits ont un prix manquant car prix était null dans le dataset brut.

#anomalie3: duplicate_names : 18 lignes 
#18 lignes ont des noms de produits qui apparaissent plusieurs fois.
# Ce sont les doublons résiduels que drop_duplicates n'a pas capturés car d'autres colonnes avec un peu de diff.