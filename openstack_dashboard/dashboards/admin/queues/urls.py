from django.conf.urls import patterns
from django.conf.urls import url

#from .views import IndexView
from openstack_dashboard.dashboards.admin.queues import views

urlpatterns = patterns('',
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^define/$', views.DefineView.as_view(), name='define'),
)
