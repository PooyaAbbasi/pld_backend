from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .serializers import TrafficSerializer
from .views import traffic_received


@receiver(traffic_received)
def save_traffic(sender, serializer: TrafficSerializer, **kwargs):

    if serializer.is_valid():
        traffic = serializer.save()

        # send traffic data via a websocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            # send for corresponding clients are in group with place_id.
            f'place_{traffic.gate.place.id}',
            {
                'type': 'new.traffic',  # send with new_traffic method.
                'data': serializer.data  # data as dictionary obj
            }
        )
    else:
        print('not valid', serializer.errors)

