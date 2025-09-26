from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/terminal/(?P<server_id>\d+)/$', consumers.SSHTerminalConsumer.as_asgi()),
]