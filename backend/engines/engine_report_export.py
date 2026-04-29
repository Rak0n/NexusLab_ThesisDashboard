from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Tuple

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine


@dataclass(frozen=True)
class ReportItem:
    """
    Un elemento esportabile del report.

    - name: nome logico (usato per sheet name)
    - df: DataFrame principale contenente i dati base
    - extra_dfs: Lista di tuple (titolo_tabella, DataFrame) da appendere sotto il primo
    - main_title: (Opzionale) Titolo da posizionare sopra il DataFrame principale
    """
    name: str
    df: pd.DataFrame
    extra_dfs: List[Tuple[str, pd.DataFrame]] = field(default_factory=list)
    main_title: str = ""


def _safe_sheet_name(name: str, used: set[str]) -> str:
    # Excel: max 31 char, no []:*?/\
    cleaned = "".join(ch for ch in str(name) if ch not in "[]:*?/\\")
    cleaned = cleaned.strip() or "Sheet"
    base = cleaned[:31]

    candidate = base
    i = 2
    while candidate in used:
        suffix = f"_{i}"
        candidate = (base[: 31 - len(suffix)] + suffix).strip()
        i += 1
    used.add(candidate)
    return candidate


def _sort_logic_target_chnso(tid: str) -> tuple:
    """Logica di ordinamento per il CHNSO: Feed/Mix -> OIL -> BC -> CHAR -> altro."""
    tid_u = str(tid).upper()
    if tid_u.startswith("FS_"):
        return (10, tid_u)
    if "MIX" in tid_u:
        return (15, tid_u)
    if tid_u.endswith("_OIL"):
        return (20, tid_u)
    if tid_u.endswith("_BC"):
        return (30, tid_u)
    if tid_u.endswith("_AP"):
        return (35, tid_u)
    if tid_u.endswith("_CHAR"):
        return (40, tid_u)
    return (90, tid_u)


def _enrich_mix_moisture_ash(df_chnso: pd.DataFrame) -> pd.DataFrame:
    """Aggiunge moisture e ash pesati per i Mix teorici calcolati."""
    if df_chnso.empty:
        return df_chnso

    df_out = df_chnso.copy()
    mix_rows = df_out['target_id'].astype(str).str.startswith('Mix (')
    if not mix_rows.any():
        return df_out

    from engines import engine_chnso
    try:
        engine = create_engine(f"sqlite:///{engine_chnso.DB_PATH}")
    except Exception:
        return df_out

    for idx in df_out[mix_rows].index.tolist():
        tid = str(df_out.at[idx, 'target_id'])
        m = re.search(r"Mix\s*\(([^)]+)\)", tid)
        if not m:
            continue
        base_p = m.group(1).strip()

        try:
            df_rec = pd.read_sql(
                "SELECT feedstock_id, percentuale FROM pirolisi_ricetta WHERE id_prova = ?",
                engine,
                params=(base_p,)
            )
        except Exception:
            continue

        if df_rec.empty or 'feedstock_id' not in df_rec.columns or 'percentuale' not in df_rec.columns:
            continue

        moist_mix = 0.0
        ash_mix = 0.0
        tot = 0.0

        for _, r in df_rec.iterrows():
            fid = str(r['feedstock_id']).strip()
            try:
                perc = float(r['percentuale']) / 100.0
            except Exception:
                continue
            if not fid or perc <= 0:
                continue

            try:
                row = pd.read_sql(
                    "SELECT moisture, ash FROM dati_chnso WHERE target_id = ?",
                    engine,
                    params=(fid,)
                )
            except Exception:
                row = pd.DataFrame()

            if row.empty:
                continue

            moist = float(row.iloc[0].get('moisture', 0.0) or 0.0)
            ash = float(row.iloc[0].get('ash', 0.0) or 0.0)

            moist_mix += moist * perc
            ash_mix += ash * perc
            tot += perc

        if tot > 0:
            df_out.at[idx, 'moisture'] = moist_mix / tot
            df_out.at[idx, 'ash'] = ash_mix / tot

    return df_out


def format_chnso_extra_table(df_chnso: pd.DataFrame) -> pd.DataFrame:
    """
    Genera la tabella aggiuntiva formattata per il foglio CHNSO (Riepilogo elementi).
    Mostra solo target_id e le colonne con stringa "mean ± std" per C,H,N,S e media per O.
    """
    df_out = pd.DataFrame()
    
    if 'target_id' in df_chnso.columns:
        df_out['target_id'] = df_chnso['target_id']
    else:
        return df_out
                
    # Creiamo le colonne stringa "mean ± std" per C, H, N, S
    for el in ['c', 'h', 'n', 's']:
        mean_c = f"{el}_mean"
        std_c = f"{el}_std"
        str_col = f"{el.upper()}%"
        
        if mean_c in df_chnso.columns:
            def fmt_str(row, m_col=mean_c, s_col=std_c):
                m = row.get(m_col)
                s = row.get(s_col, 0.0)
                
                if pd.isna(m) or str(m).strip() == "-" or str(m).strip() == "": 
                    return "-"
                    
                s_val = s if pd.notna(s) and str(s).strip() != "-" else 0.0
                return f"{float(m):.2f} ± {float(s_val):.2f}"
                
            df_out[str_col] = df_chnso.apply(fmt_str, axis=1)
            
    # Solo media per l'Ossigeno
    if 'o_diff' in df_chnso.columns:
        def fmt_o(row):
            o = row.get('o_diff')
            if pd.isna(o) or str(o).strip() == "-" or str(o).strip() == "":
                return "-"
            return f"{float(o):.2f}"
            
        df_out['O%'] = df_chnso.apply(fmt_o, axis=1)
            
    return df_out


def build_xlsx_report(
    items: Iterable[ReportItem],
    *,
    title: str = "NexusLab Report Dati",
    created_at: datetime | None = None,
    metadata_df: pd.DataFrame | None = None,
) -> bytes:
    """
    Crea un XLSX in memoria con:
    - 1 foglio 'SUMMARY' con in basso la Grid dei metadati
    - Fogli tematici con unione e spaziature dinamiche
    """
    created_at = created_at or datetime.now()
    bio = io.BytesIO()

    with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
        workbook = writer.book

        # SUMMARY INIZIALE
        df_summary = pd.DataFrame(
            [
                {"Dato Base": "Titolo", "Valore": title},
                {"Dato Base": "Data Creazione", "Valore": created_at.isoformat(sep=" ", timespec="seconds")},
                {"Dato Base": "Fogli Generati", "Valore": len(list(items))},
            ]
        )
        
        items_list: List[ReportItem] = list(items)
        df_summary.at[2, "Valore"] = len(items_list)
        df_summary.to_excel(writer, sheet_name="SUMMARY", index=False)

        # INSERIMENTO DELLA GRID (METADATI) NEL SUMMARY
        if metadata_df is not None and not metadata_df.empty:
            ws_sum = writer.sheets["SUMMARY"]
            start_meta = len(df_summary) + 4
            ws_sum.write_string(start_meta - 1, 0, "Riepilogo Prove in Analisi (Metadati):", workbook.add_format({"bold": True}))
            metadata_df.to_excel(writer, sheet_name="SUMMARY", index=False, startrow=start_meta)

        # GENERAZIONE DEGLI ALTRI FOGLI
        used_sheets: set[str] = {"SUMMARY"}
        for item in items_list:
            sheet = _safe_sheet_name(item.name, used_sheets)
            df = item.df if item.df is not None else pd.DataFrame()
            
            start_row = 0
            
            # Se è presente un main_title, scaliamo di una riga per scriverlo
            if item.main_title:
                df.to_excel(writer, sheet_name=sheet, index=False, startrow=1)
                ws = writer.sheets[sheet]
                ws.write_string(0, 0, item.main_title, workbook.add_format({"bold": True}))
                start_row = len(df) + 5
            else:
                df.to_excel(writer, sheet_name=sheet, index=False)
                ws = writer.sheets[sheet]
                start_row = len(df) + 4
            
            # Se ci sono tabelle extra, le accoda sotto distanziando dinamicamente
            if item.extra_dfs:
                for extra_title, extra_df in item.extra_dfs:
                    if extra_title:
                        ws.write_string(start_row - 1, 0, extra_title, workbook.add_format({"bold": True}))
                    
                    extra_df.to_excel(writer, sheet_name=sheet, index=False, startrow=start_row)
                    start_row += len(extra_df) + 4

        # Formattazione estetica del summary
        try:
            ws_sum = writer.sheets["SUMMARY"]
            fmt_key = workbook.add_format({"bold": True})
            ws_sum.set_column(0, 0, 25, fmt_key)
            ws_sum.set_column(1, 1, 60)
        except Exception:
            pass

    bio.seek(0)
    return bio.read()


def generate_multi_report(trial_ids: list[str]):
    """
    Funzione richiamata dalla UI. Estrae gli esatti DataFrame 
    utilizzati per generare i grafici e li impacchetta in Excel.
    """
    from engines import engine_multi_deepdive
    from engines import engine_chnso
    from engines import engine_gcms
    
    if not trial_ids:
        st.error("Nessuna prova selezionata per il report.")
        return

    st.info("⚙️ Estrazione dei dati e compilazione del report in corso...")
    
    try:
        report_items = []
        
        # --- 1. METADATI (Destinati al foglio SUMMARY) ---
        df_meta = engine_multi_deepdive.get_metadata_for_trials(trial_ids)

        # --- 2. RESE MASSICHE (Foglio Unico Dinamico) ---
        df_piro, df_ht = engine_multi_deepdive.fetch_multi_yields(trial_ids)
        
        if not df_piro.empty and not df_ht.empty:
            report_items.append(ReportItem(
                name="Rese", 
                df=df_piro,
                main_title="Rese Pirolisi:",
                extra_dfs=[("Rese Idrotermali:", df_ht)]
            ))
        elif not df_piro.empty:
            report_items.append(ReportItem(name="Rese", df=df_piro, main_title="Rese Pirolisi:"))
        elif not df_ht.empty:
            report_items.append(ReportItem(name="Rese", df=df_ht, main_title="Rese Idrotermali:"))

        # --- 3. CHNSO E VAN KREVELEN ---
        targets_chnso = []
        for tid in trial_ids:
            targets_chnso.extend([f"{tid}_OIL", f"{tid}_BC", f"{tid}_CHAR"])
            
        feed_ids = engine_multi_deepdive.get_feedstock_targets(trial_ids)
        targets_chnso.extend(feed_ids)
        targets_chnso = list(dict.fromkeys([str(t).upper() for t in targets_chnso if t]))
        
        df_chnso = engine_chnso.fetch_chnso_data(targets_chnso)
        if not df_chnso.empty:
            # Salviamo il dataframe originale per preservare i Feedstock Puri
            df_originale = df_chnso.copy()
            
            # Calcola i MIX teorici
            df_con_mix = engine_chnso.apply_theoretical_mix(df_chnso.copy())
            df_con_mix = _enrich_mix_moisture_ash(df_con_mix)
            
            # Uniamo i due DataFrame per avere SIA i Feedstock puri SIA i Mix
            df_unito = pd.concat([df_originale, df_con_mix]).drop_duplicates(subset=['target_id'])
            
            # Applica l'ordinamento intelligente (Feed -> Mix -> Oil -> BC...)
            df_unito['__sort_key'] = df_unito['target_id'].apply(_sort_logic_target_chnso)
            df_chnso = df_unito.sort_values(['__sort_key']).drop(columns=['__sort_key'])
            
            # Crea la tabella riassuntiva "mean +- std" includendo ora anche i Mix
            df_chnso_formatted = format_chnso_extra_table(df_chnso)
            
            report_items.append(ReportItem(
                name="CHNSO e Van Krevelen", 
                df=df_chnso,
                main_title="Dataset Completo CHNSO:",
                extra_dfs=[("Riepilogo C H N S O:", df_chnso_formatted)]
            ))

        # --- 4. GC-MS ---
        targets_gcms = []
        for tid in trial_ids:
            targets_gcms.extend([f"{tid}_OIL", f"{tid}_BC", f"{tid}_AP"])
        targets_gcms = list(dict.fromkeys([str(t).upper() for t in targets_gcms if t]))

        df_gcms = engine_gcms.fetch_analytical_dataset(targets_gcms)
        if not df_gcms.empty:
            area_col = 'new_area_perc' if 'new_area_perc' in df_gcms.columns else 'original_area'
            
            report_items.append(ReportItem(name="GC-MS Dataset Grezzo", df=df_gcms))
            
            df_macro = df_gcms.groupby(['target_id', 'macro_class'])[area_col].sum().reset_index()
            report_items.append(ReportItem(name="GC-MS Macro-Famiglie", df=df_macro))
            
            df_class = df_gcms.groupby(['target_id', 'class_of_compounds'])[area_col].sum().reset_index()
            report_items.append(ReportItem(name="GC-MS Classi Composti", df=df_class))
            
            df_pivot = df_gcms.pivot_table(
                index=['compound_name', 'class_of_compounds', 'macro_class'], 
                columns='target_id', 
                values=area_col, 
                aggfunc='sum'
            ).fillna(0).reset_index()
            report_items.append(ReportItem(name="GC-MS Pivot Composti", df=df_pivot))

        # --- GENERAZIONE FILENAME DINAMICO E FILE EXCEL ---
        clean_ids = [re.sub(r'[^A-Za-z0-9]', '', str(tid)) for tid in trial_ids]
        if len(clean_ids) <= 4:
            trial_str = "_".join(clean_ids)
        else:
            trial_str = "_".join(clean_ids[:3]) + f"_e_altre_{len(clean_ids)-3}"
            
        file_name = f"NexusLab_Dati_{trial_str}.xlsx"

        excel_data = build_xlsx_report(
            items=report_items, 
            title=f"Multi-Deep Dive Report ({len(trial_ids)} prove)",
            metadata_df=df_meta
        )

        st.download_button(
            label="⬇️ Scarica il Report Excel (Solo Dati)",
            data=excel_data,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"Si è verificato un errore durante la creazione del report: {e}")
