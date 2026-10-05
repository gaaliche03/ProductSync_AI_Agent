import os
import json
import pandas as pd
import sys
from typing import TypedDict,Optional
from langgraph.graph import StateGraph,END
from dotenv import load_dotenv
from analyze_file import analyze_file
from map_columns import map_columns
from clean_data import clean_data
from detect_anomalies import detect_anomalies
from enrich_products import enrich_products
from generate_report import generate_report
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')


#state final
class AgentState(TypedDict):
    filepath: str
    analysis:Optional[dict]
    mapping:Optional[dict]
    df_raw:Optional[object]
    df_clean:Optional[object]
    df_final:Optional[object]
    cleaning_stats:Optional[dict]
    anomaly_report:Optional[dict]
    enrichment_report:Optional[dict]
    report_json:Optional[dict]
    report_md:Optional[str]
    log:list
    error:Optional[str]

#definir les noeuds
def node_analyze(state: AgentState):
    print("(Agent) Step 1/6: Analyzing file")
    try:
        analysis = analyze_file(state["filepath"])
        df_raw = pd.read_excel(state["filepath"])
        return {**state,"analysis": analysis,"df_raw":df_raw,
                "log":state["log"] + [f"analyze_file: {analysis['total_rows']} rows,{analysis['total_columns']} columns, quality={analysis['quality_score']}%"]}
    except Exception as e:
        return {**state,"error": f"analyze_file failed:{e}"}


def node_map(state: AgentState):
    print("(Agent) Step 2/6: Mapping columns")
    try:
        mapping = map_columns(state["analysis"]["columns"])
        mapped = sum(1 for v in mapping.values() if v["target"] != "ignore")
        return {**state,"mapping": mapping,"log":state["log"] + [f"map_columns: {mapped}/{len(mapping)} columns mapped"]}
    except Exception as e:
        return {**state,"error": f"map_columns failed:{e}"}


def node_clean(state: AgentState):
    print("(Agent) Step 3/6: Cleaning data")
    try:
        df_clean = clean_data(state["df_raw"], state["mapping"])
        cleaning_stats = {"rows_after_cleaning": len(df_clean),"duplicates_removed":state["analysis"]["duplicates"]}
        return {**state,"df_clean":df_clean,"cleaning_stats": cleaning_stats,"log":state["log"] + [f"clean_data: {len(df_clean)} rows after cleaning"]}
    except Exception as e:
        return {**state, "error": f"clean_data failed: {e}"}


def node_detect(state: AgentState):
    print("(Agent) Step 4/6: Detecting anomalies")
    try:
        anomaly_report, df_clean = detect_anomalies(state["df_clean"])
        return {**state,"df_clean":df_clean,"anomaly_report": anomaly_report,
                "log":state["log"] + [f"detect_anomalies: {anomaly_report['flagged_rows']} flagged rows"]}
    except Exception as e:
        return {**state,"error":f"detect_anomalies failed:{e}"}


def node_enrich(state: AgentState):
    print("(Agent) Step 5/6: Enriching products")
    try:
        df_final,enrichment_report = enrich_products(state["df_clean"])
        return {**state,"df_final":df_final,"enrichment_report": enrichment_report,
                "log":state["log"] + [f"enrich_products: {enrichment_report['rows_enriched']} enriched"]
        }
    except Exception as e:
        return {**state,"error": f"enrich_products failed:{e}"}


def node_report(state: AgentState):
    print("(Agent) Step 6/6: Generating report")
    try:
        report_json,report_md= generate_report(state["analysis"],state["mapping"],
                                               state["cleaning_stats"],state["anomaly_report"],state["enrichment_report"],state["df_final"])
        return {**state,"report_json": report_json,"report_md" :report_md,"log":state["log"] + ["generate_report: done"]}
    except Exception as e:
        return {**state,"error": f"generate_report failed:{e}"}


#case d'erreur
def should_continue(state: AgentState):
    if state.get("error"):
        print(f"(Agent) ERROR:{state['error']}")
        return "end"
    return "continue"

#graph final
def build_agent():
    graph = StateGraph(AgentState)
    graph.add_node("analyze",node_analyze)
    graph.add_node("map",node_map)
    graph.add_node("clean",node_clean)
    graph.add_node("detect",node_detect)
    graph.add_node("enrich",node_enrich)
    graph.add_node("report",node_report)

    #pt de start
    graph.set_entry_point("analyze")

    #les edges et condition d'arret
    for src, dst in [("analyze","map"), ("map","clean") , ("clean","detect"),("detect","enrich"), ("enrich","report")]:
        graph.add_conditional_edges(src,should_continue,{"continue": dst,"end": END})
    graph.add_edge("report",END)
    return graph.compile()

#permet de faire run to the full productSync agent pour avoir un .xlsx file et return final state avec le rapport et dataframe cleaned
def run_agent(filepath):
    agent = build_agent()

    initial_state = AgentState(filepath=filepath,analysis=None,mapping=None,df_raw=None, df_clean=None ,  df_final=None, 
                               cleaning_stats=None,anomaly_report=None,enrichment_report=None,report_json=None,  report_md=None,log=[],error=None)
    
    print("***Starting ProductSync Agent***")
    final_state = agent.invoke(initial_state)
    print("\n[Agent] Log:")
    for entry in final_state["log"]:
        print(f"*{entry}")
    return final_state


if __name__=="__main__":
    filepath = r"C:\Users\MSI\Documents\ProductSync\data\input\products_raw.xlsx"
    state=run_agent(filepath)

    if state.get("error"):
        print(f"\nAgent failed: {state['error']}")
    else:
        os.makedirs(r"C:\Users\MSI\Documents\ProductSync\data\output",exist_ok=True)
        with open(r"C:\Users\MSI\Documents\ProductSync\data\output\report.md","w",encoding="utf-8") as f:
            f.write(state["report_md"])
        state["df_final"].to_excel(r"C:\Users\MSI\Documents\ProductSync\data\output\products_clean.xlsx",index=False)

        print(f"\nAgent completed successfully")
        print(state["df_final"]["status"].value_counts())