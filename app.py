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
        
        # 1. Leggiamo tutto partendo dalla RIGA 1 (quella viola con P1_RIS)
        df = pd.read_excel(file_path, sheet_name="TUTTOQUI", header=0)
        
        # Pulizia nomi colonne (P1_RIS, IL TUO NICK, etc.)
        df.columns = [str(c).strip().upper() for c in df.columns]

        # 2. RISULTATI REALI: Sono nella prima riga di dati (Riga 2 dell'Excel)
        # In pandas, dopo aver impostato header=0, la riga 2 dell'Excel è l'indice 0
        ris_reali = df.iloc[0]

        # 3. UTENTI: Iniziano dopo la riga dei risultati e la riga delle intestazioni secondarie
        # Se i nomi iniziano alla riga 4 dell'Excel, dobbiamo saltare le prime 2 righe di dati
        df_utenti = df.iloc[2:].copy()
        
        # Cerchiamo la colonna del nome (gestendo i due modi in cui l'hai chiamata)
        col_nome = None
        for c in ['IL TUO NICK', 'IL MIO NICK']:
            if c in df_utenti.columns:
                col_nome = c
                break
        
        if not col_nome:
            st.error("Non trovo la colonna 'il tuo nick'. Controlla la cella A3.")
            return

        df_utenti = df_utenti.dropna(subset=[col_nome])

        classifica = []

        for _, row in df_utenti.iterrows():
            nome = row[col_nome]
            punti_totali = 0
            bonus_presi = 0

            for i in range(1, 11):
                col_ris = f'P{i}_RIS'
                col_bonus = f'P{i}_BONUS'

                if col_ris not in df.columns: continue

                # Risultato Reale (Riga 2)
                r_str = str(ris_reali[col_ris])
                if "-" not in r_str: continue

                try:
                    # Analisi Risultato Reale
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

                    # Punti Segno (3 punti fissi se indovina 1X2)
                    if segno_p == segno_r:
                        punti_totali += 3.0

                    # Risultato Esatto (Quota tra parentesi)
                    if g_casa_p == g_casa_r and g_ospite_p == g_ospite_r:
                        quota_re = estrai_valore(prono_u_str)
                        # Jolly Partita (raddoppia)
                        if 'JOLLY_PARTITA' in row and str(row['JOLLY_PARTITA']) == str(i):
                            quota_re *= 2
                        punti_totali += quota_re

                    # Bonus (G/NG, U/O)
                    if col_bonus in row:
                        bonus_u = str(row[col_bonus]).upper().strip()
                        if bonus_u in [segno_r, u_ov_r, g_ng_r]:
                            bonus_presi += 1
                except:
                    continue

            # Bonus Scala
            punti_totali += {5:5, 6:10, 7:15, 8:25, 9:35, 10:50}.get(bonus_presi, 0)
            
            # Jolly Turno %
            j_perc = estrai_valore(row.get('JOLLY_TURNO_PERC', 0)) / 100
            punti_finali = punti_totali * (1 + j_perc)

            classifica.append({"Utente": nome, "Punti": round(punti_finali, 2), "Bonus": bonus_presi})

        res_df = pd.DataFrame(classifica).sort_values(by="Punti", ascending=False)
        res_df.insert(0, 'Pos', range(1, len(res_df) + 1))
        st.table(res_df.set_index('Pos'))

    except Exception as e:
        st.error(f"Errore: {e}")

if __name__ == "__main__":
    calcola()