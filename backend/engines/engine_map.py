import os
import re
from sqlalchemy import create_engine, text

DB_PATH = "nexuslab.db"

def get_experiments_by_block(block_name):
    """
    Estrae i dati dal DB incrociando tabelle di processo, rese e HHV
    in base alla selezione testuale della UI. Tollerante a dati mancanti.
    """
    if not os.path.exists(DB_PATH) or block_name == "Nessuna selezione":
        return []

    engine = create_engine(f"sqlite:///{DB_PATH}")
    results = []

    try:
        with engine.connect() as conn:
            # 1. Recupero globale degli HHV (Tollerante)
            hhv_res = conn.execute(text("SELECT target_id, hhv_stimato FROM dati_chnso")).fetchall()
            hhv_map = {row[0]: row[1] for row in hhv_res}

            # ==========================================
            # 2. LOGICA PER PROVE DI PIROLISI
            # ==========================================
            if "Pirolisi" in block_name:
                # Recupero base prove
                query_piro = text("SELECT id_prova, temperatura, catalizzatore FROM prove_pirolisi")
                piro_trials = conn.execute(query_piro).fetchall()

                # Recupero rese medie (runs_pirolisi)
                query_rese = text("SELECT id_prova, AVG(resa_olio) FROM runs_pirolisi GROUP BY id_prova")
                rese_piro = conn.execute(query_rese).fetchall()
                resa_map = {row[0]: row[1] for row in rese_piro}

                # Recupero ricette feedstocks
                recipes = conn.execute(text("SELECT id_prova, feedstock_id, percentuale FROM pirolisi_ricetta")).fetchall()
                rec_map = {}
                for r in recipes:
                    pid = r[0]
                    # Rimuove FS_ per pulizia visiva, mantiene il resto
                    feed = str(r[1]).replace("FS_", "") 
                    perc = r[2]
                    if pid not in rec_map: 
                        rec_map[pid] = []
                    # Arrotonda la % all'intero
                    perc_int = int(perc) if perc else 0
                    rec_map[pid].append(f"{feed}{perc_int}")

                # Filtraggio in Python
                for t in piro_trials:
                    id_prova = str(t[0])
                    
                    match = re.search(r'\d+', id_prova)
                    num = int(match.group()) if match else 0
                    
                    # Filtri di raggruppamento
                    if "DoE" in block_name and not (1 <= num <= 9): continue
                    if "Ottimizzate" in block_name and not (10 <= num <= 12): continue
                    if "Extra" in block_name and not (13 <= num <= 20): continue
                    
                    temp = t[1] if t[1] is not None else "-"
                    cat = t[2] if t[2] else "Nessuno"
                    resa = resa_map.get(id_prova, None)
                    
                    # Assemblaggio Stringhe
                    recipe_str = " + ".join(rec_map.get(id_prova, ["Sconosciuto"]))
                    hhv = hhv_map.get(f"{id_prova}_OIL")
                    
                    resa_str = f"{resa:.1f}%" if pd_is_valid(resa) else "N/D"
                    hhv_str = f"{hhv:.1f} MJ/kg" if pd_is_valid(hhv) else "N/D"
                    
                    label = f"🧪 **{id_prova}** (Feed: {recipe_str} | Temp: {temp}°C | Tempo: 30m | Cat: {cat} | Resa Olio: {resa_str} | HHV: {hhv_str})"
                    results.append({'id': id_prova, 'label': label, 'num_sort': num})

            # ==========================================
            # 3. LOGICA PER PROVE IDROTERMICHE (HTL / HTU)
            # ==========================================
            elif "HTL" in block_name or "HTU" in block_name:
                is_htl = "HTL" in block_name
                tipo_proc = "HTL" if is_htl else "HTU"
                
                query_ht = text(f"""
                    SELECT p.id_prova, p.temperatura, p.tempo, p.catalizzatore, p.resa_biocrude, 
                           GROUP_CONCAT(i.source_id, ' + ') as source
                    FROM prove_idrotermiche p
                    LEFT JOIN input_idrotermico i ON p.id_prova = i.id_prova
                    WHERE p.tipo_processo = '{tipo_proc}'
                    GROUP BY p.id_prova
                """)
                ht_trials = conn.execute(query_ht).fetchall()

                for t in ht_trials:
                    id_prova = str(t[0])
                    
                    match = re.search(r'\d+', id_prova)
                    num = int(match.group()) if match else 0
                    
                    # Filtri di raggruppamento
                    if not is_htl:
                        if "7 & 8" in block_name and num not in [7, 8]: continue
                        if "9 & 10" in block_name and num not in [9, 10]: continue
                        if "11 & 12 & 13" in block_name and num not in [11, 12, 13]: continue
                    else:
                        if "1 - 6 & 14" in block_name and num not in [1, 2, 3, 4, 5, 6, 14]: continue

                    temp = t[1] if t[1] is not None else "-"
                    tempo = t[2] if t[2] is not None else "-"
                    cat = t[3] if t[3] else "Nessuno"
                    resa = t[4]
                    
                    feed = str(t[5]).replace("FS_", "") if t[5] else "Sconosciuto"
                    hhv = hhv_map.get(f"{id_prova}_BC")
                    
                    resa_str = f"{resa:.1f}%" if pd_is_valid(resa) else "N/D"
                    hhv_str = f"{hhv:.1f} MJ/kg" if pd_is_valid(hhv) else "N/D"
                    
                    icon = "💧" if is_htl else "⚡"
                    label = f"{icon} **{id_prova}** (Feed: {feed} | Temp: {temp}°C | Tempo: {tempo}m | Cat: {cat} | Resa BC: {resa_str} | HHV: {hhv_str})"
                    results.append({'id': id_prova, 'label': label, 'num_sort': num})

            # ==========================================
            # 4. LOGICA PER ALTRE PROVE (Non classificate)
            # ==========================================
            elif "Altre Prove" in block_name:
                
                # ---> Controllo Pirolisi <---
                query_piro = text("SELECT id_prova, temperatura, catalizzatore FROM prove_pirolisi")
                piro_trials = conn.execute(query_piro).fetchall()
                
                query_rese = text("SELECT id_prova, AVG(resa_olio) FROM runs_pirolisi GROUP BY id_prova")
                resa_map = {row[0]: row[1] for row in conn.execute(query_rese).fetchall()}

                recipes = conn.execute(text("SELECT id_prova, feedstock_id, percentuale FROM pirolisi_ricetta")).fetchall()
                rec_map = {}
                for r in recipes:
                    pid = r[0]
                    feed = str(r[1]).replace("FS_", "") 
                    perc = r[2]
                    if pid not in rec_map: rec_map[pid] = []
                    perc_int = int(perc) if perc else 0
                    rec_map[pid].append(f"{feed}{perc_int}")

                for t in piro_trials:
                    id_prova = str(t[0])
                    match = re.search(r'\d+', id_prova)
                    num = int(match.group()) if match else 0
                    
                    # Se non è nelle prime 20, finisce in "Altre"
                    if num > 20 or num == 0:
                        temp = t[1] if t[1] is not None else "-"
                        resa = resa_map.get(id_prova, None)
                        recipe_str = " + ".join(rec_map.get(id_prova, ["Sconosciuto"]))
                        
                        resa_str = f"{resa:.1f}%" if pd_is_valid(resa) else "N/D"
                        label = f"🧪 **{id_prova}** (Altra Pirolisi | Feed: {recipe_str} | Temp: {temp}°C | Resa: {resa_str})"
                        results.append({'id': id_prova, 'label': label, 'num_sort': 900 + num})
                
                # ---> Controllo Idrotermali <---
                query_ht = text("""
                    SELECT p.id_prova, p.tipo_processo, p.temperatura, p.tempo, p.resa_biocrude, 
                           GROUP_CONCAT(i.source_id, ' + ') as source
                    FROM prove_idrotermiche p
                    LEFT JOIN input_idrotermico i ON p.id_prova = i.id_prova
                    GROUP BY p.id_prova
                """)
                ht_trials = conn.execute(query_ht).fetchall()
                
                for t in ht_trials:
                    id_prova = str(t[0])
                    tipo = str(t[1]).upper() if t[1] else "IDROTERMALE"
                    
                    match = re.search(r'\d+', id_prova)
                    num = int(match.group()) if match else 0
                    
                    is_classified = False
                    if 'HTL' in tipo and num in [1, 2, 3, 4, 5, 6, 14]: is_classified = True
                    if 'HTU' in tipo and num in [7, 8, 9, 10, 11, 12, 13]: is_classified = True
                    
                    if not is_classified:
                        temp = t[2] if t[2] is not None else "-"
                        tempo = t[3] if t[3] is not None else "-"
                        resa = t[4]
                        feed = str(t[5]).replace("FS_", "") if t[5] else "Sconosciuto"
                        
                        resa_str = f"{resa:.1f}%" if pd_is_valid(resa) else "N/D"
                        icon = "💧" if 'HTL' in tipo else "⚡"
                        label = f"{icon} **{id_prova}** (Altra {tipo} | Feed: {feed} | Temp: {temp}°C | Resa: {resa_str})"
                        results.append({'id': id_prova, 'label': label, 'num_sort': 900 + num})

            # ==========================================
            # ORDINAMENTO FINALE E PULIZIA
            # ==========================================
            results.sort(key=lambda x: x['num_sort'])
            
            for r in results:
                r.pop('num_sort', None)

    except Exception as e:
        print(f"Errore critico engine_map: {e}")
        
    return results

def pd_is_valid(val):
    """Utility per verificare che un valore non sia None e sia un numero valido."""
    if val is None:
        return False
    try:
        float(val)
        return True
    except ValueError:
        return False
