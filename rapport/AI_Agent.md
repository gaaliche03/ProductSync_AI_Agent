
# ProductSync AI Agent — Rapport complet

## 1. Problématique
Les entreprises reçoivent quotidiennement des fichiers Excel produits provenant de sources multiples (fournisseurs, ERP, partenaires). Ces fichiers ont des structures hétérogènes, des colonnes incohérentes et nécessitent un nettoyage manuel long, répétitif et sujet aux erreurs.

Objectif : automatiser entièrement l’intégration et la standardisation de ces données produits.

---

## 2. Domaine
Le projet appartient aux domaines suivants :
- Data Engineering
- Intelligence Artificielle appliquée
- Automatisation des pipelines de données
- Intégration de données e-commerce / ERP

---

## 3. Fonctionnement du projet
L’utilisateur fournit un fichier Excel brut contenant des produits.

Le système :
- analyse le fichier
- comprend sa structure
- décide des transformations à appliquer
- nettoie et normalise les données
- enrichit les informations produits si nécessaire
- génère un fichier final structuré et un rapport

---

## 4. Stack technique
- Python (pandas, numpy)
- LLM local (Ollama ou Mistral)
- Excel (openpyxl)
- FastAPI (API REST)
- Streamlit (interface utilisateur optionnelle)

---

## 5. Architecture
Excel brut
→ Agent IA (raisonnement et planification)
→ Python (traitement pandas)
→ Nettoyage et transformation
→ Enrichissement (optionnel)
→ Génération de rapport
→ Excel structuré final

---

## 6. Tools de l’agent

analyze_file :
Analyse le fichier Excel, détecte les colonnes, types et valeurs manquantes.

map_columns :
Mappe les colonnes vers un schéma standard via le LLM.

clean_data :
Nettoie les données (formats, casse, valeurs numériques).

detect_anomalies :
Détecte les doublons, valeurs aberrantes et incohérences.

enrich_products :
Enrichit les données produits via le LLM.

generate_report :
Génère un rapport global des transformations effectuées.

---

## 7. Schéma cible

Le format final est toujours :

- product_name (string)
- price (float)
- category (string)
- stock (int)
- description (string)
- status (ready / needs_review)

---

## 8. Nature “agent IA”

Le système est un agent car :
- il ne suit pas un pipeline fixe
- il adapte ses actions selon les données
- il prend des décisions conditionnelles
- il utilise des outils externes
- il conserve un état de raisonnement

---

## 9. Valeur pour le CV

Ce projet démontre :
- conception d’un agent IA complet
- intégration LLM + data engineering
- automatisation de pipelines de données réels
- exposition API et potentiel production
- résolution d’un problème concret d’entreprise

---

## 10. Limites
- erreurs possibles du LLM sur mapping complexe
- enrichissement dépendant de la qualité du modèle
- gestion multi-feuilles Excel non incluse dans la version initiale

---

# 11. Plan de réalisation

## Phase 1 — Setup
- environnement
- dataset de test

## Phase 2 — Tools
- analyze_file
- map_columns
- clean_data
- detect_anomalies
- enrich_products
- generate_report

## Phase 3 — Agent
- définition de l’état
- construction du graphe logique
- intégration LLM
- tests end-to-end

## Phase 4 — API et interface
- FastAPI endpoints
- Streamlit interface
- intégration complète

## Phase 5 — Qualité
- gestion des erreurs
- optimisation prompts
- tests sur datasets variés
- dockerisation

## Phase 6 — Finalisation
- README GitHub
- démonstration
- déploiement
