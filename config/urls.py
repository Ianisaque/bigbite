from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('cardapio.urls')),
    path('', include('contas.urls')),
    path('', include('pedidos.urls')),
]

if settings.DEBUG:
    from django.views.generic import TemplateView

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path('erro/404/', TemplateView.as_view(template_name='404.html')),
        path('erro/403/', TemplateView.as_view(template_name='403.html')),
        path('erro/500/', TemplateView.as_view(template_name='500.html')),
    ]