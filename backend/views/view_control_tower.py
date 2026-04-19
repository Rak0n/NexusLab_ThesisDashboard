import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, ColumnsAutoSizeMode
from sqlalchemy import create_engine, text
import os
import plotly.express as px

DB_PATH = "nexuslab.db"

# --- 🛠️ FUNZIONE DI DIAGNOSTICA (TROUBLESHOOTING) ---
def run_db_diagnostics():
    """Analizza l'ambiente di runtime per capire perché il DB non viene letto."""
    diagnostics = {
        "cwd": os.getcwd(),
        "files_in_cwd": os.listdir('.') if os.path.exists('.') else [],
        "db_exists": os.path.exists(DB_PATH),
        "db_size_bytes": os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0,
        "sql_error": None,
        "is_empty": False
    }
    
    if diagnostics["db_exists"]:
        try:
            engine = create_engine(f"sqlite:///{DB_PATH}")
            with engine.connect() as conn:
                # Controlliamo se ci sono tabelle nel database
                res = conn.execute(text("SELECT count(*) FROM sqlite_master WHERE type='table'")).scalar()
                if res == 0:
                    diagnostics["is_empty"] = True
        except Exception as e:
            diagnostics["sql_error"] = str(e)
            
    return diagnostics

# --- LOGICA DI ESTRAZIONE DATI DETTAGLIATI (SOLO DB REALE) ---
def fetch_detailed_data(id_prova, processo, feed_string):
    """Estrae i dati specifici interrogando le tabelle relazionali, senza fallback finti."""
    details = {
        'recipe': None,
        'is_base_recipe': False,
        'yields': {},
        'lineage_target': None,
        'lineage_source': None,
        'base_feed_string': None
    }
    
    if not os.path.exists(DB_PATH):
        return details

    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        with engine.connect() as conn:
            # 1. Risoluzione del Lineage
            if processo == 'Pirolisi':
                res_target = conn.execute(
                    text("""
                        SELECT i.id_prova, p.tipo_processo
                        FROM input_idrotermico i
                        JOIN prove_idrotermiche p ON i.id_prova = p.id_prova
                        WHERE i.source_id LIKE '%' || :id || '%'
                    """), {"id": id_prova}
                ).mappings().first()
                if res_target:
                    details['lineage_target'] = dict(res_target)
            else:
                res_source = conn.execute(
                    text("SELECT source_id FROM input_idrotermico WHERE id_prova = :id"), 
                    {"id": id_prova}
                ).mappings().first()
                if res_source:
                    clean_source = res_source['source_id'].replace('_OIL', '').replace('_BC', '')
                    details['lineage_source'] = clean_source

            # 2. Estrazione Ricetta (Composizione Feedstock)
            target_recipe_id = details['lineage_source'] if processo == 'HTU' and details['lineage_source'] else id_prova
            
            res_recipe = conn.execute(
                text("SELECT feedstock_id, percentuale FROM pirolisi_ricetta WHERE id_prova = :id"), 
                {"id": target_recipe_id}
            ).mappings().all()
            
            if res_recipe:
                details['recipe'] = pd.DataFrame(res_recipe)
                if processo == 'HTU':
                    details['is_base_recipe'] = True
                    feeds_list = [str(r['feedstock_id']).replace('FS_', '') for r in res_recipe]
                    details['base_feed_string'] = " + ".join(feeds_list)

            # 3. Estrazione Rese
            if processo == 'Pirolisi':
                res_yield = conn.execute(
                    text("SELECT AVG(resa_olio) as olio, AVG(resa_char) as char, AVG(resa_gas) as gas FROM runs_pirolisi WHERE id_prova = :id"), 
                    {"id": id_prova}
                ).mappings().first()
                if res_yield and res_yield['olio'] is not None:
                    details['yields'] = dict(res_yield)
            else:
                res_yield = conn.execute(
                    text("SELECT resa_biocrude as biocrude, resa_char as char, resa_gas as gas, resa_wso as wso, resa_tot as totale FROM prove_idrotermiche WHERE id_prova = :id"), 
                    {"id": id_prova}
                ).mappings().first()
                if res_yield and res_yield['biocrude'] is not None:
                    d = dict(res_yield)
                    if d.get('totale') is None:
                        d['totale'] = sum(filter(None, [d.get('biocrude'), d.get('char'), d.get('gas'), d.get('wso')]))
                    details['yields'] = d

    except Exception as e:
        st.toast(f"Errore caricamento dettagli prova: {e}")

    return details

# --- RENDER DEL CASSETTO (CONTEXT DRAWER) ---
@st.dialog("Dettaglio Analitico Prova", width="large")
def show_context_drawer(row_data):
    st.markdown(
        """
        <style>
            div[data-testid="stDialog"] div[role="dialog"] {
                width: 85vw !important;
                max-width: 1500px !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    id_prova = row_data.get('ID PROVA', '-')
    processo = row_data.get('PROCESSO', '-')
    feed = row_data.get('FEEDSTOCK', '-')
    
    st.markdown(f"<h3 style='color: #1e293b; margin-top: 0;'>{id_prova} <span style='color: #94a3b8;'>|</span> {processo}</h3>", unsafe_allow_html=True)
    
    details = fetch_detailed_data(id_prova, processo, feed)
    
    # -- ROW 1: Lineage & Condizioni --
    col_lineage, col_cond = st.columns([1.8, 1])
    
    with col_lineage:
        st.markdown("<p style='font-size: 11px; font-weight: 600; color: #64748b; letter-spacing: 1px; margin-bottom: 8px;'>LINEAGE RELAZIONALE</p>", unsafe_allow_html=True)
        bc_style = "display: flex; align-items: center; gap: 8px; font-size: 13px; flex-wrap: wrap;"
        box_style = "background: #f8fafc; border: 1px solid #cbd5e1; padding: 4px 10px; border-radius: 4px; font-weight: 600; color: #334155;"
        box_hl = "background: #eff6ff; border: 1px solid #bfdbfe; padding: 4px 10px; border-radius: 4px; font-weight: 600; color: #1d4ed8;"
        arrow = "<span style='color: #94a3b8; font-weight: bold;'>➔</span>"
        
        if processo == 'HTU' and details.get('lineage_source'):
            source_id = details['lineage_source']
            base_feed = details.get('base_feed_string', 'Feed Sconosciuto')
            html = f"<div style='{bc_style}'><div style='{box_style}'>{base_feed}</div>{arrow}<div style='{box_style}'>Pirolisi ({source_id})</div>{arrow}<div style='{box_hl}'>HTU ({id_prova})</div></div>"
        elif processo == 'Pirolisi':
            if details.get('lineage_target'):
                target_id = details['lineage_target']['id_prova']
                target_proc = details['lineage_target']['tipo_processo']
                html = f"<div style='{bc_style}'><div style='{box_style}'>{feed}</div>{arrow}<div style='{box_hl}'>Pirolisi ({id_prova})</div>{arrow}<div style='{box_style}'>{target_proc} ({target_id})</div></div>"
            else:
                html = f"<div style='{bc_style}'><div style='{box_style}'>{feed}</div>{arrow}<div style='{box_hl}'>Pirolisi ({id_prova})</div></div>"
        elif processo == 'HTL':
            html = f"<div style='{bc_style}'><div style='{box_style}'>{feed}</div>{arrow}<div style='{box_hl}'>HTL ({id_prova})</div></div>"
        else:
            html = f"<div style='{bc_style}'><div style='{box_style}'>{feed}</div>{arrow}<div style='{box_hl}'>{processo} ({id_prova})</div></div>"
            
        st.markdown(html, unsafe_allow_html=True)

    with col_cond:
        st.markdown("<p style='font-size: 11px; font-weight: 600; color: #64748b; letter-spacing: 1px; margin-bottom: 8px;'>PARAMETRI OPERATIVI</p>", unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        m1.metric("Temperatura", f"{row_data.get('TEMP (°C)', '-')} °C")
        m2.metric("Tempo", f"{row_data.get('TEMPO (MIN)', '-')} min")
        st.markdown(f"<p style='font-size: 13px; color: #475569;'><b>Catalizzatore:</b> {row_data.get('CATALIZZATORE', '-')}</p>", unsafe_allow_html=True)
        
    st.divider()
    
    # -- ROW 2: Composizione & Rese --
    col_pie, col_yields = st.columns([1, 1.8])
    
    with col_pie:
        st.markdown("<p style='font-size: 11px; font-weight: 600; color: #64748b; letter-spacing: 1px; margin-bottom: 0px;'>COMPOSIZIONE MATRICE</p>", unsafe_allow_html=True)
        df_recipe = details['recipe']
        
        if details.get('is_base_recipe'):
            st.markdown(f"<p style='font-size: 12px; font-style: italic; color: #64748b; margin-top: 0px;'>Riferita alla sorgente ({details['lineage_source']})</p>", unsafe_allow_html=True)
            
        if df_recipe is not None and not df_recipe.empty:
            df_recipe['feedstock_id'] = df_recipe['feedstock_id'].astype(str).str.replace("FS_", "", regex=False)
            fig = px.pie(df_recipe, values='percentuale', names='feedstock_id', hole=0.5, height=220, color_discrete_sequence=['#3b82f6', '#f59e0b', '#10b981', '#6366f1'])
            fig.update_layout(margin=dict(t=0, b=10, l=10, r=10), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessuna anagrafica ricetta trovata nel database per questa prova.")

    with col_yields:
        st.markdown("<p style='font-size: 11px; font-weight: 600; color: #64748b; letter-spacing: 1px; margin-bottom: 15px;'>FRAZIONI (MEDIE REPLICHE)</p>", unsafe_allow_html=True)
        
        y_data = details['yields']
        if not y_data:
            st.info("Nessun dato di resa massica inserito nel database per questa prova.")
        else:
            if processo == 'Pirolisi':
                fractions = [("Olio", y_data.get('olio', 0), "#ea580c"), ("Char", y_data.get('char', 0), "#10b981"), ("Gas (Diff)", y_data.get('gas', 0), "#0ea5e9")]
            else:
                fractions = [("Biocrude", y_data.get('biocrude', 0), "#ea580c"), ("Aqueous P.", y_data.get('wso', 0), "#3b82f6"), ("Char", y_data.get('char', 0), "#10b981"), ("Gas", y_data.get('gas', 0), "#0ea5e9")]
                
            for f_name, f_val, f_color in fractions:
                val_num = f_val if f_val is not None else 0
                bar_html = f"""
                <div style="display:flex; align-items:center; margin-bottom: 8px;">
                    <div style="width: 90px; font-size: 13px; font-weight: 600; color:#334155;">{f_name}</div>
                    <div style="flex-grow: 1; background-color: #f1f5f9; height: 14px; border-radius: 6px; margin: 0 10px; overflow:hidden;">
                        <div style="width: {val_num}%; background-color: {f_color}; height: 100%;"></div>
                    </div>
                    <div style="width: 50px; text-align: right; font-size: 14px; font-weight: 700; color:{f_color};">{val_num:.1f}%</div>
                </div>
                """
                st.markdown(bar_html, unsafe_allow_html=True)
            
            if processo in ('HTL', 'HTU'):
                totale = y_data.get('totale') if y_data.get('totale') is not None else 0
                tot_color = "#10b981" if 80 <= totale <= 110 else "#f59e0b"
                st.markdown(f"""
                <div style="margin-top: 15px; padding-top: 10px; border-top: 1px dashed #cbd5e1; display:flex; justify-content: space-between;">
                    <span style="font-weight: 600; font-size: 14px; color: #334155;">Resa Totale Recuperata:</span>
                    <span style="font-weight: 800; font-size: 16px; color: {tot_color};">{totale:.1f}%</span>
                </div>
                """, unsafe_allow_html=True)

    st.divider()
    if st.button("Apri Ambiente di Analisi (Deep Dive)", type="primary", use_container_width=True):
        st.session_state.current_view = "Deep Dive"
        st.rerun()

def fetch_data():
    """Recupera l'indice delle prove per la Grid principale solo dal DB."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame(), "Database non trovato."
        
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        query = text("""
            SELECT 
                p.id_prova as "ID PROVA", 
                'Pirolisi' as "PROCESSO", 
                p.temperatura as "TEMP (°C)", 
                30 as "TEMPO (MIN)", 
                GROUP_CONCAT(r.feedstock_id, ' + ') as "FEEDSTOCK",
                p.catalizzatore as "CATALIZZATORE"
            FROM prove_pirolisi p
            LEFT JOIN pirolisi_ricetta r ON p.id_prova = r.id_prova
            GROUP BY p.id_prova
            
            UNION ALL
            
            SELECT 
                i.id_prova as "ID PROVA", 
                i.tipo_processo as "PROCESSO", 
                i.temperatura as "TEMP (°C)", 
                i.tempo as "TEMPO (MIN)", 
                GROUP_CONCAT(inp.source_id, ' + ') as "FEEDSTOCK",
                i.catalizzatore as "CATALIZZATORE"
            FROM prove_idrotermiche i
            LEFT JOIN input_idrotermico inp ON i.id_prova = inp.id_prova
            GROUP BY i.id_prova
        """)
        df_db = pd.read_sql(query, engine).fillna('-')
        
        if df_db.empty:
            return pd.DataFrame(), "Il database esiste ma non contiene nessuna prova."
            
        df_db["FEEDSTOCK"] = df_db["FEEDSTOCK"].astype(str).str.replace("FS_", "", regex=False)
        df_db["CATALIZZATORE"] = df_db["CATALIZZATORE"].astype(str).str.replace("CAT_", "", regex=False)
        df_db['sort_key'] = df_db['ID PROVA'].str.extract(r'(\d+)').astype(float)
        df_db = df_db.sort_values(by=['PROCESSO', 'sort_key']).drop(columns=['sort_key']).reset_index(drop=True)

        return df_db, None
    except Exception as e:
        return pd.DataFrame(), f"Errore SQL: {str(e)}"

def render():
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("<h2 style='margin-bottom: 0px; color: #0f172a;'>Registro Prove Operative</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #64748b; font-size: 14px;'>Database relazionale. Seleziona una riga per accedere alle analitiche.</p>", unsafe_allow_html=True)
    with col2:
        st.write("")
        filtro_processo = st.radio("Filtra per Processo:", ["Tutte le Prove", "Pirolisi", "HTL/HTU"], horizontal=True, label_visibility="collapsed")
    
    # Esecuzione Fetch Dati
    df, error_msg = fetch_data()
    
    # --- GESTIONE ERRORI E DIAGNOSTICA ---
    if df.empty:
        diag = run_db_diagnostics()
        st.error("🚨 Impossibile caricare il Registro delle Prove.")
        
        with st.expander("🛠️ Pannello di Diagnostica Cloud (Apri per i dettagli)", expanded=True):
            st.markdown("### Analisi dell'Ambiente (Streamlit Cloud)")
            st.write(f"**1. Percorso Attuale (CWD):** `{diag['cwd']}`")
            
            if diag['db_exists']:
                st.success(f"**2. File Database:** Trovato (`{DB_PATH}`) | Dimensione: {diag['db_size_bytes']} bytes")
                if diag['is_empty']:
                    st.warning("**3. Stato Database:** Il file esiste ma sembra vuoto (nessuna tabella trovata). Forse Git LFS non l'ha caricato correttamente?")
                if diag['sql_error']:
                    st.error(f"**4. Errore SQLAlchemy:** {diag['sql_error']}")
            else:
                st.error(f"**2. File Database:** NON TROVATO. Il file `{DB_PATH}` non è presente in questa cartella.")
                st.write("**File visti dal server in questa cartella:**")
                st.code("\n".join(diag['files_in_cwd']))
                
            if error_msg:
                st.info(f"**Messaggio del Motore DataFetch:** {error_msg}")
                
        st.stop() # Blocca il rendering della pagina per evitare finti caricamenti
    # -------------------------------------

    if filtro_processo == "Pirolisi":
        df = df[df["PROCESSO"] == "Pirolisi"]
    elif filtro_processo == "HTL/HTU":
        df = df[df["PROCESSO"].isin(["HTL", "HTU"])]

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection('single', use_checkbox=False)
    gb.configure_default_column(editable=True, resizable=True, filter=True)
    grid_options = gb.build()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.VALUE_CHANGED,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
        theme='alpine',
        height=400
    )

    st.markdown("<br>", unsafe_allow_html=True)

    btn_col1, btn_col2 = st.columns(2)
    
    selected = grid_response['selected_rows']
    with btn_col1:
        if selected is not None and len(selected) > 0:
            row_data = selected.iloc[0] if isinstance(selected, pd.DataFrame) else selected[0]
            
            # Salvataggio in session_state per il Deep Dive
            st.session_state.selected_prova_id = row_data.get('ID PROVA')
            st.session_state.selected_processo = row_data.get('PROCESSO')
            st.session_state.selected_feed = row_data.get('FEEDSTOCK')
            
            if st.button(f"Apri Dettaglio Relazionale ({row_data.get('ID PROVA', '')})", type="primary"):
                show_context_drawer(row_data)
        else:
            st.button("Apri Dettaglio Relazionale", disabled=True)

    with btn_col2:
        if st.button("Salva modifiche su SQL", type="secondary"):
            st.warning("Funzione di edit inline disabilitata per sicurezza in cloud.")
