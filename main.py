import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from PIL import Image, ImageTk
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import datetime

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("api_key.json", scope)
client = gspread.authorize(creds)

fichier = None

fichiers_ids = {
    "Ventes civil": "1aP0wCHs4sxfbYwd68Kj-lPi75P4awfCZcJcKvuh_wto",
    "Ventes contrat": "1t0Kc1PIe2jTokKqstNQLd1rBvSe27rdPrb3x2AyAFhU"
}

def get_sheet_names():
    global fichier
    try:
        if fichier:
            feuilles = fichier.worksheets()
            noms_feuilles = [feuille.title for feuille in feuilles]
            return noms_feuilles
        else:
            return []
    except Exception as e:
        print(f"Erreur lors de la récupération des feuilles : {e}")
        return []

def trouver_premiere_ligne_vide(sheet):
    try:
        colonnes_b = sheet.col_values(4)
        for i, valeur in enumerate(colonnes_b[5:], start=6):  
            if not valeur: 
                return i
        return len(colonnes_b) + 1 
    except Exception as e:
        print(f"Erreur lors de la recherche de la première cellule vide de la colonne B : {e}")
        return None

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
        rows = sheet.row_count
        cols = sheet.col_count
        print(f"Rows: {rows}, Columns: {cols}")
    
        if ligne > rows:
            sheet.add_rows(ligne - rows)
        mises_a_jour = []
        for col, valeur in valeurs.items():
            index_col = ord(col.upper()) - ord("A") + 1
            if index_col > cols:
                sheet.add_cols(index_col - cols)
            
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
    global fichier
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
            menu_classic_combobox.set(0)
            menu_double_combobox.set(0)
            menu_contrat_combobox.set(0)
            tenders_combobox.set(0)
            petite_salade_combobox.set(0)
            boisson_combobox.set(0)
            milkshake_combobox.set(0)
        else:
            resultat_label.config(text="Erreur : Ligne non trouvée.")
    except Exception as e:
        resultat_label.config(text=f"Erreur : {e}")

def confirmer_vente2():
    global fichier
    try:
        nom_feuille = feuille_combobox.get()
        sheet = fichier.worksheet(nom_feuille)
        date_aujourdhui = datetime.datetime.now().strftime('%Y-%m-%d')
        valeurs = {
            "B": str(nom2_entry.get()),     # Vendeur
            "D": str(client_entry.get()),   # Client
            "E": date_aujourdhui,           # Date du jour
            "F": "TRUE"                     # Case à cocher
        }
        ligne = trouver_premiere_ligne_vide(sheet)
        if ligne:
            ajouter_valeurs(sheet, ligne, valeurs)
            resultat_label.config(text="Vente enregistrée avec succès !")
            reponse = messagebox.askyesno("Ajouter un autre client", "Voulez-vous ajouter un autre client ?")
            if reponse:
                ajouter_client()
            else:
                client_entry.delete(0, tk.END)
                date_entry.set_date(datetime.datetime.now())
        else:
            resultat_label.config(text="Erreur : Ligne non trouvée.")
    except Exception as e:
        resultat_label.config(text=f"Erreur : {e}")


def ajouter_client():
    client_label2 = tk.Label(app, text="Client :")
    client_entry2 = tk.Entry(app)
    client_label2.grid(row=len(client_entry.winfo_children())+5, column=0, padx=10, pady=10)
    client_entry2.grid(row=len(client_entry.winfo_children())+5, column=1, padx=10, pady=10)
    client_entry2.focus()


def enregistrer_vente():
    global fichier
    try:
        nom_feuille = feuille_combobox.get()
        sheet = fichier.worksheet(nom_feuille)
        ligne_vide = trouver_premiere_ligne_vide(sheet)
        
        if ligne_vide:
            vendeur = str(nom2_entry.get()).strip()
            client = str(client_entry.get()).strip()
            date = str(date_entry.get()).strip()
            valider = "✅"
            if vendeur and client and date:
                sheet.insert_row([vendeur, client, date, valider], ligne_vide)
                resultat_label.config(text="Vente enregistrée avec succès !")
                reponse = messagebox.askyesno("Ajouter un autre client", "Voulez-vous ajouter un autre client ?")
                if reponse:
                    ajouter_client()
                else:
                    client_entry.delete(0, tk.END)
                    date_entry.set_date(datetime.datetime.now())
            else:
                resultat_label.config(text="Erreur : Veuillez remplir tous les champs.")
        else:
            resultat_label.config(text="Erreur : Impossible de trouver une ligne vide.")
    except Exception as e:
        resultat_label.config(text=f"Erreur : {e}")

def charger_fichier():
    global fichier
    fichier_id = fichiers_ids[feuille_id_combobox.get()]
    
    fichiers_valides = {
        "1aP0wCHs4sxfbYwd68Kj-lPi75P4awfCZcJcKvuh_wto": afficher_elements,
        "1t0Kc1PIe2jTokKqstNQLd1rBvSe27rdPrb3x2AyAFhU": afficher_elements2
    }

    try:
        if fichier_id in fichiers_valides:
            fichier = client.open_by_key(fichier_id)
            feuilles = get_sheet_names()
            feuille_combobox["values"] = feuilles
            
            if feuilles:
                feuille_combobox.current(0)

            resultat_label.config(text="Fichier chargé avec succès !")
            fichiers_valides[fichier_id]()  
        else:
            resultat_label.config(text="Erreur : ID de fichier invalide.")
    
    except Exception as e:
        resultat_label.config(text=f"Erreur : {e}")

def masquer_tous_les_elements():
    masquer_elements()
    masquer_elements2()

def afficher_elements():
    masquer_tous_les_elements()
    nom_label.grid(row=2, column=0, padx=10, pady=10)
    nom_entry.grid(row=2, column=1, padx=10, pady=10)
    feuille_label.grid(row=3, column=0, padx=10, pady=10)
    feuille_combobox.grid(row=3, column=1, padx=10, pady=10)
    menu_classic_label.grid(row=4, column=0, padx=10, pady=10)
    menu_classic_combobox.grid(row=4, column=1, padx=10, pady=10)
    menu_double_label.grid(row=5, column=0, padx=10, pady=10)
    menu_double_combobox.grid(row=5, column=1, padx=10, pady=10)
    menu_contrat_label.grid(row=6, column=0, padx=10, pady=10)
    menu_contrat_combobox.grid(row=6, column=1, padx=10, pady=10)
    tenders_label.grid(row=7, column=0, padx=10, pady=10)
    tenders_combobox.grid(row=7, column=1, padx=10, pady=10)
    petite_salade_label.grid(row=8, column=0, padx=10, pady=10)
    petite_salade_combobox.grid(row=8, column=1, padx=10, pady=10)
    boisson_label.grid(row=9, column=0, padx=10, pady=10)
    boisson_combobox.grid(row=9, column=1, padx=10, pady=10)
    milkshake_label.grid(row=10, column=0, padx=10, pady=10)
    milkshake_combobox.grid(row=10, column=1, padx=10, pady=10)
    confirmer_button.grid(row=11, column=0, columnspan=3, padx=10, pady=10)
    resultat_label.grid(row=12, column=0, columnspan=3, padx=10, pady=10)

def afficher_elements2():
    masquer_tous_les_elements()
    nom2_label.grid(row=2, column=0, padx=15, pady=10, sticky="w")
    nom2_entry.grid(row=2, column=1, padx=15, pady=10, columnspan=2)
    feuille_label.grid(row=3, column=0, padx=15, pady=10, sticky="w")
    feuille_combobox.grid(row=3, column=1, padx=15, pady=10, columnspan=2)
    client_label.grid(row=4, column=0, padx=15, pady=10, sticky="w")
    client_entry.grid(row=4, column=1, padx=15, pady=10, columnspan=2)
    date_label.grid(row=5, column=0, padx=15, pady=10, sticky="w")
    date_entry.grid(row=5, column=1, padx=15, pady=10, columnspan=2)
    confirmer_button2.grid(row=6, column=0, columnspan=3, padx=15, pady=15)
    ajouter_client_button.grid(row=7, column=0, columnspan=3, padx=15, pady=10)
    resultat_label.grid(row=8, column=0, columnspan=3, padx=15, pady=10)

def masquer_elements():
    elements_a_cacher = [nom_label, nom_entry, feuille_label, feuille_combobox, menu_classic_label, menu_classic_combobox,
                         menu_double_label, menu_double_combobox, menu_contrat_label, menu_contrat_combobox,
                         tenders_label, tenders_combobox, petite_salade_label, petite_salade_combobox,
                         boisson_label, boisson_combobox, milkshake_label, milkshake_combobox, confirmer_button,
                         resultat_label]
    for elem in elements_a_cacher:
        elem.grid_remove()

def masquer_elements2():
    elements_a_cacher = [feuille_label, feuille_combobox, nom2_label, nom2_entry, client_label, client_entry,
                         date_label, date_entry, confirmer_button2, ajouter_client_button, resultat_label]
    for elem in elements_a_cacher:
        elem.grid_remove()

def sauvegarder_preferences():
    preferences = {
        "nom": nom_entry.get(),
        "feuille": feuille_combobox.get(),
        "fichier_id": feuille_id_combobox.get(),
        "vendeur": nom2_entry.get(),
    }

    dossier_preferences = os.path.join(os.getenv("APPDATA"), "burger_shot_commande_helper")
    if not os.path.exists(dossier_preferences):
        os.makedirs(dossier_preferences)

    chemin_fichier = os.path.join(dossier_preferences, "preferences.json")

    try:
        with open(chemin_fichier, "w") as f:
            json.dump(preferences, f, indent=4) 
        print("Préférences sauvegardées avec succès.")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des préférences : {e}")

def charger_preferences():
    dossier_preferences = os.path.join(os.getenv("APPDATA"), "burger_shot_commande_helper")
    chemin_fichier = os.path.join(dossier_preferences, "preferences.json")
    try:
        with open(chemin_fichier, "r") as f:
            preferences = json.load(f)
            print(f"Préférences chargées : {preferences}")
            nom_entry.insert(0, preferences.get("nom", ""))
            nom2_entry.insert(0, preferences.get("vendeur", ""))
            feuille_combobox.set(preferences.get("feuille", ""))
            feuille_id_combobox.set(preferences.get("fichier_id", ""))
            fichier_id = preferences.get("fichier_id", "")
            if fichier_id and fichier_id in fichiers_ids:
                fichier = client.open_by_key(fichiers_ids[fichier_id])
                feuilles = get_sheet_names()
                feuille_combobox["values"] = feuilles
                feuille_combobox.set(preferences.get("feuille", ""))
            else:
                fichier = None
    except FileNotFoundError:
        print("Fichier de préférences non trouvé.")
    except Exception as e:
        print(f"Erreur lors du chargement des préférences : {e}")

app = tk.Tk()
app.title("Burger Shot - Commande Helper")

image_path = "bs.png"  
image = Image.open(image_path)
image = image.resize((300, 100), Image.Resampling.LANCZOS)  
photo = ImageTk.PhotoImage(image)

titre_label = tk.Label(app, image=photo)
titre_label.grid(row=0, column=0, columnspan=3, pady=10)

feuille_id_label = tk.Label(app, text="Sélectionner le GSheet :")
feuille_id_label.grid(row=1, column=0, padx=10, pady=10)
feuille_id_combobox = ttk.Combobox(app, values=list(fichiers_ids.keys()))
feuille_id_combobox.grid(row=1, column=1, padx=10, pady=10)
feuille_id_combobox.current(0)

charger_fichier_button = tk.Button(app, text="Charger le fichier", command=charger_fichier)
charger_fichier_button.grid(row=1, column=2, padx=10, pady=10)

nom_label = tk.Label(app, text="Votre nom :")
nom_entry = tk.Entry(app)

nom2_label = tk.Label(app, text="Vendeur :")
nom2_entry = tk.Entry(app)

client_label = tk.Label(app, text="Client :")
client_entry = tk.Entry(app)

date_label = tk.Label(app, text="Date :")
date_entry = DateEntry(app, date_pattern='yyyy-mm-dd')

feuille_label = tk.Label(app, text="Sélectionner la feuille :")
feuille_combobox = ttk.Combobox(app, values=[])

menu_classic_label = tk.Label(app, text="Menu Classic:")
menu_classic_combobox = ttk.Combobox(app, values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
menu_classic_combobox.current(0)

menu_double_label = tk.Label(app, text="Menu Double:")
menu_double_combobox = ttk.Combobox(app, values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
menu_double_combobox.current(0)

menu_contrat_label = tk.Label(app, text="Menu Contrat:")
menu_contrat_combobox = ttk.Combobox(app, values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
menu_contrat_combobox.current(0)

tenders_label = tk.Label(app, text="Tenders:")
tenders_combobox = ttk.Combobox(app, values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
tenders_combobox.current(0)

petite_salade_label = tk.Label(app, text="Petite Salade:")
petite_salade_combobox = ttk.Combobox(app, values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
petite_salade_combobox.current(0)

boisson_label = tk.Label(app, text="Boisson:")
boisson_combobox = ttk.Combobox(app, values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
boisson_combobox.current(0)

milkshake_label = tk.Label(app, text="Milkshake:")
milkshake_combobox = ttk.Combobox(app, values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
milkshake_combobox.current(0)

confirmer_button = tk.Button(app, text="Confirmer la vente", command=confirmer_vente)

confirmer_button2 = tk.Button(app, text="Confirmer la vente", command=confirmer_vente2)

ajouter_client_button = tk.Button(app, text="Ajouter un autre client", command=ajouter_client)

sauvegarder_preferences_button = tk.Button(app, text="Sauvegarder les préférences", command=sauvegarder_preferences)
sauvegarder_preferences_button.grid(row=13, column=0, columnspan=3, padx=10, pady=10) 

resultat_label = tk.Label(app, text="")

charger_preferences()
app.mainloop()