import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from engines import engine_gc

def draw_gc_chart(df_plot, suffix, title_suffix, collassa):
    """Genera l'istogramma impilato per i gas con linea tratteggiata per il PCI ed etichette personalizzate."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    gases = [
        ('H2', f'h2_{suffix}', '#3b82f6'),   # Blu
        ('CO', f'co_{suffix}', '#9ca3af'),   # Grigio
        ('CH4', f'ch4_{suffix}', '#f59e0b'), # Arancione
        ('CO2', f'co2_{suffix}', '#ef4444'), # Rosso
        ('C2', f'c2_{suffix}', '#8b5cf6'),   # Viola
        ('C3', f'c3_{suffix}', '#d946ef')    # Fucsia
    ]
    
    if collassa:
        # 1. Raggruppamento e calcolo Media e Std
        agg_dict = {gas[1]: ['mean', 'std'] for gas in gases if gas[1] in df_plot.columns}
        agg_dict['pci_gas'] = ['mean', 'std']
        # Conserviamo anche i metadati per le etichette
        agg_dict['temperatura'] = ['first']
        agg_dict['pl_perc'] = ['first']
        
        df_grouped = df_plot.groupby('id_prova').agg(agg_dict).reset_index()
        # Flatten del MultiIndex creato da agg()
        df_grouped.columns = ['_'.join(col).strip('_') for col in df_grouped.columns.values]
        
        # Gestione valori nulli per sicurezza
        df_grouped['temperatura_first'] = df_grouped['temperatura_first'].fillna('-')
        df_grouped['pl_perc_first'] = df_grouped['pl_perc_first'].fillna(0).astype(int)
        
        # Creazione etichette multilinea (Prova, Temp, %PL)
        x_labels = df_grouped.apply(
            lambda r: f"<b>{r['id_prova']}</b><br>{r['temperatura_first']} °C<br>{r['pl_perc_first']}% PL", 
            axis=1
        )
        
        for name, col, color in gases:
            mean_col = f"{col}_mean"
            std_col = f"{col}_std"
            if mean_col in df_grouped.columns:
                fig.add_trace(go.Bar(
                    name=name, x=x_labels, y=df_grouped[mean_col],
                    error_y=dict(type='data', array=df_grouped[std_col], visible=True, thickness=1.5),
                    marker_color=color, opacity=0.85
                ), secondary_y=False)
        
        # Aggiunta linea PCI con barre di errore
        fig.add_trace(go.Scatter(
            name='PCI Gas (MJ/kg)', x=x_labels, y=df_grouped['pci_gas_mean'],
            error_y=dict(type='data', array=df_grouped['pci_gas_std'], visible=True, thickness=1.5),
            mode='lines+markers', line=dict(dash='dash', color='#1e293b', width=2),
            marker=dict(size=12, symbol='diamond', color='#0f172a', line=dict(width=1, color='white'))
        ), secondary_y=True)
        
    else:
        # 2. Visualizzazione standard di tutte le Run
        # Etichetta: Run ID in grassetto, sotto la Prova Madre
        x_labels = df_plot.apply(
            lambda r: f"<b>{r['target_id']}</b><br>({r['id_prova']})", 
            axis=1
        )
        
        for name, col, color in gases:
            if col in df_plot.columns:
                fig.add_trace(go.Bar(
                    name=name, x=x_labels, y=df_plot[col],
                    marker_color=color, opacity=0.85
                ), secondary_y=False)
        
        # Aggiunta linea PCI
        fig.add_trace(go.Scatter(
            name='PCI Gas (MJ/kg)', x=x_labels, y=df_plot['pci_gas'],
            mode='lines+markers', line=dict(dash='dash', color='#1e293b', width=2),
            marker=dict(size=12, symbol='diamond', color='#0f172a', line=dict(width=1, color='white'))
        ), secondary_y=True)

    fig.update_layout(
        barmode='stack', 
        title=f"Composizione Volumetrica {title_suffix}", 
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center")
    )
    fig.update_yaxes(title_text="Frazione Volumetrica (%)", secondary_y=False)
    fig.update_yaxes(title_text="PCI (MJ/kg)", secondary_y=True, showgrid=False)
    
    st.plotly_chart(fig, use_container_width=True)


def render():
    st.title("🟣 Dashboard GC Gas (Analisi)")
    st.markdown("Analisi dei gas di pirolisi: composizione volumetrica e PCI.")
    
    df_gc = engine_gc.fetch_gc_data()
    
    prove_selezionate = []
    df_filtered = pd.DataFrame()
    collassa = False
    
    # ==========================================
    # MOTORE DI SELEZIONE E FILTRI
    # ==========================================
    if not df_gc.empty:
        with st.expander("🔍 Motore di Selezione Prove GC", expanded=True):
            
            # Nuovo Filtro Strumento
            filtro_strumento = st.radio(
                "Filtra per Strumento:", 
                ["Tutti", "Solo Micro-GC", "Solo GC Classico"], 
                horizontal=True
            )
            
            df_temp = df_gc.copy()
            if filtro_strumento == "Solo Micro-GC":
                df_temp = df_temp[df_temp['strumento'] == 'Micro-GC']
            elif filtro_strumento == "Solo GC Classico":
                df_temp = df_temp[df_temp['strumento'] == 'GC Classico']
            
            if df_temp.empty:
                st.warning("Nessun dato disponibile per lo strumento selezionato.")
            else:
                prove_disponibili = sorted(df_temp['id_prova'].dropna().unique().tolist())
                prove_selezionate = st.multiselect("🧪 Seleziona le Prove Madre da analizzare:", prove_disponibili, default=prove_disponibili)
                
                if prove_selezionate:
                    df_filtered = df_temp[df_temp['id_prova'].isin(prove_selezionate)].copy()
                    st.divider()
                    
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        run_disponibili = sorted(df_filtered['target_id'].unique().tolist())
                        run_escluse = st.multiselect("❌ Escludi repliche specifiche (Outliers):", run_disponibili, default=None, help="Seleziona qui le run mal riuscite per rimuoverle dai grafici e dalle medie.")
                        
                        if run_escluse:
                            df_filtered = df_filtered[~df_filtered['target_id'].isin(run_escluse)]
                            
                    with c2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        collassa = st.toggle("📊 Collassa Repliche (Mostra Medie e Dev. Std)", value=False, help="Fonde le run della stessa prova mostrando la barra di errore.")
                        
                    st.success(f"Dati attivi: **{len(df_filtered)} Run** collegate a **{len(prove_selezionate)} Prove**.")
    else:
        st.info("Nessun dato GC disponibile nel database.")

    # ==========================================
    # TABS (Solo Grafiche)
    # ==========================================
    if not df_filtered.empty:
        tab_perc, tab_norm = st.tabs(["🌬️ % Vol. (Norm. Aria)", "🔥 % Vol. (Norm. Aria & CO2)"])
        
        with tab_perc:
            st.markdown("#### Composizione Gas Normalizzata rispetto all'Aria (incluso CO2)")
            draw_gc_chart(df_filtered, "perc", "(Normalizzazione Aria)", collassa)
            
        with tab_norm:
            st.markdown("#### Composizione Gas Normalizzata ad Aria e CO2 (Solo combustibili e C2/C3)")
            draw_gc_chart(df_filtered, "norm", "(Normalizzazione Aria & CO2)", collassa)
