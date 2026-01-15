from django.urls import path
from . import views

urlpatterns = [
    path('setup/', views.group_setup, name='group_setup'),
    path('', views.map_view, name='index'),
    path('add/', views.add_property, name='add_property'),
    path('like/<int:property_id>/', views.toggle_like, name='toggle_like'),
    path('add_station/', views.add_station, name='add_station'),
]