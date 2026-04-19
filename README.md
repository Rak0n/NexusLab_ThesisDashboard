# NexusLab_ThesisDashboard

# 🧪 NexusLab LIMS: Biorefinery & Chemical Recycling Data Workflow

**NexusLab LIMS** (Laboratory Information Management System) è una piattaforma avanzata e interattiva progettata specificamente per la gestione, l'analisi e la visualizzazione dei dati nella ricerca sulle **Bioraffinerie e il Riciclo Chimico**.

Il sistema è ottimizzato per tracciare complessi processi termochimici come la **Pirolisi**, la **Liquefazione Idrotermica (HTL)** e l'**Upgrading Idrotermico (HTU)**, permettendo ai ricercatori di seguire l'intera catena del valore (Lineage) dal rifiuto di partenza (Feedstock) fino alla molecola ad alto valore aggiunto (Platform Chemical).

## ✨ Funzionalità Principali

### 🔗 Tracciamento Relazionale (Lineage)

- **Catena del Valore Intelligente:** Traccia la storia esatta di ogni frazione. Da un mix di plastiche (PE) e fanghi (SS) alla Pirolisi, fino all'upgrading HTU dell'olio ottenuto.
    
- **Database Relazionale SQLite:** Architettura robusta basata su SQLAlchemy che previene la creazione di dati orfani e garantisce l'integrità tra le ricette, i processi e le analisi chimiche.
    

### 🔬 Modulo GC-MS (Gas Cromatografia - Spettrometria di Massa)

- **Ingestione Dati Automatizzata:** Drag & drop dei file Excel generati dallo strumento. Il motore filtra automaticamente per `Match Factor`, ricalcola le aree e inietta i dati in SQL in modo sicuro, avvisando in caso di sovrascrittura.
    
- **Classificazione in Macro-Famiglie:** Raggruppamento automatico dei composti in base al dizionario interno (es. idrocarburi, ossigenati, composti azotati).
    
- **Platform Chemicals:** Focus dedicato all'identificazione di molecole valorizzabili (es. Fenoli, Ciclopentanoni, Alcoli) per spostare l'approccio da "smaltimento" a "bioraffineria".
    
- **Rendering Molecolare 2D Live:** Integrazione in tempo reale con **PubChemPy** ed **RDKit**. Cliccando su un composto in tabella, il sistema interroga PubChem per estrarre lo SMILES e RDKit disegna istantaneamente la struttura molecolare.
    

### 🧬 Tracciamento Marker & Diagrammi Ternari

- **Source Apportionment:** Identificazione dell'origine dei biocrude/olii. I composti "Marker" vengono tracciati per determinare quanto del prodotto deriva da Polietilene (PE), Mater-Bi (MB) o Fanghi (SS), visualizzati tramite un elegante **Diagramma Triangolare (Ternary Plot) Plotly**.
    
- **Ricerca Globale:** Motore di ricerca full-text per esplorare la presenza di specifiche molecole (per nome o formula bruta) nell'intero database di prove storiche.
    

### 🏗️ Control Tower & Deep Dive

- **Control Tower:** Una griglia interattiva globale (AgGrid) per visionare tutte le prove operative e i loro parametri (Temp, Tempo, Catalizzatore, Rese).
    
- **Deep Dive a 4 Quadranti:** Un ambiente di analisi focalizzato sulla singola prova, con moduli indipendenti per esplorare:
    
    1. Metadati & Lineage
        
    2. Rese di Processo
        
    3. Famiglie Chimiche & GC-MS
        
    4. Diario Operativo (.md) e future integrazioni (CHNSO, GC Gas).
