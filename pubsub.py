from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

class AsyncConn:
    def __init__(self, id: str, channel_name: str) -> None:
        config = PNConfiguration()
        config.subscribe_key = 'sub-c-fa0c496a-d5ce-478b-a49c-24c214f7b54f'
        config.publish_key = 'pub-c-a99ddf51-aea9-4a9e-b597-badb9c1120f5'
        config.user_id = id
        config.enable_subscribe = True
        config.daemon = True

        self.pubnub = PubNub(config)
        self.channel_name = channel_name

        print(f"Configurando conexão com o canal '{self.channel_name}'...")
        subscription = self.pubnub.channel(self.channel_name).subscription()
        subscription.subscribe()

    def publish(self, data: dict):
        print("Enviando mensagem para PubNub:", data)
        self.pubnub.publish().channel(self.channel_name).message(data).sync()

