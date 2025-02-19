import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from PIL import Image, ImageTk
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import datetime
import requests
from webhook import webhook_url

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("api_key.json", scope)
client = gspread.authorize(creds)

fichier = None

fichiers_ids = {
    "Ventes civil": "1aP0wCHs4sxfbYwd68Kj-lPi75P4awfCZcJcKvuh_wto",
    "Ventes contrat": "1t0Kc1PIe2jTokKqstNQLd1rBvSe27rdPrb3x2AyAFhU"
}

prix_unitaires = {
    "Menu Classic": 100,
    "Menu Double": 120,
    "Menu Contrat": 0,
    "Tenders": 60,
    "Petite Salade": 60,
    "Boisson": 30,
    "Milkshake": 40,
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

def envoyer_webhook_discord(info_vente):

    message = {
        "content": f"Nouvelle vente enregistrée :\n{json.dumps(info_vente, indent=4)}"
    }

    try:
        response = requests.post(webhook_url, json=message)
        response.raise_for_status()
        print("Webhook envoyé avec succès.")
    except Exception as e:
        print(f"Erreur lors de l'envoi du webhook : {e}")

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

            prix_total = calculer_prix_total()

            menu_classic_combobox.set(0)
            menu_double_combobox.set(0)
            menu_contrat_combobox.set(0)
            tenders_combobox.set(0)
            petite_salade_combobox.set(0)
            boisson_combobox.set(0)
            milkshake_combobox.set(0)

            menu_mapping = {
                "D": "Menu Classic",
                "E": "Menu Double",
                "F": "Menu Contrat",
                "G": "Tenders",
                "H": "Petite Salade",
                "I": "Boisson",
                "J": "MilkShake",
            }

            valeurs_nommees = {menu_mapping[k]: v for k, v in valeurs.items() if v > 0}

            if valeurs_nommees:
                embed = {
                "title": "🟢 Nouvelle vente [CIVILS]",
                "color": 0x00FF00,
                "author": {
                    "name": "Burger Shot - NoFace",
                    "icon_url": "https://i.postimg.cc/HLw6hBVh/bs-pp.png" 
                },
                "image": {
                    "url": "https://i.postimg.cc/DfjBHWwn/banner.jpg"
                },
                "fields": [
                    {
                        "name": "Vendeur",
                        "value": votre_nom,
                        "inline": True
                    },
                    {
                            "name": "Date et heure",
                            "value": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "inline": True
                        },
                        {
                            "name": "Détails de la vente",
                            "value": "\n".join([f"- **{k} :** {v}" for k, v in valeurs_nommees.items()]),
                            "inline": False
                        },
                        {
                            "name": "Prix total",
                            "value": f"{prix_total} $",
                            "inline": True
                        }
                    ],
                    "footer": {
                        "text": "Système de gestion des ventes"
                    },
                    "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                data = {
                    "embeds": [embed]
                }

                headers = {"Content-Type": "application/json"}
                response = requests.post(webhook_url, data=json.dumps(data), headers=headers)

                if response.status_code != 204:
                    print(f"Erreur lors de l'envoi du webhook : {response.status_code}")

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
        client_nom = client_entry.get().strip()

        if not client_nom:
            resultat_label.config(text="Erreur : Le champ 'Client' est vide.")
            return

        valeurs = {
            "B": str(nom2_entry.get()),     # Vendeur
            "D": client_nom,                # Client
            "E": date_aujourdhui,           # Date du jour
            "F": "TRUE"                     # Case à cocher
        }

        ligne = trouver_premiere_ligne_vide(sheet)
        if ligne:
            ajouter_valeurs(sheet, ligne, valeurs)
            resultat_label.config(text="Vente enregistrée avec succès !")
            client_entry.delete(0, tk.END)
            date_entry.set_date(datetime.datetime.now())

            info_vente = {
                "vendeur": nom2_entry.get(),
                "client": client_nom,      
                "date": date_aujourdhui,
                "feuille": nom_feuille,
                "date_heure": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            embed = {
                "title": "🟢 Nouvelle vente [CONTRATS]",
                "color": 0x00FF00,
                "author": {
                    "name": "Burger Shot - NoFace",
                    "icon_url": "https://i.postimg.cc/HLw6hBVh/bs-pp.png" 
                },
                "image": {
                    "url": "https://i.postimg.cc/DfjBHWwn/banner.jpg"
                },
                "fields": [
                    {
                        "name": "Vendeur",
                        "value": info_vente["vendeur"],
                        "inline": True
                    },
                    {
                        "name": "Client",
                        "value": info_vente["client"],
                        "inline": True
                    },
                    {
                        "name": "Date de la vente",
                        "value": info_vente["date"],
                        "inline": False
                    },
                    {
                        "name": "Organisme",
                        "value": info_vente["feuille"],
                        "inline": True
                    },
                    {
                        "name": "Date et heure",
                        "value": info_vente["date_heure"],
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Système de gestion des ventes"
                },
                "timestamp": info_vente["date_heure"]
            }

            data = {
                "embeds": [embed]
            }

            headers = {"Content-Type": "application/json"}
            response = requests.post(webhook_url, data=json.dumps(data), headers=headers)

            if response.status_code != 204:
                print(f"Erreur lors de l'envoi du webhook : {response.status_code}")

        else:
            resultat_label.config(text="Erreur : Ligne non trouvée.")
    except Exception as e:
        resultat_label.config(text=f"Erreur : {e}")

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
            feuille_a_selectionner = feuille_combobox.get()
            if feuille_a_selectionner in feuilles:
                feuille_combobox.set(feuille_a_selectionner)
            else:
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
    prix_total_label.grid(row=11, column=0, columnspan=3, padx=10, pady=10)
    confirmer_button.grid(row=12, column=0, columnspan=3, padx=10, pady=10)
    resultat_label.grid(row=13, column=0, columnspan=3, padx=10, pady=10)

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
    resultat_label.grid(row=8, column=0, columnspan=3, padx=15, pady=10)

def masquer_elements():
    elements_a_cacher = [nom_label, nom_entry, feuille_label, feuille_combobox, menu_classic_label, menu_classic_combobox,
                         menu_double_label, menu_double_combobox, menu_contrat_label, menu_contrat_combobox,
                         tenders_label, tenders_combobox, petite_salade_label, petite_salade_combobox,
                         boisson_label, boisson_combobox, milkshake_label, milkshake_combobox, prix_total_label, confirmer_button,
                         resultat_label]
    for elem in elements_a_cacher:
        elem.grid_remove()

def masquer_elements2():
    elements_a_cacher = [feuille_label, feuille_combobox, nom2_label, nom2_entry, client_label, client_entry,
                         date_label, date_entry, confirmer_button2, resultat_label]
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

def calculer_prix_total():
    try:
        quantites = {
            "Menu Classic": int(menu_classic_combobox.get()),
            "Menu Double": int(menu_double_combobox.get()),
            "Menu Contrat": int(menu_contrat_combobox.get()),
            "Tenders": int(tenders_combobox.get()),
            "Petite Salade": int(petite_salade_combobox.get()),
            "Boisson": int(boisson_combobox.get()),
            "Milkshake": int(milkshake_combobox.get()),
        }
        prix_total = 0
        for produit, quantite in quantites.items():
            prix_total += quantite * prix_unitaires[produit]
        prix_total_label.config(text=f"Prix total : {prix_total} $")
        return prix_total
    except ValueError:
        prix_total_label.config(text="Prix total : 0 $")
        return 0

def obtenir_bilan_ventes_par_jour():
    global fichier
    try:
        nom_feuille = feuille_combobox.get()
        sheet = fichier.worksheet(nom_feuille)
        lignes = sheet.get_all_values()

        bilan_ventes = {}

        for ligne in lignes[1:]:  
            date_vente = ligne[4]
            if date_vente:
                if date_vente not in bilan_ventes:
                    bilan_ventes[date_vente] = {
                        "Menu Classic": 0,
                        "Menu Double": 0,
                        "Menu Contrat": 0,
                        "Tenders": 0,
                        "Petite Salade": 0,
                        "Boisson": 0,
                        "Milkshake": 0,
                    }
                bilan_ventes[date_vente]["Menu Classic"] += int(ligne[3])  
                bilan_ventes[date_vente]["Menu Double"] += int(ligne[4])  
                bilan_ventes[date_vente]["Menu Contrat"] += int(ligne[5])  
                bilan_ventes[date_vente]["Tenders"] += int(ligne[6])  
                bilan_ventes[date_vente]["Petite Salade"] += int(ligne[7]) 
                bilan_ventes[date_vente]["Boisson"] += int(ligne[8]) 
                bilan_ventes[date_vente]["Milkshake"] += int(ligne[9])  

        bilan_window = tk.Toplevel(app)
        bilan_window.title("Bilan des ventes par jour")

        text_area = tk.Text(bilan_window, wrap=tk.WORD, width=80, height=20)
        text_area.pack(padx=10, pady=10)

        for date, ventes in bilan_ventes.items():
            text_area.insert(tk.END, f"Date: {date}\n")
            for produit, quantite in ventes.items():
                text_area.insert(tk.END, f"  {produit}: {quantite}\n")
            text_area.insert(tk.END, "\n")

    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de la récupération du bilan des ventes : {e}")

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

bilan_button = tk.Button(app, text="Afficher le bilan des ventes par jour", command=obtenir_bilan_ventes_par_jour)
bilan_button.grid(row=14, column=0, columnspan=3, padx=10, pady=10)

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

prix_total_label = tk.Label(app, text="Prix total : 0 $")

confirmer_button = tk.Button(app, text="Confirmer la vente", command=confirmer_vente)

confirmer_button2 = tk.Button(app, text="Confirmer la vente", command=confirmer_vente2)

sauvegarder_preferences_button = tk.Button(app, text="Sauvegarder les préférences", command=sauvegarder_preferences)
sauvegarder_preferences_button.grid(row=13, column=0, columnspan=3, padx=10, pady=10) 

resultat_label = tk.Label(app, text="")

for combobox in [menu_classic_combobox, menu_double_combobox, menu_contrat_combobox,
                 tenders_combobox, petite_salade_combobox, boisson_combobox, milkshake_combobox]:
    combobox.bind("<<ComboboxSelected>>", lambda event: calculer_prix_total())

charger_preferences()
app.mainloop()