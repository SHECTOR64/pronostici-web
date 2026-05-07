import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Classifica Pronostici", layout="wide")
st.title("🏆 Classifica Live Pronostici")

def estrai_valore(cella):
    """Estrae un numero da una cella, gestendo parentesi o virgole (es: '2-1 (9.50)' -> 9.5)"""
    if pd.isna(cella): return 0.0
    match = re.search(r"(\d+[\.,]?\d*)", str(cella))
    if match:
        return float(match.group(1).replace(',', '.'))
    return 0.0

def calcola():
    try:
        file_path = "PRONOSTICIINCORSO.xlsx"
        
        # 1. Carichiamo la testata dalla riga 3 (header=2 perché Python conta da 0)
        # Qui si trova "il tuo nick" e i vari "P1_RIS", "P1_BONUS", ecc.
        df = pd.read_excel(file_path, sheet_name="TUTTOQUI", header=2)
        
        # Pulizia intestazioni: tutto maiuscolo e senza spazi per evitare errori
        df.columns = [str(c).strip().upper() for c in df.columns]

        # 2. Carichiamo i Risultati Reali dalla riga 2 (indice 1 nel file grezzo)
        df_raw = pd.read_excel(file_path, sheet_name="TUTTOQUI", header=None)
        ris_reali_row = df_raw.iloc[1]
        
        # Creiamo un dizionario per i risultati reali usando i nomi delle colonne puliti
        ris_reali = {}
        for i, col_name in enumerate(df.columns):
            ris_reali[col_name] = ris_reali_row[i]

        # 3. Prepariamo i dati degli utenti (da riga 4 in poi)
        df_utenti = df.copy()
        # Filtriamo le righe dove il nick è presente
        if 'IL TUO NICK' in df_utenti.columns:
            df_utenti = df_utenti.dropna(subset=['IL TUO NICK'])
            col_nome_utente = 'IL TUO NICK'
        elif 'IL MIO NICK' in df_utenti.columns:
            df_utenti = df_utenti.dropna(subset=['IL MIO NICK'])
            col_nome_utente = 'IL MIO NICK'
        else:
            st.error("Errore: Non trovo la colonna del Nickname (A3). Controlla che sia scritto 'il tuo nick'.")
            return

        classifica = []

        for _, row in df_utenti.iterrows():
            nome = row[col_nome_utente]
            punti_totali = 0
            bonus_presi = 0

            # Ciclo sulle 10 partite
            for i in range(1, 11):
                col_ris = f'P{i}_RIS'
                col_bonus = f'P{i}_BONUS'

                if col_ris not in ris_reali or col_ris not in row:
                    continue

                # Controllo se il risultato reale è inserito (deve esserci il trattino '-')
                r_str = str(ris_reali[col_ris])
                if "-" not in r_str:
                    continue

                try:
                    # Estrazione Gol Reali e Segno (1X2, U/O, G/NG)
                    g_casa_r, g_ospite_r = map(int, r_str.split('-'))
                    segno_r = "1" if g_casa_r > g_ospite_r else "2" if g_ospite_r > g_casa_r else "X"
                    u_ov_r = "U" if (g_casa_r + g_ospite_r) < 2.5 else "OV"
                    g_ng_r = "G" if (g_casa_r > 0 and g_ospite_r > 0) else "NG"

                    # Pronostico Utente
                    prono_u_str = str(row[col_ris])
                    prono_match = re.search(r'(\d+-\d+)', prono_u_str)
                    if not prono_match: continue
                    
                    g_casa_p, g_ospite_p = map(int, prono_match.group(1).split('-'))
                    segno_p = "1" if g_casa_p > g_ospite_p else "2" if g_ospite_p > g_casa_p else "X"

                    # --- ASSEGNAZIONE PUNTI ---
                    
                    # 1. Punti Segno (Indovinare 1, X o 2) - Punti presi dalla riga 3 (testata)
                    if segno_p == segno_r:
                        # Se nella riga 3 sotto P1_RIS c'è un valore numerico, usa quello
                        punti_totali += 3.0 # Valore di base, puoi automatizzarlo

                    # 2. Risultato Esatto (Punti tra parentesi nel pronostico utente)
                    if g_casa_p == g_casa_r and g_ospite_p == g_ospite_r:
                        punti_esatto = estrai_valore(prono_u_str)
                        # Moltiplicatore Jolly Partita
                        if 'JOLLY_PARTITA' in row and str(row['JOLLY_PARTITA']) == str(i):
                            punti_esatto *= 2
                        punti_totali += punti_esatto

                    # 3. Bonus Colonna (G, NG, U, OV, 1, X, 2)
                    if col_bonus in row:
                        bonus_u = str(row[col_bonus]).upper().strip()
                        if bonus_u in [segno_r, u_ov_r, g_ng_r]:
                            bonus_presi += 1
                except:
                    continue

            # Bonus Scala Segni (5 indovinati = 5pt, 6 = 10pt, etc.)
            bonus_scala = {5:5, 6:10, 7:15, 8:25, 9:35, 10:50}.get(bonus_presi, 0)
            punti_totali += bonus_scala
            
            # Moltiplicatore Jolly Turno %
            j_perc = 0
            if 'JOLLY_TURNO_PERC' in row:
                j_perc = estrai_valore(row['JOLLY_TURNO_PERC']) / 100
            
            punti_finali = punti_totali * (1 + j_perc)

            classifica.append({
                "Utente": nome, 
                "Punti": round(punti_finali, 2), 
                "Bonus Presi": bonus_presi
            })

        # Generazione Classifica
        if classifica:
            res_df = pd.DataFrame(classifica).sort_values(by="Punti", ascending=False)
            res_df.insert(0, 'Pos', range(1, len(res_df) + 1))
            st.table(res_df.set_index('Pos'))
        else:
            st.info("In attesa di risultati validi nella Riga 2 dell'Excel...")

    except Exception as e:
        st.error(f"Errore durante il calcolo: {e}")
        st.info("Assicurati che il file Excel si chiami PRONOSTICIINCORSO.xlsx e il foglio TUTTOQUI.")

if __name__ == "__main__":
    calcola()