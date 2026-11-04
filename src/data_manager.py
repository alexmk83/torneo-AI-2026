import pandas as pd
import os

def carica_e_filtra_dataset(csv_path: str, parole_chiave: list[str]) -> pd.DataFrame:
    """
    Step 5: Consulta e filtra il dataset degli enti in base alle parole chiave estratte dall'AI.
    """
    if not os.path.exists(csv_path):
        # Restituisce un DataFrame vuoto di sicurezza se il file non è ancora presente
        return pd.DataFrame(columns=['CAP', 'Quartiere', 'Nome_Ente', 'Ambito'])

    df = pd.read_csv(csv_path)
    if not parole_chiave:
        return df

    # Crea una maschera di ricerca booleana basata sulle parole chiave
    pattern = '|'.join(parole_chiave)
    mask = df.astype(str).apply(lambda col: col.str.contains(pattern, case=False, na=False)).any(axis=1)

    return df[mask]


def prepara_dati_per_ai(df_filtrato: pd.DataFrame, mapping_cap_path: str) -> dict:
    """
    Step 6: Calcola metriche per CAP/quartiere e unifica i dati per darli in pasto all'AI.
    """
    if df_filtrato.empty:
        return {}

    # Se il dataset contiene già la colonna 'Quartiere' che corrisponde al DENOM del KML:
    if 'Quartiere' in df_filtrato.columns:
        aggregato = df_filtrato.groupby('Quartiere').agg(
            conteggio_enti=('Nome_Ente', 'count'),
            ambiti_presenti=('Ambito', lambda x: ", ".join(x.unique()))
        ).to_dict(orient='index')
        return aggregato

    # Alternativa: se il dataset usa i CAP e possiedi una tabella di mapping CAP -> Quartiere
    if os.path.exists(mapping_cap_path):
        df_map = pd.read_csv(mapping_cap_path)
        df_unito = pd.merge(df_filtrato, df_map, on='CAP', how='inner')
        aggregato = df_unito.groupby('DENOM').agg(
            conteggio_enti=('Nome_Ente', 'count'),
            ambiti_presenti=('Ambito', lambda x: ", ".join(x.unique()))
        ).to_dict(orient='index')
        return aggregato

    return {}