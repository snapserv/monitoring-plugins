# SnapServ/monitoring-plugins - Simple and reliable Nagios / Icinga plugins
# Copyright (C) 2016 SnapServ - Pascal Mathis
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

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
