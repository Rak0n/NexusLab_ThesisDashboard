import pandas as pd
from sqlalchemy import create_engine, text
import os
import re

DB_PATH = "nexuslab.db"

META_COLUMNS = ['ID Prova', 'Processo', 'Feedstock', 'Temp (°C)', 'Tempo (m)', 'Catalizzatore']

def fetch_multi_yields(trial_ids):
    """Estrae i dati di resa massica filtrandoli in Python per la massima robustezza."""
    if not os.path.exists(DB_PATH) or not trial_ids:
        return pd.DataFrame(), pd.DataFrame()

    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        
        # Estrazione completa e filtro in Pandas (Infallibile)
        df_piro_all = pd.read_sql("SELECT id_prova, id_run, resa_olio as Olio, resa_char as Char, resa_gas as Gas FROM runs_pirolisi", engine)
        df_piro = df_piro_all[df_piro_all['id_prova'].astype(str).isin(trial_ids)].copy()
        
        df_ht_all = pd.read_sql("SELECT id_prova, id_prova as id_run, resa_biocrude as Biocrude, resa_wso as Aqueous_Phase, resa_char as Char, resa_gas as Gas FROM prove_idrotermiche", engine)
        df_ht = df_ht_all[df_ht_all['id_prova'].astype(str).isin(trial_ids)].copy()
        
        return df_piro, df_ht
    except Exception as e:
        print(f"Errore estrazione rese multiple: {e}")
        return pd.DataFrame(), pd.DataFrame()

def get_feedstock_targets(trial_ids):
    """Rintraccia gli ID dei feedstock base filtrando lato Python."""
    if not os.path.exists(DB_PATH) or not trial_ids:
        return []
        
    feeds = []
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")

        with engine.connect() as conn:
            # Pirolisi
            query_piro = text("SELECT id_prova, feedstock_id FROM pirolisi_ricetta")
            res_piro = conn.execute(query_piro).fetchall()
            for r in res_piro:
                if str(r[0]) in trial_ids and r[1]:
                    feeds.append(str(r[1]).strip())

            # Idrotermali
            query_ht = text("SELECT id_prova, source_id FROM input_idrotermico")
            res_ht = conn.execute(query_ht).fetchall()
            for r in res_ht:
                if str(r[0]) in trial_ids and r[1]:
                    parts = [p.strip() for p in re.split(r"\s*\+\s*", str(r[1])) if p and str(p).strip()]
                    for p in parts:
                        if str(p).upper().startswith('FS_'):
                            feeds.append(str(p).upper())

        # Dedup preservando l'ordine
        return list(dict.fromkeys(feeds))
    except Exception as e:
        print(f"Errore ricerca feedstock: {e}")
        return []

def get_metadata_for_trials(trial_ids):
    """Estrae le informazioni riepilogative con conversione sicura a stringa per evitare crash di tipo in Streamlit."""
    if not os.path.exists(DB_PATH) or not trial_ids:
        return pd.DataFrame(columns=META_COLUMNS)

    results = []
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")

        with engine.connect() as conn:
            # 1. Recupero Pirolisi
            query_piro = text("SELECT id_prova, temperatura, catalizzatore FROM prove_pirolisi")
            piro_trials = conn.execute(query_piro).fetchall()

            # Mappatura ricette Pirolisi
            recipes = conn.execute(text("SELECT id_prova, feedstock_id, percentuale FROM pirolisi_ricetta")).fetchall()
            rec_map = {}
            for r in recipes:
                pid = str(r[0])
                feed = str(r[1]).replace("FS_", "") if r[1] else "Mix"
                perc = r[2]
                if pid not in rec_map: rec_map[pid] = []
                rec_map[pid].append(f"{feed}({int(perc)}%)" if perc else feed)

            # Assemblaggio risultati Pirolisi
            for t in piro_trials:
                id_prova = str(t[0])
                if id_prova in trial_ids:
                    # Casting esplicito a stringa per TUTTI i valori
                    temp = str(t[1]) if t[1] is not None else "-"
                    cat = str(t[2]) if t[2] else "Nessuno"
                    feed_str = " + ".join(rec_map.get(id_prova, ["Mix"]))
                    
                    results.append({
                        'ID Prova': id_prova, 
                        'Processo': 'Pirolisi', 
                        'Feedstock': feed_str,
                        'Temp (°C)': temp, 
                        'Tempo (m)': "30",  # Passato come stringa anziché numero intero
                        'Catalizzatore': cat
                    })

            # 2. Recupero Idrotermali
            query_ht = text("""
                SELECT p.id_prova, p.tipo_processo, p.temperatura, p.tempo, p.catalizzatore,
                       GROUP_CONCAT(i.source_id, ' + ') as feed
                FROM prove_idrotermiche p
                LEFT JOIN input_idrotermico i ON p.id_prova = i.id_prova
                GROUP BY p.id_prova
            """)
            ht_trials = conn.execute(query_ht).fetchall()

            for t in ht_trials:
                id_prova = str(t[0])
                if id_prova in trial_ids:
                    # Casting esplicito a stringa
                    proc = str(t[1]).replace('Idrotermico', 'Idrotermale') if t[1] else "Idrotermale"
                    temp = str(t[2]) if t[2] is not None else "-"
                    tempo = str(t[3]) if t[3] is not None else "-"
                    cat = str(t[4]) if t[4] else "Nessuno"
                    feed_str = str(t[5]).replace('FS_', '') if t[5] else 'Sconosciuto'
                    
                    results.append({
                        'ID Prova': id_prova, 
                        'Processo': proc, 
                        'Feedstock': feed_str,
                        'Temp (°C)': temp, 
                        'Tempo (m)': tempo, 
                        'Catalizzatore': cat
                    })

        if not results:
            return pd.DataFrame(columns=META_COLUMNS)

        df = pd.DataFrame(results)
        # Ordinamento alfanumerico
        df['sort_key'] = df['ID Prova'].apply(lambda x: int(re.findall(r'\d+', str(x))[0]) if re.findall(r'\d+', str(x)) else 0)
        df = df.sort_values('sort_key').drop(columns=['sort_key']).reset_index(drop=True)
            
        return df

    except Exception as e:
        print(f"Errore metadata trials: {e}")
        return pd.DataFrame(columns=META_COLUMNS)
