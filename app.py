import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Classifica Pronostici", layout="wide")
st.title("🏆 Classifica Live Pronostici")

def estrai_valore(cella):
    """Estrae un numero da una cella, gestendo parentesi o virgole"""
    if pd.isna(cella): return 0.0
    # Cerca numeri anche con virgola o tra parentesi
    match = re.search(r"(\d+[\.,]?\d*)", str(cella))
    if match:
        return float(match.group(1).replace(',', '.'))
    return 0.0

def calcola():
    try:
        file_path = "PRONOSTICIINCORSO.xlsx"
        df = pd.read_excel(file_path, sheet_name="TUTTOQUI")

        # RIGA 2 (Indice 0): Risultati Reali (es. 2-1)
        ris_reali = df.iloc[0]
        
        # RIGA 3 (Indice 1): Punteggi Categoria (1, X, 2, G, NG, U, OV)
        # Qui il programma legge quanto vale ogni segno per quella specifica partita
        punti_partita = df.iloc[1]

        # DALLA RIGA 4 IN POI (Indice 2): Utenti
        df_utenti = df.iloc[2:].copy()
        df_utenti = df_utenti.dropna(subset=['IL MIO NICK'])

        classifica = []

        for _, row in df_utenti.iterrows():
            nome = row['IL MIO NICK']
            punti_totali = 0
            bonus_presi = 0

            for i in range(1, 11):
                col_ris = f'P{i}_RIS'
                col_bonus = f'P{i}_BONUS'

                # 1. Verifica Risultato Reale (Riga 2)
                r_str = str(ris_reali[col_ris])
                if "-" not in r_str: continue

                try:
                    # Dati Reali
                    g_casa_r, g_ospite_r = map(int, r_str.split('-'))
                    segno_r = "1" if g_casa_r > g_ospite_r else "2" if g_ospite_r > g_casa_r else "X"
                    u_ov_r = "U" if (g_casa_r + g_ospite_r) < 2.5 else "OV"
                    g_ng_r = "G" if (g_casa_r > 0 and g_ospite_r > 0) else "NG"

                    # 2. Calcolo Punti Segno 1X2 (da Riga 3)
                    prono_u_str = str(row[col_ris])
                    prono_match = re.search(r'(\d+-\d+)', prono_u_str)
                    if not prono_match: continue
                    
                    g_casa_p, g_ospite_p = map(int, prono_match.group(1).split('-'))
                    segno_p = "1" if g_casa_p > g_ospite_p else "2" if g_ospite_p > g_casa_p else "X"

                    if segno_p == segno_r:
                        # Pesca il punteggio per quel segno dalla Riga 3
                        # Cerca una colonna che contiene il valore del segno (es. P1_1, P1_X, P1_2)
                        # Se i punti sono nella stessa cella del nome partita, serve un mapping specifico
                        punti_totali += estrai_valore(punti_partita[col_ris])

                    # 3. Risultato Esatto (Quota tra parentesi nel pronostico utente)
                    if g_casa_p == g_casa_r and g_ospite_p == g_ospite_r:
                        quota_re = estrai_valore(prono_u_str)
                        if int(row['JOLLY_PARTITA']) == i:
                            quota_re *= 2
                        punti_totali += quota_re

                    # 4. Bonus (G, NG, U, OV, 1, X, 2)
                    bonus_u = str(row[col_bonus]).upper().strip()
                    if bonus_u in [segno_r, u_ov_r, g_ng_r]:
                        bonus_presi += 1
                        # Aggiungiamo i punti specifici per il bonus dalla riga 3 se presenti
                        # punti_totali += estrai_valore(punti_partita[col_bonus])
                except:
                    continue

            # Bonus scala segni
            punti_totali += {5:5, 6:10, 7:15, 8:25, 9:35, 10:50}.get(bonus_presi, 0)
            
            # Jolly Turno %
            j_perc = estrai_valore(row['JOLLY_TURNO_PERC']) / 100
            punti_finali = punti_totali * (1 + j_perc)

            classifica.append({"Utente": nome, "Punti": round(punti_finali, 2)})

        # Classifica finale
        res_df = pd.DataFrame(classifica).sort_values(by="Punti", ascending=False)
        res_df.insert(0, 'Pos', range(1, len(res_df) + 1))
        st.table(res_df.set_index('Pos'))

    except Exception as e:
        st.error(f"Errore: {e}")

if __name__ == "__main__":
    calcola()
