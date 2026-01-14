from django.urls import path
from . import views

urlpatterns = [
    path('', views.map_view, name='index'),
    path('add/', views.add_property, name='add_property'),
    path('like/<int:property_id>/', views.toggle_like, name='toggle_like'),
]