import streamlit as st
import pandas as pd
import plotly.express as px
from engines import engine_gcms
import os

try:
    from rdkit import Chem
    from rdkit.Chem import Draw
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

try:
    import pubchempy as pcp
    PUBCHEM_AVAILABLE = True
except ImportError:
    PUBCHEM_AVAILABLE = False

def fetch_smiles_from_pubchem(compound_name):
    """Chiamata HTTP diretta senza cache."""
    if not PUBCHEM_AVAILABLE: return None
    try:
        c = pcp.get_compounds(compound_name, 'name')
        if c and c[0].isomeric_smiles: return c[0].isomeric_smiles
    except: pass
    return None

def get_associated_prova(target_id):
    target_id = target_id.strip().upper()
    if target_id.endswith('_OIL'): return target_id.replace('_OIL', '')
    elif target_id.endswith('_BC') or target_id.endswith('_AP'): return target_id.rsplit('_', 1)[0]
    return "Sconosciuta"

def render():
    st.title("🔴 Spettrometria di Massa (GC-MS)")
    st.markdown("Analisi molecolare, classificazione famiglie e tracciamento marker.")

    # 1. Caricamento globale Dati (Ottimizzazione: scarica tutto una volta)
    df_meta = engine_gcms.get_targets_metadata()
    df_analytical_all = engine_gcms.fetch_analytical_dataset(None)
    
    if not df_analytical_all.empty and not df_meta.empty:
        df_analytical_all = pd.merge(df_analytical_all, df_meta[['target_id', 'Processo', 'Feedstock', 'Temperatura']], on='target_id', how='left')

    # ==========================================
    # 0. MOTORE DI SELEZIONE GLOBALE
    # ==========================================
    with st.expander("🔍 Motore di Selezione Prove (Filtri a Cascata)", expanded=True):
        lineage_sets = engine_gcms.get_lineage_sets()
        target_selezionati = []
        
        if not df_meta.empty:
            tipo_proc = st.radio("Filtra per Categoria Processo:", ["Tutti", "Pirolisi", "HTL/HTU"], horizontal=True)
            
            c1, c2, c3 = st.columns(3)
            
            df_filtered = df_meta.copy()
            if tipo_proc == "Pirolisi":
                df_filtered = df_filtered[df_filtered['Processo'] == 'Pirolisi']
            elif tipo_proc == "HTL/HTU":
                df_filtered = df_filtered[df_filtered['Processo'] != 'Pirolisi']
            
            temp_opts = sorted(df_filtered['Temperatura'].dropna().unique().tolist())
            sel_temp = c1.multiselect("🌡️ Temperatura (°C)", temp_opts)
            if sel_temp: df_filtered = df_filtered[df_filtered['Temperatura'].isin(sel_temp)]
            
            feed_opts = sorted(df_filtered['Feedstock'].unique().tolist())
            sel_feed = c2.multiselect("📦 Feedstock / Source", feed_opts)
            if sel_feed: df_filtered = df_filtered[df_filtered['Feedstock'].isin(sel_feed)]
            
            sel_sets = c3.multiselect("📚 Set di Prove (Lineage)", list(lineage_sets.keys()))
            targets_da_set = []
            for s in sel_sets: targets_da_set.extend(lineage_sets[s])
            
            st.divider()
            
            target_opts = sorted(df_filtered['target_id'].unique().tolist())
            sel_manual = st.multiselect("🧪 Selezione Manuale Prove (Incrociate coi Filtri):", target_opts, default=None)
            
            target_selezionati = list(set(sel_manual + targets_da_set))
            if target_selezionati:
                st.success(f"Prove attive per le schede: {', '.join(target_selezionati)}")
                
                st.markdown("#### Riepilogo Prove Selezionate")
                df_summary = df_meta[df_meta['target_id'].isin(target_selezionati)].copy()
                st.dataframe(
                    df_summary[['target_id', 'Processo', 'Feedstock', 'Temperatura', 'Tempo', 'Catalizzatore', 'Resa Olio/Biocrude (%)']],
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.warning("Nessun dato nel database. Esegui un'ingestione.")
    
    # Slicer per i dati selezionati
    df_selected = pd.DataFrame()
    if not df_analytical_all.empty and target_selezionati:
        df_selected = df_analytical_all[df_analytical_all['target_id'].isin(target_selezionati)].copy()

    # ==========================================
    # HEADER E TABS
    # ==========================================
    tab_ing, tab_comp, tab_val, tab_mark, tab_note = st.tabs([
        "📥 Ingestione Dati", 
        "📊 Confronto Dinamico", 
        "💎 Molecole Valorizzabili", 
        "🧬 Ricerca Globale & Marker",
        "📝 Note"
    ])
    
    # ==========================================
    # TAB 1: INGESTIONE DATI
    # ==========================================
    with tab_ing:
        col_upload, col_settings = st.columns([2, 1])
        with col_settings:
            st.info("⚙️ **Impostazioni di Filtro**")
            match_threshold = st.slider("Soglia Minima Match Factor:", min_value=0, max_value=100, value=80, step=5)
            
        with col_upload:
            uploaded_file = st.file_uploader("Trascina qui il file .xlsx esportato dallo strumento", type=["xlsx"])
            
        if uploaded_file is not None:
            st.markdown("---")
            dict_sheets = engine_gcms.parse_gcms_excel(uploaded_file, match_threshold)
            
            if "error" in dict_sheets:
                st.error(f"Errore durante la lettura: {dict_sheets['error']}")
            else:
                for sheet_name, df_processed in dict_sheets.items():
                    if df_processed.empty: continue
                        
                    with st.expander(f"📄 Foglio: {sheet_name} ({len(df_processed)} composti)", expanded=True):
                        col_preview, col_inject = st.columns([2, 1])
                        with col_preview:
                            st.dataframe(df_processed[['Component RT', 'Compound Name', 'Match Factor', 'New Area %']].head(5), use_container_width=True)
                        with col_inject:
                            target_id_input = st.text_input("Assegna il Target ID esatto:", value=sheet_name.upper(), placeholder="Es: P5_OIL", key=f"target_{sheet_name}").upper()
                            
                            if target_id_input:
                                is_valid, msg_val = engine_gcms.validate_target_id(target_id_input)
                                if is_valid: st.success(f"🔗 Prova: **{get_associated_prova(target_id_input)}**")
                                else: st.error(f"🚫 {msg_val}")

                            esiste_gia = engine_gcms.check_existing_target(target_id_input)
                            sovrascrivi = False
                            if esiste_gia:
                                st.warning(f"⚠️ Dati già presenti.")
                                sovrascrivi = st.checkbox("Conferma sovrascrittura", key=f"check_{sheet_name}")
                            
                            if st.button("💾 Iniettare in SQL", key=f"btn_save_{sheet_name}", type="primary", use_container_width=True):
                                if not is_valid: st.error("🚫 Target non valido.")
                                elif esiste_gia and not sovrascrivi: st.error("⚠️ Spunta per sovrascrivere.")
                                else:
                                    if PUBCHEM_AVAILABLE:
                                        st.info("🔍 Interrogazione PubChem in corso per Formula e Peso...")
                                        formulas, pesi = [], []
                                        for idx, row in df_processed.iterrows():
                                            try:
                                                c = pcp.get_compounds(row['Compound Name'], 'name')
                                                formulas.append(c[0].molecular_formula if c else None)
                                                pesi.append(c[0].molecular_weight if c else None)
                                            except:
                                                formulas.append(None); pesi.append(None)
                                        df_processed['Formula Bruta'] = formulas
                                        df_processed['Peso Molecolare'] = pesi

                                    success, msg = engine_gcms.inject_gcms_to_db(target_id_input, df_processed, overwrite=sovrascrivi)
                                    if success:
                                        st.success(msg)
                                        st.rerun() 
                                    else: st.error(msg)

    # ==========================================
    # TAB 2: CONFRONTO DINAMICO
    # ==========================================
    with tab_comp:
        st.subheader("📊 Confronto Multi-Prova sulle Macro-Famiglie")
        if not target_selezionati:
            st.warning("Seleziona almeno una prova dal filtro in alto.")
        elif df_selected.empty:
            st.error("Nessun dato analitico trovato per le prove selezionate.")
        else:
            normalize = st.toggle("Normalizza al 100% (Relativo)", value=True)
            y_col = 'normalized_area' if normalize else 'original_area'
            y_title = 'Area Relativa (%)' if normalize else 'Area % Originale'

            df_macro = df_selected.groupby(['target_id', 'macro_class'])[y_col].sum().reset_index()
            fig_macro = px.bar(df_macro, x='target_id', y=y_col, color='macro_class', barmode='group',
                               title="Composizione per Macro-Classi (Contaminanti Esclusi)",
                               labels={'target_id': 'Prova', y_col: y_title, 'macro_class': 'Macro Famiglia'},
                               color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_macro, use_container_width=True)

            st.divider()

            st.markdown("#### 🔬 Drill-Down Sotto-famiglie")
            macro_opts = sorted(df_selected['macro_class'].unique().tolist())
            macro_sel = st.selectbox("Esplora in dettaglio la Macro-Classe:", macro_opts)
            
            df_drill = df_selected[df_selected['macro_class'] == macro_sel]
            df_class = df_drill.groupby(['target_id', 'class_of_compounds'])[y_col].sum().reset_index()
            fig_drill = px.bar(df_class, x='target_id', y=y_col, color='class_of_compounds', barmode='group',
                               title=f"Dettaglio interno a: {macro_sel}",
                               labels={'target_id': 'Prova', y_col: y_title, 'class_of_compounds': 'Classe di Composti'},
                               color_discrete_sequence=px.colors.qualitative.Vivid)
            st.plotly_chart(fig_drill, use_container_width=True)

    # ==========================================
    # TAB 3: MOLECOLE VALORIZZABILI
    # ==========================================
    with tab_val:
        st.subheader("💎 Faretto sui Platform Chemicals")
        if not target_selezionati:
            st.warning("Seleziona una prova dal filtro in alto.")
        elif df_selected.empty:
            st.error("Nessun dato trovato.")
        else:
            df_valuable = df_selected[(df_selected['is_valuable'] == 1) | (df_selected['is_valuable'] == 'Si') | (df_selected['compound_name'].str.contains('phenol|cyclopentanone|alcohol', case=False, na=False))].copy()
            
            if not df_valuable.empty:
                df_val_grp = df_valuable.groupby(['target_id', 'compound_name'])['normalized_area'].sum().reset_index()
                fig_val = px.bar(df_val_grp, x='target_id', y='normalized_area', color='compound_name', barmode='group',
                                 title="Confronto Molecole a Valore Aggiunto tra le Prove",
                                 labels={'target_id': 'Prova', 'normalized_area': 'Area Normalizzata %', 'compound_name': 'Composto'},
                                 color_discrete_sequence=px.colors.qualitative.Set2)
                st.plotly_chart(fig_val, use_container_width=True)
            else:
                st.info("Nessuna molecola valorizzabile identificata per queste prove.")

            st.divider()
            
            st.markdown("#### 🔎 Classifica Globale per Composto Valorizzabile")
            all_val_comps = engine_gcms.get_all_valuable_compounds()
            sel_search_comps = st.multiselect("Scegli uno o più composti per vederne la classifica in TUTTO il database:", all_val_comps)
            if sel_search_comps:
                df_ranking = engine_gcms.get_compound_ranking(sel_search_comps)
                if not df_ranking.empty:
                    st.dataframe(
                        df_ranking[['compound_name', 'target_id', 'new_area_perc', 'Processo', 'Feedstock', 'Temperatura']].rename(columns={
                            'compound_name': 'Composto', 'target_id': 'Prova (Target)', 'new_area_perc': 'Area % Originale'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.warning("Nessun dato trovato per questi composti.")

            st.divider()

            st.markdown("#### 🔬 Analitica di Dettaglio (Senza Contaminanti)")
            selected_grid_target = st.selectbox("Seleziona la prova specifica di cui vedere la tabella dettagliata:", target_selezionati)
            df_grid = df_selected[df_selected['target_id'] == selected_grid_target]
            
            display_cols = ['retention_time', 'compound_name', 'formula_bruta', 'original_area', 'normalized_area', 'macro_class', 'class_of_compounds']
            
            event = st.dataframe(
                df_grid[display_cols].rename(columns={
                    'retention_time': 'RT', 'compound_name': 'Composto', 'formula_bruta': 'Formula Bruta',
                    'original_area': 'Area % Originale', 'normalized_area': 'Area Normalizzata %', 
                    'macro_class': 'Macro Famiglia', 'class_of_compounds': 'Classe'
                }),
                use_container_width=True,
                selection_mode="single-row",
                on_select="rerun",
                height=300
            )
            
            selected_rows = event.selection.rows
            if len(selected_rows) > 0:
                dati_riga = df_grid.iloc[selected_rows[0]]
                col_info, col_img = st.columns([1, 1])
                
                with col_info:
                    st.markdown(f"### {dati_riga['compound_name']}")
                    st.markdown(f"**Appartiene a:** {dati_riga['target_id']}")
                    st.markdown(f"**Area % Originale:** {dati_riga['original_area']:.2f} %")
                    st.markdown(f"**Area Normalizzata:** {dati_riga['normalized_area']:.2f} %")
                    st.markdown(f"**Classe:** {dati_riga['class_of_compounds']}")
                    st.markdown(f"**Formula Bruta:** {dati_riga.get('formula_bruta', 'N/A')}")
                    st.markdown(f"**Massa:** {dati_riga.get('peso_molecolare', 'N/A')}")
                    
                with col_img:
                    with st.spinner("Richiesta live a PubChem in corso..."):
                        smiles = fetch_smiles_from_pubchem(dati_riga['compound_name'])
                        if smiles and RDKIT_AVAILABLE:
                            try:
                                mol = Chem.MolFromSmiles(smiles)
                                if mol:
                                    img = Draw.MolToImage(mol, size=(250, 250))
                                    st.image(img, caption=f"SMILES: {smiles}")
                                else:
                                    st.warning("RDKit non ha potuto generare la molecola.")
                            except Exception:
                                st.warning("Errore nel rendering della molecola.")
                        else:
                            st.warning("SMILES non trovato per questo composto su PubChem.")
            else:
                st.caption("👈 Clicca su un composto nella tabella per visualizzare struttura e dettagli.")

    # ==========================================
    # TAB 4: MARKER E RICERCA GLOBALE
    # ==========================================
    with tab_mark:
        st.subheader("🧬 Tracciamento Marker e Ricerca Globale")
        
        # --- 1. DIAGRAMMA TRIANGOLARE ---
        if not df_selected.empty:
            st.markdown("#### 🔺 Diagramma Triangolare (Tracciamento Origine via Marker)")
            
            # Filtro per i marker string/int
            df_markers = df_selected[df_selected['is_marker'].astype(str).str.lower().isin(['1', 'si', 'yes', 'true', 'sì'])].copy()
            
            if not df_markers.empty:
                # Mappatura rigorosa come da tue istruzioni
                source_map = {'MaterBi': 'MB', 'PE': 'PE', 'Sludge': 'SS'}
                df_markers['marker_mapped'] = df_markers['marker_source_id'].map(source_map).fillna(df_markers['marker_source_id'])
                
                df_ternary_raw = df_markers.groupby(['target_id', 'marker_mapped'])['normalized_area'].sum().reset_index()
                df_pivot = df_ternary_raw.pivot(index='target_id', columns='marker_mapped', values='normalized_area').fillna(0).reset_index()
                
                for col in ['SS', 'MB', 'PE']:
                    if col not in df_pivot.columns: df_pivot[col] = 0
                        
                df_pivot['Total'] = df_pivot['SS'] + df_pivot['MB'] + df_pivot['PE']
                df_plot = df_pivot[df_pivot['Total'] > 0].copy()
                
                if not df_plot.empty:
                    df_plot['SS_norm'] = (df_plot['SS'] / df_plot['Total']) * 100
                    df_plot['MB_norm'] = (df_plot['MB'] / df_plot['Total']) * 100
                    df_plot['PE_norm'] = (df_plot['PE'] / df_plot['Total']) * 100
                    
                    fig_tern = px.scatter_ternary(df_plot, a="SS_norm", b="PE_norm", c="MB_norm", 
                                                  color="target_id", size="Total", text="target_id",
                                                  labels={"SS_norm": "Sludge (SS)", "PE_norm": "Polietilene (PE)", "MB_norm": "Mater-Bi (MB)"},
                                                  title="Tracciamento origine del campione tramite Marker")
                    fig_tern.update_traces(textposition='bottom center', marker=dict(symbol='circle', line=dict(width=2, color='DarkSlateGrey')))
                    st.plotly_chart(fig_tern, use_container_width=True)
                else:
                    st.info("I marker trovati non corrispondono a SS, PE o MB.")
            else:
                st.info("Nessun composto etichettato come Marker (is_marker=si) trovato in queste prove.")
        
        st.divider()

        # --- 2. RICERCA GLOBALE INTELLIGENTE ---
        st.markdown("#### 🔎 Ricerca Globale Database")
        
        if not df_analytical_all.empty:
            c_search, c_proc, c_feed, c_macro, c_class = st.columns(5)
            
            search_query = c_search.text_input("Cerca (Nome o Formula):", placeholder="Es. Indole")
            search_proc = c_proc.selectbox("Processo:", ["Tutti"] + sorted(df_analytical_all['Processo'].dropna().unique().tolist()))
            search_feed = c_feed.selectbox("Feedstock:", ["Tutti"] + sorted(df_analytical_all['Feedstock'].dropna().unique().tolist()))
            search_macro = c_macro.selectbox("Macro-Classe:", ["Tutte"] + sorted(df_analytical_all['macro_class'].dropna().unique().tolist()))
            search_class = c_class.selectbox("Classe:", ["Tutte"] + sorted(df_analytical_all['class_of_compounds'].dropna().unique().tolist()))
            
            is_filtering = bool(search_query) or search_proc != "Tutti" or search_feed != "Tutti" or search_macro != "Tutte" or search_class != "Tutte"
            
            if is_filtering:
                df_show = df_analytical_all.copy()
                if search_query:
                    mask = df_show['compound_name'].str.contains(search_query, case=False, na=False) | df_show['formula_bruta'].str.contains(search_query, case=False, na=False)
                    df_show = df_show[mask]
                if search_proc != "Tutti": df_show = df_show[df_show['Processo'] == search_proc]
                if search_feed != "Tutti": df_show = df_show[df_show['Feedstock'] == search_feed]
                if search_macro != "Tutte": df_show = df_show[df_show['macro_class'] == search_macro]
                if search_class != "Tutte": df_show = df_show[df_show['class_of_compounds'] == search_class]
            else:
                df_show = df_selected.copy()
                st.caption("Mostrando di default i dati delle prove selezionate nel filtro principale. Usa i filtri sopra per interrogare l'intero database.")

            st.markdown(f"**Risultati trovati:** {len(df_show)}")
            
            if not df_show.empty:
                display_cols = ['target_id', 'Processo', 'Feedstock', 'Temperatura', 'compound_name', 'formula_bruta', 'original_area', 'normalized_area', 'macro_class', 'class_of_compounds']
                
                event_mark = st.dataframe(
                    df_show[display_cols].rename(columns={
                        'target_id': 'Prova', 'compound_name': 'Composto', 'formula_bruta': 'Formula Bruta',
                        'original_area': 'Area % Originale', 'normalized_area': 'Area Normalizzata %', 
                        'macro_class': 'Macro Famiglia', 'class_of_compounds': 'Classe'
                    }),
                    use_container_width=True,
                    selection_mode="single-row",
                    on_select="rerun",
                    height=300,
                    hide_index=True
                )
                
                selected_rows_mark = event_mark.selection.rows
                if len(selected_rows_mark) > 0:
                    dati_riga = df_show.iloc[selected_rows_mark[0]]
                    col_info, col_img = st.columns([1, 1])
                    
                    with col_info:
                        st.markdown(f"### {dati_riga['compound_name']}")
                        st.markdown(f"**Appartiene a:** {dati_riga['target_id']}")
                        st.markdown(f"**Area % Originale:** {dati_riga['original_area']:.2f} %")
                        st.markdown(f"**Area Normalizzata:** {dati_riga['normalized_area']:.2f} %")
                        st.markdown(f"**Formula Bruta:** {dati_riga.get('formula_bruta', 'N/A')}")
                        
                    with col_img:
                        with st.spinner("Richiesta live a PubChem..."):
                            smiles = fetch_smiles_from_pubchem(dati_riga['compound_name'])
                            if smiles and RDKIT_AVAILABLE:
                                try:
                                    mol = Chem.MolFromSmiles(smiles)
                                    if mol:
                                        img = Draw.MolToImage(mol, size=(250, 250))
                                        st.image(img, caption=f"SMILES: {smiles}")
                                except Exception:
                                    pass

    # ==========================================
    # TAB 5: NOTE
    # ==========================================
    with tab_note:
        st.subheader("📝 Note GC-MS")
        note_path = "data_vault/notes/gcms_notes.md"
        
        os.makedirs(os.path.dirname(note_path), exist_ok=True)
        if not os.path.exists(note_path):
            with open(note_path, "w", encoding="utf-8") as f:
                f.write("### Appunti sulle analisi GC-MS\nScrivi qui le tue considerazioni generali sui cromatogrammi.")
                
        with open(note_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())
