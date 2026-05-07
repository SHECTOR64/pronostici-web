import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Classifica Pronostici", layout="wide")
st.title("🏆 Classifica Live Pronostici")

def estrai_valore(cella):
    if pd.isna(cella): return 0.0
    match = re.search(r"(\d+[\.,]?\d*)", str(cella))
    if match:
        return float(match.group(1).replace(',', '.'))
    return 0.0

def calcola():
    try:
        file_path = "PRONOSTICIINCORSO.xlsx"
        
        # Carichiamo tutto: la Riga 1 (viola) è l'header (indice 0)
        df = pd.read_excel(file_path, sheet_name="TUTTOQUI", header=0)
        
        # Pulizia nomi colonne
        df.columns = [str(c).strip().upper() for c in df.columns]

        # RISULTATI REALI: Sono nella Riga 2 dell'Excel (Indice 0 del DataFrame)
        ris_reali = df.iloc[0]

        # UTENTI: Partono dalla RIGA 4 dell'Excel.
        # In Pandas, avendo usato la riga 1 come header:
        # Riga 2 dell'Excel = Indice 0
        # Riga 3 dell'Excel = Indice 1
        # Riga 4 dell'Excel = Indice 2 (Ecco dove partono gli utenti!)
        df_utenti = df.iloc[2:].copy()
        
        col_nome = 'IL TUO NICK'
        if col_nome not in df_utenti.columns:
            st.error(f"Errore: Non trovo '{col_nome}' in A1. Controlla il nome della cella viola.")
            return

        # Pulizia: togliamo righe dove il nick è vuoto
        df_utenti = df_utenti.dropna(subset=[col_nome])

        classifica = []

        for _, row in df_utenti.iterrows():
            nome = row[col_nome]
            
            # Saltiamo eventuali righe di intestazione ripetute o vuote
            if "RISULTATI" in str(nome).upper() or pd.isna(nome):
                continue
                
            punti_totali = 0
            bonus_presi = 0

            for i in range(1, 11):
                col_ris = f'P{i}_RIS'
                col_bonus = f'P{i}_BONUS'

                if col_ris not in df.columns: continue

                r_str = str(ris_reali[col_ris])
                # Se non c'è il trattino nella riga 2, la partita non è finita
                if "-" not in r_str: continue

                try:
                    # Analisi Risultato Reale (Riga 2)
                    g_casa_r, g_ospite_r = map(int, r_str.split('-'))
                    segno_r = "1" if g_casa_r > g_ospite_r else "2" if g_ospite_r > g_casa_r else "X"
                    u_ov_r = "U" if (g_casa_r + g_ospite_r) < 2.5 else "OV"
                    g_ng_r = "G" if (g_casa_r > 0 and g_ospite_r > 0) else "NG"

                    # Pronostico utente (Riga 4+)
                    prono_u_str = str(row[col_ris])
                    prono_match = re.search(r'(\d+-\d+)', prono_u_str)
                    if not prono_match: continue
                    
                    g_casa_p, g_ospite_p = map(int, prono_match.group(1).split('-'))
                    segno_p = "1" if g_casa_p > g_ospite_p else "2" if g_ospite_p > g_casa_p else "X"

                    # 1. Punti Segno (Indovinato 1X2) -> 3 punti fissi
                    if segno_p == segno_r:
                        punti_totali += 3.0

                    # 2. Risultato Esatto (Quota tra parentesi nel pronostico utente)
                    if g_casa_p == g_casa_r and g_ospite_p == g_ospite_r:
                        quota_re = estrai_valore(prono_u_str)
                        # Jolly Partita (raddoppia la quota del risultato esatto)
                        if 'JOLLY_PARTITA' in row and str(row['JOLLY_PARTITA']) == str(i):
                            quota_re *= 2
                        punti_totali += quota_re

                    # 3. Bonus Colonna (G/NG, U/O)
                    if col_bonus in row:
                        bonus_u = str(row[col_bonus]).upper().strip()
                        if bonus_u in [segno_r, u_ov_r, g_ng_r]:
                            bonus_presi += 1
                except:
                    continue

            # Bonus Scala per segni bonus indovinati
            bonus_scala = {5:5, 6:10, 7:15, 8:25, 9:35, 10:50}.get(bonus_presi, 0)
            punti_totali += bonus_scala
            
            # Jolly Turno % (Es. se l'utente ha 10, aumenta del 10%)
            j_perc = estrai_valore(row.get('JOLLY_TURNO_PERC', 0)) / 100
            punti_finali = punti_totali * (1 + j_perc)

            classifica.append({
                "Utente": nome, 
                "Punti": round(punti_finali, 2), 
                "Bonus Indovinati": bonus_presi
            })

        # Mostra la tabella
        if classifica:
            res_df = pd.DataFrame(classifica).sort_values(by="Punti", ascending=False)
            res_df.insert(0, 'Pos', range(1, len(res_df) + 1))
            st.table(res_df.set_index('Pos'))
        else:
            st.info("In attesa di dati validi... Controlla che i giocatori inizino dalla riga 4.")

    except Exception as e:
        st.error(f"Errore tecnico: {e}")

if __name__ == "__main__":
    calcola()