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
import time
import csv

VENTES_JSON_PATH = os.path.join(os.getenv("APPDATA"), "burger_shot_commande_helper", "ventes.json")
CLIENTS_JSON_PATH = os.path.join(os.getenv("APPDATA"), "burger_shot_commande_helper", "clients.json")
PREFERENCES_JSON_PATH = os.path.join(os.getenv("APPDATA"), "burger_shot_commande_helper", "preferences.json")
EXPORTE_CSV_PATH = os.path.join(os.getenv("APPDATA"), "burger_shot_commande_helper", "ventes.csv")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("api_key.json", scope)
client = gspread.authorize(creds)

fichier = None
current_page = None
message_id = None
heure_debut = None
date_actuelle = None
pause_debut = None
pause_fin = None
pause_timer_label = None
pause_start_time = None
pause_timer_running = False

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
clients_feuilles = {}

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

def afficher_elements_accueil():
    global current_page
    masquer_tous_les_elements() 

    titre_label.grid(row=0, column=0, columnspan=3, pady=10)
    feuille_id_label.grid(row=1, column=0, padx=10, pady=10)
    feuille_id_combobox.grid(row=1, column=1, padx=10, pady=10)
    charger_fichier_button.grid(row=1, column=2, padx=10, pady=10)
    bilan_button.grid(row=2, column=0, columnspan=3, padx=10, pady=10)
    graphique_button.grid(row=3, column=0, columnspan=3, padx=10, pady=10)
    bouton_service.grid(row=4, column=0, columnspan=3, padx=10, pady=10)
    bouton_pause_reprise.grid(row=5, column=0, columnspan=3, padx=10, pady=10)
    sauvegarder_preferences_button.grid(row=6, column=0, columnspan=3, padx=10, pady=10)
    current_page = "accueil"


def ajouter_valeurs(sheet, ligne, valeurs, case_a_cocher=False):
    try:
        if isinstance(valeurs, dict):
            mises_a_jour = []
            for col, val in valeurs.items():
                index_col = ord(col.upper()) - ord("A") + 1

                if col == 'F' and case_a_cocher:
                    nouvelle_valeur = val  
                else:
                    cellule = sheet.cell(ligne, index_col).value
                    nouvelle_valeur = str(int(cellule) + val) if cellule and cellule.isdigit() else str(val)
                mises_a_jour.append({"range": f"{col}{ligne}", "values": [[nouvelle_valeur]]})

            if mises_a_jour:
                sheet.batch_update(mises_a_jour)
                print("Valeurs mises à jour avec succès !")
        elif isinstance(valeurs, list):
            for valeur in valeurs:
                ajouter_valeurs(sheet, ligne, valeur, case_a_cocher)
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
            ajouter_valeurs(sheet, ligne, valeurs, case_a_cocher=False)
            resultat_label.config(text="Vente enregistrée avec succès !")
            prix_total = calculer_prix_total()

            for combobox in [menu_classic_combobox, menu_double_combobox, menu_contrat_combobox,
                             tenders_combobox, petite_salade_combobox, boisson_combobox, milkshake_combobox]:
                combobox.set(0)
            calculer_prix_total()

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
                clients_feuilles[client] = nom_feuille 
                print(f"Client '{client}' ajouté avec succès.")
            elif client in clients_feuilles and clients_feuilles[client] != nom_feuille:
                clients_feuilles[client] = nom_feuille 
                print(f"Client '{client}' mis à jour avec la feuille '{nom_feuille}'.")

        if clients:
            client_combobox["values"] = clients_list
            sauvegarder_clients_json()
        
        valeurs = []
        for client in clients:
            valeurs.append({
                "B": str(nom2_entry.get()),     # Vendeur
                "D": client.strip(),            # Client
                "E": date_aujourdhui,           # Date du jour
                "F": True                       # Case à cocher
            })
        
        ligne = trouver_premiere_ligne_vide(sheet)
        if ligne:
            ajouter_valeurs(sheet, ligne, valeurs, case_a_cocher=True)
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

def mettre_a_jour_feuille_selectionnee(event):
    client = client_combobox.get().strip()
    if client in clients_feuilles:
        feuille = clients_feuilles[client]
        feuille_combobox.set(feuille)

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
        
        date_debut_label = tk.Label(bilan_window, text="Date de début :")
        date_debut_label.grid(row=0, column=0, padx=10, pady=10)
        date_debut_selector = DateEntry(bilan_window, date_pattern='yyyy-mm-dd')
        date_debut_selector.grid(row=0, column=1, padx=10, pady=10)
        
        date_fin_label = tk.Label(bilan_window, text="Date de fin :")
        date_fin_label.grid(row=1, column=0, padx=10, pady=10)
        date_fin_selector = DateEntry(bilan_window, date_pattern='yyyy-mm-dd')
        date_fin_selector.grid(row=1, column=1, padx=10, pady=10)
        
        item_label = tk.Label(bilan_window, text="Item :")
        item_label.grid(row=2, column=0, padx=10, pady=10)
        item_combobox = ttk.Combobox(bilan_window, values=list(prix_unitaires.keys()))
        item_combobox.grid(row=2, column=1, padx=10, pady=10)
        
        quantite_label = tk.Label(bilan_window, text="Quantité :")
        quantite_label.grid(row=3, column=0, padx=10, pady=10)
        quantite_combobox = ttk.Combobox(bilan_window, values=["Supérieur à", "Inférieur à", "Égal à"])
        quantite_combobox.grid(row=3, column=1, padx=10, pady=10)
        
        quantite_value_label = tk.Label(bilan_window, text="Valeur :")
        quantite_value_label.grid(row=4, column=0, padx=10, pady=10)
        quantite_value_entry = tk.Entry(bilan_window)
        quantite_value_entry.grid(row=4, column=1, padx=10, pady=10)
        
        total_ventes_label = tk.Label(bilan_window, text="Total des ventes : 0 $")
        total_ventes_label.grid(row=5, column=0, columnspan=2, padx=10, pady=10)
        
        afficher_button = tk.Button(bilan_window, text="Afficher les ventes", command=lambda: afficher_ventes_par_date_range(data, date_debut_selector.get_date(), date_fin_selector.get_date(), item_combobox.get(), quantite_combobox.get(), quantite_value_entry.get(), text_area, total_ventes_label))
        afficher_button.grid(row=6, column=0, columnspan=2, padx=10, pady=10)
        
        text_area = tk.Text(bilan_window, wrap=tk.WORD, width=80, height=20)
        text_area.grid(row=7, column=0, columnspan=2, padx=10, pady=10)

    except json.JSONDecodeError:
        messagebox.showerror("Erreur", "Le fichier de ventes est vide ou corrompu.")
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de la récupération du bilan des ventes : {e}")

def afficher_ventes_par_date_range(data, date_debut, date_fin, item, quantite_option, quantite_value, text_area, total_ventes_label):
    try:
        date_debut_str = date_debut.strftime('%Y-%m-%d')
        date_fin_str = date_fin.strftime('%Y-%m-%d')
        text_area.delete(1.0, tk.END)
        
        dates = sorted(data.keys())
        ventes_trouvees = False
        total_ventes = 0
        
        for date in dates:
            if date_debut_str <= date <= date_fin_str:
                ventes = data[date]
                text_area.insert(tk.END, f"Date: {date}\n")
                if not ventes:
                    text_area.insert(tk.END, "  Aucune vente pour cette date.\n")
                else:
                    for produit, quantite_vendue in ventes.items():
                        if (not item or item.lower() in produit.lower()):
                            if quantite_option == "Supérieur à" and quantite_value and quantite_vendue > int(quantite_value):
                                text_area.insert(tk.END, f"  {produit}: {quantite_vendue}\n")
                                total_ventes += quantite_vendue * prix_unitaires.get(produit, 0)
                            elif quantite_option == "Inférieur à" and quantite_value and quantite_vendue < int(quantite_value):
                                text_area.insert(tk.END, f"  {produit}: {quantite_vendue}\n")
                                total_ventes += quantite_vendue * prix_unitaires.get(produit, 0)
                            elif quantite_option == "Égal à" and quantite_value and quantite_vendue == int(quantite_value):
                                text_area.insert(tk.END, f"  {produit}: {quantite_vendue}\n")
                                total_ventes += quantite_vendue * prix_unitaires.get(produit, 0)
                            elif not quantite_option:
                                text_area.insert(tk.END, f"  {produit}: {quantite_vendue}\n")
                                total_ventes += quantite_vendue * prix_unitaires.get(produit, 0)
                text_area.insert(tk.END, "\n")
                ventes_trouvees = True
        
        if not ventes_trouvees:
            text_area.insert(tk.END, f"Aucune vente trouvée entre les dates {date_debut_str} et {date_fin_str}.\n")
        
        total_ventes_label.config(text=f"Total des ventes : {total_ventes} $")
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

def charger_clients_json():
    try:
        dossier_preferences = os.path.join(os.getenv("APPDATA"), "burger_shot_commande_helper")
        chemin_fichier = os.path.join(dossier_preferences, "clients.json")

        if os.path.exists(chemin_fichier):
            with open(chemin_fichier, "r") as f:
                global clients_list, clients_feuilles
                data = json.load(f)
                clients_list = data.get("clients", [])
                clients_feuilles = data.get("clients_feuilles", {})
                print("Clients chargés avec succès.")
    except Exception as e:
        print(f"Erreur lors du chargement des clients : {e}")

def sauvegarder_clients_json():
    try:
        dossier_preferences = os.path.join(os.getenv("APPDATA"), "burger_shot_commande_helper")
        if not os.path.exists(dossier_preferences):
            os.makedirs(dossier_preferences)

        chemin_fichier = os.path.join(dossier_preferences, "clients.json")

        with open(chemin_fichier, "w") as f:
            json.dump({"clients": clients_list, "clients_feuilles": clients_feuilles}, f, indent=4)
        print("Clients sauvegardés avec succès.")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des clients : {e}")

def masquer_tous_les_elements():
    masquer_elements()
    masquer_elements2()

def afficher_elements():
    global current_page
    masquer_tous_les_elements()
    nom_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
    nom_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
    feuille_label.grid(row=3, column=0, padx=10, pady=10, sticky="w")
    feuille_combobox.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
    menu_classic_label.grid(row=4, column=0, padx=10, pady=10, sticky="w")
    menu_classic_combobox.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
    menu_double_label.grid(row=5, column=0, padx=10, pady=10, sticky="w")
    menu_double_combobox.grid(row=5, column=1, padx=10, pady=10, sticky="ew")
    menu_contrat_label.grid(row=6, column=0, padx=10, pady=10, sticky="w")
    menu_contrat_combobox.grid(row=6, column=1, padx=10, pady=10, sticky="ew")
    tenders_label.grid(row=7, column=0, padx=10, pady=10, sticky="w")
    tenders_combobox.grid(row=7, column=1, padx=10, pady=10, sticky="ew")
    petite_salade_label.grid(row=8, column=0, padx=10, pady=10, sticky="w")
    petite_salade_combobox.grid(row=8, column=1, padx=10, pady=10, sticky="ew")
    boisson_label.grid(row=9, column=0, padx=10, pady=10, sticky="w")
    boisson_combobox.grid(row=9, column=1, padx=10, pady=10, sticky="ew")
    milkshake_label.grid(row=10, column=0, padx=10, pady=10, sticky="w")
    milkshake_combobox.grid(row=10, column=1, padx=10, pady=10, sticky="ew")
    prix_total_label.grid(row=11, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
    confirmer_button.grid(row=12, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
    resultat_label.grid(row=13, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
    retour_button.grid(row=14, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
    sauvegarder_preferences_button.grid_remove()
    bouton_service.grid_remove()
    bouton_pause_reprise.grid_remove()
    supprimer_client_button.grid_remove()
    exporter_button.grid_remove()
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
    supprimer_client_button.grid(row=4, column=3, padx=1, pady=1, sticky="ew")
    sauvegarder_preferences_button.grid_remove()
    bouton_service.grid_remove()
    bouton_pause_reprise.grid_remove()
    exporter_button.grid_remove()
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
                         client_combobox, date_label, date_entry, confirmer_button2, resultat_label, supprimer_client_button]
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
    except json.JSONDecodeError:
        messagebox.showerror("Erreur", "Le fichier de ventes est corrompu.")
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
    try:
        with open(PREFERENCES_JSON_PATH, "r") as f:
            preferences = json.load(f)
            print(f"Préférences chargées : {preferences}")
            nom_entry.insert(0, preferences.get("nom", ""))
            nom2_entry.insert(0, preferences.get("vendeur", ""))
            feuille_combobox.insert(0, preferences.get("feuille", ""))
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
    except json.JSONDecodeError:
        print("Le fichier de préférences est corrompu.")
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
    masquer_tous_les_elements()  
    afficher_elements_accueil()  
    current_page = "accueil" 

def prise_fin_service():
    global message_id, heure_debut, date_actuelle, pause_debut, pause_fin, en_pause

    headers = {
        "Authorization": USER_TOKEN,
        "Content-Type": "application/json"
    }

    if bouton_service["text"] == "Prise de service":
        heure_debut = datetime.datetime.now().strftime("%H:%M")
        date_actuelle = datetime.datetime.now().strftime("%d/%m")
        message = {
            "content": f"**Prise de service :** {heure_debut}\n**Pause :** \n**Fin de service :** \n\n**Date :** {date_actuelle}"
        }
        url = f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages"

        try:
            response = requests.post(url, data=json.dumps(message), headers=headers)
            response.raise_for_status()
            message_id = response.json()["id"]
            bouton_service.config(text="Fin de service", bg="red")
            bouton_pause_reprise.config(state=tk.NORMAL)
            en_pause = False
            messagebox.showinfo("Succès", "Message de prise de service envoyé avec succès !")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'envoi du message : {e}")

    elif bouton_service["text"] == "Fin de service":
        heure_fin_service = datetime.datetime.now().strftime("%H:%M")
        pause_text = f"{pause_debut} - {pause_fin}" if pause_debut and pause_fin else "Aucune"

        message = {
            "content": f"**Prise de service :** {heure_debut}\n**Pause :** {pause_text}\n**Fin de service :** {heure_fin_service}\n\n**Date :** {date_actuelle}"
        }
        url = f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages/{message_id}"

        try:
            response = requests.patch(url, data=json.dumps(message), headers=headers)
            response.raise_for_status()
            bouton_service.config(text="Prise de service", bg="green")
            bouton_pause_reprise.config(state=tk.DISABLED, bg="orange", text="Pause/Reprise")
            messagebox.showinfo("Succès", "Message de fin de service mis à jour avec succès !")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la mise à jour du message : {e}")

def mettre_a_jour_timer_pause():
    if pause_timer_running:
        elapsed_time = time.time() - pause_start_time
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        pause_timer_label.config(text=f"Pause: {int(hours):02}:{int(minutes):02}:{int(seconds):02}")
        app.after(1000, mettre_a_jour_timer_pause)

def pause_reprise_service():
    global pause_debut, pause_fin, en_pause, pause_start_time, pause_timer_running
    
    if not en_pause:
        pause_debut = datetime.datetime.now().strftime("%H:%M")
        pause_start_time = time.time()
        pause_timer_running = True
        pause_timer_label.grid()  
        mettre_a_jour_timer_pause()
        bouton_pause_reprise.config(text="Reprise de service", bg="orange")
        en_pause = True
        messagebox.showinfo("Succès", "Pause de service enregistrée.")
    else:  
        pause_fin = datetime.datetime.now().strftime("%H:%M")
        pause_timer_running = False
        pause_timer_label.grid_remove()
        message = {
            "content": f"**Prise de service :** {heure_debut}\n**Pause :** {pause_debut} - {pause_fin}\n**Fin de service :** \n\n**Date :** {date_actuelle}"
        }

        headers = {
            "Authorization": USER_TOKEN,
            "Content-Type": "application/json"
        }

        url = f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages/{message_id}"

        try:
            response = requests.patch(url, data=json.dumps(message), headers=headers)
            response.raise_for_status()
            bouton_pause_reprise.config(text="Pause de service", bg="orange")
            en_pause = False
            messagebox.showinfo("Succès", "Reprise de service enregistrée et message mis à jour.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la mise à jour du message : {e}")

def supprimer_client():
    client = client_combobox.get().strip()
    if client in clients_list:
        clients_list.remove(client)
        del clients_feuilles[client]
        client_combobox["values"] = clients_list
        client_combobox.set('')
        sauvegarder_clients_json()
        resultat_label.config(text=f"Client '{client}' supprimé avec succès.")
    else:
        resultat_label.config(text="Erreur : Client non trouvé.")

def filtrer_clients(event):
    valeur_entree = client_combobox.get().lower()
    listbox_suggestions.delete(0, tk.END)
    if valeur_entree:
        valeurs_filtrees = [client for client in clients_list if valeur_entree in client.lower()]
        for client in valeurs_filtrees[:10]:
            listbox_suggestions.insert(tk.END, client)
        listbox_suggestions.place(x=client_combobox.winfo_x(), y=client_combobox.winfo_y() + client_combobox.winfo_height())
        listbox_suggestions.config(height=min(10, len(valeurs_filtrees)))  
    else:
        listbox_suggestions.place_forget()

def selectionner_suggestion(event):
    try:
        selection = listbox_suggestions.get(listbox_suggestions.curselection())
        client_combobox.set(selection)
        listbox_suggestions.place_forget()
    except tk.TclError:
        pass

def valider_quantite(event):
    try:
        combobox = event.widget
        quantite = int(combobox.get())
        combobox.set(quantite)
        calculer_prix_total()
    except ValueError:
        combobox.set(0)
        calculer_prix_total()

def exporter_ventes_csv():
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

        with open(EXPORTE_CSV_PATH, "w", newline='') as csvfile:
            fieldnames = ['Date', 'Produit', 'Quantité']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for date, ventes in data.items():
                for produit, quantite in ventes.items():
                    writer.writerow({'Date': date, 'Produit': produit, 'Quantité': quantite})

        messagebox.showinfo("Succès", "Les ventes ont été exportées avec succès au format CSV.")
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de l'exportation des ventes : {e}")

app = tk.Tk()
app.title("Burger Shot - Commande Helper")

image_path = "bs.png"
image = Image.open(image_path)
image = image.resize((300, 100), Image.Resampling.LANCZOS)
photo = ImageTk.PhotoImage(image)

for i in range(3):
    app.columnconfigure(i, weight=1)
for i in range(18):
    app.rowconfigure(i, weight=1)

titre_label = tk.Label(app, image=photo)
titre_label.grid(row=0, column=0, columnspan=3, pady=10, sticky="nsew")

feuille_id_label = tk.Label(app, text="Sélectionner le GSheet :")
feuille_id_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

feuille_id_combobox = ttk.Combobox(app, values=list(fichiers_ids.keys()))
feuille_id_combobox.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
feuille_id_combobox.current(0)

charger_fichier_button = tk.Button(app, text="Charger le fichier", command=charger_fichier)
charger_fichier_button.grid(row=1, column=2, padx=10, pady=10, sticky="ew")

bilan_button = tk.Button(app, text="Afficher le bilan des ventes", command=obtenir_bilan_ventes_json)
bilan_button.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

bouton_service = tk.Button(app, text="Prise de service", command=prise_fin_service, bg="green")
bouton_service.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

bouton_pause_reprise = tk.Button(app, text="Pause/Reprise", command=pause_reprise_service, bg="orange", state=tk.DISABLED)
bouton_pause_reprise.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

pause_timer_label = tk.Label(app, text="Pause: 00:00:00")
pause_timer_label.grid(row=18, column=0, columnspan=3, padx=10, pady=10, sticky="w")
pause_timer_label.grid_remove()

nom_label = tk.Label(app, text="Votre nom :")
nom_entry = tk.Entry(app)

nom2_label = tk.Label(app, text="Vendeur :")
nom2_entry = tk.Entry(app)

client_label = tk.Label(app, text="Client :")
client_entry = tk.Entry(app)

retour_button = tk.Button(app, text="Page Acceuil", command=retour)
retour_button.grid(row=14, column=0, columnspan=3, padx=10, pady=10)
retour_button.grid_remove() 

exporter_button = tk.Button(app, text="Exporter les ventes en CSV", command=exporter_ventes_csv)
exporter_button.grid(row=7, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

client_combobox = ttk.Combobox(app, values=clients_list)
client_combobox.bind('<KeyRelease>', filtrer_clients)
client_combobox['state'] = 'normal'

listbox_suggestions = tk.Listbox(app, height=10)
listbox_suggestions.bind('<<ListboxSelect>>', selectionner_suggestion)

supprimer_client_button = tk.Button(app, text="-", command=supprimer_client, fg="black", width=0, height=0)

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
sauvegarder_preferences_button.grid(row=6, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

graphique_button = tk.Button(app, text="Générer le graphique des ventes", command=generer_graphique_ventes)
graphique_button.grid(row=3, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

resultat_label = tk.Label(app, text="")

fait_avec_amour_label = tk.Label(app, text="Fait avec amour !", anchor="e")
fait_avec_amour_label.grid(row=18, column=2, padx=10, pady=10, sticky="se")

for combobox in [menu_classic_combobox, menu_double_combobox, menu_contrat_combobox,
                 tenders_combobox, petite_salade_combobox, boisson_combobox, milkshake_combobox]:
    combobox.bind("<<ComboboxSelected>>", lambda event: calculer_prix_total())
    combobox.bind("<Return>", valider_quantite)

client_combobox.bind("<<ComboboxSelected>>", mettre_a_jour_feuille_selectionnee)

charger_clients_json()
client_combobox["values"] = clients_list
app.mainloop()