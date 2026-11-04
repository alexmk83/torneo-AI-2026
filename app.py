import os
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Importa i moduli dalla cartella src
from src.kml_parser import parse_custom_kml
from src.data_manager import carica_e_filtra_dataset, prepara_dati_per_ai
from src.ai_workflow import esegui_workflow_a_tre_fasi

# Configurazione della pagina Streamlit
st.set_page_config(layout="wide", page_title="AI Geo-Scoring Interattivo")
st.title("🗺️ Mappa Interattiva con Workflow AI Multi-Richiamo")
st.markdown(
    "Analisi delle zone delimitate tramite file KML[cite: 1] ed elaborazione intelligente dei punteggi normalizzati.")

# --- BARRA LATERALE (CONFIGURAZIONI E PERCORSI) ---
with st.sidebar:
    st.header("⚙️ Configurazione Dati")
    kml_path = st.text_input("Percorso file KML", value="data/ex_neighborhood_boundary.kml")
    csv_path = st.text_input("Percorso Dataset Enti", value="data/dataset_enti.csv")
    doc_path = st.text_input("Percorso Documentazione", value="data/documentazione_dataset.md")
    map_path = st.text_input("Percorso Mapping CAP", value="data/mapping_cap_quartieri.csv")

    st.markdown("---")
    st.info("Assicurati di aver impostato la `GEMINI_API_KEY` nel file `.env`.")


# --- CARICAMENTO DATI GEOGRAFICI (KML) ---
@st.cache_data
def load_kml_cached(path):
    if os.path.exists(path):
        return parse_custom_kml(path)
    return None


gdf_zone = load_kml_cached(kml_path)

if gdf_zone is None or gdf_zone.empty:
    st.error(f"Impossibile trovare o leggere il file KML in: {kml_path}. Verifica il percorso nella sidebar.")
    st.stop()

lista_quartieri = gdf_zone['DENOM'].tolist()

# --- INPUT UTENTE (STEP 1) ---
st.subheader("1. Inserisci la richiesta")
prompt_utente = st.text_area(
    "Cosa stai cercando sul territorio?",
    placeholder="Es. Cerco zone con alta densità di servizi culturali, scuole e spazi verdi adatti alle famiglie..."
)

if st.button("🚀 Avvia Workflow AI (3 Richiami)", type="primary"):
    if not prompt_utente.strip():
        st.warning("Per favore, inserisci una richiesta valida.")
        st.stop()

    # Carica la documentazione del dataset se esiste
    doc_text = "Il dataset contiene informazioni su enti, scuole e servizi territoriali."
    if os.path.exists(doc_path):
        with open(doc_path, "r", encoding="utf-8") as f:
            doc_text = f.read()

    with st.spinner(
            "Esecuzione in corso: Richiamo 1 (Criteri) -> Richiamo 2 (Dataset) -> Richiamo 3 (Scoring & Normalizzazione)..."):

        try:
            # 1. Esegue il primo blocco per estrarre le parole chiave (necessario per il filtro)
            # Nota: Per semplicità esecutiva all'interno della UI, passiamo i dati filtrati o grezzi
            # Leggiamo prima il dataset completo o parziale
            df_grezzo = pd.read_csv(csv_path) if os.path.exists(csv_path) else pd.DataFrame()

            # Eseguiamo il workflow a tre fasi importato da src/ai_workflow.py
            criteri, risultanze, risultato_finale = esegui_workflow_a_tre_fasi(
                prompt_utente=prompt_utente,
                documentazione_dataset=doc_text,
                dati_grezzi_per_zona=df_grezzo.to_dict(orient='records') if not df_grezzo.empty else {},
                lista_quartieri=lista_quartieri
            )

        except Exception as e:
            st.error(f - 'Errore durante l esecuzione dell AI: {e}')
            st.stop()

    st.success("Workflow completato con successo!")

    # --- MOSTRA I DETTAGLI INTERMEDI NELLA SIDEBAR O EXPANDER ---
    with st.expander("🔍 Visualizza i dettagli intermedi dei 3 richiami AI"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Richiesta Pulita & Criteri (Richiamo 1):**")
            st.write(criteri.criteri_e_pesi)
        with col_b:
            st.markdown("**Analisi Distribuzione Globale (Richiamo 3):**")
            st.write(risultato_finale.analisi_distribuzione_globale)

    # --- PREPARAZIONE DATI PER LA MAPPA ---
    # Trasforma la lista di oggetti Pydantic finali in un DataFrame Pandas
    df_scores = pd.DataFrame([v.model_dump() for v in risultato_finale.valutazioni_finali])

    # Formatta gli enti interessati come stringa per i tooltip della mappa
    df_scores['enti_str'] = df_scores['enti_interessati'].apply(lambda x: ", ".join(x) if x else "Nessuno")

    # Unisce i punteggi calcolati dall'AI con il GeoDataFrame geometrico del KML basandosi sul nome (DENOM)[cite: 1]
    gdf_mappa = gdf_zone.merge(df_scores, left_on='DENOM', right_on='denom_quartiere', how='left')
    gdf_mappa['punteggio_normalizzato'] = gdf_mappa['punteggio_normalizzato'].fillna(0)

    # --- CREAZIONE MAPPA INTERATTIVA (FOLIUM) ---
    st.subheader("2. Mappa Interattiva dei Punteggi Normalizzati")

    # Centrata su Torino (coordinate medie basate sui dati del KML)
    m = folium.Map(location=[45.0703, 7.6869], zoom_start=12, tiles="CartoDB positron")

    # Aggiunge lo strato Choropleth colorato in base al punteggio normalizzato (0-100)
    folium.Choropleth(
        geo_data=gdf_mappa,
        data=gdf_mappa,
        columns=['DENOM', 'punteggio_normalizzato'],
        key_on='feature.properties.DENOM',
        fill_color='YlOrRd',  # Scala da giallo a rosso (o 'YlGnBu')
        fill_opacity=0.75,
        line_opacity=0.4,
        legend_name='Punteggio Rilevanza Normalizzato (0-100)'
    ).add_to(m)

    # Aggiunge i tooltip interattivi al passaggio del mouse
    folium.GeoJson(
        gdf_mappa,
        style_function=lambda x: {'fillColor': '#ffffff', 'color': '#000000', 'fillOpacity': 0.0, 'weight': 0.8},
        tooltip=folium.GeoJsonTooltip(
            fields=['DENOM', 'punteggio_normalizzato', 'enti_str', 'motivazione'],
            aliases=['Quartiere:', 'Punteggio Norm.:', 'Enti Coinvolti:', 'Motivazione CoT:'],
            localize=True
        )
    ).add_to(m)

    # Renderizza la mappa dentro l'app Streamlit
    st_folium(m, width=1100, height=650)

    # --- TABELLA DI RIEPILOGO FINALE ---
    st.subheader("3. Tabella Analitica per Zona")
    st.dataframe(
        df_scores[['denom_quartiere', 'punteggio_normalizzato', 'motivazione', 'enti_str']],
        use_container_width=True
    )