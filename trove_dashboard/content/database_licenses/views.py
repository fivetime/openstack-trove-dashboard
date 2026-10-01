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

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horizon import exceptions
from horizon import forms as horizon_forms
from horizon import tables as horizon_tables

from trove_dashboard import api
from trove_dashboard.content.database_licenses import forms
from trove_dashboard.content.database_licenses import tables


class IndexView(horizon_tables.DataTableView):
    table_class = tables.LicensesTable
    template_name = 'project/database_licenses/index.html'
    page_title = _("Licenses")

    def get_data(self):
        try:
            return api.trove.license_list(self.request)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve licenses.'))
            return []


class CreateLicenseView(horizon_forms.ModalFormView):
    form_class = forms.CreateLicenseForm
    form_id = "create_license_form"
    modal_header = _("Add License")
    modal_id = "create_license_modal"
    template_name = 'project/database_licenses/create.html'
    submit_label = _("Add License")
    submit_url = reverse_lazy('horizon:project:database_licenses:create')
    success_url = reverse_lazy('horizon:project:database_licenses:index')
    page_title = _("Add License")
