import os
import io
import time
import pandas as pd
import requests
import streamlit as st

api_url= os.getenv("API_URL","http://localhost:8000")
st.set_page_config(page_title="ProductSync AI Agent", page_icon="🛒",layout="wide")

for key in ("result","clean_df","input_df","error","clean_bytes"):
    st.session_state.setdefault(key, None)


#verif que fastapi est démarrer (to add in sidebar)
def api_is_up():
    try:
        return requests.get(f"{api_url}/",timeout=3).status_code==200
    except requests.RequestException:
        return False

#envoyer excel file uplodedau POST /process et récuperer response json
def call_process(file):
    files= {"file" : (file.name,file.getvalue(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    rep = requests.post(f"{api_url}/process", files=files, timeout=900)
    if rep.status_code !=200:
        try:
            detail= rep.json().get("detail",rep.text)
        except ValueError:
            detail =rep.text
        raise RuntimeError(f"API {rep.status_code}: {detail}")
    return rep.json()

#telecharger file excel clened à partir u GET /download/{session_id}
#donne contenu binaire used pour telechagrement et affichage
def fetch_clean_file(session_id: str):
    rep=requests.get(f"{api_url}/download/{session_id}",timeout=60)
    rep.raise_for_status()
    return rep.content


#transferer ai agent activities à un report .md lisible
def render_log_line(entry):
    if isinstance(entry, dict):
        #chercher step name 
        step = entry.get("step") or entry.get("node") or entry.get("tool") or ""
        #idem pour msg sinon on affiche le dict
        msg = entry.get("message") or entry.get("decision") or entry.get("detail") or str(entry)
        return f"**{step}** — {msg}" if step else str(msg)
    return str(entry)

#afficher raport réalisé .md
def render_report(report):
    if not isinstance(report,dict):
        st.json(report)
        return

    #structure du rapport(j'ai utilisé une structure recommandé par ai)
    scalars = {k: v for k, v in report.items() if isinstance(v, (int, float, str, bool))}
    if scalars:
        cols = st.columns(min(len(scalars), 4))
        for i, (k, v) in enumerate(scalars.items()):
            cols[i % len(cols)].metric(k.replace("_", " ").capitalize(), v)

    for k, v in report.items():
        if k in scalars:
            continue
        st.subheader(k.replace("_", " ").capitalize())
        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            st.dataframe(pd.DataFrame(v), use_container_width=True)
        elif isinstance(v, dict) and v and all(isinstance(x, (int, float)) for x in v.values()):
            st.bar_chart(pd.Series(v))
        else:
            st.json(v)


#sidebar
with st.sidebar:
    st.title("ProductSync ")
    st.caption("Nettoyage et standardisation de données produits")
    if api_is_up():
        st.success(f"API connectée\n\n{api_url}")
    else:
        st.error(f"API injoignable\n\n{api_url}\n\nLancez: `python main.py`")
    st.divider()
    if st.button("🔄 Nouvelle analyse", use_container_width=True):
        for key in ("result", "clean_df","input_df" , "error"):
            st.session_state[key] = None
        st.rerun()

#page principale
st.title("ProductSync AI Agent")
st.write("Importez votre fichier Excel de produits, quel que soit le secteur. Notre AI Agent le nettoie, le standardise et génère un rapport de traitement.")
uploaded = st.file_uploader("Fichier Excel produits", type=["xlsx","xls"])

if uploaded is not None:
    try:
        st.session_state.input_df= pd.read_excel(uploaded)
        uploaded.seek(0)
    except Exception as e:  #file non lisible
        st.session_state.input_df = None
        st.error(f"Impossible de lire le fichier: {e}")

    if st.session_state.input_df is not None:
        with st.expander(
            f"Aperçu du fichier brut ({len(st.session_state.input_df)} lignes)", expanded=False
        ):
            st.dataframe(st.session_state.input_df.head(50), use_container_width=True)

    if st.button("🚀 Lancer l'agent", type="primary", disabled=st.session_state.input_df is None):
        uploaded.seek(0)
        st.session_state.result = None
        st.session_state.clean_df = None
        st.session_state.error = None
        try:
            with st.status("L'agent traite votre fichier…", expanded=True) as status:
                st.write("📤 Envoi du fichier à l'API")
                result = call_process(uploaded)

                # L'API est synchrone : on rejoue le log étape par étape
                st.write("🧠 Etapes de l'agent :")
                for entry in result.get("log", []):
                    st.markdown(f"- {render_log_line(entry)}")
                    time.sleep(0.15)

                st.write("📥 Récupération du fichier nettoyé")
                content = fetch_clean_file(result["session_id"])
                st.session_state.clean_df = pd.read_excel(io.BytesIO(content))
                st.session_state.clean_bytes = content
                st.session_state.result = result
                status.update(label="Traitement terminé ✅", state="complete")
        except requests.Timeout:
            st.session_state.error = "Délai dépassé : le traitement est trop long."
        except requests.ConnectionError:
            st.session_state.error = "Connexion impossible à l'API. Est-elle démarrée ?"
        except Exception as e:
            st.session_state.error = str(e)

if st.session_state.error:
    st.error(st.session_state.error)

result= st.session_state.result
if result:
    st.divider()
    st.subheader(f"Résultat : session `{result['session_id']}`")
    st.download_button("⬇️ Télécharger le fichier propre (.xlsx)",data=st.session_state.clean_bytes,file_name=f"products_clean_{result['session_id']}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",type="primary")
    tab_data, tab_report,tab_log= st.tabs(["📊 Données nettoyées", "📋 Rapport final","🤖 Etapes de l'agent"])

    with tab_data:
        df = st.session_state.clean_df
        raw = st.session_state.input_df
        if raw is not None:
            c1,c2,c3 = st.columns(3)
            c1.metric("Lignes (avant)",len(raw))
            c2.metric("Lignes (après)",len(df), delta=len(df)-len(raw))
            c3.metric("Valeurs nulles",int(df.isna().sum().sum()),delta=int(df.isna().sum().sum() -raw.isna().sum().sum()),delta_color="inverse")
        st.dataframe(df, use_container_width=True)

    with tab_report:
        render_report(result.get("report"))

        st.divider()

        try:
            report_bytes= fetch_report()
            st.download_button("⬇️ Télécharger le rapport (.md)",data=report_bytes,file_name="report.md",mime="text/markdown")
        except FileNotFoundError:
            st.warning("Le fichier report.md n'a pas été trouvé.")

    with tab_log:
        for entry in result.get("log", []):
            st.markdown(f"- {render_log_line(entry)}")