from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View

from .models import Notification


class NotificationListView(LoginRequiredMixin, View):
    template_name = 'notifications/list.html'

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        return render(request, self.template_name, {'notifications': notifications})


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok'})
        return redirect('notification_list')


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok'})
        return redirect('notification_list')


class NotificationDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok'})
        return redirect('notification_list')


class NotificationAPIView(LoginRequiredMixin, View):
    def get(self, request):
        notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
        data = [{
            'id': n.id, 'type': n.notification_type, 'title': n.title,
            'message': n.message, 'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
        } for n in notifs]
        unread = Notification.objects.filter(user=request.user, is_read=False).count()
        return JsonResponse({'notifications': data, 'unread_count': unread})
