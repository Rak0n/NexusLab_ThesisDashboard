import streamlit as st
import os

def render_svg_diagram():
    """Restituisce il codice SVG per un diagramma tecnico di Bioraffineria."""
    svg_code = """
    <svg viewBox="0 0 800 350" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b"/>
        </marker>
        <linearGradient id="gradReact" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#ef4444" />
          <stop offset="100%" stop-color="#f97316" />
        </linearGradient>
        <linearGradient id="gradHTL" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#0ea5e9" />
          <stop offset="100%" stop-color="#3b82f6" />
        </linearGradient>
      </defs>
      
      <!-- Sfondo -->
      <rect width="100%" height="100%" fill="#f8fafc" rx="10" stroke="#e2e8f0" stroke-width="2"/>

      <!-- Frecce di Connessione -->
      <path d="M 140 100 L 200 100" stroke="#64748b" stroke-width="3" fill="none" marker-end="url(#arrow)"/>
      <path d="M 320 100 L 380 100" stroke="#64748b" stroke-width="3" fill="none" marker-end="url(#arrow)"/>
      <path d="M 500 100 L 580 100" stroke="#64748b" stroke-width="3" fill="none" marker-end="url(#arrow)"/>
      <path d="M 500 240 L 580 240" stroke="#64748b" stroke-width="3" fill="none" marker-end="url(#arrow)"/>
      <path d="M 440 130 L 440 200" stroke="#64748b" stroke-width="3" fill="none" marker-end="url(#arrow)"/>

      <!-- Nodi (Box) -->
      
      <!-- 1. Feedstock -->
      <rect x="40" y="70" width="100" height="60" rx="5" fill="#10b981"/>
      <text x="90" y="105" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="bold" text-anchor="middle">Waste/Feed</text>
      
      <!-- 2. Pyrolysis -->
      <rect x="200" y="60" width="120" height="80" rx="8" fill="url(#gradReact)"/>
      <text x="260" y="95" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="bold" text-anchor="middle">Pyrolysis Unit</text>
      <text x="260" y="115" font-family="Arial, sans-serif" font-size="11" fill="#fee2e2" text-anchor="middle">400-600°C</text>
      
      <!-- 3. Pyrolysis Oil -->
      <rect x="380" y="70" width="120" height="60" rx="5" fill="#f59e0b"/>
      <text x="440" y="105" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="bold" text-anchor="middle">Pyrolysis Oil</text>
      
      <!-- Nodo Intermedio (Aggiunta Acqua/Cat) -->
      <circle cx="440" cy="165" r="14" fill="#334155"/>
      <text x="440" y="170" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="bold" text-anchor="middle">+</text>
      <text x="465" y="169" font-family="Arial, sans-serif" font-size="11" fill="#64748b" font-weight="bold">H₂O / Cat</text>

      <!-- 4. HTU / HTL -->
      <rect x="380" y="200" width="120" height="80" rx="8" fill="url(#gradHTL)"/>
      <text x="440" y="235" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="bold" text-anchor="middle">HTU Reactor</text>
      <text x="440" y="255" font-family="Arial, sans-serif" font-size="11" fill="#e0f2fe" text-anchor="middle">250-350°C | P > 10 MPa</text>
      
      <!-- 5. Chemicals (Destinazione in alto) -->
      <rect x="580" y="70" width="160" height="60" rx="5" fill="#8b5cf6"/>
      <text x="660" y="97" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="bold" text-anchor="middle">Platform Chemicals</text>
      <text x="660" y="115" font-family="Arial, sans-serif" font-size="11" fill="#ede9fe" text-anchor="middle">(Phenols, Alcohols, etc.)</text>
      
      <!-- 6. Upgraded Biocrude (Destinazione in basso) -->
      <rect x="580" y="210" width="160" height="60" rx="5" fill="#14b8a6"/>
      <text x="660" y="245" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="bold" text-anchor="middle">Upgraded Biocrude</text>
    </svg>
    """
    return svg_code

def render():
    st.title("📖 Mappa Tesi & Bioraffineria")
    st.markdown("Panoramica del progetto di ricerca e del flusso di valorizzazione chimica (Waste-to-Chemicals).")
    
    st.markdown("---")
    
    # --- 1. RENDER SVG ---
    st.subheader("⚙️ Schema di Processo: Da Rifiuto a Platform Chemicals")
    svg_html = render_svg_diagram()
    st.markdown(f"<div style='text-align: center; margin-top: 10px; margin-bottom: 30px;'>{svg_html}</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --- 2. RENDER NOTE MARKDOWN ---
    st.subheader("📝 Struttura e Obiettivi della Tesi")
    
    note_path = "data_vault/notes/tesi_map.md"
    os.makedirs(os.path.dirname(note_path), exist_ok=True)
    
    # Se il file non esiste, crea un template di base
    if not os.path.exists(note_path):
        template = """# Mappa della Tesi
        
## Obiettivo Principale
Valorizzazione di scarti plastici e biomasse (fanghi) attraverso processi termochimici combinati (Pirolisi e Liquefazione/Upgrading Idrotermico).

## Fasi del Lavoro
1. **Analisi Feedstocks:** Caratterizzazione elementare e compositiva.
2. **Processo Primario (Pirolisi):** Estrazione dell'olio di pirolisi.
3. **Processo Secondario (HTU):** Upgrading dell'olio in ambiente idrotermico per abbattere l'ossigeno e concentrare le molecole target.
4. **Analisi GC-MS:** - Identificazione delle macro-famiglie chimiche.
   - Ricerca di composti ad alto valore aggiunto (Platform Chemicals).
   - Source apportionment tramite molecole Marker.
"""
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(template)
            
    # Leggi e mostra il contenuto
    with open(note_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Modalità lettura/scrittura
    st.markdown("Puoi modificare questo documento per tenere traccia della scaletta dei capitoli o dei risultati principali.")
    new_content = st.text_area("Modifica e Salva Mappa Tesi (Markdown):", value=content, height=400)
    
    if new_content != content:
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        st.success("✅ Modifiche alla Mappa della Tesi salvate con successo!")
