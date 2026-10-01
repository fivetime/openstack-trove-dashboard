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

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages

from trove_dashboard import api

# A license file is a few hundred bytes of text.
MAX_LICENSE_SIZE = 64 * 1024


class CreateLicenseForm(forms.SelfHandlingForm):
    name = forms.CharField(label=_("Name"), max_length=255)
    datastore = forms.ChoiceField(
        label=_("Datastore"),
        help_text=_("The database and version the license is for."))
    license_file = forms.FileField(
        label=_("License File"), required=False,
        help_text=_("The license file the vendor issued: a .lic file for "
                    "Db2, the license key file for Vertica."))
    # Kept as it is: a license file is checked byte for byte.
    license_text = forms.CharField(
        label=_("Or Paste the License"), required=False, strip=False,
        widget=forms.Textarea(attrs={'rows': 6}),
        help_text=_("The contents of the license file, if you would rather "
                    "paste them than upload the file."))
    description = forms.CharField(label=_("Description"), required=False,
                                  max_length=255)

    def __init__(self, request, *args, **kwargs):
        super(CreateLicenseForm, self).__init__(request, *args, **kwargs)
        self.fields['datastore'].choices = self._datastore_choices(request)

    @staticmethod
    def _datastore_choices(request):
        choices = []
        try:
            for module_type, name in sorted(
                    api.trove.LICENSE_MODULE_TYPES.items(),
                    key=lambda item: item[1]):
                for version in api.trove.datastore_version_list(request,
                                                                name):
                    choices.append(("%s|%s|%s" % (module_type, name,
                                                  version.name),
                                    "%s %s" % (name, version.name)))
        except Exception:
            exceptions.handle(request,
                              _('Unable to retrieve datastore versions.'))
        if choices:
            choices.insert(0, ("", _("Select a datastore version")))
        else:
            choices.insert(0, ("", _("No licensed datastore available")))
        return choices

    def clean(self):
        cleaned_data = super(CreateLicenseForm, self).clean()
        upload = cleaned_data.get('license_file')
        text = cleaned_data.get('license_text') or ''
        if upload:
            if upload.size > MAX_LICENSE_SIZE:
                raise forms.ValidationError(
                    _("The license file is too large."))
            content = upload.read()
            try:
                content = content.decode('utf-8')
            except UnicodeDecodeError:
                raise forms.ValidationError(
                    _("The license file is not a text file."))
        else:
            # Browsers send the lines of a text area ended by CR LF.
            content = text.replace('\r\n', '\n')
        if not content.strip():
            raise forms.ValidationError(
                _("Upload the license file or paste its contents."))
        cleaned_data['contents'] = content
        return cleaned_data

    def handle(self, request, data):
        module_type, datastore, version = data['datastore'].split('|')
        try:
            api.trove.module_create(
                request, data['name'], module_type, data['contents'],
                description=data.get('description') or None,
                datastore=datastore, datastore_version=version)
            messages.success(request,
                             _('Added license "%s".') % data['name'])
        except Exception:
            redirect = reverse("horizon:project:database_licenses:index")
            exceptions.handle(request, _('Unable to add the license.'),
                              redirect=redirect)
        return True
