import pandas as pd
from sqlalchemy import create_engine, text
import os

DB_PATH = "nexuslab.db"

def fetch_yields_data(id_prova, processo):
    """Estrae i dati delle rese (tutte le repliche) per la singola prova."""
    if not os.path.exists(DB_PATH): return pd.DataFrame()
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        if processo == 'Pirolisi':
            query = text("SELECT id_run, resa_olio as Olio, resa_char as Char, resa_gas as Gas FROM runs_pirolisi WHERE id_prova = :id")
            df = pd.read_sql(query, engine, params={"id": id_prova})
            return df
        else:
            query = text("SELECT id_prova as id_run, resa_biocrude as Biocrude, resa_char as Char, resa_gas as Gas, resa_wso as Aqueous_Phase FROM prove_idrotermiche WHERE id_prova = :id")
            df = pd.read_sql(query, engine, params={"id": id_prova})
            return df
    except Exception as e:
        print(f"Errore estrazione rese deep dive: {e}")
        return pd.DataFrame()

def fetch_gcms_targets_for_prova(id_prova):
    """Trova le frazioni analizzate in GC-MS (es. _OIL, _BC) associate a questa prova."""
    if not os.path.exists(DB_PATH): return []
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        # Cerca tutti i target che iniziano con l'id della prova seguito da underscore
        query = text("SELECT DISTINCT target_id FROM dati_gcms WHERE target_id LIKE :id || '_%'")
        res = engine.execute(query, {"id": id_prova}).fetchall()
        return [r[0] for r in res]
    except Exception as e:
        print(f"Errore target gcms deep dive: {e}")
        return []
