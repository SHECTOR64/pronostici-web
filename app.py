import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Classifica Pro Pronostici", layout="wide")

def estrai_q(cella):
    """Estrae numeri da celle come '2,50' o '2.50' o '2-1 (10.00)'"""
    if pd.isna(cella): return 0.0
    m = re.search(r"(\d+[\.,]\d+)", str(cella))
    if m: return float(m.group(1).replace(',', '.'))
    return 0.0

def calcola():
    try:
        file_path = "PRONOSTICIINCORSO.xlsx"
        # Carichiamo i due fogli
        df_q = pd.read_excel(file_path, sheet_name="QUOTE")
        # Carichiamo TUTTOQUI senza header per gestire le righe a mano
        df_p = pd.read_excel(file_path, sheet_name="TUTTOQUI", header=None)

        # --- 1. IDENTIFICAZIONE RISULTATI REALI (RIGA 2) ---
        # Partiamo dal presupposto che i risultati reali siano nella riga 2, colonne B, C, D...
        ris_reali = {}
        for i in range(1, 11):
            val = str(df_p.iloc[1, i]) # Riga 2, colonne dalla 2 in poi
            if "-" in val:
                gc, go = map(int, val.split("-"))
                ris_reali[i] = {"res": val, "gc": gc, "go": go}

        if not ris_reali:
            st.warning("Inserisci i risultati reali nella riga 2 del foglio TUTTOQUI (es. 2-0 nella colonna B2)")
            return

        # --- 2. LOGICA PARTITA +GOL / -GOL ---
        max_g = max(info['gc'] + info['go'] for info in ris_reali.values())
        min_g = min(info['gc'] + info['go'] for info in ris_reali.values())
        p_piu_gol = [i for i, info in ris_reali.items() if (info['gc'] + info['go']) == max_g]
        p_meno_gol = [i for i, info in ris_reali.items() if (info['gc'] + info['go']) == min_g]

        # --- 3. CALCOLO UTENTI (DA RIGA 4) ---
        classifica = []
        # La riga 4 è l'indice 3 in Python
        for idx in range(3, len(df_p)):
            row = df_p.iloc[idx]
            utente = str(row[0]) # Colonna A: Nickname
            if utente == "nan" or "RISULTATI" in utente.upper(): continue

            # Inizializziamo i contatori per le categorie richieste
            dati = {
                "ESATTO": 0.0, "SEGNI": 0.0, "GOL_C": 0.0, "GOL_O": 0.0, 
                "BONUS_S": 0.0, "SPECIALI": 0.0, "EXTRA": 0.0
            }
            num_segni, num_bonus = 0, 0
            piu_g_presa, meno_g_presa = False, False

            for i in range(1, 11):
                if i not in ris_reali: continue
                info_r = ris_reali[i]
                
                # Pronostico utente (Colonna corrispondente alla partita)
                prono_u = str(row[i])
                m_u = re.search(r"(\d+)-(\d+)", prono_u)
                if not m_u: continue
                gc_u, go_u = map(int, m_u.groups())

                # Quote dal foglio QUOTE (Riga i-1 perché header=0)
                q_riga = df_q.iloc[i-1]
                segno_r = "1" if info_r['gc'] > info_r['go'] else ("2" if info_r['go'] > info_r['gc'] else "X")
                segno_u = "1" if gc_u > go_u else ("2" if go_u > gc_u else "X")

                # REGOLE PUNTI
                # Se Risultato Esatto: prendi Esatto + Segno (CASA/X/COSA)
                if gc_u == info_r['gc'] and go_u == info_r['go']:
                    val_esatto = estrai_q(q_riga.get(info_r['res'], 0))
                    val_segno = estrai_q(q_riga.get(segno_r, 0))
                    punti_match = val_esatto + val_segno
                    
                    # Jolly o +Difficile (Colonna G del foglio Quote indica la partita +Difficile)
                    p_difficile = int(df_q.columns[6]) if str(df_q.columns[6]).isdigit() else 99
                    if i == p_difficile: punti_match *= 2
                    
                    dati["ESATTO"] += punti_match
                    num_segni += 1
                else:
                    # Se non prendi l'esatto, verifichiamo segno e gol singoli
                    if segno_u == segno_r: 
                        dati["SEGNI"] += estrai_q(q_riga.get(segno_r, 0))
                        num_segni += 1
                    if gc_u == info_r['gc']: dati["GOL_C"] += estrai_q(q_riga.get(f"GC{gc_u}", 0))
                    if go_u == info_r['go']: dati["GOL_O"] += estrai_q(q_riga.get(f"GO{go_u}", 0))

                # BONUS G/NG U/OV (Supponiamo siano nelle colonne successive dell'utente)
                # Qui aggiungeremo la logica per le tue colonne bonus specifiche
                
            # Calcolo finali
            tot_parziale = sum(dati.values())
            jolly_turno_perc = estrai_q(row[24]) # Esempio: colonna Y è la 25esima (indice 24)
            totale_finale = tot_parziale * (1 + (jolly_turno_perc/100))

            classifica.append({
                "Utente": utente, "TOTALE": round(totale_finale, 2),
                "R.Esatto": dati["ESATTO"], "Segni": dati["SEGNI"], 
                "Gol Casa": dati["GOL_C"], "Gol Ospite": dati["GOL_O"]
            })

        st.table(pd.DataFrame(classifica).sort_values("TOTALE", ascending=False))

    except Exception as e:
        st.error(f"Errore nel calcolo: {e}")

calcola()