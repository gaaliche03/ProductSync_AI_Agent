import pandas as pd
import numpy as np
import re

from analyze_file import analyze_file
from map_columns import map_columns

#file data_clean.py : prendre les données Excel brutes + le mapping ==> produire un DataFrame propre et standardisé
#convetir format du prix en float
def clean_price(val):
    if pd.isna(val) or str(val).strip() == "":
        return np.nan
    val = str(val)
    val = re.sub(r"[€$£]", "", val)
    val = val.replace("EUR", "").replace("USD", "").replace("GBP", "")
    val = val.replace(",", ".").strip()
    try:
        return round(float(val), 2)
    except:
        return np.nan

#convrt format stock to int
def clean_stock(val):
    if pd.isna(val) or str(val).strip() == "":
        return np.nan
    val=str(val).lower()
    val=val.replace("units","").replace("pcs","").strip()
    val=val.replace(",",".").split(".")[0]
    try:
        return int(val)
    except:
        return np.nan

#normalisation text
def clean_text(val):
    if pd.isna(val) or str(val).strip()=="":
        return np.nan
    return str(val).strip().title()

#que de num
def clean_numeric_val(val):
    val = str(val).replace(",",".").replace(" g","").strip()
    try:
        return round(float(val),2)
    except:
        return val

#merge to extra_info cols dans un string 
def merge_extra_info(row,extra_cols):
    parts=[]
    for col in extra_cols:
        val=row.get(col)
        if pd.notna(val) and str(val).strip() != "":
            cleaned = clean_numeric_val(val)
            parts.append(f"{col}: {cleaned}")
    return " | ".join(parts) if parts else np.nan

#retourner dataframe with target schema 
def clean_data(df,mapping):
    df=df.copy()

    #rename cols based on mapping
    rename_map={}
    extra_info_cols=[]

    for raw_col,info in mapping.items():
        target=info["target"]
        if raw_col not in df.columns:
            continue
        if target=="ignore":
            continue
        if target=="extra_info":
            extra_info_cols.append(raw_col)
        else:
            #si target already exists (duplicate mapping) => suffix with _2
            if target in rename_map.values():
                rename_map[raw_col]=target + "_2"
            else:
                rename_map[raw_col]=target

    df.rename(columns=rename_map, inplace=True)

    #clean prix
    if "price" in df.columns:
        df["price"]=df["price"].apply(clean_price)

    #clean stock
    if "stock" in df.columns:
        df["stock"]=df["stock"].apply(clean_stock)

    #normalize text cols
    text_cols = ["product_name","brand","category","description","country","labels","quantity"]
    for col in text_cols:
        if col in df.columns:
            df[col]=df[col].apply(clean_text)

    if "quantity" in df.columns:
        df["quantity"]=df["quantity"].apply(
        lambda x: str(x).strip().lower() if pd.notna(x) else np.nan
    )

    #merge extra_info cols
    if extra_info_cols:
        df["extra_info"]=df.apply(lambda row: merge_extra_info(row,extra_info_cols),axis=1)
        df.drop(columns=extra_info_cols,inplace=True)

    #remove les duplications
    before=len(df)
    df.drop_duplicates(inplace=True)
    df.reset_index(drop=True,inplace=True)
    duplicates_removed= before - len(df)

    #add status col
    def assign_status(row):
        missing_critical = []
        for col in ["product_name","price","category"]:
            if col in df.columns and pd.isna(row.get(col)):
                missing_critical.append(col)
        return "needs_review" if missing_critical else "ready"

    df["status"] = df.apply(assign_status, axis=1)

    #keep que schema cols
    schema_cible = ["product_name","brand","category","quantity","price","stock","description","extra_info","country","labels","status"]

    final_cols = [c for c in schema_cible if c in df.columns]
    df = df[final_cols]
    print(f" clean_data done : {len(df)} rows, {duplicates_removed} duplicates removed")
    return df


#
if __name__ == "__main__":
    df = pd.read_excel(r"C:\Users\MSI\Documents\ProductSync\data\input\products_raw.xlsx")
    analysis = analyze_file(r"C:\Users\MSI\Documents\ProductSync\data\input\products_raw.xlsx")
    mapping = map_columns(analysis["columns"])
    df_clean = clean_data(df, mapping)

    print(df_clean.head(10).to_string())
    print(f"\nStatus counts:\n{df_clean['status'].value_counts()}")