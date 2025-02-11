from channels.generic.websocket import AsyncWebsocketConsumer
import json
from rest_framework.renderers import JSONRenderer


class TrafficConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
            If user is authenticated, then connect to the websocket route.
            and will be added to the room group name "place_{place_id}"
            with provided `place_id` in url.

        """
        user = self.scope["user"]

        if user.is_authenticated:
            self.place_id = self.scope["url_route"]["kwargs"]["place_id"]
            self.room_group_name = f"place_{self.place_id}"

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()  # Reject connection if not authenticated

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        # This consumer won't receive anything.
        pass

    async def new_traffic(self, event):
        # send the provided data.
        traffic_data = event["data"]

        await self.send(
            text_data=json.dumps(traffic_data)
        )

