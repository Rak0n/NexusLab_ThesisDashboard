import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from engines import engine_map

def get_html_mermaid():
    """Ritorna l'HTML esatto e funzionante per Mermaid."""
    return """
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { font-family: 'Inter', sans-serif; background-color: #ffffff; margin: 0; padding: 10px; }
            .mermaid svg { max-width: 100% !important; height: auto !important; }
        </style>
    </head>
    <body class="flex flex-col items-center">
        <div class="w-full bg-white p-2 rounded-xl flex justify-center">
            <div class="mermaid text-center">
                flowchart TD
                    classDef feed fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000,font-weight:bold;
                    classDef piro fill:#f4f4f4,stroke:#000000,stroke-width:1px,color:#000;
                    classDef htl fill:#e8e8e8,stroke:#000000,stroke-width:1px,color:#000;
                    classDef inter fill:#333333,stroke:#000000,stroke-width:2px,color:#fff,font-weight:bold;
                    classDef htu fill:#ffffff,stroke:#000000,stroke-width:2px,stroke-dasharray: 6 6,color:#000;

                    FEED["FEEDSTOCKS INIZIALI<br/>MB (MaterBi) | PE (Polietilene)<br/>SS (Sewage Sludge) | CR (Camp. Reale)"]:::feed

                    subgraph G_PIRO [FASE 1: PIROLISI]
                        P_DOE["DoE (P1 - P9)<br/>Temp: 450 - 650 °C<br/>Mix Plastica: 25 - 80%<br/>Catalizzatore: Nessuno<br/>Resa Olio: 47.0 - 85.0%<br/>HHV: 24.5 - 39.3 MJ/kg"]:::piro
                        
                        P_OPT["Prova Ottimizzata (P10-P11-P12)<br/>Temp: 520 °C<br/>Mix Plastica: 51% (MB+PE)<br/>Cat: Ze (11,12)<br/>Resa Olio: ~67-80%<br/>HHV: 24.9-35.7 MJ/kg"]:::piro
                        
                        P_EXT["Extra & Bianchi (P13 - P20)<br/>Temp: 450 - 520 °C<br/>Feed Puri (100%) <br/>Cat: Ze (14,16,18)<br/>Resa Olio: 54.8 - 95.2%<br/>HHV: 24.2 - 44.4 MJ/kg"]:::piro
                    end

                    subgraph G_HTL [FASE 2: HTL DIRETTA]
                        HTL_ALL["Prove HTL (1 - 6 & 14)<br/>Temp: 300 - 330 °C | 30 min<br/>Feed: MB, MB+PE, CR<br/>Cat: Zeolite (solo 4, 6)<br/>Resa Biocrude: 17.8 - 35.8%<br/>HHV: 20.7 - 36.7 MJ/kg"]:::htl
                    end

                    subgraph G_INTER [INTERMEDI SCELTI PER HTU]
                        direction LR
                        O_P5{{"Olio P5<br/>550°C - 50%PL"}}:::inter
                        O_P4{{"Olio P4<br/>550°C - 20%PL"}}:::inter
                        O_P2{{"Olio P2<br/>480°C - 30%PL"}}:::inter
                        O_P15{{"Olio P15<br/>450°C - 100%MB"}}:::inter
                        O_P13{{"Olio P13<br/>450°C - 100%PE"}}:::inter
                    end

                    subgraph G_HTU [FASE 3: UPGRADING OLI]
                        HTU_7_8["HTU 7 & HTU 8<br/>Temp: 330 °C | Tempo: 180 min<br/>Cat: Nessuno (7) | CoMo+Zn (8)<br/>Resa: 13.5% | 17.6%<br/>HHV: 36.7 | 37.6 MJ/kg"]:::htu
                        
                        HTU_9_10["HTU 9 & HTU 10<br/>Temp: 330 °C | Tempo: 30 min<br/>Catalizzatore: Nessuno<br/>Resa: 33.2% (9) | 32.1% (10)<br/>HHV: 35.9 (9) | 38.4 (10) MJ/kg"]:::htu
                        
                        HTU_11_12["HTU 11, 12 & 13<br/>Temp: 330 °C | Tempo: 30 min<br/>Catalizzatore: Nessuno<br/>Resa: 27.3% (11) | 59.0% (12)<br/>HHV: 29.4 (11) | 46.8 (12) MJ/kg"]:::htu
                    end

                    FEED -->|Enea DoE| P_DOE
                    FEED -.->|Prove Ottimizzate| P_OPT
                    FEED -->|Componenti Puri| P_EXT
                    FEED -->|Prova Diretta| HTL_ALL

                    P_DOE --> O_P5
                    P_DOE --> O_P4
                    P_DOE --> O_P2
                    
                    P_EXT --> O_P15
                    P_EXT --> O_P13

                    O_P5 --> HTU_7_8
                    O_P4 --> HTU_9_10
                    O_P2 --> HTU_9_10
                    O_P15 --> HTU_11_12
                    O_P13 --> HTU_11_12
                    
                    ALTRE_PROVE["⬜ Altre Prove (Non classificate)"]:::feed
            </div>
        </div>

        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({ 
                startOnLoad: true, 
                theme: 'base',
                themeVariables: {
                    fontFamily: 'Inter, sans-serif',
                    lineColor: '#000000',
                    primaryTextColor: '#000000',
                    fontSize: '14px'
                },
                securityLevel: 'loose',
                flowchart: {
                    useMaxWidth: false,
                    htmlLabels: true,
                    rankSpacing: 60,
                    nodeSpacing: 40,
                    curve: 'basis'
                }
            });
        </script>
    </body>
    </html>
    """

def render():
    st.title("🗺️ Mappa Navigazionale")
    st.markdown("Usa la mappa a sinistra come riferimento e seleziona i blocchi a destra per estrarre le prove dal Database.")
    
    if 'prove_selezionate_per_confronto' not in st.session_state:
        st.session_state.prove_selezionate_per_confronto = []

    col_mappa, col_interazione = st.columns([1.8, 1])

    with col_mappa:
        st.markdown("### Mappa Sperimentale (View-Only)")
        with st.container(border=True):
            components.html(get_html_mermaid(), height=850, scrolling=True)

    with col_interazione:
        st.markdown("### 🗂️ Esplora i Blocchi")
        st.info("Scegli un blocco logico per caricare le prove associate.")
        
        blocco_selezionato = st.selectbox(
            "Seleziona Blocco Sperimentale:",
            [
                "Nessuna selezione",
                "🟩 Pirolisi: DoE (P1 - P9)",
                "🟩 Pirolisi: Ottimizzate (P10 - P12)",
                "🟩 Pirolisi: Extra/Bianchi (P13 - P20)",
                "🟦 HTL Diretta (1 - 6 & 14)",
                "🟪 HTU 7 & 8",
                "🟪 HTU 9 & 10",
                "🟪 HTU 11 & 12 & 13",
                "⬜ Altre Prove (Non classificate)"
            ]
        )

        st.divider()

        if blocco_selezionato != "Nessuna selezione":
            st.markdown(f"**Estrazione DB:** `{blocco_selezionato}`")
            prove_estratte = engine_map.get_experiments_by_block(blocco_selezionato)
            
            if not prove_estratte:
                st.info("Nessuna prova trovata nel database per questo blocco.")
            else:
                with st.container(border=True):
                    selezioni_correnti = []
                    
                    # Logica originale ripristinata
                    for p in prove_estratte:
                        pid = p['id']
                        is_in_cart = pid in st.session_state.prove_selezionate_per_confronto
                        label_ui = p['label'] + (" *(In selezione)*" if is_in_cart else "")
                        
                        is_checked = st.checkbox(label_ui, key=f"chk_{pid}", disabled=is_in_cart)
                        if is_checked and not is_in_cart:
                            selezioni_correnti.append(pid)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("➕ Aggiungi alla Selezione", type="secondary", use_container_width=True):
                        aggiunte = 0
                        for sel in selezioni_correnti:
                            if sel not in st.session_state.prove_selezionate_per_confronto:
                                st.session_state.prove_selezionate_per_confronto.append(sel)
                                aggiunte += 1
                                
                        if aggiunte > 0:
                            st.success(f"✅ {aggiunte} prove aggiunte alla selezione!")
                            st.rerun()
                        else:
                            st.warning("Spunta almeno una prova da aggiungere.")

        st.divider()
        
        st.markdown("### 📋 Elenco Prove Selezionate")
        st.caption("Elenco delle prove selezionate pronte per il Deep Dive.")
        
        if not st.session_state.prove_selezionate_per_confronto:
            st.warning("Nessuna prova in selezione.")
        else:
            # Fallback sicuro per la visualizzazione dei dati senza crash
            try:
                from engines import engine_multi_deepdive
                df_selezionate = engine_multi_deepdive.get_metadata_for_trials(st.session_state.prove_selezionate_per_confronto)
                if not df_selezionate.empty:
                    st.dataframe(df_selezionate, hide_index=True, use_container_width=True)
                else:
                    raise ValueError("Dati vuoti")
            except Exception:
                # Se l'engine fallisce, mostra un elenco semplice senza bloccare l'app
                for item in st.session_state.prove_selezionate_per_confronto:
                    st.markdown(f"- 🧪 `{item}`")
            
            if st.button("🗑️ Svuota Selezione", use_container_width=True):
                st.session_state.prove_selezionate_per_confronto = []
                st.rerun()
            
        # LOGICA DI ROUTING DINAMICA
        btn_disabled = len(st.session_state.prove_selezionate_per_confronto) == 0
        btn_label = "🚀 Lancia Analisi (Deep Dive Singolo)" if len(st.session_state.prove_selezionate_per_confronto) == 1 else "🚀 Lancia Confronto (Multi-Deep Dive)"
        
        if st.button(btn_label, type="primary", use_container_width=True, disabled=btn_disabled):
            if len(st.session_state.prove_selezionate_per_confronto) == 1:
                st.session_state.selected_prova_id = st.session_state.prove_selezionate_per_confronto[0]
                st.session_state.current_view = "Deep Dive"
            else:
                st.session_state.current_view = "Multi Deep Dive"
            st.rerun()
