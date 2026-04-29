# Manifesto di Classificazione Molecolare (Dati GC-MS)

**Progetto:** Upgrading Idrotermico e Pirolisi di Mix Complessi (PE, Mater-Bi, Sewage Sludge, Compost)

**Scopo del Documento:** Definire in modo rigoroso e riproducibile i criteri adottati per la classificazione, l'identificazione dei target ad alto valore aggiunto e l'esclusione degli artefatti analitici dai risultati GC-MS.

## 1. Tabella Generale di Classificazione (Macro e Sub-Famiglie)

I composti identificati dal database NIST/Wiley con un Match Factor > 60 sono stati aggregati in classi chimiche in base ai loro gruppi funzionali dominanti. L'organizzazione prevede una netta distinzione tra i composti eteroatomici (O, N) e gli idrocarburi puri. I fenoli ad alto valore sono stati integrati all'interno della macroclasse dei composti ossigenati.

|   |   |   |   |
|---|---|---|---|
|**Macro class**|**Class of compounds**|**Sorting criteria**|**Examples (from detected compounds)**|
|**O-containing compounds**|**Phenols & O-Aromatics**|Aromatics containing oxygen (phenols, cresols, substituted phenols)|_Phenol; p-Cresol; Acetophenone_|
||**Acids**|Linear and cyclic molecules with detected carboxylic group|_Acetic acid; Propanoic acid; n-Hexadecanoic acid_|
||**Alcohols**|Linear and cyclic molecules with detected alcoholic group|_1-Butanol; Behenic alcohol; n-Tetracosanol-1_|
||**Carbonyls (Aldehydes & Ketones)**|Molecules with detected ketonic or aldehydic group|_Cyclopentanone; 17-Octadecenal; Phorone_|
||**Esters**|Molecules with detected ester group|_10-Octadecenoic acid, methyl ester; Butenyl adipate_|
||**Ethers**|Molecules with detected ether linkage (excluding PEGs)|_Ether, tert-butyl isopropylidenecyclopropyl_|
||**Furan derivatives**|Molecules containing a furan ring|_2-Furanmethanol; 4-Amino-4,5-dihydro-2(3H)-furanone_|
|**N-containing compounds**|**Amides**|Molecules with detected amide group|_Acetamide; Benzamide; Hexanamide_|
||**Amines**|Molecules with detected aminic group|_1,2-Ethanediamine, N-(2-aminoethyl)-_|
||**Nitriles**|Molecules containing a cyano group|_Heptadecanenitrile_|
||**N-Heterocycles (Rings & Aromatics)**|Cyclic molecules containing nitrogen (aromatic and non-aromatic)|_2-Pyrrolidinone; Imidazole; 2(1H)-Pyrazinone; Benzonitrile_|
|**Hydrocarbons**|**Aliphatic hydrocarbons**|Linear, branched, and cyclic saturated/unsaturated hydrocarbons|_Eicosane; 1-Octadecene; Cyclohexadecane; Docosane, 7-hexyl-_|
||**Aromatic hydrocarbons**|Molecules that contain at least one benzene ring (pure hydrocarbons)|_Benzene, 1,3-bis(1,1-dimethylethyl)-; Styrene; Ethylbenzene_|

## 2. Regole di Assegnazione Gerarchica (Sorting Rules)

Per garantire oggettività e scalabilità, l'assegnazione dei composti alle classi avviene in automatico ricercando pattern specifici nel nome IUPAC. L'ordine descritto di seguito ricalca la struttura della tabella. _(Nota tecnica: a livello di esecuzione del codice Python, i composti azotati e i fenoli vengono scansionati con priorità rispetto ai restanti composti ossigenati. Questo evita false classificazioni per molecole miste, garantendo ad esempio che il `2-Pyrrolidinone` venga etichettato come eterociclo azotato e non come un semplice chetone)._

1. **Esclusione Contaminanti (Priorità Assoluta)**
    
    - Se il nome contiene `siloxane`, `silane` o `tms` $\rightarrow$ **Contaminants / Siloxanes**
        
    - Se il nome si riferisce a eteri di glicole complessi (es. `glycol ... ether`) o eteri corona (`crown`) $\rightarrow$ **Contaminants / PEG & Surfactants**
        
2. **Ricerca Composti Ossigenati (O-containing)**
    
    - Se contiene `phenol`, `cresol` o `acetophenone` $\rightarrow$ **O-containing compounds / Phenols & O-Aromatics**
        
    - Se contiene `acid` $\rightarrow$ **O-containing compounds / Acids**
        
    - Se contiene `furan` o `furfural` $\rightarrow$ **O-containing compounds / Furan derivatives**
        
    - Se contiene suffissi/termini di esterificazione (`ester`, `oleate`, `propionate`, `carboxylate`, `adipate`, `sebacate`, ecc.) $\rightarrow$ **O-containing compounds / Esters**
        
    - Se contiene `one`, `phorone`, finisce in `al`, o contiene `aldehyde` o `dial` $\rightarrow$ **O-containing compounds / Carbonyls (Aldehydes & Ketones)**
        
    - Se contiene `ol`, `alcohol`, `diol` o `glycol` $\rightarrow$ **O-containing compounds / Alcohols**
        
    - Se contiene suffissi eterei (`ether`, `epoxy`, `methoxy`, `ethoxy`, `propoxy`) $\rightarrow$ **O-containing compounds / Ethers**
        
3. **Ricerca Composti Azotati (N-containing)**
    
    - Se contiene `amide` $\rightarrow$ **N-containing compounds / Amides**
        
    - Se contiene `amine` o `amino` $\rightarrow$ **N-containing compounds / Amines**
        
    - Se contiene `nitrile` $\rightarrow$ **N-containing compounds / Nitriles**
        
    - Se contiene eterocicli azotati o N-aromatici (`pyrroli`, `imide`, `indole`, `pyraz`, `oxadiazole`, `pyrimidin`, `pyridine`, `benzonitrile`) $\rightarrow$ **N-containing compounds / N-Heterocycles (Rings & Aromatics)**
        
4. **Ricerca Idrocarburi Puri (Hydrocarbons)**
    
    - Se contiene `benzene`, `styrene` o `ethylbenzene` (e non è stato intercettato prima da ossigenati/azotati) $\rightarrow$ **Hydrocarbons / Aromatic hydrocarbons**
        
    - Se contiene radici sature/insature generiche o cicliche (`ane`, `ene`, `diene`, `cyclo`, `cetene`, `squalene`) $\rightarrow$ **Hydrocarbons / Aliphatic hydrocarbons**
        

## 3. Molecole Valorizzabili (Platform Chemicals Targets)

Alcuni composti sono estratti in automatico e dotati di flag `is_valuable` nel database, giustificando possibili step di separazione per il recupero materia.

|   |   |   |
|---|---|---|
|**Target Molecolare**|**Pattern di Riconoscimento**|**Applicazione Industriale / Valore Aggiunto**|
|**Fenoli e Cresoli**|`phenol`, `cresol`|Precursori per resine fenolo-formaldeide, adesivi e solventi. Alto valore di mercato.|
|**Ciclopentanone**|`cyclopentanone`|Solvente "green", intermedio per sintesi di fragranze, polimeri (nylon) e farmaci.|
|**Acido Palmitico**|`hexadecanoic acid`, `palmitic`|Fondamentale nell'industria cosmetica e per la produzione di tensioattivi/saponi.|
|**Precursori Tereftalici**|`terephthalate`, `benzene-1,4-dicarboxylate`|Monomeri di inestimabile valore per la produzione di poliesteri e recupero plastica (PET).|
|**Alcoli Grassi Superiori**|`behenic alcohol`|Agenti emollienti, emulsionanti cosmetici e additivi per lubrificanti speciali.|

## 4. Contaminanti e Artefatti Analitici (Da escludere)

I seguenti composti ricevono il flag `is_contaminant = True` e non partecipano al bilancio di massa della miscela (normalizzazione dell'Area %).

- **Silossani e Derivati TMS (Column Bleed / Derivatizzazione):** Composti derivanti dalla degradazione termica della fase stazionaria (es. _Tetracosamethyl-cyclododecasiloxane_, _Heptasiloxane_) o silani anomali.
    
- **PEG e Tensioattivi (Surfactants):** Composti polietossilati o eteri corona (es. _Octaethylene glycol monododecyl ether_, _21-Crown-7_) riconducibili a contaminazione da detergenti di laboratorio o agenti bagnanti.
    

## 5. Selezione e Tracciamento dei Marker Specifici (Feedstock Tracking)

I profili GC-MS dei componenti puri (Bianchi) sono utilizzati per identificare composti traccianti univoci (**Marker**) nei mix finali.

### A. Marker Mater-Bi (Frazione PBAT + Frazione Amido)

Il Mater-Bi puro degrada nei frammenti primari dei suoi polimeri costituenti.

- _Target PBAT (Poliestere):_ Esteri dell'acido adipico (`3-Butenyl adipate`), tereftalico (`Terephthalic acid, di(but-3-enyl) ester`), sebacico o succinico.
    
- _Target TPS (Amido):_ Derivati di disidratazione degli zuccheri (`5-Hydroxymethylfurfural`, `3-Furaldehyde`).
    
- **Trasformazione (HTU):** Scomparsa degli esteri pesanti verso monomeri acidi liberi (decarbossilazione) e degradazione in fase acquosa o polimerizzazione dei furanici.
    

### B. Marker Polietilene (PE)

La degradazione termica radicalica del PE produce una inconfondibile serie omologa.

- _Target Alifatici Pesanti:_ Serie continua di alcani e alcheni lineari pesanti (C20-C29), es. Eicosano, Docosano, Pentacosano, 1-Eicosene.
    
- **Trasformazione (HTU):** Estrema inerzia chimica. I frammenti del PE agiscono da carrier nel biocrude, aumentandone l'HHV e riducendo l'O/C ratio per "diluizione".
    

### C. Marker Sewage Sludge (SS)

Derivando da biomassa microbica cellulare, il fango genera composti unici da proteine e lipidi.

- _Target Azotati (Proteine):_ Composti eterociclici azotati e N-aromatici (`Indole`, `Pyrrole`, `Tryptamine`) e nitrili lunghi (`Heptadecanenitrile`).
    
- **Trasformazione (HTU):** La diminuzione percentuale degli eterocicli azotati nel biocrude (migrazione come NH3 in acqua o gas) indica l'efficacia della denitrificazione termochimica/catalitica.
