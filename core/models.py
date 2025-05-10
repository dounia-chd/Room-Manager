from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('client', 'Client')
    ]
    
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='client')
    
    def is_admin_user(self):
        return self.role == 'admin' or self.is_superuser

class RoomType(models.Model):
    CATEGORY_CHOICES = [
        ('enterprise', 'Entreprises'),
        ('university', 'Universités'),
        ('hotel', 'Hôtels'),
        ('sport', 'Sports')
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    image = models.ImageField(upload_to='room_types/')

    def __str__(self):
        return f'{self.get_category_display()} - {self.name}'

class Equipment(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, help_text="Classe Font Awesome pour l'icône")

    def __str__(self):
        return self.name

class Room(models.Model):
    name = models.CharField(max_length=100)
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE)
    capacity = models.IntegerField()
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    image = models.ImageField(upload_to='rooms/')
    is_active = models.BooleanField(default=True)
    equipment = models.ManyToManyField(Equipment, blank=True)

    def __str__(self):
        return self.name

    def is_available(self, date, start_time, end_time, exclude_booking=None):
        bookings = self.booking_set.filter(
            date=date,
            status__in=['pending', 'validated', 'in_progress']
        )
        
        if exclude_booking:
            bookings = bookings.exclude(id=exclude_booking.id)
        
        for booking in bookings:
            if (start_time < booking.end_time and end_time > booking.start_time):
                return False
        return True

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('in_progress', 'En cours'),
        ('validated', 'Validée'),
        ('cancelled', 'Annulée')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.username} - {self.room.name} - {self.date}'

class Payment(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100)
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)

    def __str__(self):
        return f'Payment for {self.booking}'

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        self.read = True
        self.save()

class Review(models.Model):
    RATING_CHOICES = [
        (1, '1 étoile'),
        (2, '2 étoiles'),
        (3, '3 étoiles'),
        (4, '4 étoiles'),
        (5, '5 étoiles'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Avis de {self.user.username} sur {self.room.name}'

# Create your models here.
