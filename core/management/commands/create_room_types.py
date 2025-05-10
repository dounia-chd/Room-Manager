from django.core.management.base import BaseCommand
from core.models import RoomType
import os
from django.conf import settings
from django.core.files import File

class Command(BaseCommand):
    help = 'Crée les types de salles prédéfinis pour chaque catégorie'

    def handle(self, *args, **kwargs):
        # Créer le dossier pour les images si nécessaire
        image_dir = os.path.join(settings.MEDIA_ROOT, 'room_types')
        os.makedirs(image_dir, exist_ok=True)

        # Images spécifiques pour certaines salles
        specific_images = {
            'Salle de réunion': 'https://images.unsplash.com/photo-1431540015161-0bf868a2d407',  # Image de salle de réunion moderne
            'Salle de conférence': 'https://images.unsplash.com/photo-1517457373958-b7bdd4587205',  # Image de salle de conférence spacieuse
        }

        # Images par défaut par catégorie pour les autres salles
        category_images = {
            'enterprise': 'https://images.unsplash.com/photo-1497366216548-37526070297c',
            'university': 'https://images.unsplash.com/photo-1523050854058-8df90110c9f1',
            'hotel': 'https://images.unsplash.com/photo-1566073771259-6a8506099945',
            'sport': 'https://images.unsplash.com/photo-1534438327276-14e5300c3a48'
        }

        room_types = [
            # Entreprises
            {
                'name': 'Salle de réunion',
                'category': 'enterprise',
                'description': 'Salle idéale pour les réunions d\'équipe et les présentations'
            },
            {
                'name': 'Salle de conférence',
                'category': 'enterprise',
                'description': 'Grande salle pour les conférences et les événements d\'entreprise'
            },
            {
                'name': 'Espace coworking',
                'category': 'enterprise',
                'description': 'Espace de travail collaboratif avec postes de travail individuels'
            },
            {
                'name': 'Salle de formation',
                'category': 'enterprise',
                'description': 'Salle équipée pour les formations et les ateliers'
            },

            # Universités
            {
                'name': 'Amphithéâtre',
                'category': 'university',
                'description': 'Grande salle pour les cours magistraux et les conférences'
            },
            {
                'name': 'Salle de TD',
                'category': 'university',
                'description': 'Salle pour les travaux dirigés et les petits groupes'
            },
            {
                'name': 'Laboratoire',
                'category': 'university',
                'description': 'Salle équipée pour les travaux pratiques et expérimentations'
            },
            {
                'name': 'Salle informatique',
                'category': 'university',
                'description': 'Salle équipée d\'ordinateurs pour les cours d\'informatique'
            },

            # Hôtels
            {
                'name': 'Salle de banquet',
                'category': 'hotel',
                'description': 'Grande salle pour les banquets et les événements'
            },
            {
                'name': 'Salle de réunion hôtel',
                'category': 'hotel',
                'description': 'Salle de réunion professionnelle avec service hôtelier'
            },
            {
                'name': 'Espace événementiel',
                'category': 'hotel',
                'description': 'Espace polyvalent pour les événements et les réceptions'
            },
            {
                'name': 'Salle de séminaire',
                'category': 'hotel',
                'description': 'Salle équipée pour les séminaires et les formations'
            },

            # Sports
            {
                'name': 'Salle de sport',
                'category': 'sport',
                'description': 'Salle polyvalente pour les activités sportives'
            },
            {
                'name': 'Salle de danse',
                'category': 'sport',
                'description': 'Salle spécialement aménagée pour la danse'
            },
            {
                'name': 'Salle de yoga',
                'category': 'sport',
                'description': 'Espace calme et apaisant pour le yoga et la méditation'
            },
            {
                'name': 'Salle de musculation',
                'category': 'sport',
                'description': 'Salle équipée pour la musculation et le fitness'
            }
        ]

        for room_type_data in room_types:
            room_type, created = RoomType.objects.get_or_create(
                name=room_type_data['name'],
                category=room_type_data['category'],
                defaults={'description': room_type_data['description']}
            )
            
            # Si le type de salle vient d'être créé ou n'a pas d'image
            if created or not room_type.image:
                # Télécharger l'image depuis Unsplash
                import requests
                from io import BytesIO
                
                # Utiliser l'image spécifique si elle existe, sinon utiliser l'image de la catégorie
                image_url = specific_images.get(room_type_data['name'], category_images[room_type_data['category']])
                image_url = f"{image_url}?w=800&h=600&fit=crop"
                
                try:
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        # Sauvegarder l'image
                        image_name = f"{room_type_data['category']}_{room_type_data['name'].lower().replace(' ', '_')}.jpg"
                        image_path = os.path.join(image_dir, image_name)
                        
                        with open(image_path, 'wb') as f:
                            f.write(response.content)
                        
                        # Associer l'image au type de salle
                        with open(image_path, 'rb') as f:
                            room_type.image.save(image_name, File(f), save=True)
                        
                        self.stdout.write(f"Image ajoutée pour {room_type_data['name']}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Erreur lors du téléchargement de l'image pour {room_type_data['name']}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS('Types de salles créés avec succès')) 