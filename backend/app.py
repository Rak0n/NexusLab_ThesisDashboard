import streamlit as st

# 1. SETUP GLOBALE (Deve essere il primo comando Streamlit)
st.set_page_config(
    page_title="NexusLab | LIMS",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. INIZIALIZZAZIONE STATO DI ROUTING
if 'current_view' not in st.session_state:
    st.session_state.current_view = "Control Tower"

def set_view(view_name):
    """Aggiorna lo stato della vista corrente quando si clicca un bottone."""
    st.session_state.current_view = view_name

# 3. SIDEBAR DI NAVIGAZIONE (LEFT)
with st.sidebar:
    st.title("🧪 NexusLab")
    st.caption("Data Workflow & LIMS")
    
    # Sezione Documentazione (Nuova)
    st.markdown("---")
    st.subheader("📚 DOCUMENTAZIONE")
    st.button("📖 Mappa Tesi", on_click=set_view, args=("Tesi",), use_container_width=True)

    # Sezione Database
    st.markdown("---")
    st.subheader("📂 DATABASE")
    st.button("🏗️ Control Tower", on_click=set_view, args=("Control Tower",), use_container_width=True)
    st.button("🧫 Feedstocks", on_click=set_view, args=("Feedstocks",), use_container_width=True)
    
    st.markdown("---")
    
    # Sezione Motori di Analisi
    st.subheader("🔬 ANALYSIS")
    st.button("🔴 GC-MS", on_click=set_view, args=("GC-MS",), use_container_width=True)
    st.button("🟢 CHNSO", on_click=set_view, args=("CHNSO",), use_container_width=True)
    st.button("🟣 GC Gas", on_click=set_view, args=("GC",), use_container_width=True)

# 4. ROUTER DELLE VISTE (MAIN WORKSPACE)
if st.session_state.current_view == "Control Tower":
    import views.view_control_tower as vct
    vct.render()

elif st.session_state.current_view == "Tesi":
    import views.view_thesis_map as vtesi
    vtesi.render()

elif st.session_state.current_view == "Feedstocks":
    st.title("🧫 Anagrafica Feedstocks")
    st.info("🚧 Modulo in costruzione (Fase successiva)")

elif st.session_state.current_view == "GC-MS":
    import views.view_gcms as vgcms
    vgcms.render()

elif st.session_state.current_view == "CHNSO":
    import views.view_chnso as vchnso
    vchnso.render()

elif st.session_state.current_view == "GC":
    import views.view_gc as vgc
    vgc.render()

elif st.session_state.current_view == "Deep Dive":
    import views.view_deepdive as vdeep
    vdeep.render()
