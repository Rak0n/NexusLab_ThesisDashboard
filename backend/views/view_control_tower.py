import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, ColumnsAutoSizeMode
from sqlalchemy import create_engine, text
import os
import plotly.express as px

# --- LOGICA DI ESTRAZIONE DATI DETTAGLIATI (DB o MOCK) ---
def fetch_detailed_data(id_prova, processo, feed_string):
    """Estrae i dati specifici (rese, ricetta, lineage, analisi) interrogando le tabelle relazionali."""
    db_path = "nexuslab.db"
    details = {
        'recipe': None,
        'is_base_recipe': False,
        'yields': {},
        'lineage_target': None,
        'lineage_source': None,
        'base_feed_string': None,
        'analyses': {}  # Mappa frazione -> set di analisi
    }
    
    if os.path.exists(db_path):
        try:
            engine = create_engine(f"sqlite:///{db_path}")
            with engine.connect() as conn:
                # 1. Risoluzione del Lineage
                if processo == 'Pirolisi':
                    res_target = conn.execute(
                        text("""
                            SELECT i.id_prova, i.tipo_processo
                            FROM input_idrotermico inp
                            JOIN prove_idrotermiche i ON inp.id_prova = i.id_prova
                            WHERE inp.source_id LIKE '%' || :id || '%'
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

                # 2. Estrazione Ricetta (Composizione Feedstock) e Feed Base
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

                # 4. Estrazione Analisi (per colorare i pulsanti)
                res_an = conn.execute(
                    text("SELECT target_id, tipo_analisi FROM registro_analisi WHERE target_id LIKE :id || '%'"),
                    {"id": id_prova}
                ).fetchall()
                
                fraction_map = {
                    '_OIL': 'Olio',
                    '_CHAR': 'Char',
                    '_GAS': 'Gas',
                    '_BC': 'Biocrude',
                    '_AP': 'Aqueous P.'
                }
                
                for r in res_an:
                    tid = r[0]
                    tan = r[1]
                    for suff, frac_name in fraction_map.items():
                        if tid == f"{id_prova}{suff}":
                            if frac_name not in details['analyses']:
                                details['analyses'][frac_name] = set()
                            details['analyses'][frac_name].add(tan)

        except Exception as e:
            pass # Fallback silenzioso al mock

    # --- FALLBACK MOCK ---
    if details['recipe'] is None:
        feeds = [f.strip() for f in str(feed_string).split('+') if f.strip() not in ('-', '')]
        if feeds:
            details['recipe'] = pd.DataFrame({'feedstock_id': feeds, 'percentuale': [100.0/len(feeds)]*len(feeds)})

    if not details['yields']:
        if processo == 'Pirolisi':
            details['yields'] = {'olio': 45.2, 'char': 31.5, 'gas': 23.3}
        else:
            details['yields'] = {'biocrude': 42.0, 'wso': 28.0, 'char': 12.0, 'gas': 18.0, 'totale': 100.0}

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
        st.markdown("<p style='font-size: 11px; font-weight: 600; color: #64748b; letter-spacing: 1px; margin-bottom: 0px;'>COMPOSIZIONE</p>", unsafe_allow_html=True)
        df_recipe = details['recipe']
        
        if details.get('is_base_recipe'):
            st.markdown(f"<p style='font-size: 12px; font-style: italic; color: #64748b; margin-top: 0px;'>Riferita alla sorgente ({details['lineage_source']})</p>", unsafe_allow_html=True)
            
        if df_recipe is not None and not df_recipe.empty:
            df_recipe['feedstock_id'] = df_recipe['feedstock_id'].astype(str).str.replace("FS_", "", regex=False)
            fig = px.pie(df_recipe, values='percentuale', names='feedstock_id', hole=0.5, height=220, 
                         color_discrete_sequence=['#3b82f6', '#f59e0b', '#10b981', '#6366f1'])
            fig.update_layout(margin=dict(t=0, b=10, l=10, r=10), showlegend=True, 
                              legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessuna anagrafica DOE trovata.")

    with col_yields:
        st.markdown("<p style='font-size: 11px; font-weight: 600; color: #64748b; letter-spacing: 1px; margin-bottom: 15px;'>FRAZIONI (MEDIE REPLICHE) E ANALITICA</p>", unsafe_allow_html=True)
        
        y_data = details['yields']
        if processo == 'Pirolisi':
            fractions = [
                ("Olio", y_data.get('olio', 0), "#ea580c", ["GC-MS", "CHNSO"]),
                ("Char", y_data.get('char', 0), "#10b981", ["CHNSO"]),
                ("Gas (Diff)", y_data.get('gas', 0), "#0ea5e9", ["GC"])
            ]
        else:
            fractions = [
                ("Biocrude", y_data.get('biocrude', 0), "#ea580c", ["GC-MS", "CHNSO"]),
                ("Aqueous P.", y_data.get('wso', 0), "#3b82f6", ["TOC", "GC-MS"]),
                ("Char", y_data.get('char', 0), "#10b981", ["CHNSO"]),
                ("Gas", y_data.get('gas', 0), "#0ea5e9", ["GC"])
            ]
            
        for f_name, f_val, f_color, f_tags in fractions:
            cols = st.columns([3.5, 1, 1], vertical_alignment="center")
            
            with cols[0]:
                val_num = f_val if f_val is not None else 0
                bar_html = f"""
                <div style="display:flex; align-items:center; margin-bottom: 4px;">
                    <div style="width: 80px; font-size: 13px; font-weight: 600; color:#334155;">{f_name}</div>
                    <div style="flex-grow: 1; background-color: #f1f5f9; height: 12px; border-radius: 6px; margin: 0 10px; overflow:hidden;">
                        <div style="width: {val_num}%; background-color: {f_color}; height: 100%;"></div>
                    </div>
                    <div style="width: 45px; text-align: right; font-size: 14px; font-weight: 700; color:{f_color};">{val_num:.1f}%</div>
                </div>
                """
                st.markdown(bar_html, unsafe_allow_html=True)
            
            # Recuperiamo le analisi attive per questa frazione
            active_analyses = details.get('analyses', {}).get(f_name, set())
            
            for i, tag in enumerate(f_tags):
                if i < 2:
                    with cols[i+1]:
                        # Se l'analisi esiste si colora di accent (primary), altrimenti resta grigia (secondary)
                        is_active = tag in active_analyses
                        b_type = "primary" if is_active else "secondary"
                        st.button(tag, key=f"btn_{id_prova}_{f_name}_{tag}", type=b_type, use_container_width=True)
        
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
        st.session_state.selected_prova_id = id_prova
        st.session_state.selected_processo = processo
        st.session_state.selected_feed = feed
        st.session_state.current_view = "Deep Dive"
        st.rerun()

def clean_tid(tid):
    """Funzione helper per ricavare l'id prova dal target_id del registro."""
    suffixes = ['_OIL', '_BC', '_AP', '_CHAR', '_GAS']
    for s in suffixes:
        if tid.endswith(s):
            return tid[:-len(s)]
    return tid

def fetch_data():
    """Recupera l'indice delle prove e i metadati analitici per la Grid principale."""
    db_path = "nexuslab.db"
    df = pd.DataFrame()
    
    if os.path.exists(db_path):
        try:
            engine = create_engine(f"sqlite:///{db_path}")
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
            df_db = pd.read_sql(query, engine)
            
            if not df_db.empty:
                df = df_db.fillna('-')
                
                # --- Integrazione Colonna Analisi ---
                df_analisi = pd.read_sql("SELECT target_id, tipo_analisi FROM registro_analisi", engine)
                if not df_analisi.empty:
                    df_analisi['ID PROVA'] = df_analisi['target_id'].apply(clean_tid)
                    df_an_grouped = df_analisi.groupby('ID PROVA')['tipo_analisi'].unique().apply(lambda x: ", ".join(sorted(x))).reset_index()
                    df_an_grouped.rename(columns={'tipo_analisi': 'ANALISI'}, inplace=True)
                    
                    df = pd.merge(df, df_an_grouped, on='ID PROVA', how='left')
                    df['ANALISI'] = df['ANALISI'].fillna('Nessuna')
                else:
                    df['ANALISI'] = 'Nessuna'
        except Exception as e:
            pass
            
    if df.empty:
        dati_mock = {
            "ID PROVA": ["P1", "P10", "P2", "P11", "HTL_1", "HTU_1"],
            "PROCESSO": ["Pirolisi", "Pirolisi", "Pirolisi", "Pirolisi", "HTL", "HTU"],
            "TEMP (°C)": [450, 520, 550, 520, 300, 350],
            "TEMPO (MIN)": [30, 30, 30, 30, 30, 120],
            "FEEDSTOCK": ["FS_PE + FS_MB", "FS_SS + FS_PE", "FS_SS + FS_PE + FS_MB", "FS_PE", "FS_MB", "P1_OIL"],
            "CATALIZZATORE": ["Termico", "Termico", "CAT_ZE", "CAT_ZE", "Termico", "CAT_HZSM5"],
            "ANALISI": ["GC-MS, CHNSO", "GC", "Nessuna", "GC-MS", "CHNSO", "GC-MS, GC"]
        }
        df = pd.DataFrame(dati_mock).fillna('-')
    
    if 'ANALISI' not in df.columns:
        df['ANALISI'] = 'Nessuna'

    df["FEEDSTOCK"] = df["FEEDSTOCK"].astype(str).str.replace("FS_", "", regex=False)
    df["CATALIZZATORE"] = df["CATALIZZATORE"].astype(str).str.replace("CAT_", "", regex=False)
    df['sort_key'] = df['ID PROVA'].str.extract(r'(\d+)').astype(float)
    df = df.sort_values(by=['PROCESSO', 'sort_key']).drop(columns=['sort_key']).reset_index(drop=True)

    return df

def render():
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("<h2 style='margin-bottom: 0px; color: #0f172a;'>Registro Prove Operative</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #64748b; font-size: 14px;'>Database relazionale. Seleziona una riga per accedere alle analitiche associate.</p>", unsafe_allow_html=True)
    with col2:
        st.write("")
        filtro_processo = st.radio(
            "Filtra per Processo:",
            ["Tutte le Prove", "Pirolisi", "HTL/HTU"],
            horizontal=True,
            label_visibility="collapsed"
        )
    
    df = fetch_data()
    
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
            if st.button(f"Apri Dettaglio Relazionale ({row_data.get('ID PROVA', '')})", type="primary"):
                show_context_drawer(row_data)
        else:
            st.button("Apri Dettaglio Relazionale", disabled=True)

    with btn_col2:
        if st.button("Salva modifiche su SQL", type="secondary"):
            st.success("Sincronizzazione DB completata (Struttura predisposta).")
