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

from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from trove_dashboard import api
from trove_dashboard.test import helpers as test

INDEX_URL = reverse('horizon:project:database_licenses:index')
CREATE_URL = reverse('horizon:project:database_licenses:create')


class DatabaseLicensesTests(test.TestCase):

    def _versions(self, request, name):
        version = mock.Mock()
        version.name = {'db2': '12.1', 'vertica': '25.4'}[name]
        return [version]

    @test.create_mocks({api.trove: ('license_list',)})
    def test_index(self):
        licenses = [m for m in self.database_modules.list()
                    if m.type != 'ping']
        self.mock_license_list.return_value = licenses
        res = self.client.get(INDEX_URL)
        self.mock_license_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, 'project/database_licenses/index.html')
        self.assertEqual(2, len(res.context['table'].data))
        # The page tells the tenant what runs without a license.
        self.assertContains(res, 'Community Edition')

    @test.create_mocks({api.trove: ('license_list',)})
    def test_index_exception(self):
        self.mock_license_list.side_effect = self.exceptions.trove
        res = self.client.get(INDEX_URL)
        self.assertEqual(res.status_code, 200)
        self.assertMessageCount(res, error=1)

    @test.create_mocks({api.trove: ('datastore_version_list',)})
    def test_create_form_offers_the_licensed_datastores(self):
        self.mock_datastore_version_list.side_effect = self._versions
        res = self.client.get(CREATE_URL)
        self.assertTemplateUsed(res, 'project/database_licenses/create.html')
        choices = dict(res.context['form'].fields['datastore'].choices)
        self.assertIn('db2_license|db2|12.1', choices)
        self.assertIn('vertica_license|vertica|25.4', choices)
        # Uploads need a multipart form.
        self.assertContains(res, 'enctype="multipart/form-data"')

    @test.create_mocks({api.trove: ('datastore_version_list',
                                    'module_create')})
    def test_create_from_a_file(self):
        self.mock_datastore_version_list.side_effect = self._versions
        upload = SimpleUploadedFile('db2ese_u.lic', b'[LicenseCertificate]\n')
        res = self.client.post(CREATE_URL, {
            'name': 'prod', 'datastore': 'db2_license|db2|12.1',
            'license_file': upload, 'description': 'bought'})
        self.assertNoFormErrors(res)
        self.mock_module_create.assert_called_once_with(
            test.IsHttpRequest(), 'prod', 'db2_license',
            '[LicenseCertificate]\n', description='bought',
            datastore='db2', datastore_version='12.1')
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({api.trove: ('datastore_version_list',
                                    'module_create')})
    def test_create_from_pasted_text(self):
        self.mock_datastore_version_list.side_effect = self._versions
        res = self.client.post(CREATE_URL, {
            'name': 'vt', 'datastore': 'vertica_license|vertica|25.4',
            'license_text': 'Acme\r\n10TB\r\n'})
        self.assertNoFormErrors(res)
        self.mock_module_create.assert_called_once_with(
            test.IsHttpRequest(), 'vt', 'vertica_license', 'Acme\n10TB\n',
            description=None, datastore='vertica',
            datastore_version='25.4')

    @test.create_mocks({api.trove: ('datastore_version_list',
                                    'module_create')})
    def test_create_needs_a_license(self):
        self.mock_datastore_version_list.side_effect = self._versions
        res = self.client.post(CREATE_URL, {
            'name': 'empty', 'datastore': 'db2_license|db2|12.1',
            'license_text': '  '})
        self.assertFormErrors(res, 1)
        self.mock_module_create.assert_not_called()

    @test.create_mocks({api.trove: ('datastore_version_list',
                                    'module_create')})
    def test_create_refuses_a_binary_file(self):
        self.mock_datastore_version_list.side_effect = self._versions
        upload = SimpleUploadedFile('x.lic', b'\xff\xfe\x00binary')
        res = self.client.post(CREATE_URL, {
            'name': 'bin', 'datastore': 'db2_license|db2|12.1',
            'license_file': upload})
        self.assertFormErrors(res, 1)
        self.mock_module_create.assert_not_called()

    @test.create_mocks({api.trove: ('license_list', 'module_delete')})
    def test_delete(self):
        license = self.database_modules.first()
        self.mock_license_list.return_value = [license]
        res = self.client.post(
            INDEX_URL, {'action': 'licenses__delete__%s' % license.id})
        self.mock_module_delete.assert_called_once_with(
            test.IsHttpRequest(), license.id)
        self.assertRedirectsNoFollow(res, INDEX_URL)


class LicenseApiTests(test.TestCase):

    @mock.patch.object(api.trove, 'module_list')
    def test_license_list_keeps_the_license_types(self, module_list):
        module_list.return_value = self.database_modules.list()
        self.assertEqual(
            ['db2_license', 'vertica_license'],
            sorted(m.type for m in api.trove.license_list(mock.Mock())))
