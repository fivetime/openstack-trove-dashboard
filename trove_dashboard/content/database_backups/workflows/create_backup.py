# Copyright 2013 Rackspace Hosting
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging

from django.utils.translation import gettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon.utils import memoized
from horizon import workflows

from trove_dashboard import api
from trove_dashboard.content.databases import db_capability
from trove_dashboard.content.databases \
    import tables as project_tables


LOG = logging.getLogger(__name__)


class BackupDetailsAction(workflows.Action):
    name = forms.CharField(max_length=80, label=_("Name"),
                           help_text=_("Name of the backup."))
    instance = forms.ChoiceField(label=_("Database Instance"),
                                 help_text=_("Select the database instance to "
                                             "backup."),
                                 widget=forms.Select(attrs={
                                     'class': 'switchable',
                                     'data-slug': 'instance'}))
    description = forms.CharField(max_length=512, label=_("Description"),
                                  widget=forms.TextInput(),
                                  required=False,
                                  help_text=_("Optional Backup Description"))
    # Shown only for an instance whose backups can be incremental.
    parent = forms.ChoiceField(label=_("Parent Backup"),
                               required=False,
                               help_text=_("Optional parent backup: a backup "
                                           "of the same instance this one "
                                           "builds on."),
                               widget=forms.Select(attrs={
                                   'class': 'switched',
                                   'data-switch-on': 'instance'}))
    swift_container = forms.CharField(max_length=256,
                                      widget=forms.TextInput(),
                                      label=_("Swift Container Name"),
                                      required=False,
                                      help_text=_(
                                          "User defined swift container name.")
                                      )

    class Meta(object):
        name = _("Details")
        help_text_template = \
            "project/database_backups/_backup_details_help.html"

    @memoized.memoized_method
    def _instances(self, request):
        # Every page: a project with more instances than a page holds
        # could not pick the ones after it.
        try:
            instances = api.trove.instance_list_all(request)
        except Exception:
            instances = []
            msg = _("Unable to list database instances to backup.")
            exceptions.handle(request, msg)
        return [i for i in instances
                if i.status in project_tables.ACTIVE_STATES]

    def _incremental_instances(self, request):
        return {i.id for i in self._instances(request)
                if db_capability.supports_incremental_backup(
                    (getattr(i, 'datastore', None) or {}).get('type'))}

    def populate_instance_choices(self, request, context):
        LOG.info("Obtaining list of instances.")
        return [(i.id, i.name) for i in self._instances(request)]

    @memoized.memoized_method
    def _backups(self, request):
        try:
            return [b for b in api.trove.backup_list(request)
                    if b.status == 'COMPLETED']
        except Exception:
            msg = _("Unable to list parent database backups.")
            exceptions.handle(request, msg)
            return []

    def populate_parent_choices(self, request, context):
        incremental = self._incremental_instances(request)
        widget = self.fields['parent'].widget
        for instance_id in incremental:
            widget.attrs['data-instance-' + instance_id] = _("Parent Backup")
        names = {i.id: i.name for i in self._instances(request)}
        choices = [(b.id, "%s (%s)" % (b.name, names[b.instance_id]))
                   for b in self._backups(request)
                   if b.instance_id in incremental]

        if choices:
            choices.insert(0, ("", _("Select parent backup")))
        else:
            choices.insert(0, ("", _("No backups available")))
        return choices

    def clean(self):
        cleaned_data = super(BackupDetailsAction, self).clean()
        parent = cleaned_data.get('parent')
        instance = cleaned_data.get('instance')
        if parent and instance:
            if instance not in self._incremental_instances(self.request):
                raise forms.ValidationError(_(
                    "Backups of this database cannot be incremental: leave "
                    "the parent backup empty."))
            backup = next((b for b in self._backups(self.request)
                           if b.id == parent), None)
            if backup is None or backup.instance_id != instance:
                raise forms.ValidationError(_(
                    "The parent backup must be a backup of the same "
                    "instance."))
        return cleaned_data


class SetBackupDetails(workflows.Step):
    action_class = BackupDetailsAction
    contributes = ["name", "description", "instance", "parent",
                   "swift_container"]


class CreateBackup(workflows.Workflow):
    slug = "create_backup"
    name = _("Backup Database")
    finalize_button_name = _("Create Backup")
    success_message = _('Scheduled backup "%(name)s".')
    failure_message = _('Unable to launch %(count)s named "%(name)s".')
    success_url = "horizon:project:database_backups:index"
    default_steps = [SetBackupDetails]

    def get_initial(self):
        initial = super(CreateBackup, self).get_initial()
        initial['instance_id']

    def format_status_message(self, message):
        name = self.context.get('name', 'unknown instance')
        return message % {"count": _("instance"), "name": name}

    def handle(self, request, context):
        try:
            LOG.info("Creating backup")
            api.trove.backup_create(request,
                                    context['name'],
                                    context['instance'],
                                    context['description'],
                                    context['parent'],
                                    context['swift_container'])
            return True
        except Exception:
            LOG.exception("Exception while creating backup")
            msg = _('Error creating database backup.')
            exceptions.handle(request, msg)
            return False
