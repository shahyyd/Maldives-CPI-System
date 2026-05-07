from django.urls import path
from . import views

urlpatterns = [
    path("outlets/<int:outlet_id>/items/", views.outlet_items),
    path("collectors/<int:collector_id>/outlets/", views.collector_outlets, name="collector-outlets"),
    path("login/", views.collector_login, name="collector-login"),
    path("submit-price/", views.submit_price, name="submit-price"),
    path("start-visit/", views.start_visit, name="start-visit"),
    path("countries/", views.countries_list, name="countries-list"),
    path(
    "visits/<int:visit_id>/items/<int:collection_item_id>/saved-price/",
    views.saved_price,
    name="saved-price"
  ),

    path("record-start-time/", views.record_start_time, name="record-start-time"),
 
]
