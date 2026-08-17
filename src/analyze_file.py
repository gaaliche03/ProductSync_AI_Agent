import pandas as pd
import numpy as np
import json

#analyse file excel et output resume bien structuré pour le donner à l'agent ai pour les transformations
def analyze_file(filepath: str):
    df=pd.read_excel(filepath)
    col_info ={}
    for col in df.columns:
        series=df[col]
        null_pct=round(series.isna().sum()/len(df)*100,1) #calcul de % des val manquantes
        #détecter le type réel de la colonne
        non_null=series.dropna().astype(str).str.strip()
        non_null=non_null[non_null != ""]
        #verif si une val peut etre interpretee comme un nombre
        def is_numeric(val):
            try:
                float(str(val).replace(",",".").replace("€","").replace("$","").replace("USD","").replace("EUR","").replace("g","").strip())
                return True
            except:
                return False
        #detection du type de la col
        if len(non_null)==0:
            detected_type="empty"
        elif non_null.apply(is_numeric).mean()>0.85:
            detected_type="numeric"
        elif non_null.apply(is_numeric).mean()>0.3:
            detected_type="mixed"
        else:
            detected_type="text"
        samples = non_null.head(3).tolist()
        #stock des info de la col
        col_info[col] = {"type":detected_type,"null_%":null_pct,"sample":samples,}
    #score de qualité global=moy du remplissage
    quality_score=round(sum(100-v["null_%"] for v in col_info.values())/len(col_info),1)
    result = {"total_rows":len(df),"total_columns":len(df.columns),"duplicates":int(df.duplicated().sum()),
              "quality_score":quality_score,"columns":col_info}
    return result


##
if __name__ == "__main__":
    result = analyze_file(r"C:\Users\MSI\Documents\ProductSync\data\input\products_raw.xlsx")
    print(json.dumps(result, indent=2, ensure_ascii=False))