from django.urls import path
# from .views import 
from telegram_content_scrapper.telegram_scrapper.views import telegram_user_authentication_view, user_telegram_entities_view, get_telegram_otp_code, fetch_telegram_entity_contents,update_telegram_entity_contents, assign_telegram_entity_contents_fetching_task

app_name = "telegram"

urlpatterns = [
    path("contents/", view=user_telegram_entities_view, name="contents"),
    path("api/entity/contents/", fetch_telegram_entity_contents, name="get-contents"),
    path("api/task/contents/", assign_telegram_entity_contents_fetching_task, name="contents-fetching"),
    path("api/entity/contents/update", update_telegram_entity_contents, name="update-content"),
    path("authentication/", view=telegram_user_authentication_view, name="authentication"),
    path("api/auth/send-otp/", get_telegram_otp_code, name="send-otp"),
]
