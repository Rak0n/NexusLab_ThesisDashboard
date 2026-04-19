 🧪 Mappa Architetturale della Tesi (Data Workflow)


## 1. 🧫 Feedstocks (Materie Prime) & Caratterizzazione

Le radici dell'albero sperimentale. Ogni feedstock ha una sua anagrafica fissa.

- **SS:** Sewage Sludge (Fango di depurazione).
    
- **PE:** Polietilene (Plastica sintetica).
    
- **MB:** MaterBi (Bioplastica sintetica).
    
- **CR:** Campione Reale (Sopravaglio da impianto di compostaggio).
    
- _Mix Sintetico DOE:_ 50% PE + 50% MB.
    
- **Analisi Caratterizzazione (Grezzi):**
    
    - Analisi Elementare (CHNSO).
        
    - Bomba di Mahler (HHV).
        
    - TGA (Termogravimetria).
        

## 2. 🔥 Fase 1: Pirolisi & DOE (Design of Experiments)

Questa fase rappresenta la matrice di ottimizzazione principale.

- **Reattori:** Reattore da banco  vs TGA (simulazione per fit modelli).
    
- **Fattori Variabili (Input):**
    
    - `Temperatura`: 450 - 650 °C.
        
    - `% Plastiche`: 20 - 80% (sul mix sintetico).
        
    - `Catalizzatore`: Presenza/Assenza.
        
- **Risposte (Output per il DOE):**
    
    - `Resa_Olio`: Dati estratti dal Reattore da banco.
        
    - `Resa_Char`: Dati estratti dalla TGA (per migliorare il fitting statistico).
        
    - `Resa_Gas`: Calcolata per differenza `(100 - Resa_Olio - Resa_Char)`.
        
- **Validazione e Ottimizzazione:**
    
    - Priorità Ottimizzazione: (3) Minimizzare Plastica, (5) Massimizzare Olio.
        
    - Prove eseguite: Baseline (Mix Sintetico), Ottimizzate (Sintetico), Reali (SS + CR), Bianche (Singoli componenti).
        
- **Analisi Prodotti (Fase 1):**
    
    - Gas: GC (tutte le prove).
        
    - Oli: GC-MS + Analisi Elementare.
        

## 3. 💧 Fase 2: HTL & HTU (Hydrothermal Processing)

L'upgrading e la valorizzazione in fase umida.

- **Reattore:** Batch Reactor.
    
- **Processi:**
    
    - **HTL:** Su campioni singoli, mix di feedstock crudi, con/senza catalizzatore.
        
    - **HTU (Hydrothermal Upgrading):** HTL eseguito _sugli_ oli ottenuti dalla pirolisi.
        
- **Prodotti (Frazioni):**
    
    - `AP` (Aqueous Phase).
        
    - `BC` (Biocrude).
        
    - `Char` (Solido residuo).
        
- **Analisi Prodotti (Fase 2):**
    
    - AP: GC-MS.
        
    - BC: GC-MS + Analisi Elementare.
    

