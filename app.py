import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Classifica Pro Pronostici", layout="wide")

def estrai_q(cella):
    if pd.isna(cella): return 0.0
    m = re.search(r"(\d+[\.,]\d+)", str(cella))
    if m: return float(m.group(1).replace(',', '.'))
    return 0.0

def calcola():
    try:
        file = "PRONOSTICIINCORSO.xlsx"
        df_q = pd.read_excel(file, sheet_name="QUOTE", header=0)
        df_p = pd.read_excel(file, sheet_name="TUTTOQUI", header=0)
        
        df_q.columns = [str(c).strip().upper() for c in df_q.columns]
        df_p.columns = [str(c).strip().upper() for c in df_p.columns]

        # 1. ANALISI GIORNATA (Risultati Reali in riga 2 di TUTTOQUI)
        ris_reali_row = df_p.iloc[0]
        partite_info = {}
        max_gol, min_gol = -1, 99
        p_piu_gol, p_meno_gol = [], []

        for i in range(1, 11):
            res = str(ris_reali_row.get(f'P{i}_RIS', ""))
            if "-" in res:
                gc, go = map(int, res.split('-'))
                tot = gc + go
                partite_info[i] = {'gc': gc, 'go': go, 'tot': tot, 'res': res}
                if tot > max_gol: max_gol = tot
                if tot < min_gol: min_gol = tot

        for i, info in partite_info.items():
            if info['tot'] == max_gol: p_piu_gol.append(i)
            if info['tot'] == min_gol: p_meno_gol.append(i)

        # Partita +Difficile (da colonna G del foglio QUOTE riga 1)
        p_difficile = int(df_q.iloc[0].get('G', 0))

        # 2. CALCOLO UTENTI (da riga 4)
        classifica = []
        for _, row in df_p.iloc[2:].iterrows():
            u = str(row.get('IL TUO NICK', ""))
            if u == "" or "RISULTATI" in u.upper(): continue

            p = {k: 0.0 for k in ['ESATTO', 'SEGNI', 'GOL_C', 'GOL_O', 'BONUS_S', 'SPECIALI', 'EXTRA']}
            bonus_centrati_count = 0
            segni_centrati_count = 0
            piu_gol_centrata = False
            meno_gol_centrata = False

            for i in range(1, 11):
                if i not in partite_info: continue
                info = partite_info[i]
                q_riga = df_q.iloc[i-1] # Riga corrispondente alla partita
                
                # Pronostico Utente
                prono_u = str(row.get(f'P{i}_RIS', ""))
                if "-" not in prono_u: continue
                gc_u, go_u = map(int, re.search(r"(\d+)-(\d+)", prono_u).groups())
                
                # Analisi Segni
                s_r = "1" if info['gc'] > info['go'] else ("2" if info['go'] > info['gc'] else "X")
                s_u = "1" if gc_u > go_u else ("2" if go_u > gc_u else "X")
                
                # A. RISULTATO ESATTO vs GOL CASA/OSPITE
                if gc_u == info['gc'] and go_u == info['go']:
                    quota_esatto = q_riga.get(info['res'], 0)
                    quota_segno = q_riga.get(s_r, 0)
                    valore = quota_esatto + quota_segno
                    
                    # Jolly o Difficile?
                    if str(row.get('JOLLY_PARTITA')) == str(i) or i == p_difficile:
                        valore *= 2
                    
                    p['ESATTO'] += valore
                    p['SEGNI'] += quota_segno
                else:
                    # Se non prende l'esatto, verifichiamo i singoli gol
                    if s_u == s_r: 
                        p['SEGNI'] += q_riga.get(s_r, 0)
                        segni_centrati_count += 1
                    if gc_u == info['gc']: p['GOL_C'] += q_riga.get(f'GC{gc_u}', 0)
                    if go_u == info['go']: p['GOL_O'] += q_riga.get(f'GO{go_u}', 0)

                # B. BONUS SEGNI (TUTTO O NIENTE)
                # Qui servirebbe una logica per verificare se TUTTI i bonus giocati sono ok
                # Per ora implementiamo la verifica del singolo bonus colonna
                bon_u = str(row.get(f'P{i}_BONUS', "")).upper()
                esito_g = "G" if info['gc']>0 and info['go']>0 else "NG"
                esito_uo = "OV" if info['tot']>2.5 else "U"
                
                if bon_u in [s_r, esito_g, esito_uo]:
                    p['BONUS_S'] += q_riga.get(bon_u, 0)
                    bonus_centrati_count += 1

                # C. PARTITA +GOL / -GOL
                if i in p_piu_gol and bon_u == "G" and esito_uo == "OV":
                    p['SPECIALI'] += (q_riga.get('G', 0) + q_riga.get('OV', 0))
                    piu_gol_centrata = True
                if i in p_meno_gol and bon_u == "NG" and esito_uo == "U":
                    p['SPECIALI'] += (q_riga.get('NG', 0) + q_riga.get('U', 0))
                    meno_gol_centrata = True

            # D. COPPIA & JOLLY TURNO
            if piu_gol_centrata and meno_gol_centrata:
                p['SPECIALI'] *= 2 # Bonus COPPIA

            # Extra Segni & Bonus
            p['EXTRA'] += {5:5, 6:10, 7:15, 8:25, 9:35, 10:50}.get(segni_centrati_count, 0)
            p['EXTRA'] += {5:10, 6:20, 7:30, 8:50, 9:70, 10:90}.get(bonus_centrati_count, 0)

            tot_day = sum(p.values())
            j_turno_perc = estrai_q(row.get('JOLLY_TURNO_PERC', 0))
            punti_finali = tot_day * (1 + (j_turno_perc/100))

            classifica.append({
                "Utente": u, "PT TOTALI": round(punti_finali, 2),
                "R.ESATTO": p['ESATTO'], "SEGNI": p['SEGNI'], "GOL C": p['GOL_C'],
                "GOL O": p['GOL_O'], "BONUS": p['BONUS_S'], "SPECIALI": p['SPECIALI'],
                "JOLLY %": j_turno_perc, "EXTRA": p['EXTRA']
            })

        res_df = pd.DataFrame(classifica).sort_values("PT TOTALI", ascending=False)
        st.table(res_df)

    except Exception as e:
        st.error(f"Errore: {e}")

calcola()