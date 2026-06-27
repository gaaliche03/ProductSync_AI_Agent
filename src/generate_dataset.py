import pandas as pd
import numpy as np
import random
import os
random.seed(42)
np.random.seed(42)

#voir les col dispo
"""COLONNES = [
    "product_name", "abbreviated_product_name", "generic_name",
    "brands", "quantity", "categories_en", "main_category_en",
    "labels_en", "ingredients_text", "packaging_en", "allergens",
    "countries_en", "stores", "energy-kcal_100g", "fat_100g",
    "sugars_100g", "proteins_100g", "salt_100g"
]"""
COLONNES = [
    "product_name", "brands", "quantity",
    "categories_en", "main_category_en", "labels_en",
    "ingredients_text", "countries_en",
    "energy-kcal_100g", "fat_100g",
    "sugars_100g", "proteins_100g", "salt_100g"
]

#read csv file de Open Food Facts
print("Lecture du csv de Open Food Facts ")
df=pd.read_csv(r"C:\Users\MSI\Documents\ProductSync\data\en.openfoodfacts.org.products.csv.gz",sep="\t",encoding="utf-8",nrows=5000,low_memory=False,usecols=COLONNES)

print(df.columns)

#verification des colonnes
for col in COLONNES:
    status = "YES" if col in df.columns else "NO"
    print(f"{status} {col}")

#garder que kes lignes avec un nom produit valide
df=df[df["product_name"].notna() & (df["product_name"].str.strip() != "")]
df = df[df["energy-kcal_100g"].notna()].head(100).reset_index(drop=True)
print(f"{len(df)} produits retenus")

#ajouter col price et stock 
df["price"]=[round(random.uniform(0.5, 120.0), 2) for i in range(len(df))]
df["stock"]=[random.randint(0, 300) for i in range(len(df))]

#standarisation
def first_value(val, max_len=40):
    if pd.isna(val): return np.nan
    return str(val).split(",")[0].strip()[:max_len]
#nettoyage
df["categories_en"]= df["categories_en"].apply(first_value)
df["main_category_en"]= df["main_category_en"].apply(first_value)
df["labels_en"]= df["labels_en"].apply(first_value)
df["countries_en"]= df["countries_en"].apply(first_value)
df["packaging_en"]= df["packaging_en"].apply(first_value)
df["ingredients_text"] = df["ingredients_text"].apply(lambda x: str(x)[:150].strip() if pd.notna(x) else np.nan)

#dans cette partie, faut salir les données pour préarer une dataset de test
#et le role de notre agent AI de les nettoyer 
def random_case(s):
    if pd.isna(s): return s
    style = random.choice(["lower", "upper", "title", "mixed"])
    s = str(s)
    if style == "lower":  return s.lower()
    if style == "upper":  return s.upper()
    if style == "title":  return s.title()
    return "".join(c.upper() if random.random() > 0.5 else c.lower() for c in s)

PRICE_FORMATS = [
    lambda p: f"{p}€",
    lambda p: f"${p}",
    lambda p: f"{p} USD",
    lambda p: str(p).replace(".", ","),
    lambda p: f"  {p}  ",
    lambda p: str(p),
    lambda p: f"EUR {p}",
]
CAT_ABBREVS = {
    "beverage":  ["bev", "BEV", "Bvrg", "boissons"],
    "snack":     ["snk", "SNACK", "Snk.", "en-cas"],
    "dairy":     ["dair", "DAIRY", "lait", "Ltr"],
    "cereal":    ["cer", "CER", "céréal", "Cer."],
    "meat":      ["meat", "MEAT", "viande", "Mts"],
    "juice":     ["jus", "JUICE", "Jc.", "JUS"],
    "bread":     ["bread", "BREAD", "pain", "Brd"],
    "sauce":     ["sce", "SAUCE", "Sce.", "sauces"],
    "cosmetic":  ["cosm", "COSM", "beauté", "Csm"],
    "hygiene":   ["hyg", "HYG", "hygiène", "Hyg."],
    "cleaning":  ["cln", "CLEAN", "nettoy", "Cln"],
}
 
def dirty_category(cat):
    if pd.isna(cat): return np.nan
    cat_lower = str(cat).lower()
    for key, variants in CAT_ABBREVS.items():
        if key in cat_lower:
            return random.choice(variants)
    return random_case(str(cat)[:5])
 
def dirty_stock(s):
    r = random.random()
    if r < 0.20: return float(s)
    if r < 0.35: return f"{s} units"
    return s
 
def dirty_numeric(val):
    if pd.isna(val): return np.nan
    r = random.random()
    if r < 0.3: return f"{val} g"
    if r < 0.5: return str(val).replace(".", ",")
    return val
 
n = len(df)

#case alétoire sur texte des cols
df["product_name"]= df["product_name"].apply(random_case)
df["brands"]= df["brands"].apply(random_case)
df["generic_name"]= df["generic_name"].apply(random_case)
df["abbreviated_product_name"]= df["abbreviated_product_name"].apply(random_case)
#prix mal formé
df["price"] = df["price"].apply(lambda p: random.choice(PRICE_FORMATS)(p))
df["categories_en"]    = df["categories_en"].apply(dirty_category)
df["main_category_en"] = df["main_category_en"].apply(dirty_category)
#stock avec float ou  texte
df["stock"] = df["stock"].apply(dirty_stock)
#valeurs mal formatées
for col in ["energy-kcal_100g", "fat_100g", "sugars_100g", "proteins_100g", "salt_100g"]:
    df[col] = df[col].apply(dirty_numeric)
#injection de nulls (10% par col)
for col in ["ingredients_text", "categories_en", "price", "brands", "allergens", "labels_en"]:
    idx = random.sample(range(n), k=max(1, n // 10))
    df.loc[idx, col] = np.nan
#descrip vides(20%)
empty_idx = random.sample(range(n), k=n // 5)
df.loc[empty_idx, "ingredients_text"] = ""
#doublons(8%)
dup_rows = df.sample(n=max(1, n // 12)).copy()
df = pd.concat([df, dup_rows], ignore_index=True)
#renommer les cols q'une facon ambigus
df.rename(columns={
    "product_name":"Prod Name",
    "abbreviated_product_name": "Short Name",
    "generic_name":"Generic",
    "brands":"Brand",
    "quantity":"Qty/Vol",
    "categories_en":"Cat",
    "main_category_en":"Main Cat",
    "labels_en":"Labels",
    "ingredients_text":"Desc",
    "packaging_en":"Pack",
    "allergens":"Allergens",
    "countries_en":"Country",
    "stores":"Store",
    "energy-kcal_100g":"Kcal",
    "fat_100g":"Fat",
    "sugars_100g":"Sugar",
    "proteins_100g":"Prot",
    "salt_100g":"Salt",
    "price":"Prix (€)",
    "stock":"Qty Avail",}, inplace=True)

#.xlsx
os.makedirs(r"C:\Users\MSI\Documents\ProductSync\data\input", exist_ok=True)
out = r"C:\Users\MSI\Documents\ProductSync\data\input\products_raw.xlsx"
df.to_excel(out, index=False, sheet_name="Products")
