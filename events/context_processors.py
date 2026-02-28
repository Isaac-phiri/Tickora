from django.urls import resolve

def home_page_context(request):
    current_url = resolve(request.path_info).url_name
    return {
        'is_home_page': current_url == 'homepage'  # Adjust 'home' to your home page's URL name
    }