import pandas as pd
from sqlalchemy import create_engine, text
import os

DB_PATH = "nexuslab.db"

# ==========================================
# 1. FUNZIONI DI INGESTIONE
# ==========================================
def validate_target_id(target_id):
    if not target_id: return False, "Target ID vuoto."
    if not os.path.exists(DB_PATH): return False, "Database non trovato."
    target_id = target_id.strip().upper()
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        with engine.connect() as conn:
            if target_id.startswith('FS_'):
                res = conn.execute(text("SELECT id FROM feedstocks WHERE id = :id"), {"id": target_id}).scalar()
                if res: return True, "Valido"
                return False, f"Il Feedstock '{target_id}' non è in anagrafica."
                
            elif target_id.endswith('_OIL') or (target_id.endswith('_CHAR') and not target_id.startswith('HT')):
                base_id = target_id.rsplit('_', 1)[0]
                res = conn.execute(text("SELECT id_prova FROM prove_pirolisi WHERE id_prova = :id"), {"id": base_id}).scalar()
                if res: return True, "Valido"
                return False, f"La prova Pirolisi '{base_id}' non esiste."
                
            elif target_id.endswith('_BC') or target_id.endswith('_AP') or (target_id.endswith('_CHAR') and target_id.startswith('HT')):
                base_id = target_id.rsplit('_', 1)[0]
                res = conn.execute(text("SELECT id_prova FROM prove_idrotermiche WHERE id_prova = :id"), {"id": base_id}).scalar()
                if res: return True, "Valido"
                return False, f"La prova Idrotermica '{base_id}' non esiste."
            else:
                return False, "Usa i prefissi/suffissi validi (FS_..., _OIL, _BC, _CHAR, _AP)."
    except Exception as e:
        return False, f"Errore SQL: {str(e)}"

def check_existing_target(target_id):
    if not os.path.exists(DB_PATH) or not target_id: return False
    target_id = target_id.strip().upper()
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        with engine.connect() as conn:
            res = conn.execute(text("SELECT COUNT(*) FROM dati_chnso WHERE target_id = :tid"), {"tid": target_id}).scalar()
            return res > 0
    except Exception: return False

def parse_chnso_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        if '1 - Raw Data' in xls.sheet_names:
            df_raw = pd.read_excel(xls, sheet_name='1 - Raw Data')
        else:
            df_raw = pd.read_excel(xls, sheet_name=0)
            
        if 'Name' not in df_raw.columns or 'C' not in df_raw.columns:
            return {"error": "Il file non contiene le colonne grezze necessarie (Name, C, H, N)."}

        numeric_cols = ['N', 'C', 'H', 'S']
        available_num = [c for c in numeric_cols if c in df_raw.columns]
        
        df_mean = df_raw.groupby('Name')[available_num].mean(numeric_only=True).reset_index()
        df_std = df_raw.groupby('Name')[available_num].std(numeric_only=True).reset_index().fillna(0.0)

        df_agg = pd.merge(df_mean, df_std, on='Name', suffixes=('_mean', '_std'))

        for col in numeric_cols:
            if f"{col}_mean" not in df_agg.columns: df_agg[f"{col}_mean"] = 0.0
            if f"{col}_std" not in df_agg.columns: df_agg[f"{col}_std"] = 0.0

        return {"success": True, "data": df_agg}
    except Exception as e:
        return {"error": str(e)}

def inject_chnso_to_db(target_id, row_data, moisture=0.0, ash=0.0, ignore_s=False, overwrite=False):
    if not os.path.exists(DB_PATH): return False, "Database non trovato."
    target_id = target_id.strip().upper()
    try:
        s_mean = 0.0 if ignore_s else float(row_data.get('S_mean', 0.0))
        s_std = 0.0 if ignore_s else float(row_data.get('S_std', 0.0))
        c_mean = float(row_data.get('C_mean', 0.0))
        h_mean = float(row_data.get('H_mean', 0.0))
        n_mean = float(row_data.get('N_mean', 0.0))

        o_diff = max(0.0, 100.0 - c_mean - h_mean - n_mean - s_mean - moisture - ash)
        hhv_stimato = max(0.0, 0.3491 * c_mean + 1.1783 * h_mean + 0.1005 * s_mean - 0.1034 * o_diff - 0.0151 * n_mean)

        engine = create_engine(f"sqlite:///{DB_PATH}")
        with engine.connect() as conn:
            if overwrite:
                conn.execute(text("DELETE FROM dati_chnso WHERE target_id = :tid"), {"tid": target_id})
                conn.commit()
            
            df_db = pd.DataFrame([{
                'target_id': target_id, 'c_mean': c_mean, 'c_std': float(row_data.get('C_std', 0.0)),
                'h_mean': h_mean, 'h_std': float(row_data.get('H_std', 0.0)),
                'n_mean': n_mean, 'n_std': float(row_data.get('N_std', 0.0)),
                's_mean': s_mean, 's_std': s_std, 'moisture': moisture, 'ash': ash,
                'o_diff': o_diff, 'hhv_stimato': hhv_stimato
            }])
            
            df_db.to_sql('dati_chnso', con=conn, if_exists='append', index=False)
            
            if conn.execute(text("SELECT COUNT(*) FROM registro_analisi WHERE target_id = :tid AND tipo_analisi = 'CHNSO'"), {"tid": target_id}).scalar() == 0:
                conn.execute(text("INSERT INTO registro_analisi (target_id, tipo_analisi) VALUES (:tid, 'CHNSO')"), {"tid": target_id})
            conn.commit()
            
        return True, f"✅ Dati salvati per: {target_id}"
    except Exception as e:
        return False, f"Errore DB: {str(e)}"

# ==========================================
# 2. FUNZIONI ANALITICHE E METADATI
# ==========================================
def get_targets_metadata():
    if not os.path.exists(DB_PATH): return pd.DataFrame()
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        targets_meta = []
        with engine.connect() as conn:
            res = conn.execute(text("SELECT DISTINCT target_id FROM dati_chnso")).fetchall()
            for r in res:
                tid = r[0]
                proc, feed, temp, tempo, cat, resa = 'Sconosciuto', 'Sconosciuto', 0.0, 0.0, '-', None
                
                if tid.startswith('FS_'):
                    proc = 'Feedstock'
                    feed = tid.replace('FS_', '')
                elif tid.endswith('_OIL') or (tid.endswith('_CHAR') and not tid.startswith('HT')):
                    base_id = tid.rsplit('_', 1)[0]
                    row = conn.execute(text("SELECT temperatura, catalizzatore FROM prove_pirolisi WHERE id_prova=:id"), {"id":base_id}).first()
                    if row:
                        proc = 'Pirolisi'
                        temp = row[0]
                        tempo = 30
                        cat = row[1] if row[1] else '-'
                        feeds = conn.execute(text("SELECT feedstock_id FROM pirolisi_ricetta WHERE id_prova=:id"), {"id":base_id}).fetchall()
                        feed = " + ".join([f[0].replace('FS_', '') for f in feeds]) if feeds else 'Sconosciuto'
                        resa_val = conn.execute(text("SELECT AVG(resa_olio) FROM runs_pirolisi WHERE id_prova=:id"), {"id":base_id}).scalar()
                        resa = round(resa_val, 2) if resa_val else None
                elif tid.endswith('_BC') or tid.endswith('_AP') or (tid.endswith('_CHAR') and tid.startswith('HT')):
                    base_id = tid.rsplit('_', 1)[0]
                    row = conn.execute(text("SELECT tipo_processo, temperatura, tempo, catalizzatore, resa_biocrude FROM prove_idrotermiche WHERE id_prova=:id"), {"id":base_id}).first()
                    if row:
                        suff = "Biocrude" if tid.endswith('_BC') else "Fase Acquosa" if tid.endswith('_AP') else "Char"
                        proc = f"{row[0]} {suff}"
                        temp = row[1]
                        tempo = row[2]
                        cat = row[3] if row[3] else '-'
                        resa = round(row[4], 2) if row[4] else None
                        feeds = conn.execute(text("SELECT source_id FROM input_idrotermico WHERE id_prova=:id"), {"id":base_id}).fetchall()
                        feed = " + ".join([f[0].replace('_OIL', '').replace('_BC', '') for f in feeds]) if feeds else 'Sconosciuto'
                
                targets_meta.append({
                    'target_id': tid, 'Processo': proc, 'Feedstock': feed, 
                    'Temperatura': temp, 'Tempo': tempo, 'Catalizzatore': cat, 'Resa Olio/Biocrude (%)': resa
                })
        return pd.DataFrame(targets_meta)
    except Exception as e:
        return pd.DataFrame()

def get_lineage_sets():
    if not os.path.exists(DB_PATH): return {}
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        sets = {}
        with engine.connect() as conn:
            res_piro = conn.execute(text("""
                SELECT p.id_prova, GROUP_CONCAT(r.feedstock_id, ' + ')
                FROM prove_pirolisi p LEFT JOIN pirolisi_ricetta r ON p.id_prova = r.id_prova GROUP BY p.id_prova
            """)).fetchall()
            for r in res_piro:
                id_p = r[0]
                feed_list = [f.strip() for f in str(r[1]).split(' + ')] if r[1] else []
                feed_str = str(r[1]).replace('FS_', '') if r[1] else 'Mix'
                sets[f"{feed_str} ➔ {id_p}"] = feed_list + [f"{id_p}_OIL", f"{id_p}_CHAR"]
                
            res_ht = conn.execute(text("""
                SELECT p.id_prova, p.tipo_processo, GROUP_CONCAT(i.source_id, ' + ')
                FROM prove_idrotermiche p LEFT JOIN input_idrotermico i ON p.id_prova = i.id_prova GROUP BY p.id_prova
            """)).fetchall()
            for r in res_ht:
                id_ht = r[0]
                tipo = r[1]
                source = str(r[2])
                
                if tipo == 'HTU':
                    base_p = source.replace('_OIL', '')
                    feed_res = conn.execute(text("SELECT GROUP_CONCAT(feedstock_id, ' + ') FROM pirolisi_ricetta WHERE id_prova=:id"), {"id":base_p}).scalar()
                    feed_list = [f.strip() for f in str(feed_res).split(' + ')] if feed_res else []
                    feed_str = str(feed_res).replace('FS_', '') if feed_res else 'Sconosciuto'
                    sets[f"{feed_str} ➔ {source} ➔ {id_ht}"] = feed_list + [source, f"{id_ht}_BC", f"{id_ht}_AP", f"{id_ht}_CHAR"]
                elif tipo == 'HTL':
                    feed_list = [f.strip() for f in source.split(' + ')] if source else []
                    sets[f"{source.replace('FS_', '')} ➔ {id_ht}"] = feed_list + [f"{id_ht}_BC", f"{id_ht}_AP", f"{id_ht}_CHAR"]
        return sets
    except Exception as e:
        return {}

def get_lineage_edges():
    """Restituisce la lista di tupe (Padre, Figlio) esatte per connettere i punti in parallelo o serie."""
    edges = []
    if not os.path.exists(DB_PATH): return edges
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        with engine.connect() as conn:
            res_piro = conn.execute(text("SELECT p.id_prova, r.feedstock_id FROM prove_pirolisi p JOIN pirolisi_ricetta r ON p.id_prova = r.id_prova")).fetchall()
            for r in res_piro:
                edges.append((r[1], f"{r[0]}_OIL"))
                edges.append((r[1], f"{r[0]}_CHAR"))

            res_htu = conn.execute(text("SELECT p.id_prova, i.source_id FROM prove_idrotermiche p JOIN input_idrotermico i ON p.id_prova = i.id_prova WHERE p.tipo_processo='HTU'")).fetchall()
            for r in res_htu:
                edges.append((r[1], f"{r[0]}_BC"))
                edges.append((r[1], f"{r[0]}_CHAR"))

            res_htl = conn.execute(text("SELECT p.id_prova, i.source_id FROM prove_idrotermiche p JOIN input_idrotermico i ON p.id_prova = i.id_prova WHERE p.tipo_processo='HTL'")).fetchall()
            for r in res_htl:
                sources = r[1].split(' + ') if r[1] else []
                for s in sources:
                    edges.append((s.strip(), f"{r[0]}_BC"))
                    edges.append((s.strip(), f"{r[0]}_CHAR"))
    except Exception: pass
    return edges

def fetch_chnso_data(target_ids):
    if not os.path.exists(DB_PATH) or not target_ids: return pd.DataFrame()
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        placeholders = ','.join(['?'] * len(target_ids))
        query = f"SELECT * FROM dati_chnso WHERE target_id IN ({placeholders})"
        df = pd.read_sql(query, engine, params=tuple(target_ids))
        
        if not df.empty:
            # Calcolo corretto rapporti MOLARI e non massici!
            c_moles = df['c_mean'] / 12.011
            df['H/C'] = (df['h_mean'] / 1.008) / c_moles
            df['O/C'] = (df['o_diff'] / 15.999) / c_moles
            df['N/C'] = (df['n_mean'] / 14.007) / c_moles
            df = df.replace([float('inf'), -float('inf')], 0.0).fillna(0.0)
        return df
    except Exception as e:
        return pd.DataFrame()

def apply_theoretical_mix(df_in):
    df_out = df_in.copy()
    if df_out.empty: return df_out
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        with engine.connect() as conn:
            piro_tests = [str(tid).replace('_OIL', '') for tid in df_out['target_id'] if str(tid).endswith('_OIL')]
            feeds_to_remove = set()
            new_rows = []
            
            for pt in piro_tests:
                recipes = conn.execute(text("SELECT feedstock_id, percentuale FROM pirolisi_ricetta WHERE id_prova=:id"), {"id":pt}).fetchall()
                if not recipes or len(recipes) <= 1: continue 
                
                c_mix = h_mix = n_mix = s_mix = o_mix = hhv_mix = 0.0
                valid_mix = True
                
                for r in recipes:
                    fid = r[0]
                    perc = r[1] / 100.0
                    f_data = conn.execute(text("SELECT c_mean, h_mean, n_mean, s_mean, o_diff, hhv_stimato FROM dati_chnso WHERE target_id=:id"), {"id":fid}).first()
                    if not f_data:
                        valid_mix = False
                        break
                    c_mix += f_data[0] * perc
                    h_mix += f_data[1] * perc
                    n_mix += f_data[2] * perc
                    s_mix += f_data[3] * perc
                    o_mix += f_data[4] * perc
                    hhv_mix += f_data[5] * perc
                    feeds_to_remove.add(fid)
                    
                if valid_mix:
                    c_moles = c_mix / 12.011
                    new_row = {
                        'target_id': f"Mix ({pt})",
                        'c_mean': c_mix, 'c_std': 0, 'h_mean': h_mix, 'h_std': 0,
                        'n_mean': n_mix, 'n_std': 0, 's_mean': s_mix, 's_std': 0,
                        'o_diff': o_mix, 'hhv_stimato': hhv_mix,
                        'H/C': (h_mix/1.008)/c_moles if c_moles > 0 else 0,
                        'O/C': (o_mix/15.999)/c_moles if c_moles > 0 else 0,
                        'N/C': (n_mix/14.007)/c_moles if c_moles > 0 else 0,
                    }
                    new_rows.append(new_row)
                    
            if new_rows:
                df_out = df_out[~df_out['target_id'].isin(feeds_to_remove)]
                df_out = pd.concat([pd.DataFrame(new_rows), df_out], ignore_index=True)
        return df_out
    except Exception as e:
        return df_in
