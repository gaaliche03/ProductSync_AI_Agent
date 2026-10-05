import os
import uuid #generate unique identifants
import shutil
import sys
import time
from fastapi import FastAPI,UploadFile,File,HTTPException
from fastapi.responses import FileResponse,JSONResponse
import uvicorn #excuter app asynchro created avec fastapi
sys.path.append(r"C:\Users\MSI\Documents\ProductSync\src")
from productsync_agent import run_agent



app=FastAPI(title="ProductSync AI Agent", version="1.0.0")
sessions={}

#endpoints
@app.get("/")
#accessible via GET http.. et il retuorne ses infos sur api réalisé
def root():
    return {"message":"ProductSync AI Agent API",
            "endpoints": {"POST /process":"upload excel file and process it","GET /download/{session_id}":"download the clean excel file",
                          "GET /report/{session_id}":"get the processing report","GET /docs":"interactive API documentation"}}

@app.post("/process")
#traiter file
#... ca veut dire que on doit obligatoirement recevoir un file envoyé par user
def process_file(file: UploadFile=File(...)):
    #verif d'extension du file envoyé
    if not file.filename.endswith((".xlsx",".xls")):
        raise HTTPException(status_code=422,detail="only .xlsx or .xls files are accepted")
    
    session_id= str(uuid.uuid4())[:8] #generer id
    input_path= os.path.join(r"C:\Users\MSI\Documents\ProductSync\data\uploads",f"{session_id}_input.xlsx")
    output_path= os.path.join(r"C:\Users\MSI\Documents\ProductSync\data\output",f"{session_id}_clean.xlsx")
    report_path= os.path.join(r"C:\Users\MSI\Documents\ProductSync\data\output",f"{session_id}_report.md")

    #sauvegarder le file uploaded
    with open(input_path,"wb") as f:
        shutil.copyfileobj(file.file,f)
    start = time.time()
    state = run_agent(input_path)
    duration = round(time.time()-start,1)
    print("temps du traitement",duration)

    #verif si l'agent a donné une erreur
    if state.get("error"):
        raise HTTPException(status_code=500, detail=state["error"])

    #sauvegarder les outputs(dataframe)
    state["df_final"].to_excel(output_path,index=False)
    with open(report_path,"w",encoding="utf-8") as f:
        f.write(state["report_md"])

    #stocker les infos de la session en mémoire
    sessions[session_id]= {"input_path" : input_path,"output_path": output_path,"report_json":state["report_json"],"log":state["log"]}

    #retourner le rapport aka reponse de l'api
    return JSONResponse(content={"session_id":session_id,"status":"success","report":state["report_json"],"log":state["log"],
                                 "download_url":f"/download/{session_id}","report_url": f"/report/{session_id}"})

#endpoint de telechargement
@app.get("/download/{session_id}")
def download_file_cleaned(session_id:str):
    if session_id not in sessions:
        raise HTTPException(status_code=404,detail="session not found")
    output_path = sessions[session_id]["output_path"]
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404,detail="file not found")
    return FileResponse(path=output_path,filename=f"products_clean_{session_id}.xlsx",media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

#endpoint du rapport
@app.get("/report/{session_id}")
def get_report(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404,detail="session not found")
    return JSONResponse(content={"session_id":session_id,"report_json": sessions[session_id]["report_json"],"log":sessions[session_id]["log"]})

#endpoint de la session
@app.get("/sessions")
def list_sessions():
    return {"total":len(sessions),"sessions" : list(sessions.keys())}


if __name__ == "__main__":
    uvicorn.run("main:app",host="0.0.0.0",port=8000, reload=False)