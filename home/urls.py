from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('questionnaires/', views.questionnaires, name='questionnaires'),  # Adding the route
]