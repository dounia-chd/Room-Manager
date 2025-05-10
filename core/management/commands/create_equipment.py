from django.core.management.base import BaseCommand
from core.models import Equipment

class Command(BaseCommand):
    help = 'Crée les équipements spécifiques pour chaque catégorie de salle'

    def handle(self, *args, **kwargs):
        equipments = [
            # Équipements généraux
            {
                'name': 'Climatisation',
                'description': 'Système de climatisation',
                'icon': 'fas fa-snowflake'
            },
            {
                'name': 'WiFi',
                'description': 'Accès Internet haut débit',
                'icon': 'fas fa-wifi'
            },
            {
                'name': 'Éclairage',
                'description': 'Système d\'éclairage ajustable',
                'icon': 'fas fa-lightbulb'
            },

            # Équipements Entreprises
            {
                'name': 'Projecteur',
                'description': 'Projecteur HD pour présentations',
                'icon': 'fas fa-video'
            },
            {
                'name': 'Tableau blanc',
                'description': 'Tableau blanc effaçable',
                'icon': 'fas fa-chalkboard'
            },
            {
                'name': 'Système audio',
                'description': 'Système de son professionnel',
                'icon': 'fas fa-volume-up'
            },
            {
                'name': 'Écran TV',
                'description': 'Écran TV grand format',
                'icon': 'fas fa-tv'
            },
            {
                'name': 'Tables de réunion',
                'description': 'Tables modulables pour réunions',
                'icon': 'fas fa-table'
            },
            {
                'name': 'Chaises confortables',
                'description': 'Chaises ergonomiques',
                'icon': 'fas fa-chair'
            },

            # Équipements Universités
            {
                'name': 'Tableau interactif',
                'description': 'Tableau numérique interactif',
                'icon': 'fas fa-chalkboard-teacher'
            },
            {
                'name': 'Ordinateurs',
                'description': 'Postes informatiques',
                'icon': 'fas fa-laptop'
            },
            {
                'name': 'Microscope',
                'description': 'Microscope pour laboratoire',
                'icon': 'fas fa-microscope'
            },
            {
                'name': 'Équipement de laboratoire',
                'description': 'Matériel scientifique',
                'icon': 'fas fa-flask'
            },
            {
                'name': 'Bancs d\'expérimentation',
                'description': 'Bancs de laboratoire',
                'icon': 'fas fa-vial'
            },

            # Équipements Hôtels
            {
                'name': 'Service traiteur',
                'description': 'Service de restauration',
                'icon': 'fas fa-utensils'
            },
            {
                'name': 'Décoration événementielle',
                'description': 'Éléments de décoration',
                'icon': 'fas fa-gift'
            },
            {
                'name': 'Système de sonorisation',
                'description': 'Système audio professionnel',
                'icon': 'fas fa-music'
            },
            {
                'name': 'Éclairage d\'ambiance',
                'description': 'Éclairage modulable',
                'icon': 'fas fa-lightbulb'
            },
            {
                'name': 'Service hôtelier',
                'description': 'Service de conciergerie',
                'icon': 'fas fa-concierge-bell'
            },

            # Équipements Sports
            {
                'name': 'Matériel de sport',
                'description': 'Équipement sportif varié',
                'icon': 'fas fa-dumbbell'
            },
            {
                'name': 'Tapis de yoga',
                'description': 'Tapis de sol',
                'icon': 'fas fa-yoga'
            },
            {
                'name': 'Miroirs',
                'description': 'Miroirs muraux',
                'icon': 'fas fa-mirror'
            },
            {
                'name': 'Barres de danse',
                'description': 'Barres de ballet',
                'icon': 'fas fa-balance-scale'
            },
            {
                'name': 'Vestiaires',
                'description': 'Vestiaires avec douches',
                'icon': 'fas fa-shower'
            }
        ]

        for equipment_data in equipments:
            Equipment.objects.get_or_create(
                name=equipment_data['name'],
                defaults={
                    'description': equipment_data['description'],
                    'icon': equipment_data['icon']
                }
            )

        self.stdout.write(self.style.SUCCESS('Équipements créés avec succès')) 