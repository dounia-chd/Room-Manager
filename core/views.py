from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User, Room, RoomType, Booking, Payment, Notification, Equipment, Review
from django.utils import timezone
from django.db import models
from datetime import datetime
from django.http import FileResponse, HttpResponse
from django.core.files.base import File
from decimal import Decimal
from django.db.models import Sum
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO

def home(request):
    # Récupérer toutes les catégories
    categories = dict(RoomType.CATEGORY_CHOICES)
    
    # Pour chaque catégorie, récupérer les types de salles associés
    room_types_by_category = {}
    for category_code, category_name in categories.items():
        room_types = RoomType.objects.filter(category=category_code)
        if room_types.exists():
            room_types_by_category[category_name] = room_types
    
    # Récupérer les avis approuvés
    reviews = Review.objects.filter(is_approved=True).select_related('user', 'room')[:6]
    
    total_rooms = Room.objects.filter(is_active=True).count()
    total_bookings = Booking.objects.count()
    total_users = User.objects.filter(is_staff=False).count()
    
    context = {
        'room_types_by_category': room_types_by_category,
        'reviews': reviews,
        'total_rooms': total_rooms,
        'total_bookings': total_bookings,
        'total_users': total_users,
    }
    return render(request, 'core/home.html', context)

def preview_site(request):
    """View for previewing the site's content and layout."""
    room_types = RoomType.objects.all()
    rooms = Room.objects.all().order_by('room_type', 'name')
    context = {
        'room_types': room_types,
        'rooms': rooms,
    }
    return render(request, 'core/preview_site.html', context)

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')

        if password1 != password2:
            messages.error(request, 'Les mots de passe ne correspondent pas')
            return redirect('core:register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Ce nom d\'utilisateur est déjà pris')
            return redirect('core:register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà utilisé')
            return redirect('core:register')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            address=address
        )

        login(request, user)
        messages.success(request, 'Inscription réussie !')
        return redirect('core:dashboard')

    return render(request, 'core/register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_type = request.POST.get('user_type')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user_type == 'admin' and not user.is_staff:
                messages.error(request, 'Accès refusé. Vous devez être administrateur.')
                return redirect('core:login')
            elif user_type == 'client' and user.is_staff:
                messages.error(request, 'Veuillez utiliser le formulaire administrateur.')
                return redirect('core:login')
            
            login(request, user)
            return redirect('core:dashboard')  # Redirection vers le tableau de bord pour tous les utilisateurs
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
    
    return render(request, 'core/login.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('core:login')

@login_required
def profile(request):
    if request.method == 'POST':
        user = request.user
        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.phone_number = request.POST.get('phone_number')
        user.address = request.POST.get('address')
        
        new_password = request.POST.get('new_password')
        if new_password:
            user.set_password(new_password)
        
        user.save()
        messages.success(request, 'Votre profil a été mis à jour avec succès!')
        
        if new_password:
            login(request, user)
        return redirect('core:profile')
    
    # Statistiques pour l'utilisateur
    total_bookings = request.user.booking_set.count()
    active_bookings = request.user.booking_set.filter(status__in=['pending', 'confirmed']).count()
    total_spent = sum(booking.total_amount for booking in request.user.booking_set.filter(payment_status=True))
    
    context = {
        'total_bookings': total_bookings,
        'active_bookings': active_bookings,
        'total_spent': total_spent
    }
    
    return render(request, 'core/profile.html', context)

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, 'Accès refusé. Vous devez être administrateur.')
            return redirect('core:login')
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
def dashboard(request):
    if request.user.is_staff:
        # Statistiques pour les administrateurs
        total_bookings = Booking.objects.count()
        total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
        total_users = User.objects.filter(is_staff=False).count()
        total_payments = Payment.objects.count()
        
        # Statistiques des paiements
        today = timezone.now().date()
        payments_today = Payment.objects.filter(payment_date=today).count()
        payments_this_month = Payment.objects.filter(
            payment_date__year=today.year,
            payment_date__month=today.month
        ).count()
        
        # Calcul des pourcentages
        pending_bookings = Booking.objects.filter(status='pending').count()
        pending_percent = (pending_bookings / total_bookings * 100) if total_bookings > 0 else 0
        
        today_payments_percent = (payments_today / total_payments * 100) if total_payments > 0 else 0
        monthly_payments_percent = (payments_this_month / total_payments * 100) if total_payments > 0 else 0
        
        # Réservations récentes
        recent_bookings = Booking.objects.select_related('user', 'room').order_by('-date')[:5]
        
        context = {
            'total_bookings': total_bookings,
            'total_revenue': total_revenue,
            'total_users': total_users,
            'total_payments': total_payments,
            'payments_today': payments_today,
            'payments_this_month': payments_this_month,
            'pending_bookings': pending_bookings,
            'pending_percent': pending_percent,
            'today_payments_percent': today_payments_percent,
            'monthly_payments_percent': monthly_payments_percent,
            'recent_bookings': recent_bookings,
        }
        return render(request, 'core/dashboard.html', context)
    else:
        # Statistiques pour les clients
        user_bookings = Booking.objects.filter(user=request.user)
        total_bookings = user_bookings.count()
        total_spent = Payment.objects.filter(booking__user=request.user).aggregate(total=Sum('amount'))['total'] or 0
        
        # Statistiques des réservations
        booking_stats = {
            'pending': user_bookings.filter(status='pending').count(),
            'in_progress': user_bookings.filter(status='in_progress').count(),
            'validated': user_bookings.filter(status='validated').count(),
            'cancelled': user_bookings.filter(status='cancelled').count(),
        }
        booking_stats['pending_percent'] = (booking_stats['pending'] / total_bookings * 100) if total_bookings > 0 else 0
        
        # Dernier paiement
        last_payment = Payment.objects.filter(booking__user=request.user).order_by('-payment_date').first()
        last_payment_date = last_payment.payment_date if last_payment else None
        
        # Notifications
        notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
        unread_notifications = notifications.filter(read=False).count()
        notifications = notifications[:5]  # Prendre les 5 dernières notifications après le comptage
        notification_percent = (unread_notifications / notifications.count() * 100) if notifications.count() > 0 else 0
        
        # Réservations récentes
        recent_bookings = user_bookings.select_related('room').order_by('-date')[:5]
        
        # Salles recommandées (basé sur les types de salles les plus réservés par l'utilisateur)
        user_room_types = user_bookings.values_list('room__room_type', flat=True).distinct()
        recommended_rooms = Room.objects.filter(
            room_type__in=user_room_types,
            is_active=True
        ).exclude(
            booking__user=request.user
        ).distinct()[:3]
        
        context = {
            'total_bookings': total_bookings,
            'total_spent': total_spent,
            'booking_stats': booking_stats,
            'last_payment_date': last_payment_date,
            'notifications': notifications,
            'unread_notifications': unread_notifications,
            'notification_percent': notification_percent,
            'recent_bookings': recent_bookings,
            'recommended_rooms': recommended_rooms,
        }
        return render(request, 'core/client_dashboard.html', context)

@admin_required
def manage_rooms(request):
    rooms = Room.objects.all().order_by('room_type', 'name')
    room_types = RoomType.objects.all()
    equipments = Equipment.objects.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        room_id = request.POST.get('room_id')
        
        if action == 'add':
            name = request.POST.get('name')
            room_type_id = request.POST.get('room_type')
            capacity = request.POST.get('capacity')
            price_per_hour = request.POST.get('price_per_hour')
            description = request.POST.get('description')
            image = request.FILES.get('image')
            equipment_ids = request.POST.getlist('equipment')
            
            room = Room.objects.create(
                name=name,
                room_type_id=room_type_id,
                capacity=capacity,
                price_per_hour=price_per_hour,
                description=description,
                image=image
            )
            
            if equipment_ids:
                room.equipment.set(equipment_ids)
            
            messages.success(request, f'La salle {name} a été créée avec succès.')
            return redirect('core:manage_rooms')
            
        elif action and room_id:
            room = get_object_or_404(Room, id=room_id)
            if action == 'toggle_active':
                room.is_active = not room.is_active
                room.save()
                messages.success(request, f'Statut de la salle {room.name} mis à jour.')
    
    context = {
        'rooms': rooms,
        'room_types': room_types,
        'equipments': equipments
    }
    return render(request, 'core/admin/manage_rooms.html', context)

@login_required
def manage_users(request):
    if not request.user.is_staff:
        return redirect('core:dashboard')
    
    users = User.objects.all()
    
    # Statistiques des utilisateurs
    total_users = users.count()
    active_users = users.filter(is_active=True).count()
    inactive_users = users.filter(is_active=False).count()
    
    # Pour chaque utilisateur, récupérer ses statistiques
    for user in users:
        user.total_bookings = user.booking_set.count()
        user.total_payments = Payment.objects.filter(booking__user=user).count()
        user.total_notifications = Notification.objects.filter(recipient=user).count()
        user.total_spent = sum(payment.amount for payment in Payment.objects.filter(booking__user=user))
    
    return render(request, 'core/admin/manage_users.html', {
        'users': users,
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'is_admin': True
    })

@admin_required
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Update user information
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.phone_number = request.POST.get('phone_number')
        user.address = request.POST.get('address')
        user.is_active = request.POST.get('is_active') == 'on'
        
        # Update password if provided
        new_password = request.POST.get('new_password')
        if new_password:
            user.set_password(new_password)
        
        user.save()
        messages.success(request, f'Utilisateur {user.username} mis à jour avec succès.')
        return redirect('core:manage_users')
    
    return render(request, 'core/admin/edit_user.html', {
        'user': user,
        'is_admin': True
    })

@admin_required
def manage_bookings(request):
    bookings = Booking.objects.all().order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        new_status = request.POST.get('status')
        
        if booking_id and new_status:
            booking = get_object_or_404(Booking, id=booking_id)
            booking.status = new_status
            booking.save()
            messages.success(request, f'Statut de la réservation mis à jour.')
    
    # Calculer les statistiques par statut
    booking_stats = {
        'pending': Booking.objects.filter(status='pending').count(),
        'in_progress': Booking.objects.filter(status='in_progress').count(),
        'validated': Booking.objects.filter(status='validated').count(),
        'cancelled': Booking.objects.filter(status='cancelled').count()
    }
    
    context = {
        'bookings': bookings,
        'status_choices': Booking.STATUS_CHOICES,
        'booking_stats': booking_stats
    }
    return render(request, 'core/admin/manage_bookings.html', context)

def room_types(request):
    room_types = RoomType.objects.all()
    return render(request, 'core/room_types.html', {
        'room_types': room_types
    })

def room_list(request):
    room_type_id = request.GET.get('type')
    search_query = request.GET.get('search')
    
    if room_type_id:
        rooms = Room.objects.filter(room_type_id=room_type_id, is_active=True)
    else:
        rooms = Room.objects.filter(is_active=True)
    
    if search_query:
        rooms = rooms.filter(name__icontains=search_query)
    
    room_types = RoomType.objects.all()
    return render(request, 'core/room_list.html', {'rooms': rooms, 'room_types': room_types, 'search_query': search_query})

def room_detail(request, pk):
    room = get_object_or_404(Room, pk=pk)
    return render(request, 'core/room_detail.html', {'room': room})

@login_required
def book_room(request, pk):
    room = get_object_or_404(Room, pk=pk)
    
    if request.method == 'POST':
        date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        if not room.is_available(date, start_time, end_time):
            messages.error(request, 'Cette salle n\'est pas disponible pour la période sélectionnée.')
            return redirect('core:room_detail', pk=pk)
        
        # Calculer le montant total
        start = datetime.strptime(start_time, '%H:%M')
        end = datetime.strptime(end_time, '%H:%M')
        duration = Decimal(str((end - start).total_seconds() / 3600))  # durée en heures
        total_amount = room.price_per_hour * duration
        
        # Créer la réservation
        booking = Booking.objects.create(
            user=request.user,
            room=room,
            date=date,
            start_time=start_time,
            end_time=end_time,
            total_amount=total_amount
        )
        
        # Créer une notification
        Notification.objects.create(
            recipient=request.user,
            title='Réservation créée',
            message=f'Votre réservation pour {room.name} a été créée. Montant total: {total_amount}€'
        )
        
        return redirect('core:payment', pk=booking.pk)
    
    return render(request, 'core/book_room.html', {'room': room})

@login_required
def booking_list(request):
    status_filter = request.GET.get('status')
    date_filter = request.GET.get('date')
    
    bookings = request.user.booking_set.all().order_by('-date', '-start_time')
    
    if status_filter and status_filter != 'all':
        bookings = bookings.filter(status=status_filter)
        
    if date_filter:
        if date_filter == 'today':
            bookings = bookings.filter(date=timezone.now().date())
        elif date_filter == 'week':
            start_of_week = timezone.now().date() - timezone.timedelta(days=timezone.now().weekday())
            end_of_week = start_of_week + timezone.timedelta(days=6)
            bookings = bookings.filter(date__range=[start_of_week, end_of_week])
        elif date_filter == 'month':
            today = timezone.now().date()
            bookings = bookings.filter(date__year=today.year, date__month=today.month)
    
    # Grouper les réservations par statut pour les statistiques
    stats = {
        'total': bookings.count(),
        'pending': bookings.filter(status='pending').count(),
        'in_progress': bookings.filter(status='in_progress').count(),
        'validated': bookings.filter(status='validated').count(),
        'cancelled': bookings.filter(status='cancelled').count(),
    }
    
    context = {
        'bookings': bookings,
        'stats': stats,
        'current_status': status_filter,
        'current_date': date_filter,
        'status_choices': Booking.STATUS_CHOICES
    }
    
    return render(request, 'core/booking_list.html', context)

@login_required
def payment(request, pk):
    booking = get_object_or_404(Booking, id=pk, user=request.user)
    
    if request.method == 'POST':
        # Simuler un paiement réussi
        booking.payment_status = True
        booking.status = 'validated'
        booking.save()
        
        # Créer un paiement
        payment = Payment.objects.create(
            booking=booking,
            amount=booking.total_amount,
            payment_date=timezone.now()
        )
        
        # Créer une notification
        Notification.objects.create(
            recipient=request.user,
            title='Paiement confirmé',
            message=f'Votre paiement de {booking.total_amount}€ pour la réservation de {booking.room.name} a été confirmé.'
        )
        
        # Rediriger vers le reçu
        return redirect('core:payment_receipt', booking_id=booking.id)
    
    return render(request, 'core/payment.html', {
        'booking': booking,
        'title': 'Paiement'
    })

@login_required
def payment_receipt(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if not booking.payment_status:
        messages.error(request, "Cette réservation n'a pas encore été payée.")
        return redirect('core:my_bookings')
    
    # Récupérer le paiement associé
    payment = Payment.objects.filter(booking=booking).first()
    if not payment:
        messages.error(request, "Aucun paiement trouvé pour cette réservation.")
        return redirect('core:my_bookings')
    
    # Créer le PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Centré
    )
    
    # Style pour les informations
    info_style = ParagraphStyle(
        'CustomInfo',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12
    )
    
    # Titre
    story.append(Paragraph("Reçu de Paiement", title_style))
    story.append(Spacer(1, 20))
    
    # Informations de la réservation
    story.append(Paragraph(f"<b>Numéro de réservation:</b> #{booking.id}", info_style))
    story.append(Paragraph(f"<b>Date:</b> {booking.date.strftime('%d/%m/%Y')}", info_style))
    story.append(Paragraph(f"<b>Heure:</b> {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}", info_style))
    story.append(Paragraph(f"<b>Salle:</b> {booking.room.name}", info_style))
    story.append(Paragraph(f"<b>Montant payé:</b> {booking.total_amount}€", info_style))
    story.append(Paragraph(f"<b>Date du paiement:</b> {payment.payment_date.strftime('%d/%m/%Y %H:%M')}", info_style))
    
    # Construire le PDF
    doc.build(story)
    
    # Préparer la réponse
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="receipt_{booking.id}.pdf"'
    
    return response

@login_required
def download_receipt(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if not booking.payment_status:
        messages.error(request, "Cette réservation n'a pas encore été payée.")
        return redirect('core:my_bookings')
    
    # Récupérer le paiement associé
    payment = Payment.objects.filter(booking=booking).first()
    if not payment:
        messages.error(request, "Aucun paiement trouvé pour cette réservation.")
        return redirect('core:my_bookings')
    
    # Créer le PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Centré
    )
    
    # Style pour les informations
    info_style = ParagraphStyle(
        'CustomInfo',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12
    )
    
    # Titre
    story.append(Paragraph("Reçu de Paiement", title_style))
    story.append(Spacer(1, 20))
    
    # Informations de la réservation
    story.append(Paragraph(f"<b>Numéro de réservation:</b> #{booking.id}", info_style))
    story.append(Paragraph(f"<b>Date:</b> {booking.date.strftime('%d/%m/%Y')}", info_style))
    story.append(Paragraph(f"<b>Heure:</b> {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}", info_style))
    story.append(Paragraph(f"<b>Salle:</b> {booking.room.name}", info_style))
    story.append(Paragraph(f"<b>Montant payé:</b> {booking.total_amount}€", info_style))
    story.append(Paragraph(f"<b>Date du paiement:</b> {payment.payment_date.strftime('%d/%m/%Y %H:%M')}", info_style))
    
    # Construire le PDF
    doc.build(story)
    
    # Préparer la réponse
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{booking.id}.pdf"'
    
    return response

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Créer une notification pour tous les administrateurs
        admin_users = User.objects.filter(is_staff=True)
        for admin in admin_users:
            Notification.objects.create(
                recipient=admin,
                title=f'Nouveau message de contact: {subject}',
                message=f'Message de {name} ({email}):\n\n{message}'
            )
        
        messages.success(request, 'Votre message a été envoyé avec succès!')
        return redirect('core:contact')
    return render(request, 'core/contact.html')

def help_page(request):
    return render(request, 'core/help.html')

@login_required
def cancel_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    if request.method == 'POST' and booking.status in ['pending', 'confirmed']:
        booking.status = 'cancelled'
        booking.save()
        messages.success(request, 'Votre réservation a été annulée avec succès.')
    return redirect('core:booking_list')

@login_required
def notifications(request):
    # Récupérer toutes les notifications de l'utilisateur
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    # Compter les notifications non lues
    unread_count = notifications.filter(read=False).count()
    
    if request.method == 'POST':
        notification_id = request.POST.get('notification_id')
        action = request.POST.get('action')
        
        if notification_id and action:
            notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
            if action == 'mark_read':
                notification.mark_as_read()
                messages.success(request, 'Notification marquée comme lue.')
            elif action == 'delete':
                notification.delete()
                messages.success(request, 'Notification supprimée.')
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'is_admin': request.user.is_staff
    }
    return render(request, 'core/notifications.html', context)

@login_required
def my_bookings(request):
    # Récupérer toutes les réservations de l'utilisateur, triées par date et heure
    bookings = Booking.objects.filter(user=request.user).order_by('-date', '-start_time')
    
    # Ajouter des logs de débogage détaillés
    print(f"Nombre de réservations trouvées : {bookings.count()}")
    for booking in bookings:
        print(f"Réservation #{booking.id}")
        print(f"- Statut : {booking.status}")
        print(f"- Statut d'affichage : {dict(Booking.STATUS_CHOICES).get(booking.status)}")
        print(f"- Est en attente : {booking.status == 'pending'}")
        print(f"- Est validée : {booking.status == 'validated'}")
        print(f"- Est payée : {booking.payment_status}")
        print("---")
    
    context = {
        'bookings': bookings,
    }
    return render(request, 'core/my_bookings.html', context)

@login_required
def delete_booking(request, booking_id):
    """
    Vue pour supprimer une réservation.
    Seuls les administrateurs peuvent supprimer les réservations.
    """
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas les permissions nécessaires pour effectuer cette action.")
        return redirect('home')
    
    try:
        booking = Booking.objects.get(id=booking_id)
        booking.delete()
        messages.success(request, "La réservation a été supprimée avec succès.")
    except Booking.DoesNotExist:
        messages.error(request, "La réservation n'existe pas.")
    except Exception as e:
        messages.error(request, f"Une erreur est survenue lors de la suppression : {str(e)}")
    
    return redirect('manage_bookings')

@login_required
def delete_room(request, room_id):
    """Vue pour supprimer une salle."""
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas les permissions nécessaires.")
        return redirect('core:home')
    
    try:
        room = Room.objects.get(id=room_id)
        room_name = room.name
        room.delete()
        messages.success(request, f"La salle '{room_name}' a été supprimée avec succès.")
    except Room.DoesNotExist:
        messages.error(request, "La salle n'existe pas.")
    except Exception as e:
        messages.error(request, f"Une erreur est survenue lors de la suppression de la salle: {str(e)}")
    
    return redirect('core:manage_rooms')

@admin_required
def add_room(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        room_type_id = request.POST.get('room_type')
        capacity = request.POST.get('capacity')
        price_per_hour = request.POST.get('price_per_hour')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        
        room_type = get_object_or_404(RoomType, id=room_type_id)
        
        room = Room.objects.create(
            name=name,
            room_type=room_type,
            capacity=capacity,
            price_per_hour=price_per_hour,
            description=description,
            image=image
        )
        
        equipment_ids = request.POST.getlist('equipment')
        if equipment_ids:
            room.equipment.set(Equipment.objects.filter(id__in=equipment_ids))
        
        messages.success(request, 'La salle a été ajoutée avec succès!')
        return redirect('core:manage_rooms')
        
    room_types = RoomType.objects.all()
    equipments = Equipment.objects.all()
    
    context = {
        'room_types': room_types,
        'equipments': equipments,
    }
    
    return render(request, 'core/admin/add_room.html', context)

@admin_required
def edit_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    
    if request.method == 'POST':
        room.name = request.POST.get('name')
        room.room_type = get_object_or_404(RoomType, id=request.POST.get('room_type'))
        room.capacity = request.POST.get('capacity')
        room.price_per_hour = request.POST.get('price_per_hour')
        room.description = request.POST.get('description')
        
        if 'image' in request.FILES:
            room.image = request.FILES['image']
            
        room.save()
        
        equipment_ids = request.POST.getlist('equipment')
        room.equipment.set(Equipment.objects.filter(id__in=equipment_ids))
        
        messages.success(request, 'La salle a été modifiée avec succès!')
        return redirect('core:manage_rooms')
    
    room_types = RoomType.objects.all()
    equipments = Equipment.objects.all()
    
    context = {
        'room': room,
        'room_types': room_types,
        'equipments': equipments,
    }
    
    return render(request, 'core/admin/edit_room.html', context)

@admin_required
def manage_equipment(request):
    equipment_list = Equipment.objects.all()
    return render(request, 'core/admin/manage_equipment.html', {'equipment_list': equipment_list})

@admin_required
def add_equipment(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        Equipment.objects.create(name=name, description=description)
        messages.success(request, 'L\'équipement a été ajouté avec succès!')
        return redirect('core:manage_equipment')
    return render(request, 'core/admin/add_equipment.html')

@admin_required
def edit_equipment(request, equipment_id):
    equipment = get_object_or_404(Equipment, id=equipment_id)
    if request.method == 'POST':
        equipment.name = request.POST.get('name')
        equipment.description = request.POST.get('description')
        equipment.save()
        messages.success(request, 'L\'équipement a été modifié avec succès!')
        return redirect('core:manage_equipment')
    return render(request, 'core/admin/edit_equipment.html', {'equipment': equipment})

@admin_required
def delete_equipment(request, equipment_id):
    equipment = get_object_or_404(Equipment, id=equipment_id)
    equipment.delete()
    messages.success(request, 'L\'équipement a été supprimé avec succès!')
    return redirect('core:manage_equipment')

@admin_required
def equipment_detail(request, equipment_id):
    equipment = get_object_or_404(Equipment, id=equipment_id)
    return render(request, 'core/admin/equipment_detail.html', {'equipment': equipment})

@admin_required
def manage_notifications(request):
    notifications = Notification.objects.all().order_by('-created_at')
    return render(request, 'core/admin/manage_notifications.html', {'notifications': notifications})

@admin_required
def add_notification(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')
        recipient_id = request.POST.get('recipient')
        recipient = get_object_or_404(User, id=recipient_id) if recipient_id else None
        
        Notification.objects.create(
            title=title,
            message=message,
            recipient=recipient
        )
        messages.success(request, 'La notification a été créée avec succès!')
        return redirect('core:manage_notifications')
    
    users = User.objects.all()
    return render(request, 'core/admin/add_notification.html', {'users': users})

@admin_required
def edit_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    if request.method == 'POST':
        notification.title = request.POST.get('title')
        notification.message = request.POST.get('message')
        recipient_id = request.POST.get('recipient')
        notification.recipient = get_object_or_404(User, id=recipient_id) if recipient_id else None
        notification.save()
        messages.success(request, 'La notification a été modifiée avec succès!')
        return redirect('core:manage_notifications')
    
    users = User.objects.all()
    return render(request, 'core/admin/edit_notification.html', {
        'notification': notification,
        'users': users
    })

@admin_required
def delete_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    notification.delete()
    messages.success(request, 'La notification a été supprimée avec succès!')
    return redirect('core:manage_notifications')

@admin_required
def notification_detail(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    return render(request, 'core/admin/notification_detail.html', {'notification': notification})

@admin_required
def manage_payments(request):
    payments = Payment.objects.all().order_by('-created_at')
    return render(request, 'core/admin/manage_payments.html', {'payments': payments})

@admin_required
def payment_detail(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    return render(request, 'core/admin/payment_detail.html', {'payment': payment})

@admin_required
def reports(request):
    # Statistiques générales
    total_bookings = Booking.objects.count()
    total_revenue = sum(booking.total_amount for booking in Booking.objects.filter(payment_status=True))
    total_users = User.objects.filter(role='client').count()
    
    # Statistiques par type de salle
    room_type_stats = RoomType.objects.annotate(
        booking_count=models.Count('room__booking'),
        total_revenue=models.Sum('room__booking__total_amount', filter=models.Q(room__booking__payment_status=True))
    )
    
    context = {
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'total_users': total_users,
        'room_type_stats': room_type_stats,
    }
    
    return render(request, 'core/admin/reports.html', context)

@admin_required
def admin_settings(request):
    if request.method == 'POST':
        # Traitement des paramètres du site
        pass
    return render(request, 'core/admin/settings.html')

@admin_required
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Utilisateur {username} supprimé avec succès.')
        return redirect('core:manage_users')
    return redirect('core:manage_users')

@admin_required
def download_users_list(request):
    users = User.objects.all().order_by('username')
    
    # Créer le PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Centré
    )
    
    # Style pour les informations
    info_style = ParagraphStyle(
        'CustomInfo',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12
    )
    
    # Titre
    story.append(Paragraph("Liste des Utilisateurs", title_style))
    story.append(Spacer(1, 20))
    
    # Informations des utilisateurs
    for user in users:
        story.append(Paragraph(f"<b>Nom d'utilisateur:</b> {user.username}", info_style))
        story.append(Paragraph(f"<b>Email:</b> {user.email}", info_style))
        story.append(Paragraph(f"<b>Nom:</b> {user.first_name} {user.last_name}", info_style))
        story.append(Paragraph(f"<b>Téléphone:</b> {user.phone_number}", info_style))
        story.append(Paragraph(f"<b>Adresse:</b> {user.address}", info_style))
        story.append(Paragraph(f"<b>Rôle:</b> {'Administrateur' if user.is_staff else 'Client'}", info_style))
        story.append(Paragraph(f"<b>Date d'inscription:</b> {user.date_joined.strftime('%d/%m/%Y')}", info_style))
        story.append(Spacer(1, 20))
    
    # Construire le PDF
    doc.build(story)
    
    # Préparer la réponse
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="users_list.pdf"'
    
    return response

@admin_required
def download_bookings_list(request):
    bookings = Booking.objects.all().select_related('user', 'room').order_by('-date', '-start_time')
    
    # Créer le PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Centré
    )
    
    # Style pour les informations
    info_style = ParagraphStyle(
        'CustomInfo',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12
    )
    
    # Titre
    story.append(Paragraph("Liste des Réservations", title_style))
    story.append(Spacer(1, 20))
    
    # Informations des réservations
    for booking in bookings:
        story.append(Paragraph(f"<b>Réservation #{booking.id}</b>", info_style))
        story.append(Paragraph(f"<b>Client:</b> {booking.user.username}", info_style))
        story.append(Paragraph(f"<b>Salle:</b> {booking.room.name}", info_style))
        story.append(Paragraph(f"<b>Date:</b> {booking.date.strftime('%d/%m/%Y')}", info_style))
        story.append(Paragraph(f"<b>Heure:</b> {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}", info_style))
        story.append(Paragraph(f"<b>Montant:</b> {booking.total_amount}€", info_style))
        story.append(Paragraph(f"<b>Statut:</b> {booking.status}", info_style))
        story.append(Paragraph(f"<b>Paiement:</b> {'Payé' if booking.payment_status else 'En attente'}", info_style))
        story.append(Spacer(1, 20))
    
    # Construire le PDF
    doc.build(story)
    
    # Préparer la réponse
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="bookings_list.pdf"'
    
    return response

@admin_required
def download_rooms_list(request):
    rooms = Room.objects.all().select_related('room_type').order_by('room_type', 'name')
    
    # Créer le PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Centré
    )
    
    # Style pour les informations
    info_style = ParagraphStyle(
        'CustomInfo',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12
    )
    
    # Titre
    story.append(Paragraph("Liste des Salles", title_style))
    story.append(Spacer(1, 20))
    
    # Informations des salles
    for room in rooms:
        story.append(Paragraph(f"<b>Salle:</b> {room.name}", info_style))
        story.append(Paragraph(f"<b>Type:</b> {room.room_type.name}", info_style))
        story.append(Paragraph(f"<b>Capacité:</b> {room.capacity} personnes", info_style))
        story.append(Paragraph(f"<b>Prix par heure:</b> {room.price_per_hour}€", info_style))
        story.append(Paragraph(f"<b>Description:</b> {room.description}", info_style))
        story.append(Paragraph(f"<b>Statut:</b> {'Active' if room.is_active else 'Inactive'}", info_style))
        story.append(Spacer(1, 20))
    
    # Construire le PDF
    doc.build(story)
    
    # Préparer la réponse
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="rooms_list.pdf"'
    
    return response

@login_required
def edit_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Vérifier si la réservation peut être modifiée
    if booking.status != 'pending':
        messages.error(request, "Seules les réservations en attente peuvent être modifiées.")
        return redirect('core:my_bookings')
    
    if request.method == 'POST':
        date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        try:
            # Convertir les chaînes en objets datetime
            booking_date = datetime.strptime(date, '%Y-%m-%d').date()
            start_datetime = datetime.strptime(start_time, '%H:%M').time()
            end_datetime = datetime.strptime(end_time, '%H:%M').time()
            
            # Vérifier si la nouvelle date est dans le futur
            if booking_date < timezone.now().date():
                messages.error(request, "La date de réservation doit être dans le futur.")
                return redirect('core:my_bookings')
            
            # Vérifier si la salle est disponible pour la nouvelle date et heure
            if not booking.room.is_available(booking_date, start_datetime, end_datetime, exclude_booking=booking):
                messages.error(request, "La salle n'est pas disponible pour cette date et ces horaires.")
                return redirect('core:my_bookings')
            
            # Mettre à jour la réservation
            booking.date = booking_date
            booking.start_time = start_datetime
            booking.end_time = end_datetime
            
            # Recalculer le montant total
            start = datetime.combine(booking_date, start_datetime)
            end = datetime.combine(booking_date, end_datetime)
            duration = Decimal(str((end - start).total_seconds() / 3600))
            booking.total_amount = booking.room.price_per_hour * duration
            
            booking.save()
            
            # Créer une notification
            Notification.objects.create(
                recipient=request.user,
                title='Réservation modifiée',
                message=f'Votre réservation pour {booking.room.name} a été modifiée avec succès. Nouveau montant: {booking.total_amount}€'
            )
            
            messages.success(request, "La réservation a été modifiée avec succès.")
            return redirect('core:my_bookings')
            
        except ValueError:
            messages.error(request, "Format de date ou d'heure invalide.")
            return redirect('core:my_bookings')
    
    return redirect('core:my_bookings')
