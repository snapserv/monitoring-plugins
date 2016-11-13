import nagiosplugin
import tikapy


class MikrotikApiResource(nagiosplugin.Resource):
    def __init__(self, api_host, api_user, api_pass, api_use_ssl=False):
        self.api_client = None
        self.api_host = api_host
        self.api_user = api_user
        self.api_pass = api_pass
        self.api_use_ssl = api_use_ssl

        self.connect_to_api()

    def connect_to_api(self):
        if self.api_use_ssl:
            self.api_client = tikapy.TikapySslClient(self.api_host)
        else:
            self.api_client = tikapy.TikapyClient(self.api_host)
        self.api_client.login(self.api_user, self.api_pass)
