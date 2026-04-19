# Manifesto di Classificazione Molecolare (Dati GC-MS)

**Progetto:** Upgrading Idrotermico e Pirolisi di Mix Complessi (PE, Mater-Bi, Sewage Sludge, Campione Reale) **Scopo del Documento:** Definire in modo rigoroso e riproducibile i criteri adottati per la classificazione, l'identificazione dei target ad alto valore aggiunto e l'esclusione degli artefatti analitici dai risultati GC-MS.

## 1. Tabella Generale di Classificazione (Macro e Sub-Famiglie)

I composti identificati dal database  con un Match Factor > 60 sono stati aggregati in classi chimiche in base ai loro gruppi funzionali dominanti.

|   |   |   |   |
|---|---|---|---|
|**Macro class**|**Class of compounds**|**Sorting criteria**|**Examples (from detected compounds)**|
|**O-containing compounds**|**Acids**|Linear and cyclic molecules with detected carboxylic group|_Acetic acid; Propanoic acid; n-Hexadecanoic acid_|
||**Alcohols**|Linear and cyclic molecules with detected alcoholic group|_1-Butanol; Behenic alcohol; n-Tetracosanol-1_|
||**Ketones**|Molecules with detected ketonic group|_Cyclopentanone; 4-Propoxy-2-butanone_|
||**Esters**|Molecules with detected ester group|_10-Octadecenoic acid, methyl ester; Ethyl Oleate_|
||**Aldehydes**|Molecules with detected aldehydic group|_17-Octadecenal; E-14-Hexadecenal_|
||**Furan derivatives**|Molecules containing a furan ring|_2-Furanmethanol; 4-Amino-4,5-dihydro-2(3H)-furanone_|
|**N-containing compounds**|**Amides**|Molecules with detected amide group|_Acetamide; Benzamide; Hexanamide_|
||**Amines**|Molecules with detected aminic group|_1,2-Ethanediamine, N-(2-aminoethyl)-_|
||**N-Rings**|Cyclic molecules containing nitrogen (non-aromatic)|_2-Pyrrolidinone; Glutarimide_|
|**Aromatics**|**Aromatics**|Molecules that contain at least one benzene ring|_Benzene, 1,3-bis(1,1-dimethylethyl)-_|
||**O-Aromatics**|Aromatics containing oxygen (e.g., phenols)|_Phenol; p-Cresol; Acetophenone_|
||**N-Aromatics**|Aromatics containing nitrogen|_2(1H)-Pyrazinone; Benzonitrile, 4-methyl-_|
|**Hydrocarbons**|**Alkanes**|Linear and branched saturated hydrocarbons|_Eicosane; Octadecane; Hexadecane_|
||**Alkenes**|Linear and branched unsaturated hydrocarbons|_1-Octadecene; 9-Tricosene; Cetene_|
||**Cycloalkanes**|Cyclic saturated hydrocarbons|_Cyclohexadecane; Cyclopentadecane_|

## 2. Regole di Assegnazione (Sorting Rules)

Per garantire oggettività e scalabilità nell'analisi dei dati, l'assegnazione dei composti alle classi riportate nella Tabella 1 avviene in modo automatico (tramite script Python nel database SQL) ricercando pattern specifici, suffissi o stringhe nel nome IUPAC/comune della molecola. L'ordine di applicazione delle regole è gerarchico (dal più stringente al più generico).

1. **Ricerca Composti Aromatici (Priorità Alta)**
    
    - Se il nome contiene `phenol`, `cresol` o `acetophenone` $\rightarrow$ **O-Aromatics**
        
    - Se il nome contiene `nitrile`, `pyridine` o `benzonitrile` $\rightarrow$ **N-Aromatics**
        
    - Se il nome contiene `benzene` (ma non contiene `acid` o `ester`) $\rightarrow$ **Aromatics**
        
2. **Ricerca Composti Azotati (N-containing)**
    
    - Se il nome contiene la stringa `amide` $\rightarrow$ **Amides**
        
    - Se il nome contiene le stringhe `amine` o `amino` $\rightarrow$ **Amines**
        
    - Se il nome contiene `pyrroli`, `imide`, `indole` o `pyraz` $\rightarrow$ **N-Rings**
        
3. **Ricerca Composti Ossigenati (O-containing)**
    
    - Se il nome contiene `acid` $\rightarrow$ **Acids**
        
    - Se il nome contiene `furan` $\rightarrow$ **Furan derivatives**
        
    - Se il nome contiene `ester`, `oleate`, `propionate` o `carboxylate` $\rightarrow$ **Esters**
        
    - Se il nome contiene `one` (escludendo i lattoni) $\rightarrow$ **Ketones**
        
    - Se il nome finisce in `al` o contiene `aldehyde` o `dial` $\rightarrow$ **Aldehydes**
        
    - Se il nome contiene `ol`, `alcohol`, `diol` o `glycol` $\rightarrow$ **Alcohols**
        
4. **Ricerca Idrocarburi (Hydrocarbons)**
    
    - Se il nome contiene `cyclo` e finisce in `ane` $\rightarrow$ **Cycloalkanes**
        
    - Se il nome finisce in `ane` $\rightarrow$ **Alkanes**
        
    - Se il nome finisce in `ene`, `diene` o contiene `cetene` $\rightarrow$ **Alkenes**
        

## 3. Molecole Valorizzabili (Platform Chemicals Targets)

In ottica di bioraffineria e circolarità, alcuni composti non vengono considerati semplici costituenti dell'olio, ma potenziali "Platform Chemicals". Questi composti (estratti in automatico e dotati di flag `is_valuable` nel database) giustificano possibili step di separazione post-processo.

|   |   |   |
|---|---|---|
|**Target Molecolare**|**Pattern di Riconoscimento**|**Applicazione Industriale / Valore Aggiunto**|
|**Fenoli e Cresoli**|`phenol`, `cresol`|Precursori per resine fenolo-formaldeide, adesivi e solventi. Alto valore di mercato.|
|**Ciclopentanone**|`cyclopentanone`|Solvente "green", intermedio per sintesi di fragranze, polimeri (nylon) e farmaci.|
|**Acido Palmitico**|`hexadecanoic acid`, `palmitic`|Fondamentale nell'industria cosmetica e per la produzione di tensioattivi/saponi.|
|**Precursori Tereftalici**|`terephthalate`, `benzene-1,4-dicarboxylate`|Monomeri di inestimabile valore per la produzione di poliesteri e recupero plastica (PET).|
|**Alcoli Grassi Superiori**|`behenic alcohol`|Agenti emollienti, emulsionanti cosmetici e additivi per lubrificanti speciali.|

## 4. Contaminanti e Artefatti Analitici (Da escludere)

I seguenti gruppi di composti vengono identificati dal sistema ma **esclusi** dal calcolo delle aree percentuali normalizzate (`Area %`), in quanto non rappresentativi dei prodotti di conversione del feedstock, bensì artefatti della procedura analitica GC-MS o additivi spuri.

- **Silossani (Column Bleed):** Composti derivanti dalla degradazione termica della fase stazionaria della colonna cromatografica o da contaminazione da grasso siliconico.
    
    - _Pattern di riconoscimento:_ `siloxane` (es. _Tetracosamethyl-cyclododecasiloxane_, _Heptasiloxane_).
        
- **Derivati TMS e Silani:** Prodotti di reazioni di derivatizzazione o contaminazioni.
    
    - _Pattern di riconoscimento:_ `tms`, `silane` (es. _2,5-Dihydroxybenzoic acid, 3TMS derivative_).
        

_(Tutte le molecole corrispondenti a questi pattern ricevono il flag `is_contaminant = True` nel database e non partecipano al bilancio di massa della miscela)._

## 5. Selezione e Tracciamento dei Marker Specifici e Logiche HTU

Per comprendere le interazioni sinergiche nei mix e le trasformazioni di upgrading, i profili GC-MS dei singoli componenti puri (Bianchi) vengono utilizzati per identificare composti traccianti univoci (**Marker**).

### Caso Studio: Tracciamento del Mater-Bi (MB)

Il Mater-Bi è tipicamente una miscela di **PBAT** (polibutilene adipato tereftalato) e **TPS** (amido termoplastico). Dalla pirolisi del MB puro emergono marker inconfondibili che permettono di tracciarne la presenza nei mix e di valutarne l'evoluzione durante l'Hydrothermal Upgrading (HTU).

1. **Marker della Frazione PBAT (Biopoliestere):** Durante la pirolisi, il PBAT subisce scissione formando esteri monomerici e oligomerici complessi.
    
    - _Target:_ Esteri dell'acido adipico (`3-Butenyl adipate`), dell'acido tereftalico (`Terephthalic acid, di(but-3-enyl) ester`), del sebacato e del succinato.
        
    - _Regola di Riconoscimento:_ Presenza di `adipate`, `terephthalate`, `sebacic` o `succinic` nel nome.
        
2. **Marker della Frazione Amido/Carboidrati (TPS):** La disidratazione e degradazione dei polisaccaridi genera strutture furaniche e ciclopentanoniche.
    
    - _Target:_ `5-Hydroxymethylfurfural` (HMF), `3-Furaldehyde`.
        
    - _Regola di Riconoscimento:_ Presenza di `furan`, `furfural` o `furaldehyde` nel nome.
        

**Regole di Trasformazione (Da Pirolisi a HTL/HTU):** In ottica di upgrading, la presenza di acqua in condizioni subcritiche/supercritiche (HTU) altera radicalmente il destino di questi marker primari:

- **Evoluzione PBAT:** L'acqua ad alta temperatura promuove l'idrolisi degli esteri complessi (es. _Butenyl adipate_). Nel biocrude HTL/HTU ci si attende la scomparsa degli esteri pesanti e la formazione dei monomeri acidi liberi (es. _Adipic acid_, _Terephthalic acid_), i quali possono in parte subire decarbossilazione termica, riducendo l'O/C ratio.
    
- **Evoluzione Amido:** I composti furanici primari (HMF) sono intermedi reattivi. In ambiente idrotermico, essi degradano rapidamente in acidi organici più leggeri e stabili (es. Acido Levulinico, Formico, Acetico) che migrano in fase acquosa, oppure polimerizzano formando _char_ o _humins_. Pertanto, la loro scomparsa nell'olio HTU è un indicatore di reazione avvenuta.
