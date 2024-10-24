from django.shortcuts import render

def home(request):
  return render(request, 'home/index.html')

def questionnaires(request):
    return render(request, 'home/questionnares.html')  # Render the correct template