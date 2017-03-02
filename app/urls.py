"""app URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from blog import views

urlpatterns = [
    url(r'^$', views.IndexView.as_view()),
    url(r'^post/(?P<post_id>\d+)', views.PostView.as_view()),
    url(r'^posts/', views.PostsView.as_view()),
    url(r'^group/(?P<group_id>\d+)', views.GroupView.as_view()),
    url(r'^series/(?P<series_id>\d+)', views.SeriesView.as_view()),
    url(r'^series', views.SeriesListView.as_view()),
    #url(r'^admin/', admin.site.urls),
    url(r'^editor/', views.EditorView.as_view()),
    url(r'^ckeditor/', include('ckeditor_uploader.urls')),
    url(r'^comments/', include('django_comments.urls')),
    url(r'^metrics/', views.MetricsView.as_view()),
    url(r'^render/', views.RenderView.as_view()),
    url(r'^page/(?P<page_number>\d+)', views.IndexView.get_page),
]

from django.conf import settings
from django.conf.urls import include, url
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]