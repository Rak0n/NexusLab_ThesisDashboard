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
            if target_id.endswith('_OIL'):
                base_id = target_id.replace('_OIL', '')
                res = conn.execute(text("SELECT id_prova FROM prove_pirolisi WHERE id_prova = :id"), {"id": base_id}).scalar()
                if res: return True, "Valido"
                return False, f"La prova base '{base_id}' non esiste."
            elif target_id.endswith('_BC') or target_id.endswith('_AP'):
                base_id = target_id.rsplit('_', 1)[0]
                res = conn.execute(text("SELECT id_prova FROM prove_idrotermiche WHERE id_prova = :id"), {"id": base_id}).scalar()
                if res: return True, "Valido"
                return False, f"La prova base '{base_id}' non esiste."
            else:
                return False, "Usa i suffissi _OIL, _BC o _AP."
    except Exception as e:
        return False, f"Errore SQL: {str(e)}"

def check_existing_target(target_id):
    if not os.path.exists(DB_PATH) or not target_id: return False
    target_id = target_id.strip().upper()
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        with engine.connect() as conn:
            res = conn.execute(text("SELECT COUNT(*) FROM dati_gcms WHERE target_id = :tid"), {"tid": target_id}).scalar()
            return res > 0
    except Exception: return False

def parse_gcms_excel(uploaded_file, match_threshold):
    try:
        xls = pd.ExcelFile(uploaded_file)
        dict_dfs = {}
        for sheet_name in xls.sheet_names:
            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            header_idx = 0
            for idx, row in df_raw.iterrows():
                if 'Compound Name' in row.values or 'Component RT' in row.values:
                    header_idx = idx
                    break
            df = pd.read_excel(xls, sheet_name=sheet_name, header=header_idx)
            df.columns = [str(c).strip() for c in df.columns]
            
            req_cols = ['Component RT', 'Compound Name', 'Match Factor', 'Component Area']
            if not [c for c in req_cols if c not in df.columns]:
                df_filtered = df[df['Match Factor'] >= match_threshold].copy()
                total_area = df_filtered['Component Area'].sum()
                df_filtered['New Area %'] = (df_filtered['Component Area'] / total_area) * 100 if total_area > 0 else 0.0
                if 'Area %' not in df_filtered.columns: df_filtered['Area %'] = df_filtered['New Area %']
                df_filtered = df_filtered.sort_values(by='New Area %', ascending=False).reset_index(drop=True)
                dict_dfs[sheet_name] = df_filtered
            else:
                dict_dfs[sheet_name] = pd.DataFrame()
        return dict_dfs
    except Exception as e: return {"error": str(e)}

def inject_gcms_to_db(target_id, df_processed, overwrite=False):
    if not os.path.exists(DB_PATH): return False, "Database non trovato."
    target_id = target_id.strip().upper()
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        with engine.connect() as conn:
            if overwrite:
                conn.execute(text("DELETE FROM dati_gcms WHERE target_id = :tid"), {"tid": target_id})
                conn.commit()

            df_db = pd.DataFrame()
            df_db['target_id'] = [target_id] * len(df_processed)
            df_db['retention_time'] = df_processed.get('Component RT', 0.0)
            df_db['compound_name'] = df_processed.get('Compound Name', 'Unknown')
            df_db['match_factor'] = df_processed.get('Match Factor', 0.0)
            df_db['area_perc'] = df_processed.get('Area %', 0.0)
            df_db['new_area_perc'] = df_processed.get('New Area %', 0.0)
            df_db['formula_bruta'] = df_processed.get('Formula Bruta', None)
            df_db['peso_molecolare'] = df_processed.get('Peso Molecolare', None)
            df_db['famiglia'] = df_processed.get('Famiglia Assegnata', None)
            
            df_db.to_sql('dati_gcms', con=conn, if_exists='append', index=False)
            
            if conn.execute(text("SELECT COUNT(*) FROM registro_analisi WHERE target_id = :tid AND tipo_analisi = 'GC-MS'"), {"tid": target_id}).scalar() == 0:
                conn.execute(text("INSERT INTO registro_analisi (target_id, tipo_analisi) VALUES (:tid, 'GC-MS')"), {"tid": target_id})
            conn.commit()
        return True, f"✅ Dati GC-MS iniettati con successo per il campione: {target_id}"
    except Exception as e: return False, f"Errore DB: {str(e)}"

# ==========================================
# 2. FUNZIONI ANALITICHE (BI & METADATA)
# ==========================================
def get_targets_metadata():
    """Ricostruisce i metadati completi per ogni prova GC-MS."""
    if not os.path.exists(DB_PATH): return pd.DataFrame()
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        targets_meta = []
        with engine.connect() as conn:
            res = conn.execute(text("SELECT DISTINCT target_id FROM dati_gcms")).fetchall()
            for r in res:
                tid = r[0]
                proc, feed, temp, tempo, cat, resa = 'Sconosciuto', 'Sconosciuto', 0.0, 0.0, '-', None
                
                if tid.endswith('_OIL'):
                    base_id = tid.replace('_OIL', '')
                    row = conn.execute(text("SELECT temperatura, catalizzatore FROM prove_pirolisi WHERE id_prova=:id"), {"id":base_id}).first()
                    if row:
                        proc = 'Pirolisi'
                        temp = row[0]
                        tempo = 30 # Default Pirolisi
                        cat = row[1] if row[1] else '-'
                        feeds = conn.execute(text("SELECT feedstock_id FROM pirolisi_ricetta WHERE id_prova=:id"), {"id":base_id}).fetchall()
                        feed = " + ".join([f[0].replace('FS_', '') for f in feeds]) if feeds else 'Sconosciuto'
                        # Calcolo Media Resa Olio
                        resa_val = conn.execute(text("SELECT AVG(resa_olio) FROM runs_pirolisi WHERE id_prova=:id"), {"id":base_id}).scalar()
                        resa = round(resa_val, 2) if resa_val else None
                        
                elif tid.endswith('_BC') or tid.endswith('_AP'):
                    base_id = tid.rsplit('_', 1)[0]
                    row = conn.execute(text("SELECT tipo_processo, temperatura, tempo, catalizzatore, resa_biocrude FROM prove_idrotermiche WHERE id_prova=:id"), {"id":base_id}).first()
                    if row:
                        suff = "Biocrude" if tid.endswith('_BC') else "Fase Acquosa"
                        proc = f"{row[0]} {suff}"
                        temp = row[1]
                        tempo = row[2]
                        cat = row[3] if row[3] else '-'
                        resa = round(row[4], 2) if row[4] else None
                        feeds = conn.execute(text("SELECT source_id FROM input_idrotermico WHERE id_prova=:id"), {"id":base_id}).fetchall()
                        feed = " + ".join([f[0].replace('_OIL', '').replace('_BC', '') for f in feeds]) if feeds else 'Sconosciuto'
                
                targets_meta.append({
                    'target_id': tid,
                    'Processo': proc,
                    'Feedstock': feed,
                    'Temperatura': temp,
                    'Tempo': tempo,
                    'Catalizzatore': cat,
                    'Resa Olio/Biocrude (%)': resa
                })
        return pd.DataFrame(targets_meta)
    except Exception as e:
        print(f"Errore recupero metadati: {e}")
        return pd.DataFrame()

def get_lineage_sets():
    """Genera i set di prove raggruppate seguendo la logica esatta: Feed -> Processo."""
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
                feed = str(r[1]).replace('FS_', '') if r[1] else 'Mix'
                sets[f"{feed} ➔ {id_p}"] = [f"{id_p}_OIL"]
                
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
                    feed_str = str(feed_res).replace('FS_', '') if feed_res else 'Sconosciuto'
                    sets[f"{feed_str} ➔ {source} ➔ {id_ht}"] = [source, f"{id_ht}_BC", f"{id_ht}_AP"]
                elif tipo == 'HTL':
                    sets[f"{source.replace('FS_', '')} ➔ {id_ht}"] = [f"{id_ht}_BC", f"{id_ht}_AP"]
        return sets
    except Exception as e:
        print(f"Errore lineage sets: {e}")
        return {}

def fetch_analytical_dataset(target_ids=None):
    """Estrae i dati GC-MS globali o parziali, restituendo i marker testuali correttamente."""
    if not os.path.exists(DB_PATH): return pd.DataFrame()
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        
        query = """
            SELECT 
                d.target_id,
                d.retention_time,
                d.compound_name,
                d.match_factor,
                d.new_area_perc as original_area,
                d.formula_bruta,
                d.peso_molecolare,
                COALESCE(dic.macro_class, 'Non Classificato') as macro_class,
                COALESCE(dic.class_of_compounds, 'Non Classificato') as class_of_compounds,
                COALESCE(dic.is_contaminant, 0) as is_contaminant,
                COALESCE(dic.is_valuable, 0) as is_valuable,
                COALESCE(dic.is_marker, 'No') as is_marker,
                dic.marker_source_id
            FROM dati_gcms d
            LEFT JOIN dizionario_gcms dic ON d.compound_name = dic.compound_name
        """
        
        if target_ids is not None and len(target_ids) > 0:
            placeholders = ','.join(['?'] * len(target_ids))
            query += f" WHERE d.target_id IN ({placeholders})"
            df = pd.read_sql(query, engine, params=tuple(target_ids))
        else:
            df = pd.read_sql(query, engine)
            
        if not df.empty:
            df_clean = df[df['is_contaminant'] == 0].copy()
            df_clean['normalized_area'] = df_clean.groupby('target_id')['original_area'].transform(lambda x: (x / x.sum()) * 100)
            return df_clean
        return df
    except Exception as e:
        print(f"Errore fetch analitico: {e}")
        return pd.DataFrame()

def get_all_valuable_compounds():
    if not os.path.exists(DB_PATH): return []
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        with engine.connect() as conn:
            res = conn.execute(text("""
                SELECT DISTINCT d.compound_name 
                FROM dati_gcms d
                LEFT JOIN dizionario_gcms dic ON d.compound_name = dic.compound_name
                WHERE dic.is_valuable = 1 
                   OR dic.is_valuable = 'Si'
                   OR d.compound_name LIKE '%phenol%' 
                   OR d.compound_name LIKE '%cyclopentanone%' 
                   OR d.compound_name LIKE '%alcohol%'
            """)).fetchall()
            return sorted([r[0] for r in res])
    except Exception: return []

def get_compound_ranking(compounds_list):
    if not os.path.exists(DB_PATH) or not compounds_list: return pd.DataFrame()
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        placeholders = ','.join(['?'] * len(compounds_list))
        query = f"""
            SELECT target_id, compound_name, new_area_perc, formula_bruta 
            FROM dati_gcms 
            WHERE compound_name IN ({placeholders})
            ORDER BY new_area_perc DESC
        """
        df = pd.read_sql(query, engine, params=tuple(compounds_list))
        if df.empty: return df
        
        meta = get_targets_metadata()
        if not meta.empty:
            df = pd.merge(df, meta, on='target_id', how='left')
            df = df.sort_values(['compound_name', 'new_area_perc'], ascending=[True, False])
        return df
    except Exception as e:
        print(f"Errore ranking: {e}")
        return pd.DataFrame()
