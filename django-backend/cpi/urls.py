from django.urls import path
from . import views
from .views import record_gps
from .views import AppUserCreateAPIView

urlpatterns = [
    # Android API
    path("outlets/<int:outlet_id>/items/", views.outlet_items),
    path("collectors/<int:collector_id>/outlets/", views.collector_outlets, name="collector-outlets"),

    # Android API
    path("login/", views.collector_login, name="collector-login"),
    path("submit-price/", views.submit_price, name="submit-price"),
    path("start-visit/", views.start_visit, name="start-visit"),
    path("countries/", views.countries_list, name="countries-list"),
    path("record-gps/", record_gps, name="record-gps"),
    path("visits/<int:visit_id>/items/<int:collection_item_id>/saved-price/", views.saved_price, name="saved-price"),
    path("record-start-time/", views.record_start_time, name="record-start-time"),
    path("record-end-time/", views.record_end_time, name="record-end-time"),
    path("items/<int:collection_item_id>/photo/", views.item_photo, name="item-photo"),
    
    path("upload-replacement-photo/",views.upload_item_photo,name="upload-replacement-photo",),
    path("approve-item-photo/",views.ApprovePhotoAPIView.as_view(),name="approve-item-photo",),
    path("reject-item-photo/",views.RejectPhotoAPIView.as_view(),name="reject-item-photo",),
    path("supervisor/photos/<int:photo_id>/approve/",views.supervisor_approve_photo,name="supervisor-approve-photo",),
    path("supervisor/pending-item-photos/",views.pending_item_photos,name="pending-item-photos",),

    # Supervisor Interface
    path("supervisor/login/", views.supervisor_login, name="supervisor-login"),
    path("supervisor/logout/",views.supervisor_logout,name="supervisor-logout",),
    path("supervisor/rounds/", views.supervisor_rounds, name="supervisor-rounds"),
    path("supervisor/rounds/create/", views.supervisor_round_create, name="supervisor-round-create"),
    path("supervisor/rounds/<int:round_id>/open/", views.supervisor_round_open, name="supervisor-round-open"),
    path("supervisor/rounds/<int:round_id>/close/", views.supervisor_round_close, name="supervisor-round-close"),
    path("supervisor/rounds/<int:round_id>/lock/", views.supervisor_round_lock, name="supervisor-round-lock"),
    path("supervisor/", views.supervisor_dashboard, name="supervisor-dashboard"),
    path("supervisor/products/",views.supervisor_products,name="supervisor-products"),
    path("supervisor/products/<int:item_id>/",views.supervisor_product_detail,name="supervisor-product-detail"),
    path("supervisor/products/<int:item_id>/edit/",views.supervisor_product_edit,name="supervisor-product-edit"),
    path("supervisor/products/<int:item_id>/delete/",views.supervisor_product_delete,name="supervisor-product-delete"),
 
    path("supervisor/rounds/<int:round_id>/unlock/",views.supervisor_round_unlock,name="supervisor-round-unlock"),
    path("supervisor/rounds/<int:round_id>/prepare/",views.supervisor_round_prepare,name="supervisor-round-prepare"),
    path("supervisor/outlets/", views.supervisor_outlets, name="supervisor-outlets"),
    path("supervisor/outlets/add/",views.supervisor_outlet_create,name="supervisor-outlet-create"),
    path("supervisor/outlets/<int:outlet_id>/add-item/",views.supervisor_outlet_add_item,name="supervisor-outlet-add-item"),
    path("supervisor/outlets/<int:outlet_id>/delete/",views.supervisor_outlet_delete,name="supervisor-outlet-delete"),
    path("supervisor/outlets/<int:outlet_id>/",views.supervisor_outlet_detail,name="supervisor-outlet-detail"),

    path("supervisor/outlets/<int:outlet_id>/edit/",views.supervisor_outlet_edit,name="supervisor-outlet-edit"),
    path("supervisor/collection-items/",views.supervisor_collection_items,name="supervisor-collection-items"),
    path("supervisor/collection-items/<int:collection_item_id>/",views.supervisor_collection_item_detail,name="supervisor-collection-item-detail"),
    path("supervisor/collection-items/<int:collection_item_id>/edit/",views.supervisor_collection_item_edit,name="supervisor-collection-item-edit"),
    path("supervisor/assignments/",views.supervisor_assignments,name="supervisor-assignments"),

    path("supervisor/assignments/small/",views.supervisor_small_assignment,name="supervisor-small-assignment"),
    path("supervisor/assignments/small/items/",views.supervisor_small_assignment_items,name="supervisor-small-assignment-items",),
    path("supervisor/assignments/large/",views.supervisor_large_assignment,name="supervisor-large-assignment"),
    path("supervisor/assignments/large/items/",views.supervisor_large_assignment_half_items,name="supervisor-large-assignment-half-items",),

    path("supervisor/assignments/clear/",views.supervisor_assignments_clear,name="supervisor-assignments-clear"),
    path("supervisor/assignments/remove/",views.supervisor_assignment_remove,name="supervisor-assignment-remove"),
    path("supervisor/assignments/reassign/",views.supervisor_assignment_reassign,name="supervisor-assignment-reassign",),
    path("supervisor/replacements/", views.supervisor_replacements, name="supervisor-replacements"),
    path("supervisor/replacements/<int:replacement_id>/approve/",views.supervisor_replacement_approve,name="supervisor-replacement-approve"),
    path("supervisor/replacements/<int:replacement_id>/reject/",views.supervisor_replacement_reject,name="supervisor-replacement-reject"),
    path("replacements/<int:replacement_id>/restore/",views.supervisor_restore_original,name="supervisor-replacement-restore-original",),
    path("supervisor/reviews/",views.supervisor_reviews,name="supervisor-reviews"),
    path("supervisor/progress/", views.supervisor_progress, name="supervisor-progress"),
    path("supervisor/reviews/outlet/<int:visit_id>/", views.supervisor_review_outlet, name="supervisor-review-outlet"),
    path("supervisor/reviews/outlet/<int:visit_id>/approve/", views.supervisor_approve_outlet, name="supervisor-approve-outlet"),
    path("supervisor/reviews/outlet/<int:visit_id>/reject/", views.supervisor_reject_outlet, name="supervisor-reject-outlet"),
    path("supervisor/reviews/item/<int:price_id>/comment/", views.supervisor_price_comment, name="supervisor-price-comment"),
    path("rounds/<int:round_id>/reopen/",views.supervisor_round_reopen,name="supervisor-round-reopen",),
    path("users/create/",AppUserCreateAPIView.as_view(),name="app-user-create",),
    path("supervisor/users/",views.supervisor_users,name="supervisor-users",),
    path("supervisor/users/create/",views.supervisor_user_create,name="supervisor-user-create",),
    path("supervisor/users/<int:user_id>/edit/",views.supervisor_user_edit,name="supervisor-user-edit",),
    path("supervisor/users/<int:user_id>/reset-password/",views.supervisor_user_reset_password,name="supervisor-user-reset-password",),



]