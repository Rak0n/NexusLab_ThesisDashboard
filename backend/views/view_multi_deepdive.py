import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

from engines import engine_multi_deepdive
from engines import engine_chnso
from engines import engine_gcms

# Importazione protetta per l'export
try:
    from engines import engine_report_export
except Exception as e:
    engine_report_export = None
    st.sidebar.error(f"⚠️ Attenzione: Motore Report non caricato ({e})")

from sqlalchemy import create_engine, text

def sort_logic_target_chnso(tid: str) -> tuple:
    tid_u = str(tid).upper()
    if tid_u.startswith("FS_") or "MIX" in tid_u:
        return (10, tid_u)
    if tid_u.endswith("_OIL"):
        return (20, tid_u)
    if tid_u.endswith("_BC"):
        return (30, tid_u)
    if tid_u.endswith("_AP"):
        return (35, tid_u)
    if tid_u.endswith("_CHAR"):
        return (40, tid_u)
    return (90, tid_u)

def sort_logic_target_gcms(tid: str) -> tuple:
    tid_u = str(tid).upper()
    if tid_u.endswith("_OIL"):
        return (10, tid_u)
    if tid_u.endswith("_BC"):
        return (20, tid_u)
    if tid_u.endswith("_AP"):
        return (30, tid_u)
    return (90, tid_u)

def enrich_mix_moisture_ash(df_chnso: pd.DataFrame) -> pd.DataFrame:
    if df_chnso.empty:
        return df_chnso

    df_out = df_chnso.copy()
    mix_rows = df_out['target_id'].astype(str).str.startswith('Mix (')
    if not mix_rows.any():
        return df_out

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

def draw_vk_connections(fig, df, x_col, y_col):
    edges = engine_chnso.get_lineage_edges()
    target_to_point = {row['target_id']: (row[x_col], row[y_col]) for _, row in df.iterrows()}
    
    for src, tgt in edges:
        if src in target_to_point and tgt in target_to_point:
            fig.add_trace(go.Scatter(
                x=[target_to_point[src][0], target_to_point[tgt][0]],
                y=[target_to_point[src][1], target_to_point[tgt][1]],
                mode='lines',
                line=dict(dash='dot', color='gray', width=1.5),
                showlegend=False,
                hoverinfo='skip'
            ))

def draw_vk_connections_mix(fig, df, x_col, y_col):
    edges = engine_chnso.get_lineage_edges()
    new_edges = set()
    target_to_point = {row['target_id']: (row[x_col], row[y_col]) for _, row in df.iterrows()}
    
    for src, tgt in edges:
        if src.startswith('FS_') and (tgt.endswith('_OIL') or tgt.endswith('_CHAR')):
            base_p = tgt.rsplit('_', 1)[0]
            
            # Cerca se esiste il mix esatto o un mix accorpato (es. Mix (P1, P2))
            mix_node = None
            exact_mix = f"Mix ({base_p})"
            if exact_mix in target_to_point:
                mix_node = exact_mix
            else:
                for t in target_to_point.keys():
                    if str(t).startswith('Mix ('):
                        m = re.search(r"Mix\s*\(([^)]+)\)", str(t))
                        if m:
                            parts = [p.strip() for p in m.group(1).split(',')]
                            if base_p in parts:
                                mix_node = t
                                break
            if mix_node:
                new_edges.add((mix_node, tgt))
        else:
            new_edges.add((src, tgt))

    for src, tgt in new_edges:
        if src in target_to_point and tgt in target_to_point:
            fig.add_trace(go.Scatter(
                x=[target_to_point[src][0], target_to_point[tgt][0]],
                y=[target_to_point[src][1], target_to_point[tgt][1]],
                mode='lines',
                line=dict(dash='dot', color='gray', width=1.5),
                showlegend=False,
                hoverinfo='skip'
            ))

def render():
    if 'prove_selezionate_per_confronto' not in st.session_state or not st.session_state.prove_selezionate_per_confronto:
        st.warning("Nessuna prova selezionata. Torna alla Mappa Navigazionale.")
        if st.button("⬅️ Torna alla Mappa"):
            st.session_state.current_view = "Map View"
            st.rerun()
        return

    trial_ids = st.session_state.prove_selezionate_per_confronto

    # --- HEADER E EXPORT ---
    c_back, c_title, c_export = st.columns([1, 7, 2])
    with c_back:
        if st.button("⬅️ Torna alla Mappa", use_container_width=True):
            st.session_state.current_view = "Map View"
            st.rerun()
    with c_title:
        st.markdown(f"<h2 style='margin-top: -10px; color: #0f172a;'>🔬 Multi-Deep Dive (Confronto)</h2>", unsafe_allow_html=True)
    with c_export:
        if st.button("📄 Genera Report", type="primary", use_container_width=True):
            if engine_report_export:
                engine_report_export.generate_multi_report(trial_ids)
            else:
                st.error("Il motore di export non è al momento disponibile.")

    # --- GRIGLIA METADATI SUPERIORE (RIPRISTINATA A NATIVA E STABILE) ---
    st.markdown("### 📋 Riepilogo Prove in Analisi")
    df_meta = engine_multi_deepdive.get_metadata_for_trials(trial_ids)
    if not df_meta.empty:
        st.dataframe(df_meta, hide_index=True, use_container_width=True)
    else:
        st.info("Nessun metadato disponibile per le prove selezionate.")

    st.markdown("<hr style='margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

    # ==========================================
    # SEZIONE 1: RESE DI PROCESSO
    # ==========================================
    with st.expander("⚖️ 1. Confronto Rese Massiche", expanded=True):
        df_piro, df_ht = engine_multi_deepdive.fetch_multi_yields(trial_ids)
        
        c_toggles1, c_toggles2 = st.columns(2)
        collassa_rese = c_toggles1.toggle("📊 Collassa Repliche in Media (con Std. Dev.)", value=True, key="tgl_rese_multi")
        stile_barre = c_toggles2.radio("Stile Grafico:", ["Affiancate (Group)", "Impilate (Stack)"], horizontal=True)
        barmode = 'group' if "Affiancate" in stile_barre else 'stack'
        
        c_piro, c_ht = st.columns(2)
        
        # Grafico Pirolisi
        with c_piro:
            if not df_piro.empty:
                st.markdown("#### Rese Pirolisi")
                fig_piro = go.Figure()
                y_cols_piro = ['Olio', 'Char', 'Gas']
                colors_piro = ['#ea580c', '#10b981', '#0ea5e9']
                
                if collassa_rese:
                    df_mean = df_piro.groupby('id_prova')[y_cols_piro].mean()
                    df_std = df_piro.groupby('id_prova')[y_cols_piro].std().fillna(0)
                    for idx, col in enumerate(y_cols_piro):
                        fig_piro.add_trace(go.Bar(
                            name=col, x=df_mean.index, y=df_mean[col],
                            error_y=dict(type='data', array=df_std[col], visible=True, thickness=1.5) if barmode == 'group' else None,
                            marker_color=colors_piro[idx]
                        ))
                else:
                    for idx, col in enumerate(y_cols_piro):
                        fig_piro.add_trace(go.Bar(
                            name=col, x=df_piro['id_run'], y=df_piro[col],
                            marker_color=colors_piro[idx]
                        ))
                        
                fig_piro.update_layout(
                    barmode=barmode,
                    yaxis_title="Resa (%)",
                    margin=dict(t=10),
                    height=420,
                    bargap=0.35,
                    bargroupgap=0.0
                )
                st.plotly_chart(fig_piro, use_container_width=True)
            else:
                st.info("Nessuna prova di Pirolisi.")

        # Grafico Idrotermali
        with c_ht:
            if not df_ht.empty:
                st.markdown("#### Rese Idrotermali (HTL/HTU)")
                fig_ht = go.Figure()
                y_cols_ht = ['Biocrude', 'Aqueous_Phase', 'Char', 'Gas']
                colors_ht = ['#ea580c', '#a855f7', '#10b981', '#0ea5e9']
                
                if collassa_rese:
                    df_mean = df_ht.groupby('id_prova')[y_cols_ht].mean()
                    df_std = df_ht.groupby('id_prova')[y_cols_ht].std().fillna(0)
                    for idx, col in enumerate(y_cols_ht):
                        fig_ht.add_trace(go.Bar(
                            name=col.replace('_', ' '), x=df_mean.index, y=df_mean[col],
                            error_y=dict(type='data', array=df_std[col], visible=True, thickness=1.5) if barmode == 'group' else None,
                            marker_color=colors_ht[idx]
                        ))
                else:
                    for idx, col in enumerate(y_cols_ht):
                        fig_ht.add_trace(go.Bar(
                            name=col.replace('_', ' '), x=df_ht['id_run'], y=df_ht[col],
                            marker_color=colors_ht[idx]
                        ))
                        
                fig_ht.update_layout(
                    barmode=barmode,
                    yaxis_title="Resa (%)",
                    margin=dict(t=10),
                    height=420,
                    bargap=0.35,
                    bargroupgap=0.0
                )
                st.plotly_chart(fig_ht, use_container_width=True)
            else:
                st.info("Nessuna prova Idrotermale.")

    # ==========================================
    # SEZIONE 2: CHNSO E VAN KREVELEN
    # ==========================================
    with st.expander("🟢 2. Confronto Elementare (CHNSO & Van Krevelen)", expanded=True):
        targets_chnso = []
        for tid in trial_ids:
            targets_chnso.extend([f"{tid}_OIL", f"{tid}_BC", f"{tid}_CHAR"])
            
        c_chnso1, c_chnso2 = st.columns(2)
        mostra_feed = c_chnso1.checkbox("Mostra i Feedstock originali unici", value=True)
        seleziona_mix = c_chnso2.checkbox("Calcola MIX teorici in base alle ricette", value=False)
        
        if mostra_feed:
            feed_ids = engine_multi_deepdive.get_feedstock_targets(trial_ids)
            targets_chnso.extend(feed_ids)
            
        targets_chnso = list(dict.fromkeys([str(t).upper() for t in targets_chnso if t]))
        df_chnso = engine_chnso.fetch_chnso_data(targets_chnso)
        
        if not df_chnso.empty:
            if seleziona_mix:
                df_chnso = engine_chnso.apply_theoretical_mix(df_chnso)
                df_chnso = enrich_mix_moisture_ash(df_chnso)
                
                # --- CHIRURGIA: Accorpamento Mix Identici ---
                mix_mask = df_chnso['target_id'].astype(str).str.startswith('Mix (')
                if mix_mask.any():
                    df_mixes = df_chnso[mix_mask].copy()
                    df_others = df_chnso[~mix_mask].copy()
                    
                    # Usiamo i valori elementali (arrotondati a 4 decimali) per trovare Mix identici
                    comp_cols = [c for c in ['c_mean', 'h_mean', 'n_mean', 's_mean', 'o_diff'] if c in df_mixes.columns]
                    if comp_cols:
                        df_mixes_rounded = df_mixes[comp_cols].astype(float).round(4).fillna(-999)
                        df_mixes['__grp'] = df_mixes_rounded.apply(tuple, axis=1)
                        
                        merged_mixes = []
                        for _, group in df_mixes.groupby('__grp'):
                            if len(group) > 1:
                                p_nums = []
                                for tid in group['target_id']:
                                    m = re.search(r"Mix\s*\(([^)]+)\)", str(tid))
                                    if m:
                                        p_nums.append(m.group(1))
                                # Crea il nuovo nome concatenato: es. Mix (P1, P2)
                                new_name = f"Mix ({', '.join(p_nums)})"
                                new_row = group.iloc[0].copy()
                                new_row['target_id'] = new_name
                                merged_mixes.append(new_row)
                            else:
                                merged_mixes.append(group.iloc[0])
                                
                        df_chnso = pd.concat([df_others, pd.DataFrame(merged_mixes)], ignore_index=True).drop(columns=['__grp'], errors='ignore')

            df_chnso = df_chnso.copy()
            df_chnso['__sort_key'] = df_chnso['target_id'].apply(sort_logic_target_chnso)
            df_chnso = df_chnso.sort_values(['__sort_key']).drop(columns=['__sort_key'])
            ordered_targets = df_chnso['target_id'].drop_duplicates().tolist()
                
            fig_stack = make_subplots(specs=[[{"secondary_y": True}]])
            elements = [('C', 'c_mean', '#4338ca'), ('H', 'h_mean', '#10b981'), ('N', 'n_mean', '#3b82f6'),
                        ('S', 's_mean', '#f59e0b'), ('O', 'o_diff', '#ef4444'),
                        ('Moisture', 'moisture', '#f472b6'), ('Ash', 'ash', '#64748b')]
                        
            for name, mean_col, color in elements:
                if mean_col in df_chnso.columns:
                    fig_stack.add_trace(go.Bar(name=name, x=df_chnso['target_id'], y=df_chnso[mean_col], marker_color=color), secondary_y=False)
                
            if 'hhv_stimato' in df_chnso.columns:
                fig_stack.add_trace(go.Scatter(
                    name='HHV (MJ/Kg)', x=df_chnso['target_id'], y=df_chnso['hhv_stimato'], 
                    mode='lines+markers', line=dict(dash='dash', color='black', width=2),
                    marker=dict(symbol='diamond', size=10, color='black')
                ), secondary_y=True)
            
            fig_stack.update_layout(
                barmode='stack', title="Composizione Massica e Potere Calorifico", 
                margin=dict(t=30, b=10), legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
                xaxis={'categoryorder':'array', 'categoryarray':ordered_targets},
                height=520,
                bargap=0.35,
                bargroupgap=0.12
            )
            fig_stack.update_yaxes(title_text="Frazione Massica (%)", secondary_y=False)
            fig_stack.update_yaxes(title_text="HHV (MJ/Kg)", secondary_y=True, showgrid=False)
            st.plotly_chart(fig_stack, use_container_width=True)

            # --- DIAGRAMMI VAN KREVELEN AFFIANCATI ---
            st.markdown("#### Diagrammi di Van Krevelen")
            
            df_vk = df_chnso.dropna(subset=['O/C', 'H/C']).copy()
            if not df_vk.empty:
                # Abbrevia i nomi dei Mix solo per il testo sul grafico (mantiene il nome intero per colore/legenda)
                df_vk['point_label'] = df_vk['target_id'].apply(lambda x: 'Mix' if str(x).startswith('Mix (') else x)
                
                cv1, cv2 = st.columns(2)
                
                with cv1:
                    fig_vk1 = px.scatter(df_vk, x='O/C', y='H/C', color='target_id', text='point_label', 
                                         size_max=14, title="Diagramma (O/C vs H/C)",
                                         category_orders={'target_id': ordered_targets})
                    fig_vk1.update_traces(textposition='top center', marker=dict(size=12, line=dict(width=1, color='DarkSlateGrey')))
                    fig_vk1.update_layout(height=520)
                    fig_vk1.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
                    fig_vk1.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
                    if seleziona_mix:
                        draw_vk_connections_mix(fig_vk1, df_vk, 'O/C', 'H/C')
                    else:
                        draw_vk_connections(fig_vk1, df_vk, 'O/C', 'H/C')
                    st.plotly_chart(fig_vk1, use_container_width=True)
                    
                with cv2:
                    if 'N/C' in df_vk.columns:
                        fig_vk2 = px.scatter(df_vk, x='N/C', y='H/C', color='target_id', text='point_label', 
                                             size_max=14, title="Diagramma (N/C vs H/C)",
                                             category_orders={'target_id': ordered_targets})
                        fig_vk2.update_traces(textposition='top center', marker=dict(size=12, line=dict(width=1, color='DarkSlateGrey')))
                        fig_vk2.update_layout(height=520)
                        fig_vk2.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
                        fig_vk2.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
                        if seleziona_mix:
                            draw_vk_connections_mix(fig_vk2, df_vk, 'N/C', 'H/C')
                        else:
                            draw_vk_connections(fig_vk2, df_vk, 'N/C', 'H/C')
                        st.plotly_chart(fig_vk2, use_container_width=True)
            else:
                st.info("Dati atomici (O/C, H/C) insufficienti per tracciare i Van Krevelen.")
        else:
            st.warning("Nessun dato CHNSO presente per questa selezione.")

    # ==========================================
    # SEZIONE 3: GC-MS E PIVOT
    # ==========================================
    with st.expander("🔴 3. Confronto Molecolare (GC-MS)", expanded=True):
        frazione_scelta = st.radio(
            "Seleziona la frazione da confrontare:",
            [
                "Olio Pirolitico / Biocrude (_OIL, _BC)",
                "Fase Acquosa HTL/HTU (_AP)",
                "Tutte le frazioni (_OIL, _BC, _AP)"
            ],
            horizontal=True
        )
        
        targets_gcms = []
        for tid in trial_ids:
            if "Tutte" in frazione_scelta:
                targets_gcms.extend([f"{tid}_OIL", f"{tid}_BC", f"{tid}_AP"])
            elif "Acquosa" in frazione_scelta:
                targets_gcms.append(f"{tid}_AP")
            else:
                targets_gcms.extend([f"{tid}_OIL", f"{tid}_BC"])

        targets_gcms = list(dict.fromkeys([str(t).upper() for t in targets_gcms if t]))
        ordered_targets_gcms = sorted(targets_gcms, key=sort_logic_target_gcms)

        df_gcms = engine_gcms.fetch_analytical_dataset(targets_gcms)
        
        if df_gcms.empty:
            st.warning("Nessun composto identificato in GC-MS per la frazione selezionata.")
        else:
            area_col = 'new_area_perc' if 'new_area_perc' in df_gcms.columns else 'original_area'
            present_targets = df_gcms['target_id'].dropna().drop_duplicates().astype(str).str.upper().tolist()
            ordered_targets_gcms = sorted(present_targets, key=sort_logic_target_gcms)

            c_bar, c_pivot = st.columns([1.15, 1.5])
            
            with c_bar:
                st.markdown("#### Composizione Macro-Famiglie")
                df_macro = df_gcms.groupby(['target_id', 'macro_class'])[area_col].sum().reset_index()
                df_macro = df_macro[df_macro[area_col] > 0]
                
                fig_macro = px.bar(df_macro, x='target_id', y=area_col, color='macro_class', 
                                   barmode='group', labels={area_col: 'Area %', 'target_id': 'Prova'},
                                   color_discrete_sequence=px.colors.qualitative.Safe,
                                   category_orders={'target_id': ordered_targets_gcms})
                fig_macro.update_xaxes(categoryorder='array', categoryarray=ordered_targets_gcms)
                fig_macro.update_layout(
                    height=285,
                    margin=dict(t=10),
                    bargap=0.35,
                    bargroupgap=0.0,
                    legend=dict(orientation="h", y=-0.3, x=0.5, xanchor="center")
                )
                st.plotly_chart(fig_macro, use_container_width=True)
                
                st.markdown("#### Composizione Classi Famiglie")
                df_class = df_gcms.groupby(['target_id', 'class_of_compounds'])[area_col].sum().reset_index()
                df_class = df_class[df_class[area_col] > 0]

                class_opts = sorted(df_class['class_of_compounds'].dropna().unique().tolist())
                palette = px.colors.qualitative.Dark24
                color_map = {c: palette[i % len(palette)] for i, c in enumerate(class_opts)}

                fig_class = px.bar(
                    df_class,
                    x='target_id',
                    y=area_col,
                    color='class_of_compounds',
                    barmode='group',
                    labels={'target_id': 'Prova', area_col: 'Area %', 'class_of_compounds': 'Classe'},
                    category_orders={'target_id': ordered_targets_gcms, 'class_of_compounds': class_opts},
                    color_discrete_map=color_map
                )
                fig_class.update_xaxes(categoryorder='array', categoryarray=ordered_targets_gcms)
                fig_class.update_layout(
                    height=285,
                    margin=dict(t=10),
                    bargap=0.35,
                    bargroupgap=0.0,
                    legend=dict(orientation="h", y=-0.35, x=0.5, xanchor="center")
                )
                st.plotly_chart(fig_class, use_container_width=True)
                
            with c_pivot:
                st.markdown("#### Tabella Comparativa Composti")
                st.caption("Aree % fianco a fianco. (Filtro base > 0.5%)")
                
                df_pivot = df_gcms.pivot_table(
                    index=['compound_name', 'class_of_compounds'], 
                    columns='target_id', 
                    values=area_col, 
                    aggfunc='sum'
                ).fillna(0).reset_index()
                
                df_pivot.columns.name = None
                
                colonne_dati = [c for c in df_pivot.columns if c not in ['compound_name', 'class_of_compounds']]
                if colonne_dati:
                    colonne_dati_sorted = sorted([c for c in colonne_dati if c.upper() in set(ordered_targets_gcms)], key=sort_logic_target_gcms)
                    df_pivot = df_pivot[['compound_name', 'class_of_compounds'] + colonne_dati_sorted]
                    colonne_dati = colonne_dati_sorted
                
                if colonne_dati:
                    df_pivot['max_val'] = df_pivot[colonne_dati].max(axis=1)
                    df_pivot = df_pivot[df_pivot['max_val'] >= 0.5].drop(columns=['max_val'])
                    df_pivot = df_pivot.sort_values(by=colonne_dati[0], ascending=False)
                    
                    # Arrotondamento matematico NATIVO
                    for col in colonne_dati:
                        df_pivot[col] = df_pivot[col].round(2)
                
                # Resettiamo l'indice in modo che sia un intero puro (0, 1, 2...)
                df_pivot = df_pivot.reset_index(drop=True)

                # Tabella barebones.
                st.dataframe(df_pivot, height=600)
