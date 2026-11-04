import os
from google import genai
from pydantic import BaseModel, Field

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# --- SCHEMI PER I 3 RICHIAMI ---

# Richiamo 1
class EstrazioneCriteri(BaseModel):
    richiesta_pulita: str = Field(description="Step 2: Riformulazione e pulizia della richiesta utente")
    parole_chiave: list[str] = Field(description="Step 3: Parole chiave estratte")
    criteri_e_pesi: dict[str, float] = Field(
        description="Step 3: Ambiti o criteri di valutazione con pesi da 0.0 a 1.0")


# Richiamo 2
class ConsultoDatasetAI(BaseModel):
    sintesi_risultanze_per_zona: dict[str, str] = Field(
        description="Step 4 e 5: Analisi incrociata tra documentazione dataset e dati grezzi per ogni zona")
    elementi_chiave_trovati: dict[str, list[str]] = Field(
        description="Enti o indicatori rilevanti trovati nel dataset per ciascun quartiere")


# Richiamo 3
class PunteggioNormalizzatoZona(BaseModel):
    denom_quartiere: str
    ragionamento_cot: str = Field(
        description="Chain of Thought sul perché questo quartiere merita tale punteggio rispetto agli altri")
    punteggio_normalizzato: float = Field(
        description="Punteggio finale rigorosamente normalizzato tra 0 e 100 basato sulla distribuzione dell'intera città")
    motivazione: str
    enti_interessati: list[str]


class RisultatoWorkflowCompleto(BaseModel):
    analisi_distribuzione_globale: str = Field(
        description="Valutazione complessiva per garantire che i punteggi siano ben distribuiti ed equi")
    valutazioni_finali: list[PunteggioNormalizzatoZona]


def esegui_workflow_a_tre_fasi(prompt_utente: str, documentazione_dataset: str, dati_grezzi_per_zona: dict,
                               lista_quartieri: list[str]):
    # =========================================================================
    # RICHIAMO 1: Valutazione Criteri e Ambiti (Step 2 & 3)
    # =========================================================================
    prompt_1 = f"""
    Sei un assistente AI specializzato in analisi territoriale.
    Analizza la richiesta dell'utente (Step 1): "{prompt_utente}"

    Compiti (Step 2 e 3):
    1. Pulisci e formula la richiesta in modo strutturato.
    2. Estrai le parole chiave fondamentali.
    3. Definisci i criteri di valutazione e assegna a ciascuno un peso di rilevanza da 0.0 a 1.0.
    """

    res_1 = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt_1,
        config={'response_mime_type': 'application/json', 'response_schema': EstrazioneCriteri}
    )
    criteri_estratti: EstrazioneCriteri = res_1.parsed

    # =========================================================================
    # RICHIAMO 2: Consulto Documentazione e Dataset (Step 4 & 5)
    # =========================================================================
    prompt_2 = f"""
    Criteri e pesi stabiliti nella fase precedente: {criteri_estratti.model_dump_json()}
    Documentazione del dataset (Step 4): {documentazione_dataset}
    Dati estratti dal dataset grezzo (Step 5): {dati_grezzi_per_zona}

    Compiti:
    - Consulta la documentazione per interpretare correttamente i dati.
    - Estrai e riassumi le risultanze del dataset mappandole sui quartieri disponibili ({lista_quartieri}) 
      in base ai criteri definiti.
    """

    res_2 = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt_2,
        config={'response_mime_type': 'application/json', 'response_schema': ConsultoDatasetAI}
    )
    risultanze_dataset: ConsultoDatasetAI = res_2.parsed

    # =========================================================================
    # RICHIAMO 3: Chain of Thought, Punteggio e Normalizzazione (Step 6 & 7)
    # =========================================================================
    prompt_3 = f"""
    Criteri originali: {criteri_estratti.model_dump_json()}
    Risultanze del dataset per zona (Step 5): {risultanze_dataset.model_dump_json()}
    Elenco di tutti i quartieri della città: {lista_quartieri}

    Compiti (Step 6 e 7):
    1. Esegui un Chain of Thought (ragionamento_cot) valutando la performance di ogni quartiere in base ai criteri.
    2. Calcola un punteggio grezzo e applica una **normalizzazione globale** in scala 0-100, facendo in modo che 
       il quartiere migliore si attesti vicino a 100 e quello peggiore vicino a 0, evitando appiattimenti.
    3. Restituisci la zona, il punteggio normalizzato, la motivazione e gli enti interessati.
    """

    res_3 = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt_3,
        config={'response_mime_type': 'application/json', 'response_schema': RisultatoWorkflowCompleto}
    )

    return criteri_estratti, risultanze_dataset, res_3.parsed