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

from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

from horizon import tables

from trove_dashboard import api


LICENSE_TYPE_NAMES = {
    'vertica_license': _('Vertica'),
    'db2_license': _('Db2'),
}


class CreateLicense(tables.LinkAction):
    name = "create"
    verbose_name = _("Add License")
    url = "horizon:project:database_licenses:create"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("database", "module:create"),)


class DeleteLicense(tables.DeleteAction):
    policy_rules = (("database", "module:delete"),)

    @staticmethod
    def action_present(count):
        return ngettext_lazy(
            "Delete License",
            "Delete Licenses",
            count
        )

    @staticmethod
    def action_past(count):
        return ngettext_lazy(
            "Deleted License",
            "Deleted Licenses",
            count
        )

    def delete(self, request, obj_id):
        api.trove.module_delete(request, obj_id)


def get_type(module):
    return LICENSE_TYPE_NAMES.get(module.type, module.type)


def get_datastore(module):
    return "%s %s" % (module.datastore, module.datastore_version)


class LicensesTable(tables.DataTable):
    name = tables.Column("name", verbose_name=_("Name"))
    type = tables.Column(get_type, verbose_name=_("Database"))
    datastore = tables.Column(get_datastore,
                              verbose_name=_("Datastore Version"))
    description = tables.Column("description",
                                verbose_name=_("Description"))
    created = tables.Column("created", verbose_name=_("Created"))

    class Meta(object):
        name = "licenses"
        verbose_name = _("Licenses")
        table_actions = (CreateLicense, DeleteLicense)
        row_actions = (DeleteLicense,)
