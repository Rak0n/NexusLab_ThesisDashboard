# NexusLab_ThesisDashboard

# 🧪 NexusLab LIMS: Biorefinery & Chemical Recycling Data Workflow

**NexusLab LIMS** (Laboratory Information Management System) è una piattaforma avanzata e interattiva progettata per la gestione, l'analisi e la visualizzazione dei dati nella ricerca sulle **Bioraffinerie e il Riciclo Chimico**.

L'architettura del sistema è ottimizzata per tracciare complessi processi termochimici e le loro interconnessioni (Lineage), seguendo l'intera catena del valore: dal rifiuto di partenza (Feedstock), passando per la **Pirolisi**, fino alla **Liquefazione Idrotermica (HTL)** e all'**Upgrading Idrotermico (HTU)**.

## 🎯 Struttura dell'Applicazione e Moduli

L'applicazione è suddivisa in diverse aree di lavoro, accessibili tramite la sidebar laterale, progettate per accompagnare il ricercatore dalla visione globale fino al dettaglio molecolare della singola prova.

### 🏗️ Control Tower (Visione Globale)

Il cuore gestionale del LIMS.

- **Registro Interattivo:** Una griglia globale (AgGrid) che racchiude tutte le prove operative (Pirolisi, HTL, HTU) con i rispettivi parametri chiave (Temperatura, Tempo, Catalizzatore, Feedstock composito) e le analisi disponibili.
    
- **Cassetto Analitico (Context Drawer):** Selezionando una prova, si apre un dettaglio rapido che mostra la ricetta di partenza a torta, il lineage relazionale grafico (es. `Feed ➔ Pirolisi ➔ HTU`) e le medie delle rese di processo con badge per le analisi completate.
    

### 🔍 Deep Dive (Analisi a 4 Quadranti)

Un ambiente di indagine isolato per esplorare a fondo una singola prova (es. `P1`, `HTL_1`). Costruito con una dashboard personalizzabile a 4 quadranti:

1. **Metadati & Lineage:** Riepilogo delle condizioni operative e della "storia" del campione.
    
2. **Rese di Processo:** Grafici a barre per visualizzare le rese massiche (Olio, Char, Gas, Aqueous Phase, Biocrude) con possibilità di collassare le repliche (media e deviazione standard).
    
3. **Analitica Specifica:** Scelta tra moduli interattivi per esplorare i dati **GC-MS** (torte per macro-famiglie, griglia composti e rendering RDKit live), **CHNSO** (composizione elementare e HHV) o **GC Gas** (composizione gas e PCI).
    
4. **Diario Operativo:** Un editor integrato per leggere e scrivere note di laboratorio in formato Markdown (`.md`) salvate in locale.
    

### 🔬 Modulo GC-MS (Analisi Molecolare)

Modulo dedicato all'ingestione e visualizzazione dei dati di Gas Cromatografia - Spettrometria di Massa.

- **Ingestione Automatizzata:** Sistema drag&drop per i report Excel dello strumento. Ricalcola le aree filtrando per Match Factor e inietta i dati nel database, gestendo le associazioni al `target_id` esatto (es. `P1_OIL`, `HTL_1_BC`). Integra PubChemPy per calcolare al volo Formula Bruta e Peso Molecolare.
    
- **Confronto Dinamico:** Grafici a barre raggruppate per confrontare diverse prove in base alle macro-classi chimiche (es. idrocarburi, ossigenati), con funzionalità di drill-down per esplorare le sotto-famiglie.
    
- **Molecole Valorizzabili (Platform Chemicals):** Focus sui composti ad alto valore aggiunto (es. Fenoli, Ciclopentanoni, Alcoli). Permette di generare classifiche globali interrogando tutto il database per scoprire quali prove massimizzano specifici target chimici.
    
- **Ricerca Globale & Marker:** Motore di ricerca full-text per composti e formule. Include un **Diagramma Triangolare (Ternary Plot)** che, basandosi su molecole "Marker" tracciate nel dizionario interno, stima l'origine del biocrude (es. % da Polietilene, % da Fanghi, % da Mater-Bi).
    

### 🟢 Modulo CHNSO (Analisi Elementare)

- Gestione della composizione elementare (Carbonio, Idrogeno, Azoto, Zolfo, Ossigeno calcolato per differenza).
    
- Visualizzazione dei trend grafici multi-frazione.
    
- Calcolo e visualizzazione dei rapporti atomici chiave (H/C, O/C, N/C) e stima del Potere Calorifico Superiore (HHV).
    

### 🟣 Modulo GC (Analisi Gas)

- Ingestione dei risultati gas-cromatografici per i gas incondensabili (H2, CO, CO2, CH4, C2, C3).
    
- Dashboard comparativa che mostra le percentuali di volume sia normalizzate sull'aria che assolute.
    
- Monitoraggio del Potere Calorifico Inferiore (PCI) della miscela di gas prodotta.
    

## 📊 Struttura del Database Relazionale (SQLite)

Il sistema si appoggia a un robusto database SQLite gestito tramite **SQLAlchemy 2.0**, progettato con un'architettura Entity-Relationship che previene la formazione di dati orfani e garantisce la rigida tracciabilità del _Lineage_ di processo.

### 1. Tabelle di Anagrafica e Processo (Il Core)

- **`feedstocks`**: Anagrafica delle matrici di partenza (es. PE, Fanghi, Mater-Bi) con le loro categorie.
    
- **`prove_pirolisi`**: Registro delle prove termiche di base (condizioni operative, catalizzatori).
    
- **`runs_pirolisi`**: Gestione delle repliche sperimentali associate a una specifica prova di pirolisi, con le relative rese (Olio, Char, Gas).
    
- **`prove_idrotermiche`**: Registro per processi avanzati in pressione (HTL e HTU), con rese dettagliate per Biocrude, WSO (Fase Acquosa), Char e Gas.
    

### 2. Tabelle Relazionali (Il Motore del Lineage)

Definiscono il "cosa entra in cosa".

- **`pirolisi_ricetta`**: Tabella ponte che collega più `feedstocks` a una singola prova di pirolisi definendone le percentuali di mix (es. 50% PE + 50% Fanghi).
    
- **`input_idrotermico`**: Collega l'input di un processo idrotermico alla sua origine. Se è un processo HTU, la sorgente sarà un olio di pirolisi (es. `P1_OIL`). Se è HTL diretto, la sorgente sarà un feedstock solido.
    

### 3. Tabelle Analitiche (Il Dato Scientifico)

- **`registro_analisi`**: La "Spina Dorsale" analitica. Associa ogni frazione fisica (il `target_id`, es. `P1_OIL`, `HTL_1_BC`) ai tipi di analisi eseguiti (GC-MS, CHNSO, GC) per sapere sempre quali dati sono disponibili.
    
- **`dati_chnso`**: Contiene le medie, deviazioni standard e rapporti atomici per ogni `target_id`.
    
- **`dati_gc`**: Contiene la ripartizione dei gas e il PCI calcolato.
    
- **`dati_gcms`**: Tabella massiva che raccoglie tutti i composti identificati, con tempo di ritenzione, Match Factor, e le aree percentuali originali e normalizzate.
    
- **`dizionario_gcms`**: Il cervello chimico dell'app. Una tabella di lookup che mappa i nomi dei composti presenti in `dati_gcms` associandovi la `macro_class`, la `class_of_compounds`, e flag fondamentali come `is_contaminant`, `is_valuable` e `is_marker` (con la rispettiva `marker_source_id` per i diagrammi ternari).
    

## 🛠️ Stack Tecnologico

- **Frontend / UI:** [Streamlit](https://streamlit.io/ "null") e `streamlit-aggrid`
    
- **Data Manipulation:** Pandas
    
- **Data Visualization:** Plotly Express / Graph Objects
    
- **Database Management:** SQLite + SQLAlchemy 2.0 (Query sicure con parametri nominati dinamici)
    
- **Cheminformatica Live:** PubChemPy (estrazione SMILES via API) e RDKit (rendering 2D in-memory)
