import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from engines import engine_chnso
from sqlalchemy import create_engine, text

def get_associated_prova(target_id):
    target_id = target_id.strip().upper()
    if target_id.startswith('FS_'): return "Anagrafica Feedstock"
    if target_id.endswith('_OIL'): return target_id.replace('_OIL', '')
    elif target_id.endswith('_BC') or target_id.endswith('_AP'): return target_id.rsplit('_', 1)[0]
    elif target_id.endswith('_CHAR'): return target_id.rsplit('_', 1)[0]
    return "Sconosciuta"

def get_mix_percentages(target_selezionati):
    """Trova le percentuali dei feed nei mix se la prova madre di Pirolisi è tra i selezionati."""
    mix_map = {}
    piro_tests = [t.replace('_OIL', '') for t in target_selezionati if t.endswith('_OIL')]
    if not piro_tests:
        return mix_map
        
    try:
        engine = create_engine(f"sqlite:///{engine_chnso.DB_PATH}")
        with engine.connect() as conn:
            for pt in piro_tests:
                recipes = conn.execute(text("SELECT feedstock_id, percentuale FROM pirolisi_ricetta WHERE id_prova=:id"), {"id": pt}).fetchall()
                for r in recipes:
                    fid = r[0]
                    perc = r[1]
                    if fid in target_selezionati:
                        if fid in mix_map:
                            mix_map[fid] += f" | {perc}%"
                        else:
                            mix_map[fid] = f"{perc}%"
    except Exception:
        pass
    return mix_map

def draw_van_krevelen_lines(fig, df_plot, x_col, y_col, valuta_mix):
    """Traccia le linee nel diagramma di Van Krevelen collegando solo i punti legati da un lineage relazionale."""
    edges = engine_chnso.get_lineage_edges()
    
    if valuta_mix:
        new_edges = set()
        for src, tgt in edges:
            if src.startswith('FS_') and tgt.endswith('_OIL'):
                base_p = tgt.replace('_OIL', '')
                new_edges.add((f"Mix ({base_p})", tgt))
            elif src.startswith('FS_') and tgt.endswith('_CHAR'):
                base_p = tgt.replace('_CHAR', '')
                new_edges.add((f"Mix ({base_p})", tgt))
            else:
                new_edges.add((src, tgt))
        edges = list(new_edges)

    target_to_point = {row['target_id']: (row[x_col], row[y_col]) for _, row in df_plot.iterrows()}

    for src, tgt in edges:
        if src in target_to_point and tgt in target_to_point:
            fig.add_trace(go.Scatter(
                x=[target_to_point[src][0], target_to_point[tgt][0]],
                y=[target_to_point[src][1], target_to_point[tgt][1]],
                mode='lines', line=dict(dash='dot', color='gray', width=1.5),
                showlegend=False, hoverinfo='skip'
            ))

def render():
    st.title("🟢 Spettrometria CHNSO (Analisi Elementare)")
    st.markdown("Ingestione, composizione elementare, poteri calorifici e diagrammi di Van Krevelen.")
    
    # ==========================================
    # 0. MOTORE DI SELEZIONE GLOBALE
    # ==========================================
    with st.expander("🔍 Motore di Selezione Prove (Filtri a Cascata)", expanded=True):
        df_meta = engine_chnso.get_targets_metadata()
        lineage_sets = engine_chnso.get_lineage_sets()
        target_selezionati = []
        valuta_mix = False
        
        if not df_meta.empty:
            tipo_proc = st.radio("Filtra per Categoria Processo:", ["Tutti", "Feedstock", "Pirolisi", "HTL/HTU"], horizontal=True)
            
            c1, c2, c3 = st.columns(3)
            
            df_filtered = df_meta.copy()
            if tipo_proc == "Feedstock": df_filtered = df_filtered[df_filtered['Processo'] == 'Feedstock']
            elif tipo_proc == "Pirolisi": df_filtered = df_filtered[df_filtered['Processo'] == 'Pirolisi']
            elif tipo_proc == "HTL/HTU": df_filtered = df_filtered[~df_filtered['Processo'].isin(['Pirolisi', 'Feedstock'])]
            
            temp_opts = sorted(df_filtered['Temperatura'].dropna().unique().tolist())
            sel_temp = c1.multiselect("🌡️ Temperatura (°C)", temp_opts)
            if sel_temp: df_filtered = df_filtered[df_filtered['Temperatura'].isin(sel_temp)]
            
            feed_opts = sorted(df_filtered['Feedstock'].unique().tolist())
            sel_feed = c2.multiselect("📦 Feedstock / Source", feed_opts)
            if sel_feed: df_filtered = df_filtered[df_filtered['Feedstock'].isin(sel_feed)]
            
            sel_sets = c3.multiselect("📚 Set di Prove (Lineage completo)", list(lineage_sets.keys()))
            targets_da_set = []
            for s in sel_sets: targets_da_set.extend(lineage_sets[s])
            
            st.divider()
            
            target_opts = sorted(df_filtered['target_id'].unique().tolist())
            sel_manual = st.multiselect("🧪 Selezione Manuale Prove (Incrociate coi Filtri):", target_opts, default=None)
            
            target_selezionati = list(set(sel_manual + targets_da_set))
            
            if target_selezionati:
                st.success(f"Prove attive: {', '.join(target_selezionati)}")
                
                # --- GRID RIASSUNTIVA DELLE PROVE SOTTO I FILTRI ---
                st.markdown("#### 📋 Riepilogo Prove Selezionate")
                df_summary = df_meta[df_meta['target_id'].isin(target_selezionati)].copy()
                
                # Ordine Logico anche per la tabella (Feed -> P -> HTL/HTU -> AP -> CHAR)
                def sort_logic_meta(tid):
                    tid = str(tid).upper()
                    if tid.startswith("FS_") or "MIX" in tid: return 10
                    if tid.endswith("_OIL"): return 20
                    if tid.endswith("_BC"): return 30
                    if tid.endswith("_AP"): return 40
                    if tid.endswith("_CHAR"): return 50
                    return 60
                    
                df_summary['sort_order'] = df_summary['target_id'].apply(sort_logic_meta)
                df_summary = df_summary.sort_values(['sort_order', 'target_id'])
                
                # Calcolo della Resa/Mix %
                mix_map = get_mix_percentages(target_selezionati)
                resa_mix = []
                for _, row in df_summary.iterrows():
                    tid = row['target_id']
                    resa = row['Resa Olio/Biocrude (%)']
                    
                    if tid.startswith('FS_'):
                        if tid in mix_map:
                            resa_mix.append(mix_map[tid])
                        else:
                            resa_mix.append("-")
                    else:
                        resa_mix.append(f"{resa}%" if pd.notnull(resa) else "-")
                        
                df_summary['Resa / % Mix'] = resa_mix
                
                st.dataframe(
                    df_summary[['target_id', 'Processo', 'Feedstock', 'Temperatura', 'Tempo', 'Catalizzatore', 'Resa / % Mix']],
                    use_container_width=True,
                    hide_index=True
                )
                
                valuta_mix = st.toggle("🧪 Valuta Mix (Collassa le ricette nei Grafici calcolando le medie pesate)", value=False)
        else:
            st.warning("Nessun dato nel database. Esegui un'ingestione.")
    
    # Preparazione e Ordinamento Dati per Grafici
    df_plot = engine_chnso.fetch_chnso_data(target_selezionati)
    if valuta_mix and not df_plot.empty:
        df_plot = engine_chnso.apply_theoretical_mix(df_plot)
        
    ordered_targets = []
    if not df_plot.empty:
        def sort_logic_plot(tid):
            tid = str(tid).upper()
            if tid.startswith("FS_") or "MIX" in tid: return 10
            if tid.endswith("_OIL"): return 20
            if tid.endswith("_BC"): return 30
            if tid.endswith("_AP"): return 40
            if tid.endswith("_CHAR"): return 50
            return 60
        df_plot['sort_order'] = df_plot['target_id'].apply(sort_logic_plot)
        df_plot = df_plot.sort_values(['sort_order', 'target_id'])
        ordered_targets = df_plot['target_id'].drop_duplicates().tolist() 

    # ==========================================
    # HEADER E TABS
    # ==========================================
    tab_ing, tab_comp, tab_vk = st.tabs(["📥 Ingestione Dati", "📊 Composizione e HHV", "💧 Van Krevelen"])
    
    # ==========================================
    # TAB 1: INGESTIONE DATI
    # ==========================================
    with tab_ing:
        st.subheader("Caricamento File CHNSO (Dati Grezzi)")
        st.info("💡 L'engine legge il foglio `1 - Raw Data`, media le repliche con Dev. Std., e permette la correzione O% con l'inserimento di Moisture/Ash.")
        
        uploaded_file = st.file_uploader("Trascina qui il file .xlsx raw", type=["xlsx"])
        
        if uploaded_file is not None:
            st.markdown("---")
            res = engine_chnso.parse_chnso_excel(uploaded_file)
            
            if "error" in res:
                st.error(res["error"])
            else:
                df_data = res["data"]
                st.success(f"Dati elaborati! Trovati **{len(df_data)}** campioni unici.")
                
                for idx, row in df_data.iterrows():
                    sample_name = str(row['Name'])
                    with st.expander(f"🧪 Campione Mediano Rilevato: {sample_name}", expanded=True):
                        col_dati, col_inject = st.columns([1.5, 1])
                        
                        with col_dati:
                            st.markdown(f"**C:** `{row['C_mean']:.2f} ± {row['C_std']:.2f}%` | **H:** `{row['H_mean']:.2f} ± {row['H_std']:.2f}%`")
                            st.markdown(f"**N:** `{row['N_mean']:.2f} ± {row['N_std']:.2f}%` | **S:** `{row['S_mean']:.2f} ± {row['S_std']:.2f}%`")
                            
                            st.divider()
                            
                            ignore_s = False
                            if row['S_mean'] > 0:
                                st.warning(f"⚠️ Zolfo rilevato: {row['S_mean']:.2f}%.")
                                ignore_s = st.checkbox("Trascura Zolfo (Forza a 0 per O_diff)", value=False, key=f"ign_s_{idx}")
                            
                            moisture = 0.0
                            ash = 0.0
                            use_moist_ash = st.checkbox("Inserisci manualmente Moisture e Ash", value=False, key=f"chk_ma_{idx}")
                            
                            if use_moist_ash:
                                m_col1, m_col2 = st.columns(2)
                                moisture = m_col1.number_input("Moisture (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key=f"m_{idx}")
                                ash = m_col2.number_input("Ash (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key=f"a_{idx}")
                            
                            s_sim = 0.0 if ignore_s else row['S_mean']
                            o_sim = max(0.0, 100.0 - row['C_mean'] - row['H_mean'] - row['N_mean'] - s_sim - moisture - ash)
                            hhv_sim = max(0.0, 0.3491 * row['C_mean'] + 1.1783 * row['H_mean'] + 0.1005 * s_sim - 0.1034 * o_sim - 0.0151 * row['N_mean'])
                            
                            st.markdown(f"💡 **Anteprima O (diff):** `{o_sim:.2f}%` | **HHV Stimato:** `{hhv_sim:.2f} MJ/Kg`")
                            
                        with col_inject:
                            target_id_input = st.text_input("Assegna Target ID esatto:", value=sample_name.upper(), placeholder="Es: FS_PE", key=f"target_{idx}").upper()
                            
                            if target_id_input:
                                is_valid, msg = engine_chnso.validate_target_id(target_id_input)
                                if is_valid: st.caption(f"🔗 Base: **{get_associated_prova(target_id_input)}**")
                                else: st.caption(f"🚫 {msg}")
                                
                            esiste_gia = engine_chnso.check_existing_target(target_id_input)
                            sovrascrivi = False
                            if esiste_gia:
                                st.warning("⚠️ Dati già presenti in SQL.")
                                sovrascrivi = st.checkbox("Conferma sovrascrittura", key=f"check_{idx}")
                            
                            if st.button("💾 Salva in SQL", key=f"btn_{idx}", type="primary", use_container_width=True):
                                if not is_valid: st.error("Target ID non valido.")
                                elif esiste_gia and not sovrascrivi: st.error("Spunta per sovrascrivere.")
                                else:
                                    success, m = engine_chnso.inject_chnso_to_db(target_id_input, row, moisture=moisture, ash=ash, ignore_s=ignore_s, overwrite=sovrascrivi)
                                    if success:
                                        st.success(m)
                                        st.rerun()
                                    else: st.error(m)

    # ==========================================
    # TAB 2: COMPOSIZIONE E HHV
    # ==========================================
    with tab_comp:
        st.subheader("📊 Analisi Composizione e Potere Calorifico")
        if df_plot.empty:
            st.warning("Nessun dato o selezione mancante.")
        else:
            fig_grp = go.Figure()
            elements = [
                ('Carbonio (C)', 'c_mean', 'c_std', '#4338ca'), 
                ('Idrogeno (H)', 'h_mean', 'h_std', '#10b981'), 
                ('Azoto (N)', 'n_mean', 'n_std', '#3b82f6'), 
                ('Zolfo (S)', 's_mean', 's_std', '#f59e0b'), 
                ('Ossigeno (O_diff)', 'o_diff', None, '#ef4444')
            ]
            
            for name, mean_col, std_col, color in elements:
                error_y = dict(type='data', array=df_plot[std_col], visible=True) if std_col else None
                fig_grp.add_trace(go.Bar(
                    name=name, x=df_plot['target_id'], y=df_plot[mean_col],
                    error_y=error_y, marker_color=color
                ))
                
            fig_grp.update_layout(
                barmode='group', 
                title="Composizione Elementare Assoluta con Dev. Standard",
                yaxis_title="Percentuale in Massa (%)", 
                xaxis_title="Prova"
            )
            fig_grp.update_xaxes(categoryorder='array', categoryarray=ordered_targets)
            st.plotly_chart(fig_grp, use_container_width=True)

            st.divider()

            fig_stack = make_subplots(specs=[[{"secondary_y": True}]])
            
            for name, mean_col, _, color in elements:
                fig_stack.add_trace(go.Bar(name=name, x=df_plot['target_id'], y=df_plot[mean_col], marker_color=color, opacity=0.85), secondary_y=False)
                
            fig_stack.add_trace(go.Scatter(
                name='HHV (MJ/Kg)', x=df_plot['target_id'], y=df_plot['hhv_stimato'], 
                mode='lines+markers', line=dict(dash='dash', color='black', width=2),
                marker=dict(size=12, symbol='diamond', color='#27272a', line=dict(width=1, color='white'))
            ), secondary_y=True)
            
            fig_stack.update_layout(
                barmode='stack', 
                title="Bilancio Elementare Complessivo e Andamento HHV",
                legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center")
            )
            fig_stack.update_yaxes(title_text="Frazione Massica (%)", secondary_y=False)
            fig_stack.update_yaxes(title_text="HHV (MJ/Kg)", secondary_y=True, showgrid=False)
            fig_stack.update_xaxes(categoryorder='array', categoryarray=ordered_targets)
            st.plotly_chart(fig_stack, use_container_width=True)

    # ==========================================
    # TAB 3: VAN KREVELEN
    # ==========================================
    with tab_vk:
        st.subheader("💧 Diagrammi di Van Krevelen (Evoluzione del Lineage)")
        if df_plot.empty:
            st.warning("Nessun dato selezionato.")
        else:
            c1, c2 = st.columns(2)
            
            with c1:
                fig_vk1 = px.scatter(df_plot, x='O/C', y='H/C', color='target_id', text='target_id', 
                                     size_max=14, title="Diagramma Principale (O/C vs H/C)",
                                     category_orders={'target_id': ordered_targets})
                fig_vk1.update_traces(textposition='top center', marker=dict(size=12, line=dict(width=1, color='DarkSlateGrey')))
                draw_van_krevelen_lines(fig_vk1, df_plot, 'O/C', 'H/C', valuta_mix)
                st.plotly_chart(fig_vk1, use_container_width=True)
                
            with c2:
                fig_vk2 = px.scatter(df_plot, x='N/C', y='H/C', color='target_id', text='target_id', 
                                     size_max=14, title="Diagramma Ausiliario (N/C vs H/C)",
                                     category_orders={'target_id': ordered_targets})
                fig_vk2.update_traces(textposition='top center', marker=dict(size=12, line=dict(width=1, color='DarkSlateGrey')))
                draw_van_krevelen_lines(fig_vk2, df_plot, 'N/C', 'H/C', valuta_mix)
                st.plotly_chart(fig_vk2, use_container_width=True)
                
            st.info("💡 I punti sono legati fra loro **soltanto** se condividono lo stesso Lineage di Processo (es. Feed ➔ Olio ➔ Biocrude). Le linee in parallelo indicano ricette composte da più feed.")
