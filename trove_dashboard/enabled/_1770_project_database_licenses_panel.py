# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from trove_dashboard import exceptions

PANEL = 'database_licenses'
PANEL_DASHBOARD = 'project'
PANEL_GROUP = 'database'

ADD_PANEL = ('trove_dashboard.content.database_licenses.panel.Licenses')

ADD_EXCEPTIONS = {
    'not_found': exceptions.NOT_FOUND,
    'recoverable': exceptions.RECOVERABLE,
    'unauthorized': exceptions.UNAUTHORIZED,
}
