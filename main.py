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
from webhook import WEBHOOK_URL, USER_TOKEN, CHANNEL_ID
import matplotlib.pyplot as plt

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("api_key.json", scope)
client = gspread.authorize(creds)

fichier = None
current_page = None
message_id = None

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

clients_list = []

VENTES_JSON_PATH = "C:\\Users\\PC GAMER\\AppData\\Roaming\\burger_shot_commande_helper\\ventes.json"
CLIENTS_JSON_PATH = "C:\\Users\\PC GAMER\\AppData\\Roaming\\burger_shot_commande_helper\\clients.json"

def get_sheet_names():
    global fichier
    try:
        if fichier:
            return [feuille.title for feuille in fichier.worksheets()]
        return []
    except Exception as e:
        print(f"Erreur lors de la récupération des feuilles : {e}")
        return []

def envoyer_webhook_discord(info_vente):
    message = {"content": f"Nouvelle vente enregistrée :\n{json.dumps(info_vente, indent=4)}"}
    try:
        response = requests.post(WEBHOOK_URL, json=message)
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
        print(f"Erreur lors de la recherche de la première cellule vide : {e}")
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
        if isinstance(valeurs, dict):
            mises_a_jour = []
            for col, val in valeurs.items():
                index_col = ord(col.upper()) - ord("A") + 1
                cellule = sheet.cell(ligne, index_col).value
                nouvelle_valeur = str(int(cellule) + val) if cellule and cellule.isdigit() else str(val)
                mises_a_jour.append({"range": f"{col}{ligne}", "values": [[nouvelle_valeur]]})
            if mises_a_jour:
                sheet.batch_update(mises_a_jour)
                print("Valeurs mises à jour avec succès !")
        elif isinstance(valeurs, list):
            for valeur in valeurs:
                ajouter_valeurs(sheet, ligne, valeur)
                ligne += 1
    except Exception as e:
        print(f"Erreur lors de la mise à jour des valeurs : {e}")

def confirmer_vente():
    global fichier
    try:
        nom_feuille = feuille_combobox.get()
        sheet = fichier.worksheet(nom_feuille)
        votre_nom = nom_entry.get()

        colonnes_produits = {
            "D": "Menu Classic",
            "E": "Menu Double",
            "F": "Menu Contrat",
            "G": "Tenders",
            "H": "Petite Salade",
            "I": "Boisson",
            "J": "Milkshake"
        }

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

            for combobox in [menu_classic_combobox, menu_double_combobox, menu_contrat_combobox,
                             tenders_combobox, petite_salade_combobox, boisson_combobox, milkshake_combobox]:
                combobox.set(0)

            valeurs_nommees = {colonnes_produits[k]: v for k, v in valeurs.items() if v > 0}
            date_aujourdhui = datetime.datetime.now().strftime('%Y-%m-%d')
            sauvegarder_ventes_json(date_aujourdhui, valeurs_nommees)

            if valeurs_nommees:
                embed = {
                    "title": "🟢 Nouvelle vente [CIVILS]",
                    "color": 0x00FF00,
                    "author": {"name": "Burger Shot - NoFace", "icon_url": "https://i.postimg.cc/HLw6hBVh/bs-pp.png"},
                    "image": {"url": "https://i.postimg.cc/DfjBHWwn/banner.jpg"},
                    "fields": [
                        {"name": "Vendeur", "value": votre_nom, "inline": True},
                        {"name": "Date et heure", "value": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "inline": True},
                        {"name": "Détails de la vente", "value": "\n".join([f"- **{k} :** {v}" for k, v in valeurs_nommees.items()]), "inline": False},
                        {"name": "Prix total", "value": f"{prix_total} $", "inline": True}
                    ],
                    "footer": {"text": "Système de gestion des ventes"},
                    "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                data = {"embeds": [embed]}
                headers = {"Content-Type": "application/json"}
                response = requests.post(WEBHOOK_URL, data=json.dumps(data), headers=headers)
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
        
        clients_saisis = client_combobox.get().strip()
        
        if not clients_saisis:
            resultat_label.config(text="Erreur : Le champ 'Client' est vide.")
            return
        
        clients = [client.strip() for client in clients_saisis.split(",") if client.strip()]
        
        for client in clients:
            if client and client not in clients_list:
                clients_list.append(client)
                print(f"Client '{client}' ajouté avec succès.")
        
        if clients:
            client_combobox["values"] = clients_list
            sauvegarder_clients_json()
        
        valeurs = []
        for client in clients:
            valeurs.append({
                "B": str(nom2_entry.get()),     # Vendeur
                "D": client.strip(),            # Client
                "E": date_aujourdhui,           # Date du jour
                "F": "TRUE"                     # Case à cocher
            })
        
        ligne = trouver_premiere_ligne_vide(sheet)
        if ligne:
            ajouter_valeurs(sheet, ligne, valeurs)
            resultat_label.config(text="Vente enregistrée avec succès !")
            client_combobox.set('')
            date_entry.set_date(datetime.datetime.now())

            info_vente = {
                "vendeur": nom2_entry.get(),
                "clients": clients,
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
                        "name": "Clients",
                        "value": ", ".join(info_vente["clients"]),
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
            response = requests.post(WEBHOOK_URL, data=json.dumps(data), headers=headers)

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
    fichier_id = fichiers_ids.get(feuille_id_combobox.get())
    
    if not fichier_id:
        resultat_label.config(text="Erreur : ID de fichier invalide.")
        return
    
    nom_entry.delete(0, tk.END)
    nom2_entry.delete(0, tk.END)
    feuille_combobox.set("")
    feuille_id_combobox.set("")
    
    fichiers_valides = {
        "1aP0wCHs4sxfbYwd68Kj-lPi75P4awfCZcJcKvuh_wto": afficher_elements,
        "1t0Kc1PIe2jTokKqstNQLd1rBvSe27rdPrb3x2AyAFhU": afficher_elements2
    }
    charger_preferences()
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
            app.after(2000, lambda: resultat_label.config(text=""))
            fichiers_valides[fichier_id]()  
            masquer_boutons_bilan_et_graphique()
        else:
            resultat_label.config(text="Erreur : ID de fichier invalide.")
    
    except Exception as e:
        resultat_label.config(text=f"Erreur : {e}")

def obtenir_bilan_ventes_json():
    try:
        if not os.path.exists(VENTES_JSON_PATH):
            messagebox.showinfo("Info", "Aucune vente enregistrée.")
            return
        if os.path.getsize(VENTES_JSON_PATH) == 0:
            messagebox.showinfo("Info", "Aucune vente enregistrée.")
            return
        with open(VENTES_JSON_PATH, "r") as f:
            data = json.load(f)

        if not data:
            messagebox.showinfo("Info", "Aucune vente enregistrée.")
            return
        bilan_window = tk.Toplevel(app)
        bilan_window.title("Bilan des ventes")
        date_label = tk.Label(bilan_window, text="Choisir une date :")
        date_label.grid(row=0, column=0, padx=10, pady=10)
        date_selector = DateEntry(bilan_window, date_pattern='yyyy-mm-dd')
        date_selector.grid(row=0, column=1, padx=10, pady=10)
        afficher_button = tk.Button(bilan_window, text="Afficher les ventes", command=lambda: afficher_ventes_par_date(data, date_selector.get_date(), text_area))
        afficher_button.grid(row=0, column=2, padx=10, pady=10)
        text_area = tk.Text(bilan_window, wrap=tk.WORD, width=80, height=20)
        text_area.grid(row=1, column=0, columnspan=3, padx=10, pady=10)

    except json.JSONDecodeError:
        messagebox.showerror("Erreur", "Le fichier de ventes est vide ou corrompu.")
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de la récupération du bilan des ventes : {e}")
            
    except json.JSONDecodeError:
        messagebox.showerror("Erreur", "Le fichier de ventes est vide ou corrompu.")
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de la récupération du bilan des ventes : {e}")

def afficher_ventes_par_date(data, selected_date, text_area):
    try:
        selected_date_str = selected_date.strftime('%Y-%m-%d')
        text_area.delete(1.0, tk.END)
        if selected_date_str in data:
            ventes = data[selected_date_str]
            text_area.insert(tk.END, f"Date: {selected_date_str}\n")
            if not ventes:
                text_area.insert(tk.END, "  Aucune vente pour cette date.\n")
            else:
                for produit, quantite in ventes.items():
                    text_area.insert(tk.END, f"  {produit}: {quantite}\n")
            text_area.insert(tk.END, "\n")
        else:
            text_area.insert(tk.END, f"Aucune vente trouvée pour la date {selected_date_str}.\n")
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de l'affichage des ventes : {e}")

def generer_graphique_ventes():
    try:
        if not os.path.exists(VENTES_JSON_PATH):
            messagebox.showinfo("Info", "Aucune vente enregistrée.")
            return
        if os.path.getsize(VENTES_JSON_PATH) == 0:
            messagebox.showinfo("Info", "Aucune vente enregistrée.")
            return
        with open(VENTES_JSON_PATH, "r") as f:
            data = json.load(f)

        if not data:
            messagebox.showinfo("Info", "Aucune vente enregistrée.")
            return
        
        dates = sorted(data.keys())  
        produits = set()  

        for date in dates:
            produits.update(data[date].keys())

        ventes_par_produit = {produit: [] for produit in produits}
        for date in dates:
            for produit in produits:
                if produit in data[date]:
                    ventes_par_produit[produit].append(data[date][produit])
                else:
                    ventes_par_produit[produit].append(0) 

        plt.figure(figsize=(10, 6))
        for produit in produits:
            plt.plot(dates, ventes_par_produit[produit], label=produit, marker='o')

        plt.xlabel("DATE")
        plt.ylabel("QUANTITE VENDU")
        plt.title("Ventes de produits/date")
        plt.xticks(rotation=35) 
        plt.legend()  
        plt.tight_layout() 
        plt.show()  

    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de la génération du graphique : {e}")

def sauvegarder_clients_json():
    try:
        dossier_preferences = os.path.join(os.getenv("APPDATA"), "burger_shot_commande_helper")
        if not os.path.exists(dossier_preferences):
            os.makedirs(dossier_preferences)

        chemin_fichier = os.path.join(dossier_preferences, "clients.json")

        with open(chemin_fichier, "w") as f:
            json.dump(clients_list, f, indent=4)
        print("Clients sauvegardés avec succès.")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des clients : {e}")

def charger_clients_json():
    try:
        dossier_preferences = os.path.join(os.getenv("APPDATA"), "burger_shot_commande_helper")
        chemin_fichier = os.path.join(dossier_preferences, "clients.json")

        if os.path.exists(chemin_fichier):
            with open(chemin_fichier, "r") as f:
                global clients_list
                clients_list = json.load(f)
                print("Clients chargés avec succès.")
    except Exception as e:
        print(f"Erreur lors du chargement des clients : {e}")

def masquer_tous_les_elements():
    masquer_elements()
    masquer_elements2()

def afficher_elements():
    global current_page
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
    retour_button.grid(row=14, column=0, columnspan=3, padx=10, pady=10)
    sauvegarder_preferences_button.grid_remove()
    prise_service_button.grid_remove()
    current_page = "ventes_civiles"

def afficher_elements2():
    global current_page
    masquer_tous_les_elements()
    nom2_label.grid(row=2, column=0, padx=15, pady=10, sticky="w")
    nom2_entry.grid(row=2, column=1, padx=15, pady=10, columnspan=2)
    feuille_label.grid(row=3, column=0, padx=15, pady=10, sticky="w")
    feuille_combobox.grid(row=3, column=1, padx=15, pady=10, columnspan=2)
    client_label.grid(row=4, column=0, padx=15, pady=10, sticky="w")
    client_entry.grid(row=4, column=1, padx=15, pady=10, columnspan=2)
    client_combobox.grid(row=4, column=1, padx=15, pady=10, columnspan=2) 
    date_label.grid(row=5, column=0, padx=15, pady=10, sticky="w")
    date_entry.grid(row=5, column=1, padx=15, pady=10, columnspan=2)
    confirmer_button2.grid(row=6, column=0, columnspan=3, padx=15, pady=15)
    resultat_label.grid(row=7, column=0, columnspan=3, padx=15, pady=10)
    retour_button.grid(row=8, column=0, columnspan=3, padx=15, pady=10)
    sauvegarder_preferences_button.grid_remove()
    prise_service_button.grid_remove()
    
    current_page = "ventes_contrats"

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
                         client_combobox, date_label, date_entry, confirmer_button2, resultat_label]
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

def sauvegarder_ventes_json(date, ventes):
    try:
        data = {}
        if os.path.exists(VENTES_JSON_PATH) and os.path.getsize(VENTES_JSON_PATH) > 0:
            with open(VENTES_JSON_PATH, "r") as f:
                data = json.load(f)
        if date in data:
            for produit, quantite in ventes.items():
                data[date][produit] = data[date].get(produit, 0) + quantite
        else:
            data[date] = ventes
        with open(VENTES_JSON_PATH, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Ventes sauvegardées pour la date {date}.")
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde des ventes : {e}")

def get_sheet_names():
    global fichier
    try:
        if fichier:
            feuilles = fichier.worksheets()
            print("Feuilles récupérées depuis l'API :", [feuille.title for feuille in feuilles])
            return [feuille.title for feuille in feuilles]
        else:
            print("Erreur : Aucun fichier Google Sheets chargé.")
            return []
    except Exception as e:
        print(f"Erreur lors de la récupération des feuilles : {e}")
        return []

def charger_preferences():
    dossier_preferences = os.path.join(os.getenv("APPDATA"), "burger_shot_commande_helper")
    chemin_fichier = os.path.join(dossier_preferences, "preferences.json")
    try:
        with open(chemin_fichier, "r") as f:
            preferences = json.load(f)
            print(f"Préférences chargées : {preferences}")
            nom_entry.insert(0, preferences.get("nom", ""))
            nom2_entry.insert(0, preferences.get("vendeur", ""))
            feuille_combobox.insert(0,preferences.get("feuille", ""))
            feuille_id_combobox.set(preferences.get("fichier_id", ""))
            fichier_id = preferences.get("fichier_id", "")
            if fichier_id and fichier_id in fichiers_ids:
                try:
                    fichier = client.open_by_key(fichiers_ids[fichier_id])
                    print("Fichier Google Sheets chargé avec succès :", fichier.title)

                    feuilles = get_sheet_names()
                    if feuilles:
                        print("Feuilles récupérées avec succès :", feuilles)
                        feuille_combobox["values"] = feuilles
                        feuille_combobox.set(preferences.get("feuille", ""))
                    else:
                        print("Erreur : Aucune feuille trouvée dans le fichier Google Sheets.")
                except Exception as e:
                    print(f"Erreur lors du chargement du fichier Google Sheets : {e}")
            else:
                print("Erreur : ID de fichier invalide ou manquant.")
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
        prix_total = sum(quantites[produit] * prix_unitaires[produit] for produit in quantites)
        prix_total_label.config(text=f"Prix total : {prix_total} $")
        return prix_total
    except ValueError:
        prix_total_label.config(text="Prix total : 0 $")

def masquer_boutons_bilan_et_graphique():
    bilan_button.grid_remove()
    graphique_button.grid_remove()

def retour():
    global current_page
    if current_page == "ventes_civiles":
        masquer_elements()
        afficher_elements2()  
    elif current_page == "ventes_contrats":
        masquer_elements2()
        afficher_elements()  
    else:
        masquer_tous_les_elements()
        retour_button.grid_remove() 

def envoyer_prise_de_service():
    global message_id

    heure_actuelle = datetime.datetime.now().strftime("%H:%M")
    date_actuelle = datetime.datetime.now().strftime("%d/%m")

    message = {
        "content": "**Prise de service :** " + heure_actuelle + "\n**Pause :** \n**Fin de service :** \n\n**Date :** " + date_actuelle
    }

    headers = {
        "Authorization": USER_TOKEN,
        "Content-Type": "application/json"
    }

    url = f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages"

    try:
        response = requests.post(url, data=json.dumps(message), headers=headers)
        response.raise_for_status()
        message_id = response.json()["id"]
        messagebox.showinfo("Succès", "Message de prise de service envoyé avec succès !")
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de l'envoi du message : {e}")


def envoyer_fin_de_service():
    global message_id

    if not message_id:
        messagebox.showerror("Erreur", "Aucun message de prise de service n'a été envoyé.")
        return

    heure_fin_service = datetime.datetime.now().strftime("%H:%M")

    message = {
        "content": f"**Prise de service :** [Heure initiale]\n**Pause :** \n**Fin de service :** {heure_fin_service}\n\n**Date :** [Date initiale]"
    }

    headers = {
        "Authorization": USER_TOKEN,
        "Content-Type": "application/json"
    }

    url = f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages/{message_id}"

    try:
        response = requests.patch(url, data=json.dumps(message), headers=headers)
        response.raise_for_status()
        messagebox.showinfo("Succès", "Message de fin de service mis à jour avec succès !")
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de la mise à jour du message : {e}")

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

bilan_button = tk.Button(app, text="Afficher le bilan des ventes", command=obtenir_bilan_ventes_json)
bilan_button.grid(row=14, column=0, columnspan=3, padx=10, pady=10)

prise_service_button = tk.Button(app, text="Prise de service", command=envoyer_prise_de_service)
prise_service_button.grid(row=3, column=0, columnspan=3, padx=10, pady=20)

fin_service_button = tk.Button(app, text="Fin de service", command=envoyer_fin_de_service)
fin_service_button.grid(row=4, column=1, padx=10, pady=10)

nom_label = tk.Label(app, text="Votre nom :")
nom_entry = tk.Entry(app)

nom2_label = tk.Label(app, text="Vendeur :")
nom2_entry = tk.Entry(app)

client_label = tk.Label(app, text="Client :")
client_entry = tk.Entry(app)

retour_button = tk.Button(app, text="Switch Page", command=retour)
retour_button.grid(row=14, column=0, columnspan=3, padx=10, pady=10)
retour_button.grid_remove() 

client_combobox = ttk.Combobox(app, values=clients_list)

date_label = tk.Label(app, text="Date :")
date_entry = DateEntry(app, date_pattern='yyyy-mm-dd')

feuille_label = tk.Label(app, text="Sélectionner la feuille :")
feuille_combobox = ttk.Combobox(app, values=[])

menu_classic_label = tk.Label(app, text="Menu Classic:")
menu_classic_combobox = ttk.Combobox(app, values=list(range(100)), state="normal")
menu_classic_combobox.current(0)

menu_double_label = tk.Label(app, text="Menu Double:")
menu_double_combobox = ttk.Combobox(app, values=list(range(100)), state="normal")
menu_double_combobox.current(0)

menu_contrat_label = tk.Label(app, text="Menu Contrat:")
menu_contrat_combobox = ttk.Combobox(app, values=list(range(100)), state="normal")
menu_contrat_combobox.current(0)

tenders_label = tk.Label(app, text="Tenders:")
tenders_combobox = ttk.Combobox(app, values=list(range(100)), state="normal")
tenders_combobox.current(0)

petite_salade_label = tk.Label(app, text="Petite Salade:")
petite_salade_combobox = ttk.Combobox(app, values=list(range(100)), state="normal")
petite_salade_combobox.current(0)

boisson_label = tk.Label(app, text="Boisson:")
boisson_combobox = ttk.Combobox(app, values=list(range(100)), state="normal")
boisson_combobox.current(0)

milkshake_label = tk.Label(app, text="Milkshake:")
milkshake_combobox = ttk.Combobox(app, values=list(range(100)), state="normal")
milkshake_combobox.current(0)

prix_total_label = tk.Label(app, text="Prix total : 0 $")

confirmer_button = tk.Button(app, text="Confirmer la vente", command=confirmer_vente)

confirmer_button2 = tk.Button(app, text="Confirmer la vente", command=confirmer_vente2)

sauvegarder_preferences_button = tk.Button(app, text="Sauvegarder les préférences", command=sauvegarder_preferences)
sauvegarder_preferences_button.grid(row=13, column=0, columnspan=3, padx=10, pady=10) 

graphique_button = tk.Button(app, text="Générer le graphique des ventes", command=generer_graphique_ventes)
graphique_button.grid(row=15, column=0, columnspan=3, padx=10, pady=10)

resultat_label = tk.Label(app, text="")

for combobox in [menu_classic_combobox, menu_double_combobox, menu_contrat_combobox,
                 tenders_combobox, petite_salade_combobox, boisson_combobox, milkshake_combobox]:
    combobox.bind("<<ComboboxSelected>>", lambda event: calculer_prix_total())

charger_clients_json()
client_combobox["values"] = clients_list
#charger_preferences()
app.mainloop()