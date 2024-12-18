from kivymd.app import MDApp
import openrouteservice
from openrouteservice import convert
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton
from kivy_garden.mapview import MapView, MapMarker
from firebase_admin import credentials, db, initialize_app
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.screen import Screen
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.list import OneLineIconListItem

# Initialisation Firebase
cred = credentials.Certificate("bus-tracking-51ff9-firebase-adminsdk-2nvt3-01cff1bf74.json")
initialize_app(cred, {
    'databaseURL': 'https://bus-tracking-51ff9-default-rtdb.europe-west1.firebasedatabase.app/'
})

# Clé API OpenRouteService
API_KEY = "5b3ce3597851110001cf6248579071b446ed43b6871633b7a72226af"
client = openrouteservice.Client(key=API_KEY)

# Liste des arrêts prédéfinis, je pourrais utiliser un fichier json mais j'ai la flemme du coup on van créer un dictionnaire
BUS_STOPS = {
    "Station de bus non loin du commissaria du 22eme": {
        "latitude": 5.3963968,
        "longitude": -3.9917385
    },
    "Arrêt du terminus 81/82": {
        "latitude": 5.353600,
        "longitude": -4.001200
    },
    "Arrêt Angré vers petro ivoire": {
        "latitude": 5.353600,
        "longitude": -4.001200
    },
    "Arrêt vers pharmacie Gabriel boulevard latrille": {
        "latitude": 5.3890938,
        "longitude": -3.9927009
    },
    "Arrêt de bus Yop devant cosmos": {
        "latitude": 5.349300,
        "longitude": -4.073374
    },
    "Arrêt en face d'emploie jeune": {
        "latitude": 5.354896,
        "longitude": -4.076167
    },
    "Arrêt Siporex avant le marché": {
        "latitude": 5.349300,
        "longitude": -4.073374
    },

}

class UserApp(MDApp):
    def build(self):
        # Conteneur principal
        self.main_layout = MDBoxLayout(orientation="vertical")

        # Création de la toolbar
        top_app_bar = MDTopAppBar(
            title="ChapRun",
            left_action_items=[["menu", lambda x: self.menu_pressed()]],
            right_action_items=[["dots-vertical", lambda x: self.dots_pressed()]],
        )
        self.main_layout.add_widget(top_app_bar)

        # Drawer pour afficher la liste dans un menu latéral
        self.nav_drawer = MDNavigationDrawer()
        self.nav_list = MDList()
        self.nav_drawer.add_widget(self.nav_list)

        # Écran principal
        self.screen = Screen()

        # Carte interactive
        self.mapview = MapView(
            zoom=12,
            lat=5.336,  # Coordonnées de démarrage d'Abidjan
            lon=-4.026,
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            size_hint=(1, 0.5)
        )
        self.screen.add_widget(self.mapview)

        # Barre de recherche pour entrer le numéro du bus
        self.search_field = MDTextField(
            hint_text="Entrez le numéro du bus",
            pos_hint={'center_x': 0.5, 'center_y': 0.85},
            size_hint_x=0.8
        )
        self.screen.add_widget(self.search_field)

        # Bouton pour rechercher le bus
        search_button = MDRaisedButton(
            text="Rechercher",
            pos_hint={'center_x': 0.5, 'center_y': 0.79},
            on_release=self.search_bus
        )
        self.screen.add_widget(search_button)

        # Liste des arrêts de bus pour menu latéral
        self.update_nav_list()

        # Ajouter l'écran au layout principal
        self.main_layout.add_widget(self.screen)

        return self.main_layout

    def update_nav_list(self):
        """Remplit le drawer avec les arrêts visibles."""
        self.nav_list.clear_widgets()
        for stop_name in BUS_STOPS.keys():
            list_item = OneLineIconListItem(text=stop_name, on_release=self.select_stop)
            self.nav_list.add_widget(list_item)

    def menu_pressed(self):
        """Ouvre le menu latéral."""
        if not self.nav_drawer.parent:
            self.main_layout.add_widget(self.nav_drawer)
        self.nav_drawer.set_state("open")

    def dots_pressed(self):
        print("Dots button pressed")

    def select_stop(self, instance):
        stop_name = instance.text
        stop_data = BUS_STOPS[stop_name]
        self.select_stop = (stop_data["latitude"], stop_data["longitude"])
        print(f"Arrêt sélectionné : {stop_name}, Coordonnées : {self.select_stop}")

    def search_bus(self, instance):
        bus_id = self.search_field.text.strip()

        if not bus_id:
            print("Veuillez entrer un numéro de bus.")
            return

        if not self.select_stop:
            print("Veuillez sélectionner un arrêt.")
            return

        # Rechercher les données du bus dans Firebase
        try:
            ref = db.reference(f'buses/{bus_id}')
            bus_data = ref.get()

            if bus_data:
                bus_lat = bus_data.get('latitude')
                bus_lon = bus_data.get('longitude')

                if bus_lat and bus_lon:
                    print(f"Bus {bus_id} trouvé : Latitude {bus_lat}, Longitude {bus_lon}")
                    self.estimate_arrival_time(bus_lat, bus_lon)
                else:
                    print("Les coordonnées du bus sont invalides.")
            else:
                print(f"Aucun bus trouvé avec l'ID {bus_id}.")

        except Exception as e:
            print(f"Erreur lors de la récupération des données du bus : {e}")

    def estimate_arrival_time(self, bus_lat, bus_lon):
        try:
            stop_lat, stop_lon = self.select_stop
            coords = [(bus_lon, bus_lat), (stop_lon, stop_lat)]

            # Requête OpenRouteService pour le calcul de la durée
            route = client.directions(
                coordinates=coords,
                profile='driving-car',
                format='geojson'
            )

            duration = route['features'][0]['properties']['segments'][0]['duration']
            duration_minutes = round(duration / 60, 2)

            print(f"Temps estimé d'arrivée : {duration_minutes} minutes")
            self.show_estimate_dialog(duration_minutes)
        except Exception as e:
            print(f"Erreur lors du calcul du temps d'arrivée : {e}")

    def show_estimate_dialog(self, duration_minutes):
       self.dialog = MDDialog(
            title="Temps d'arrivée estimé",
            text=f"Le bus arrivera à l'arrêt dans environ {duration_minutes} minutes.",
            buttons=[
                MDRaisedButton(text="OK", on_release=lambda x: self.dialog.dismiss())
            ]
        )
       self.dialog.open()

if __name__ == "__main__":
    UserApp().run()
