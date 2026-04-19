import streamlit as st
import os
import base64

def render_svg_diagram():
    """Restituisce l'HTML con il diagramma SVG tecnico codificato in Base64 per evitare crash React."""
    svg_code = """
    <svg viewBox="0 0 1000 450" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <!-- Frecce -->
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569"/>
        </marker>
        <marker id="arrow-blue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#2563eb"/>
        </marker>
        <marker id="arrow-green" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981"/>
        </marker>
        <!-- Gradienti -->
        <linearGradient id="gradPyro" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#f87171" />
          <stop offset="100%" stop-color="#b91c1c" />
        </linearGradient>
        <linearGradient id="gradHTU" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#38bdf8" />
          <stop offset="100%" stop-color="#0369a1" />
        </linearGradient>
        <linearGradient id="gradOil" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#fbbf24" />
          <stop offset="100%" stop-color="#b45309" />
        </linearGradient>
      </defs>
      
      <!-- Sfondo -->
      <rect width="100%" height="100%" fill="#f1f5f9" rx="15" stroke="#cbd5e1" stroke-width="2"/>
      
      <!-- Titolo Diagramma -->
      <text x="30" y="40" font-family="Arial, sans-serif" font-size="20" fill="#1e293b" font-weight="bold">Waste-to-Chemicals: Biorefinery Flowsheet</text>

      <!-- COLLEGAMENTI (Tubi/Frecce) -->
      <!-- Feed -> Pyrolysis -->
      <path d="M 160 140 L 220 140" stroke="#475569" stroke-width="4" fill="none" marker-end="url(#arrow)"/>
      <!-- Pyrolysis -> Oil -->
      <path d="M 340 140 L 400 140" stroke="#475569" stroke-width="4" fill="none" marker-end="url(#arrow)"/>
      <!-- Pyrolysis -> Gas/Char -->
      <path d="M 280 80 L 280 40 L 320 40" stroke="#475569" stroke-width="2" fill="none" stroke-dasharray="5,5" marker-end="url(#arrow)"/>
      <path d="M 280 200 L 280 240 L 320 240" stroke="#475569" stroke-width="2" fill="none" stroke-dasharray="5,5" marker-end="url(#arrow)"/>
      
      <!-- Oil -> HTU -->
      <path d="M 500 140 L 560 140" stroke="#475569" stroke-width="4" fill="none" marker-end="url(#arrow)"/>
      <!-- Additivi -> HTU -->
      <path d="M 620 60 L 620 100" stroke="#2563eb" stroke-width="3" fill="none" marker-end="url(#arrow-blue)"/>
      
      <!-- HTU -> Prodotti -->
      <path d="M 680 140 L 740 140" stroke="#475569" stroke-width="4" fill="none" marker-end="url(#arrow)"/>
      <path d="M 620 200 L 620 280 L 740 280" stroke="#475569" stroke-width="3" fill="none" marker-end="url(#arrow)"/>

      <!-- Estrazione -> Platform Chemicals -->
      <path d="M 860 140 L 890 140 L 890 200 L 800 200 L 800 260" stroke="#10b981" stroke-width="3" fill="none" marker-end="url(#arrow-green)"/>

      <!-- ================= COMPONENTI (UNITÀ) ================= -->
      
      <!-- 1. FEEDSTOCK (Silos) -->
      <path d="M 40 100 L 160 100 L 140 180 L 60 180 Z" fill="#94a3b8" stroke="#475569" stroke-width="2"/>
      <text x="100" y="145" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="bold" text-anchor="middle">Feedstock</text>
      <text x="100" y="165" font-family="Arial, sans-serif" font-size="10" fill="#f1f5f9" text-anchor="middle">(Plastic/Sludge)</text>

      <!-- 2. REATTORE PIROLISI (Cilindro con fiamme) -->
      <rect x="220" y="80" width="120" height="120" rx="10" fill="url(#gradPyro)" stroke="#7f1d1d" stroke-width="2"/>
      <text x="280" y="130" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="bold" text-anchor="middle">Pyrolysis</text>
      <text x="280" y="150" font-family="Arial, sans-serif" font-size="12" fill="#fecaca" text-anchor="middle">450 - 600 °C</text>
      <!-- Simbolo gas/char -->
      <text x="330" y="45" font-family="Arial, sans-serif" font-size="11" fill="#475569" font-weight="bold">Py-Gas</text>
      <text x="330" y="245" font-family="Arial, sans-serif" font-size="11" fill="#475569" font-weight="bold">Bio-char</text>

      <!-- 3. SERBATOIO OLIO (Oil Tank) -->
      <ellipse cx="450" cy="180" rx="40" ry="10" fill="#b45309" stroke="#78350f" stroke-width="2"/>
      <rect x="410" y="100" width="80" height="80" fill="url(#gradOil)" stroke="#78350f" stroke-width="2"/>
      <ellipse cx="450" cy="100" rx="40" ry="10" fill="#f59e0b" stroke="#78350f" stroke-width="2"/>
      <text x="450" y="145" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="bold" text-anchor="middle">Py-Oil</text>

      <!-- 4. REATTORE HTU/HTL (Reattore Pressione) -->
      <rect x="560" y="100" width="120" height="100" rx="30" fill="url(#gradHTU)" stroke="#0c4a6e" stroke-width="2"/>
      <rect x="600" y="80" width="40" height="20" fill="#94a3b8" stroke="#475569" stroke-width="2"/> <!-- Valvola -->
      <text x="620" y="145" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="bold" text-anchor="middle">HTU / HTL</text>
      <text x="620" y="165" font-family="Arial, sans-serif" font-size="12" fill="#bae6fd" text-anchor="middle">300 °C | 15 MPa</text>
      <!-- Input Reagenti -->
      <text x="620" y="50" font-family="Arial, sans-serif" font-size="12" fill="#2563eb" font-weight="bold" text-anchor="middle">+ H₂O / Catalyst</text>

      <!-- 5. SEPARAZIONE / UPGRADED BIOCRUDE -->
      <rect x="740" y="100" width="120" height="80" fill="#14b8a6" stroke="#0f766e" stroke-width="2" rx="5"/>
      <text x="800" y="135" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="bold" text-anchor="middle">Upgraded</text>
      <text x="800" y="155" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="bold" text-anchor="middle">Biocrude</text>
      
      <!-- Aqueous Phase -->
      <rect x="740" y="260" width="120" height="40" fill="#60a5fa" stroke="#1d4ed8" stroke-width="2" rx="5"/>
      <text x="800" y="285" font-family="Arial, sans-serif" font-size="12" fill="white" font-weight="bold" text-anchor="middle">Aqueous Phase</text>

      <!-- 6. PLATFORM CHEMICALS (Beuta/Chimica) -->
      <rect x="720" y="320" width="160" height="80" fill="#8b5cf6" stroke="#4c1d95" stroke-width="2" rx="8" stroke-dasharray="4,4"/>
      <text x="800" y="350" font-family="Arial, sans-serif" font-size="14" fill="white" font-weight="bold" text-anchor="middle">Platform Chemicals</text>
      <text x="800" y="375" font-family="Arial, sans-serif" font-size="12" fill="#ede9fe" text-anchor="middle">Phenols, Alcohols, Ketones</text>
      <path d="M 800 260 L 800 320" stroke="#10b981" stroke-width="3" fill="none" stroke-dasharray="5,5" marker-end="url(#arrow-green)"/>
      <text x="810" y="295" font-family="Arial, sans-serif" font-size="11" fill="#10b981" font-weight="bold">Extraction / GC-MS</text>
      
    </svg>
    """
    
    # Codifica in Base64 per evitare il TypeError del DOM React di Streamlit
    b64 = base64.b64encode(svg_code.encode('utf-8')).decode('utf-8')
    return f'<img src="data:image/svg+xml;base64,{b64}" style="width: 100%; max-width: 900px; display: block; margin: auto; border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">'

def render():
    st.title("📖 Mappa Tesi & Bioraffineria")
    st.markdown("Panoramica del progetto di ricerca e del flusso di valorizzazione chimica (Waste-to-Chemicals).")
    
    st.markdown("---")
    
    # --- 1. RENDER SVG BASE64 ---
    st.subheader("⚙️ Schema di Processo: Dalla Matrice alla Molecola")
    svg_html = render_svg_diagram()
    st.markdown(f"<div style='margin-top: 15px; margin-bottom: 35px;'>{svg_html}</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --- 2. RENDER NOTE MARKDOWN ---
    st.subheader("📝 Struttura e Appunti della Tesi")
    
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
4. **Analisi GC-MS:**
   - Identificazione delle macro-famiglie chimiche.
   - Ricerca di composti ad alto valore aggiunto (Platform Chemicals).
   - Source apportionment tramite molecole Marker.
"""
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(template)
            
    with open(note_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    st.markdown("Usa questo spazio per tenere traccia della scaletta dei capitoli, dei ragionamenti o dei risultati principali.")
    new_content = st.text_area("Editor Markdown (salvataggio automatico):", value=content, height=450)
    
    if new_content != content:
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        st.success("✅ Documento aggiornato e salvato in `data_vault/notes/tesi_map.md`!")
