import json
from datetime import datetime
import sys
import pandas as pd
import os

from analyze_file import analyze_file
from map_columns import map_columns
from clean_data import clean_data
from detect_anomalies import detect_anomalies
from enrich_products import enrich_products

sys.stdout.reconfigure(encoding='utf-8')

#mettre al agent decisions into a structured report
def generate_report(analysis, mapping, cleaning_stats, anomaly_report, enrichment_report, df_final):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    #mapping summary
    mapped={k: v for k, v in mapping.items() if v["target"] != "ignore"}
    ignored={k: v for k, v in mapping.items() if v["target"] == "ignore"}
    low_conf={k: v for k, v in mapping.items() if v["confidence"] < 80}

    #status summary
    status_counts=df_final["status"].value_counts().to_dict() if "status" in df_final.columns else {}
    ready_count=status_counts.get("ready", 0)
    review_count=status_counts.get("needs_review", 0)

    #category coverage
    cat_filled=int(df_final["category"].notna().sum()) if "category" in df_final.columns else 0

    #build json report
    report_json = {"generated_at":now,
                   "input_file": {"total_rows":analysis["total_rows"],"total_columns": analysis["total_columns"],"quality_score": analysis["quality_score"],"duplicates":analysis["duplicates"],},
                   "mapping": {"total_columns":len(mapping),"mapped":len(mapped),"ignored":len(ignored),
                               "low_confidence": [{"column": k, "target": v["target"], "confidence": v["confidence"]}for k, v in low_conf.items()]},
                    "cleaning": {"rows_after_cleaning":cleaning_stats["rows_after_cleaning"],"duplicates_removed":cleaning_stats["duplicates_removed"]},
                    "anomalies": {"total_types": anomaly_report["total_anomalies"],"flagged_rows":anomaly_report["flagged_rows"],
                                  "details":[{"type": a["type"], "count": a["count"], "message": a["message"]}for a in anomaly_report["anomalies"]]},
                    "enrichment": {"rows_processed": enrichment_report["rows_processed"],"rows_enriched":enrichment_report["rows_enriched"],
                                   "rows_failed":    enrichment_report["rows_failed"]},
                    "output": {"total_rows":len(df_final),"ready":ready_count,"needs_review":review_count,"category_coverage": f"{cat_filled}/{len(df_final)}"}}

    #build .md rapport
    low_conf_lines = "\n".join(
        f"  - `{item['column']}` -> `{item['target']}` (confidence: {item['confidence']}%)"
        for item in report_json["mapping"]["low_confidence"]) or "None"

    anomaly_lines = "\n".join(
        f"  - **{a['type']}**: {a['message']}"
        for a in report_json["anomalies"]["details"]) or "None"

    enrichment_log = enrichment_report.get("enrichment_log", [])
    enrichment_lines = "\n".join(
        f"  - Row {e['row']} `{e['product']}`: {', '.join(e['changes'])}"
        for e in enrichment_log[:5]) or "None"

    report_md = f"""# ProductSync AI Agent — Processing Report
Generated: {now}

## Input File
- Total rows: {analysis['total_rows']}
- Total columns: {analysis['total_columns']}
- Quality score: {analysis['quality_score']}%
- Duplicates detected: {analysis['duplicates']}

## Column Mapping
- Columns mapped: {len(mapped)}/{len(mapping)}
- Columns ignored: {len(ignored)}
- Low confidence mappings (<80%):
{low_conf_lines}

## Cleaning
- Rows after cleaning: {cleaning_stats['rows_after_cleaning']}
- Duplicates removed: {cleaning_stats['duplicates_removed']}

## Anomalies Detected
{anomaly_lines}

## Enrichment
- Rows processed: {enrichment_report['rows_processed']}
- Rows enriched: {enrichment_report['rows_enriched']}
- Rows failed: {enrichment_report['rows_failed']}
- Sample enrichments:
{enrichment_lines}

## Final Output
- Total rows: {len(df_final)}
- Ready: {ready_count}
- Needs review: {review_count}
- Category coverage: {cat_filled}/{len(df_final)}

## Verdict
{"All products processed successfully." if review_count == 0 else f"{review_count} products need manual review (missing price or category)."}
"""

    print(f" generate_report done")
    return report_json, report_md


#
if __name__ == "__main__":

    filepath = r"C:\Users\MSI\Documents\ProductSync\data\input\products_raw.xlsx"
    df= pd.read_excel(filepath)
    analysis = analyze_file(filepath)
    mapping= map_columns(analysis["columns"])
    df_clean = clean_data(df, mapping)
    cleaning_stats = {"rows_after_cleaning": len(df_clean),"duplicates_removed":analysis["duplicates"],}

    anomaly_report,df_clean = detect_anomalies(df_clean)
    df_enriched,enrichment_report= enrich_products(df_clean)
    report_json, report_md = generate_report(analysis, mapping, cleaning_stats,anomaly_report, enrichment_report, df_enriched)
    print(report_md)

    os.makedirs(r"C:\Users\MSI\Documents\ProductSync\data\output", exist_ok=True)
    with open(r"C:\Users\MSI\Documents\ProductSync\data\output\report.md", "w", encoding="utf-8") as f:
        f.write(report_md)

    df_enriched.to_excel(r"C:\Users\MSI\Documents\ProductSync\data\output\products_clean.xlsx",index=False)
