import tkinter as tk
from tkinter import ttk
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("api_key.json", scope)
client = gspread.authorize(creds)

fichier_id = "1AbG1Cbei_ny33IFpC5Hyi2LkU00xe84xTQNsnVFUoVY"

fichier = client.open_by_key(fichier_id)

def get_sheet_names():
    try:
        feuilles = fichier.worksheets()
        return [feuille.title for feuille in feuilles]  
    except Exception as e:
        print(f"Erreur lors de la récupération des feuilles : {e}")
        return []

def trouver_ligne(sheet, nom):
    try:
        lignes = sheet.get_all_values()
        for i, ligne in enumerate(lignes):
            if nom in ligne:
                return i + 1  

        print(f"Erreur : {nom} non trouvé dans la feuille.")
        return None
    except Exception as e:
        print(f"Erreur lors de la recherche de la ligne : {e}")
        return None

def ajouter_valeurs(sheet, ligne, valeurs):
    try:
        mises_a_jour = []
        for col, valeur in valeurs.items():
            index_col = ord(col.upper()) - ord("A") + 1
            cellule = sheet.cell(ligne, index_col).value
            if cellule and cellule.isdigit():
                nouvelle_valeur = str(int(cellule) + valeur)
            else:
                nouvelle_valeur = str(valeur)
            mises_a_jour.append({
                "range": f"{col}{ligne}",  
                "values": [[nouvelle_valeur]]  
            })

        sheet.batch_update(mises_a_jour)
        print("Valeurs mises à jour avec succès !")
    except Exception as e:
        print(f"Erreur lors de la mise à jour des valeurs : {e}")

def confirmer_vente():
    try:
        nom_feuille = feuille_combobox.get()
        sheet = fichier.worksheet(nom_feuille)
        votre_nom = nom_entry.get()
        valeurs = {
            "D": int(menu_classic_combobox.get()),  # Menu Classic
            "E": int(menu_double_combobox.get()),  # Menu Double
            "F": int(menu_contrat_combobox.get()),  # Menu Contrat
            "G": int(tenders_combobox.get()),  # Tenders
            "H": int(petite_salade_combobox.get()),  # Petite Salade
            "I": int(boisson_combobox.get()),  # Boisson
            "J": int(milkshake_combobox.get()),  # MilkShake
        }

        ligne = trouver_ligne(sheet, votre_nom)
        if ligne:
            ajouter_valeurs(sheet, ligne, valeurs)
            resultat_label.config(text="Vente enregistrée avec succès !")
        else:
            resultat_label.config(text="Erreur : Ligne non trouvée.")
    except Exception as e:
        resultat_label.config(text=f"Erreur : {e}")

app = tk.Tk()
app.title("Enregistrement des ventes")

nom_label = tk.Label(app, text="Votre nom :")
nom_label.grid(row=0, column=0, padx=10, pady=10)
nom_entry = tk.Entry(app)
nom_entry.grid(row=0, column=1, padx=10, pady=10)

feuille_label = tk.Label(app, text="Sélectionner la feuille :")
feuille_label.grid(row=1, column=0, padx=10, pady=10)
feuille_combobox = ttk.Combobox(app, values=get_sheet_names())
feuille_combobox.grid(row=1, column=1, padx=10, pady=10)
feuille_combobox.current(0)

menu_classic_label = tk.Label(app, text="Menu Classic:")
menu_classic_label.grid(row=2, column=0, padx=10, pady=10)
menu_classic_combobox = ttk.Combobox(app, values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
menu_classic_combobox.grid(row=2, column=1, padx=10, pady=10)
menu_classic_combobox.current(0)

menu_double_label = tk.Label(app, text="Menu Double:")
menu_double_label.grid(row=3, column=0, padx=10, pady=10)
menu_double_combobox = ttk.Combobox(app, values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
menu_double_combobox.grid(row=3, column=1, padx=10, pady=10)
menu_double_combobox.current(0)

menu_contrat_label = tk.Label(app, text="Menu Contrat:")
menu_contrat_label.grid(row=4, column=0, padx=10, pady=10)
menu_contrat_combobox = ttk.Combobox(app, values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
menu_contrat_combobox.grid(row=4, column=1, padx=10, pady=10)
menu_contrat_combobox.current(0)

tenders_label = tk.Label(app, text="Tenders:")
tenders_label.grid(row=5, column=0, padx=10, pady=10)
tenders_combobox = ttk.Combobox(app, values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
tenders_combobox.grid(row=5, column=1, padx=10, pady=10)
tenders_combobox.current(0)

petite_salade_label = tk.Label(app, text="Petite Salade:")
petite_salade_label.grid(row=6, column=0, padx=10, pady=10)
petite_salade_combobox = ttk.Combobox(app, values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
petite_salade_combobox.grid(row=6, column=1, padx=10, pady=10)
petite_salade_combobox.current(0)

boisson_label = tk.Label(app, text="Boisson:")
boisson_label.grid(row=7, column=0, padx=10, pady=10)
boisson_combobox = ttk.Combobox(app, values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
boisson_combobox.grid(row=7, column=1, padx=10, pady=10)
boisson_combobox.current(0)

milkshake_label = tk.Label(app, text="MilkShake:")
milkshake_label.grid(row=8, column=0, padx=10, pady=10)
milkshake_combobox = ttk.Combobox(app, values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
milkshake_combobox.grid(row=8, column=1, padx=10, pady=10)
milkshake_combobox.current(0)

confirmer_button = tk.Button(app, text="Confirmer la vente", command=confirmer_vente)
confirmer_button.grid(row=9, column=0, columnspan=2, padx=10, pady=10)

resultat_label = tk.Label(app, text="")
resultat_label.grid(row=10, column=0, columnspan=2, padx=10, pady=10)

app.mainloop()