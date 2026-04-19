import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from sqlalchemy import create_engine, text

from engines import engine_gcms

# Fallback sicuri in caso i motori non siano ancora implementati
try:
    from engines import engine_chnso
except ImportError:
    engine_chnso = None
try:
    from engines import engine_gc
except ImportError:
    engine_gc = None

DB_PATH = "nexuslab.db"

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

# ==========================================
# MODULI DEI QUADRANTI
# ==========================================

def render_modulo_rese(id_prova, processo, q_id):
    st.markdown("##### ⚖️ Rese di Processo")
    
    df_yields = pd.DataFrame()
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        if 'Pirolisi' in processo:
            df_yields = pd.read_sql(text("SELECT id_run, resa_olio as Olio, resa_char as Char, resa_gas as Gas FROM runs_pirolisi WHERE id_prova=:id"), engine, params={"id": id_prova})
        else:
            df_yields = pd.read_sql(text("SELECT id_prova as id_run, resa_biocrude as Biocrude, resa_wso as Aqueous_Phase, resa_char as Char, resa_gas as Gas FROM prove_idrotermiche WHERE id_prova=:id"), engine, params={"id": id_prova})
    except Exception:
        pass
    
    if df_yields.empty:
        st.info("Nessun dato sulle rese disponibile per questa prova.")
        return
        
    collassa = st.toggle("📊 Collassa Repliche (Media e Std)", value=False, key=f"tgl_rese_{id_prova}_{q_id}")
    
    if 'Pirolisi' in processo:
        y_cols = ['Olio', 'Char', 'Gas']
        colors = ['#ea580c', '#10b981', '#0ea5e9']
    else:
        y_cols = ['Biocrude', 'Aqueous_Phase', 'Char', 'Gas']
        colors = ['#ea580c', '#3b82f6', '#10b981', '#0ea5e9']
        
    fig = go.Figure()
    
    if collassa and len(df_yields) > 1:
        df_mean = df_yields[y_cols].mean()
        df_std = df_yields[y_cols].std().fillna(0)
        
        for idx, col in enumerate(y_cols):
            fig.add_trace(go.Bar(
                name=col, x=[id_prova], y=[df_mean[col]],
                error_y=dict(type='data', array=[df_std[col]], visible=True, thickness=1.5),
                marker_color=colors[idx]
            ))
    else:
        for idx, col in enumerate(y_cols):
            fig.add_trace(go.Bar(
                name=col, x=df_yields['id_run'], y=df_yields[col],
                marker_color=colors[idx]
            ))
            
    fig.update_layout(barmode='group', margin=dict(t=10, b=10, l=10, r=10), yaxis_title="Resa Massica (%)", legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"))
    st.plotly_chart(fig, use_container_width=True, key=f"chart_rese_{q_id}")

def render_modulo_gcms(id_prova, processo, q_id):
    st.markdown("##### 🔴 Molecolare (GC-MS)")
    
    targets = []
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        with engine.connect() as conn:
            res = conn.execute(text("SELECT DISTINCT target_id FROM registro_analisi WHERE target_id LIKE :id || '%' AND tipo_analisi = 'GC-MS'"), {"id": id_prova}).fetchall()
            targets = [r[0] for r in res]
    except Exception:
        pass
    
    if not targets:
        st.info("Nessun dato GC-MS trovato per le frazioni di questa prova.")
        return
        
    tid = st.selectbox("Seleziona Frazione Analizzata:", targets, key=f"sel_gcms_{id_prova}_{q_id}")
    df_gcms = engine_gcms.fetch_analytical_dataset([tid])
    
    if df_gcms.empty:
        st.warning("Nessun composto trovato per la frazione selezionata.")
        return
        
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("<p style='font-size:12px; font-weight:bold;'>Macro Famiglie</p>", unsafe_allow_html=True)
        df_macro = df_gcms.groupby('macro_class')['normalized_area'].sum().reset_index()
        fig_pie = px.pie(df_macro, values='normalized_area', names='macro_class', hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
        fig_pie.update_layout(
            height=220, 
            margin=dict(t=10, b=10, l=10, r=10), 
            showlegend=True, 
            legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5, font=dict(size=9))
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent')
        st.plotly_chart(fig_pie, use_container_width=True, key=f"pie_{id_prova}_{q_id}")
        
    with c2:
        df_valuable = df_gcms[(df_gcms['is_valuable'] == 1) | (df_gcms['is_valuable'] == 'Si')]
        val_sum = df_valuable['normalized_area'].sum() if not df_valuable.empty else 0
        st.markdown(f"<p style='font-size:12px; font-weight:bold; margin-bottom: 5px;'>💎 Valuables (Platform Chem.): {val_sum:.1f} %</p>", unsafe_allow_html=True)
        
        df_markers = df_gcms[df_gcms['is_marker'].astype(str).str.lower().isin(['1', 'si', 'yes', 'true', 'sì'])].copy()
        if not df_markers.empty:
            source_map = {'MaterBi': 'MB', 'PE': 'PE', 'Sludge': 'SS'}
            df_markers['marker_mapped'] = df_markers['marker_source_id'].map(source_map).fillna(df_markers['marker_source_id'])
            df_ternary = df_markers.groupby(['target_id', 'marker_mapped'])['normalized_area'].sum().reset_index()
            df_pivot = df_ternary.pivot(index='target_id', columns='marker_mapped', values='normalized_area').fillna(0).reset_index()
            for col in ['SS', 'MB', 'PE']:
                if col not in df_pivot.columns: df_pivot[col] = 0
            df_pivot['Total'] = df_pivot['SS'] + df_pivot['MB'] + df_pivot['PE']
            df_plot = df_pivot[df_pivot['Total'] > 0].copy()
            if not df_plot.empty:
                df_plot['SS_norm'] = (df_plot['SS'] / df_plot['Total']) * 100
                df_plot['MB_norm'] = (df_plot['MB'] / df_plot['Total']) * 100
                df_plot['PE_norm'] = (df_plot['PE'] / df_plot['Total']) * 100
                fig_tern = px.scatter_ternary(df_plot, a="SS_norm", b="PE_norm", c="MB_norm", size="Total", title="Tracciamento Marker")
                fig_tern.update_layout(height=200, margin=dict(t=25, b=0, l=0, r=0))
                st.plotly_chart(fig_tern, use_container_width=True, key=f"tern_{id_prova}_{q_id}")
        else:
            st.caption("Nessun marker di origine rilevato.")

    st.markdown("<p style='font-size:12px; font-weight:bold; margin-top: 5px;'>Elenco Composti e Struttura Molecolare</p>", unsafe_allow_html=True)
    
    df_sorted = df_gcms.sort_values('normalized_area', ascending=False).copy()
    
    # Normalizzazione per la visualizzazione nella griglia
    df_sorted['is_valuable'] = df_sorted['is_valuable'].apply(lambda x: 'Si' if str(x).lower() in ['1', 'si', 'true', 'yes'] else 'No')
    df_sorted['is_marker'] = df_sorted['is_marker'].apply(lambda x: 'Si' if str(x).lower() in ['1', 'si', 'true', 'yes'] else 'No')
    
    display_cols = ['retention_time', 'compound_name', 'formula_bruta', 'normalized_area', 'class_of_compounds', 'is_valuable', 'is_marker']
    
    event = st.dataframe(
        df_sorted[display_cols].rename(columns={
            'retention_time': 'RT', 'compound_name': 'Composto', 'formula_bruta': 'Formula',
            'normalized_area': 'Area Norm. %', 'class_of_compounds': 'Classe', 
            'is_valuable': 'Valuable', 'is_marker': 'Marker'
        }),
        use_container_width=True, selection_mode="single-row", on_select="rerun", height=280, key=f"grid_gcms_{id_prova}_{q_id}", hide_index=True
    )
    
    if len(event.selection.rows) > 0:
        row = df_sorted.iloc[event.selection.rows[0]]
        if PUBCHEM_AVAILABLE and RDKIT_AVAILABLE:
            with st.spinner("Disegnando la molecola..."):
                try:
                    c = pcp.get_compounds(row['compound_name'], 'name')
                    if c and c[0].isomeric_smiles:
                        mol = Chem.MolFromSmiles(c[0].isomeric_smiles)
                        if mol:
                            img = Draw.MolToImage(mol, size=(200, 200))
                            st.image(img, caption=row['compound_name'], width=200)
                except: pass

def render_modulo_chnso(id_prova, q_id):
    st.markdown("##### 🟢 Elementare (CHNSO)")
    targets = [f"{id_prova}_OIL", f"{id_prova}_BC", f"{id_prova}_CHAR", f"{id_prova}_AP"]
    
    df_chnso = pd.DataFrame()
    if engine_chnso:
        try:
            df_chnso = engine_chnso.fetch_chnso_data(targets)
        except Exception:
            pass
            
    if df_chnso.empty:
        st.info("Nessun dato CHNSO trovato per le frazioni di questa prova.")
        return
        
    fig_stack = make_subplots(specs=[[{"secondary_y": True}]])
    elements = [('C', 'c_mean', '#4338ca'), ('H', 'h_mean', '#10b981'), ('N', 'n_mean', '#3b82f6'), 
                ('S', 's_mean', '#f59e0b'), ('O', 'o_diff', '#ef4444')]
                
    for name, mean_col, color in elements:
        if mean_col in df_chnso.columns:
            fig_stack.add_trace(go.Bar(name=name, x=df_chnso['target_id'], y=df_chnso[mean_col], marker_color=color), secondary_y=False)
        
    if 'hhv_stimato' in df_chnso.columns:
        fig_stack.add_trace(go.Scatter(
            name='HHV (MJ/Kg)', x=df_chnso['target_id'], y=df_chnso['hhv_stimato'], 
            mode='lines+markers', line=dict(dash='dash', color='black', width=2),
            marker=dict(symbol='diamond', size=10, color='black')
        ), secondary_y=True)
    
    fig_stack.update_layout(barmode='stack', margin=dict(t=10, b=10, l=0, r=0), legend=dict(orientation="h", y=-0.3, x=0.5, xanchor="center"))
    fig_stack.update_yaxes(title_text="Massa %", secondary_y=False)
    fig_stack.update_yaxes(title_text="HHV", secondary_y=True, showgrid=False)
    st.plotly_chart(fig_stack, use_container_width=True, key=f"chnso_chart_{q_id}")
    
    st.markdown("<p style='font-size:12px; font-weight:bold;'>Rapporti Atomici</p>", unsafe_allow_html=True)
    cols_to_show = ['target_id']
    for c in ['H/C', 'O/C', 'N/C', 'hhv_stimato']:
        if c in df_chnso.columns: cols_to_show.append(c)
    
    st.dataframe(
        df_chnso[cols_to_show].round(3).rename(columns={'target_id': 'Frazione', 'hhv_stimato': 'HHV'}), 
        use_container_width=True, hide_index=True, key=f"grid_chnso_{q_id}"
    )

def render_modulo_gc(id_prova, q_id):
    st.markdown("##### 🟣 Gas (GC)")
    df_gc = pd.DataFrame()
    if engine_gc:
        try:
            df_gc = engine_gc.fetch_gc_data()
            if not df_gc.empty:
                df_gc = df_gc[df_gc['id_prova'] == id_prova]
        except Exception:
            pass
            
    if df_gc.empty:
        st.info("Nessun dato Gas GC trovato per questa prova.")
        return
        
    collassa = st.toggle("📊 Collassa Repliche in Media", value=False, key=f"tgl_gc_{id_prova}_{q_id}")
    
    fig = make_subplots(rows=1, cols=2, specs=[[{"secondary_y": True}, {"secondary_y": True}]], subplot_titles=("Norm. Aria", "Norm. Aria + CO2"))
    
    gases = [('H2', 'h2', '#3b82f6'), ('CO', 'co', '#9ca3af'), ('CH4', 'ch4', '#f59e0b'), 
             ('CO2', 'co2', '#ef4444'), ('C2', 'c2', '#8b5cf6'), ('C3', 'c3', '#d946ef')]
             
    def plot_gc_trace(suffix, col_idx):
        if collassa:
            agg_dict = {f"{g[1]}_{suffix}": 'mean' for g in gases}
            if 'pci_gas' in df_gc.columns: agg_dict['pci_gas'] = 'mean'
            df_grp = df_gc.groupby('id_prova').agg(agg_dict).reset_index()
            x_val = df_grp['id_prova']
            for name, base_col, color in gases:
                if f"{base_col}_{suffix}" in df_grp.columns:
                    fig.add_trace(go.Bar(name=name, x=x_val, y=df_grp[f"{base_col}_{suffix}"], marker_color=color, showlegend=(col_idx==1)), row=1, col=col_idx, secondary_y=False)
            if 'pci_gas' in df_grp.columns:
                fig.add_trace(go.Scatter(name='PCI', x=x_val, y=df_grp['pci_gas'], mode='lines+markers', line=dict(color='black', dash='dash'), marker=dict(symbol='diamond'), showlegend=(col_idx==1)), row=1, col=col_idx, secondary_y=True)
        else:
            x_val = df_gc['target_id']
            for name, base_col, color in gases:
                if f"{base_col}_{suffix}" in df_gc.columns:
                    fig.add_trace(go.Bar(name=name, x=x_val, y=df_gc[f"{base_col}_{suffix}"], marker_color=color, showlegend=(col_idx==1)), row=1, col=col_idx, secondary_y=False)
            if 'pci_gas' in df_gc.columns:
                fig.add_trace(go.Scatter(name='PCI', x=x_val, y=df_gc['pci_gas'], mode='lines+markers', line=dict(color='black', dash='dash'), marker=dict(symbol='diamond'), showlegend=(col_idx==1)), row=1, col=col_idx, secondary_y=True)

    plot_gc_trace("perc", 1)
    plot_gc_trace("norm", 2)
    
    fig.update_layout(barmode='stack', margin=dict(t=30, b=10, l=10, r=10), legend=dict(orientation="h", y=-0.3, x=0.5, xanchor="center"))
    fig.update_yaxes(showgrid=False, secondary_y=True)
    st.plotly_chart(fig, use_container_width=True, key=f"gc_chart_{q_id}")

def render_modulo_note(id_prova, q_id):
    st.markdown("##### 📝 Diario Operativo (Note .md)")
    note_path = f"data_vault/notes/prove/{id_prova}.md"
    
    os.makedirs(os.path.dirname(note_path), exist_ok=True)
    if not os.path.exists(note_path):
        content = f"### Note Sperimentali per la prova {id_prova}\n\nScrivi qui le tue considerazioni, osservazioni o anomalie."
    else:
        with open(note_path, "r", encoding="utf-8") as f:
            content = f.read()
            
    new_content = st.text_area("Modifica e Salva (Markdown supportato):", value=content, height=280, key=f"note_edit_{id_prova}_{q_id}")
    
    if new_content != content:
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        st.success("✅ Modifiche salvate automaticamente nel file .md!")


# ==========================================
# RENDER DELLA VISTA COMPLETA DEEP DIVE
# ==========================================

def render():
    if 'selected_prova_id' not in st.session_state:
        st.warning("Nessuna prova selezionata. Torna alla Control Tower.")
        if st.button("⬅️ Torna alla Control Tower"):
            st.session_state.current_view = "Control Tower"
            st.rerun()
        return

    id_prova = st.session_state.selected_prova_id
    processo = st.session_state.get('selected_processo', 'Sconosciuto')
    feed = st.session_state.get('selected_feed', 'Sconosciuto')

    # --- Estrazione Dati Aggiuntivi per Header e Lineage ---
    temp_val = "-"
    tempo_val = "-"
    ricetta_str = feed
    lineage_html = "Lineage non disponibile"
    
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        with engine.connect() as conn:
            if 'Pirolisi' in processo:
                row = conn.execute(text("SELECT temperatura, 30 as tempo FROM prove_pirolisi WHERE id_prova=:id"), {"id": id_prova}).first()
                if row:
                    temp_val, tempo_val = row[0], row[1]
                recipe = conn.execute(text("SELECT feedstock_id, percentuale FROM pirolisi_ricetta WHERE id_prova=:id"), {"id": id_prova}).fetchall()
                if recipe:
                    ricetta_str = " + ".join([f"{r[0].replace('FS_','')} ({r[1]:.0f}%)" for r in recipe])
                
                # Calcolo Lineage
                res_target = conn.execute(text("""
                    SELECT i.id_prova, p.tipo_processo
                    FROM input_idrotermico i
                    JOIN prove_idrotermiche p ON i.id_prova = p.id_prova
                    WHERE i.source_id LIKE '%' || :id || '%'
                """), {"id": id_prova}).first()
                if res_target:
                    lineage_html = f"📦 {feed} ➔ 🔥 Pirolisi ({id_prova}) ➔ ⚡ {res_target[1]} ({res_target[0]})"
                else:
                    lineage_html = f"📦 {feed} ➔ 🔥 Pirolisi ({id_prova}) ➔ 🛢️ Frazioni"
                    
            elif processo in ['HTL', 'HTU']:
                row = conn.execute(text("SELECT temperatura, tempo FROM prove_idrotermiche WHERE id_prova=:id"), {"id": id_prova}).first()
                if row:
                    temp_val, tempo_val = row[0], row[1]
                
                # Calcolo Lineage
                res_source = conn.execute(text("SELECT source_id FROM input_idrotermico WHERE id_prova=:id"), {"id": id_prova}).first()
                if res_source:
                    source_id = res_source[0]
                    if 'HTU' in processo:
                        base_p = source_id.replace('_OIL', '')
                        feed_res = conn.execute(text("SELECT GROUP_CONCAT(feedstock_id, ' + ') FROM pirolisi_ricetta WHERE id_prova=:id"), {"id": base_p}).scalar()
                        base_feed = str(feed_res).replace('FS_', '') if feed_res else 'Mix'
                        lineage_html = f"📦 {base_feed} ➔ 🔥 Pirolisi ({base_p}) ➔ ⚡ HTU ({id_prova})"
                        ricetta_str = f"Derivato da {source_id}"
                    else:
                        clean_source = source_id.replace('FS_', '')
                        lineage_html = f"📦 {clean_source} ➔ 💧 HTL ({id_prova}) ➔ 🛢️ Biocrude/AP"
                        ricetta_str = f"Mix Diretto: {clean_source}"
                else:
                    lineage_html = f"📦 {feed} ➔ ⚙️ {processo} ({id_prova})"
                    ricetta_str = f"Mix Diretto: {feed}"
    except Exception:
        pass

    # --- HEADER VISIVO ---
    c_back, c_title = st.columns([1, 8])
    with c_back:
        if st.button("⬅️ Esci (Control Tower)", use_container_width=True):
            st.session_state.current_view = "Control Tower"
            st.rerun()
    with c_title:
        st.markdown(f"<h2 style='margin-top: -10px; color: #0f172a;'>🔬 Analisi Approfondita: <span style='color: #2563eb;'>{id_prova}</span></h2>", unsafe_allow_html=True)

    st.markdown(f"""
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 6px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
            <div style='margin-bottom: 10px;'>
                <span style='font-size: 12px; font-weight: 700; color: #64748b; letter-spacing: 1px;'>🔄 LINEAGE</span><br>
                <span style='font-size: 14px; font-weight: 700; color: #0f172a;'>{lineage_html}</span>
            </div>
            <hr style='margin: 10px 0; border: 0; border-top: 1px solid #e2e8f0;'>
            <span style="font-weight: 600; color: #475569;">Processo:</span> <span style="color: #0f172a;">{processo}</span> &nbsp;|&nbsp; 
            <span style="font-weight: 600; color: #475569;">Temp:</span> <span style="color: #0f172a;">{temp_val} °C</span> &nbsp;|&nbsp; 
            <span style="font-weight: 600; color: #475569;">Tempo:</span> <span style="color: #0f172a;">{tempo_val} min</span> <br>
            <span style="font-weight: 600; color: #475569;">Composizione Feedstock:</span> <span style="color: #0f172a;">{ricetta_str}</span>
        </div>
    """, unsafe_allow_html=True)

    # --- SETUP QUADRANTI 2x2 ---
    opzioni_moduli = ["Nessuno", "⚖️ Rese di Processo", "🔴 GC-MS (Molecolare)", "🟢 CHNSO (Elementare)", "🟣 GC (Gas)", "📝 Diario Operativo (.md)"]
    
    def_q1 = opzioni_moduli.index("⚖️ Rese di Processo")
    def_q2 = opzioni_moduli.index("🔴 GC-MS (Molecolare)")
    def_q3 = opzioni_moduli.index("🟢 CHNSO (Elementare)")
    def_q4 = opzioni_moduli.index("📝 Diario Operativo (.md)")

    def render_quadrante(scelta, q_id):
        if scelta == "⚖️ Rese di Processo": render_modulo_rese(id_prova, processo, q_id)
        elif scelta == "🔴 GC-MS (Molecolare)": render_modulo_gcms(id_prova, processo, q_id)
        elif scelta == "🟢 CHNSO (Elementare)": render_modulo_chnso(id_prova, q_id)
        elif scelta == "🟣 GC (Gas)": render_modulo_gc(id_prova, q_id)
        elif scelta == "📝 Diario Operativo (.md)": render_modulo_note(id_prova, q_id)
        else: st.caption("Seleziona un modulo dal menu a tendina per visualizzare i dati.")

    # Riga 1
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        with st.container(border=True):
            scelta_q1 = st.selectbox("Vista Quadrante 1", opzioni_moduli, index=def_q1, key="q1_sel", label_visibility="collapsed")
            render_quadrante(scelta_q1, "q1")
            
    with r1c2:
        with st.container(border=True):
            scelta_q2 = st.selectbox("Vista Quadrante 2", opzioni_moduli, index=def_q2, key="q2_sel", label_visibility="collapsed")
            render_quadrante(scelta_q2, "q2")

    # Riga 2
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        with st.container(border=True):
            scelta_q3 = st.selectbox("Vista Quadrante 3", opzioni_moduli, index=def_q3, key="q3_sel", label_visibility="collapsed")
            render_quadrante(scelta_q3, "q3")
            
    with r2c2:
        with st.container(border=True):
            scelta_q4 = st.selectbox("Vista Quadrante 4", opzioni_moduli, index=def_q4, key="q4_sel", label_visibility="collapsed")
            render_quadrante(scelta_q4, "q4")
