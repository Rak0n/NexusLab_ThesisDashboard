import pandas as pd
from sqlalchemy import create_engine, text
import os

DB_PATH = "nexuslab.db"

# ==========================================
# 1. FUNZIONI DI INSERIMENTO MANUALE
# ==========================================
def insert_manual_gc_data(data_dict):
    """
    Aggiunge un singolo record GC al database in modalità 'append' (non distruttiva).
    Gestisce la creazione della colonna 'strumento' se non esiste.
    """
    if not os.path.exists(DB_PATH): 
        return False, "Database non trovato."
        
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        with engine.connect() as conn:
            
            # Sicurezza: se la colonna strumento non esiste ancora nel DB, la crea on-the-fly
            try:
                conn.execute(text("ALTER TABLE dati_gc ADD COLUMN strumento VARCHAR DEFAULT 'Micro-GC'"))
                conn.commit()
            except Exception:
                pass 
            
            # Converte il dizionario in DataFrame e lo appende alla tabella
            df_to_inject = pd.DataFrame([data_dict])
            df_to_inject.to_sql('dati_gc', con=conn, if_exists='append', index=False)
            
            # Registrazione delle Analisi Effettuate (Tracciabilità)
            tid = data_dict['target_id']
            if conn.execute(text("SELECT COUNT(*) FROM registro_analisi WHERE target_id = :tid AND tipo_analisi = 'GC'"), {"tid": tid}).scalar() == 0:
                conn.execute(text("INSERT INTO registro_analisi (target_id, tipo_analisi) VALUES (:tid, 'GC')"), {"tid": tid})
            conn.commit()
            
        return True, f"✅ Run '{tid}' aggiunta con successo al database."
    except Exception as e:
        return False, f"Errore DB: {str(e)}"

# ==========================================
# 2. FUNZIONI ANALITICHE (BI & METADATA)
# ==========================================
def fetch_gc_data():
    """
    Estrae i dati GC, incrociandoli con le tabelle runs_pirolisi e prove_pirolisi 
    per risalire dall'id_run all'id_prova madre, alla temperatura e alla %PL.
    """
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
        
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        
        # Estrazione base dei dati e risoluzione run -> prova
        query = """
            SELECT 
                d.*,
                r.id_prova as id_prova_run
            FROM dati_gc d
            LEFT JOIN runs_pirolisi r 
                ON d.target_id = r.id_run 
                OR REPLACE(d.target_id, '_GAS', '') = r.id_run
                OR d.target_id = r.id_run || '_GAS'
        """
        df = pd.read_sql(query, engine)
        
        if not df.empty:
            # Fallback se non trova in runs_pirolisi
            df['id_prova'] = df['id_prova_run'].fillna(df['target_id'].str.replace('_GAS', '').str.rsplit('_').str[0])
            
            # Estrazione Temperatura e calcolo %PL (Polimeri = Mater-Bi + Polietilene)
            with engine.connect() as conn:
                prove_info = pd.read_sql("""
                    SELECT 
                        p.id_prova, 
                        p.temperatura,
                        COALESCE(SUM(r.percentuale), 0) as pl_perc
                    FROM prove_pirolisi p
                    LEFT JOIN pirolisi_ricetta r 
                        ON p.id_prova = r.id_prova 
                        AND (r.feedstock_id LIKE '%MB%' OR r.feedstock_id LIKE '%PE%')
                    GROUP BY p.id_prova
                """, conn)
                
            # Uniamo i metadati calcolati al dataframe principale
            df = pd.merge(df, prove_info, on='id_prova', how='left')
        
        return df
        
    except Exception as e:
        print(f"Errore fetch dati GC: {e}")
        return pd.DataFrame()
