# Copyright (c) 2014 eBay Software Foundation
# Copyright 2015 HP Software, LLC
# All Rights Reserved.
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
from unittest import mock

from django.urls import reverse
from openstack_dashboard import api
from troveclient import common

from trove_dashboard import api as trove_api
from trove_dashboard.content.database_clusters \
    import cluster_manager
from trove_dashboard.content.database_clusters import forms
from trove_dashboard.content.database_clusters import tables
from trove_dashboard.content.database_clusters import tabs
from trove_dashboard.content.databases import db_capability
from trove_dashboard.test import helpers as test
from trove_dashboard.utils import common as common_utils

INDEX_URL = reverse('horizon:project:database_clusters:index')
LAUNCH_URL = reverse('horizon:project:database_clusters:launch')
DETAILS_URL = reverse('horizon:project:database_clusters:detail', args=['id'])
RESET_PASSWORD_VIEWNAME = 'horizon:project:database_clusters:reset_password'


class ClustersTests(test.TestCase):
    @test.create_mocks({trove_api.trove: ('cluster_list',
                                          'flavor_list')})
    def test_index(self):
        clusters = common.Paginated(self.trove_clusters.list())
        self.mock_cluster_list.return_value = clusters
        self.mock_flavor_list.return_value = self.flavors.list()

        res = self.client.get(INDEX_URL)
        self.mock_cluster_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, 'project/database_clusters/index.html')

    @test.create_mocks({trove_api.trove: ('cluster_list',
                                          'flavor_list')})
    def test_index_flavor_exception(self):
        clusters = common.Paginated(self.trove_clusters.list())
        self.mock_cluster_list.return_value = clusters
        self.mock_flavor_list.side_effect = self.exceptions.trove

        res = self.client.get(INDEX_URL)
        self.mock_cluster_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, 'project/database_clusters/index.html')
        self.assertMessageCount(res, error=1)

    @test.create_mocks({trove_api.trove: ('cluster_list',)})
    def test_index_list_exception(self):
        self.mock_cluster_list.side_effect = self.exceptions.trove

        res = self.client.get(INDEX_URL)
        self.mock_cluster_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        self.assertTemplateUsed(res, 'project/database_clusters/index.html')
        self.assertMessageCount(res, error=1)

    @test.create_mocks({trove_api.trove: ('cluster_list',
                                          'flavor_list')})
    def test_index_pagination(self):
        clusters = self.trove_clusters.list()
        last_record = clusters[1]
        clusters = common.Paginated(clusters, next_marker="foo")
        self.mock_cluster_list.return_value = clusters
        self.mock_flavor_list.return_value = self.flavors.list()

        res = self.client.get(INDEX_URL)
        self.mock_cluster_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, 'project/database_clusters/index.html')
        self.assertContains(
            res, 'marker=' + last_record.id)

    @test.create_mocks({trove_api.trove: ('datastore_flavors',
                                          'datastore_list',
                                          'datastore_version_list'),
                        api.cinder: ['volume_type_list'],
                        api.base: ['is_service_enabled']})
    def test_launch_cluster(self):
        self.mock_is_service_enabled.return_value = False
        self.mock_volume_type_list.return_value = (
            self.cinder_volume_types.list())
        self.mock_datastore_flavors.return_value = self.flavors.list()

        filtered_datastores = self._get_filtered_datastores('mongodb')
        self.mock_datastore_list.return_value = filtered_datastores
        self.mock_datastore_version_list.return_value = (
            self._get_filtered_datastore_versions(filtered_datastores))

        res = self.client.get(LAUNCH_URL)
        self.mock_is_service_enabled.assert_called_once_with(
            test.IsHttpRequest(), 'network')
        self.mock_datastore_flavors.assert_called_once_with(
            test.IsHttpRequest(), 'mongodb', '2.6')
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_datastore_version_list.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.assertTemplateUsed(res, 'project/database_clusters/launch.html')

    def test_launch_cluster_mongo_fields(self):
        datastore = 'mongodb'
        datastore_version = '2.6'
        fields = self.launch_cluster_fields_setup(datastore,
                                                  datastore_version)
        field_name = self._build_flavor_widget_name(datastore,
                                                    datastore_version)

        self.assertTrue(self._contains_datastore_in_attribute(
            fields[field_name], field_name))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['num_instances'], field_name))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['num_shards'], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['root_password'], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_instances_vertica'], field_name))

    def test_launch_cluster_redis_fields(self):
        datastore = 'redis'
        datastore_version = '3.0'
        fields = self.launch_cluster_fields_setup(datastore,
                                                  datastore_version)
        field_name = self._build_flavor_widget_name(datastore,
                                                    datastore_version)

        self.assertTrue(self._contains_datastore_in_attribute(
            fields[field_name], field_name))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['num_instances'], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_shards'], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['root_password'], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_instances_vertica'], field_name))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['replicas_per_master'], field_name))

    @test.create_mocks({trove_api.trove: ('datastore_flavors',
                                          'datastore_list',
                                          'datastore_version_list'),
                        api.cinder: ['volume_type_list'],
                        api.base: ['is_service_enabled']})
    def test_launch_cluster_group_replication_fields(self):
        # The test data has two MySQL versions; one is enough here.
        self.mock_is_service_enabled.return_value = False
        self.mock_volume_type_list.return_value = []
        self.mock_datastore_flavors.return_value = self.flavors.list()
        filtered_datastores = self._get_filtered_datastores('mysql')
        self.mock_datastore_list.return_value = filtered_datastores
        self.mock_datastore_version_list.return_value = [
            v for v in self._get_filtered_datastore_versions(
                filtered_datastores) if v.name == '5.5']
        fields = self.client.get(LAUNCH_URL).context_data['form'].fields
        field_name = self._build_flavor_widget_name('mysql', '5.5')

        self.assertTrue(self._contains_datastore_in_attribute(
            fields['num_instances'], field_name))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['group_replication_mode'], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['replicas_per_master'], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_shards'], field_name))

    def test_launch_cluster_vertica_fields(self):
        datastore = 'vertica'
        datastore_version = '7.1'
        fields = self.launch_cluster_fields_setup(datastore,
                                                  datastore_version)
        field_name = self._build_flavor_widget_name(datastore,
                                                    datastore_version)

        self.assertTrue(self._contains_datastore_in_attribute(
            fields[field_name], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_instances'], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_shards'], field_name))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['root_password'], field_name))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['num_instances_vertica'], field_name))

    @test.create_mocks({trove_api.trove: ('datastore_flavors',
                                          'datastore_list',
                                          'datastore_version_list'),
                        api.cinder: ['volume_type_list'],
                        api.base: ['is_service_enabled']})
    def launch_cluster_fields_setup(self, datastore, datastore_version):
        self.mock_is_service_enabled.return_value = False
        self.mock_volume_type_list.return_value = (
            self.cinder_volume_types.list())
        self.mock_datastore_flavors.return_value = self.flavors.list()

        filtered_datastores = self._get_filtered_datastores(datastore)
        self.mock_datastore_list.return_value = filtered_datastores
        self.mock_datastore_version_list.return_value = (
            self._get_filtered_datastore_versions(filtered_datastores))

        res = self.client.get(LAUNCH_URL)
        self.mock_is_service_enabled.assert_called_once_with(
            test.IsHttpRequest(), 'network')
        self.mock_datastore_flavors.assert_called_once_with(
            test.IsHttpRequest(), datastore, datastore_version)
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_datastore_version_list.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        return res.context_data['form'].fields

    @test.create_mocks({trove_api.trove: ['datastore_flavors',
                                          'cluster_create',
                                          'datastore_list',
                                          'datastore_version_list'],
                        api.cinder: ['volume_type_list'],
                        api.base: ['is_service_enabled']})
    def test_create_simple_cluster(self):
        self.mock_is_service_enabled.return_value = False
        self.mock_volume_type_list.return_value = (
            self.cinder_volume_types.list())
        self.mock_datastore_flavors.return_value = self.flavors.list()

        filtered_datastores = self._get_filtered_datastores('mongodb')
        self.mock_datastore_list.return_value = filtered_datastores
        self.mock_datastore_version_list.return_value = (
            self._get_filtered_datastore_versions(filtered_datastores))

        self.mock_cluster_create.return_value = self.trove_clusters.first()

        cluster_name = 'MyCluster'
        cluster_volume = 1
        cluster_flavor = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        cluster_instances = 3
        cluster_datastore = 'mongodb'
        cluster_datastore_version = '2.6'
        cluster_network = ''

        field_name = self._build_flavor_widget_name(cluster_datastore,
                                                    cluster_datastore_version)
        post = {
            'name': cluster_name,
            'volume': cluster_volume,
            'num_instances': cluster_instances,
            'num_shards': 1,
            'datastore': field_name,
            field_name: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        }

        res = self.client.post(LAUNCH_URL, post)
        self.mock_is_service_enabled.assert_called_once_with(
            test.IsHttpRequest(), 'network')
        self.mock_datastore_flavors.assert_called_once_with(
            test.IsHttpRequest(), 'mongodb', '2.6')
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_datastore_version_list.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_cluster_create.assert_called_once_with(
            test.IsHttpRequest(),
            cluster_name,
            cluster_volume,
            cluster_flavor,
            cluster_instances,
            datastore=cluster_datastore,
            datastore_version=cluster_datastore_version,
            nics=cluster_network,
            root_password=None,
            locality=None,
            configuration=None,
            volume_type=None,
            extended_properties=None)
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)

    def _create_group_replication_cluster(self, mode):
        self.mock_is_service_enabled.return_value = False
        self.mock_volume_type_list.return_value = []
        self.mock_datastore_flavors.return_value = self.flavors.list()
        filtered_datastores = self._get_filtered_datastores('mysql')
        self.mock_datastore_list.return_value = filtered_datastores
        self.mock_datastore_version_list.return_value = (
            self._get_filtered_datastore_versions(filtered_datastores))
        self.mock_cluster_create.return_value = self.trove_clusters.first()

        field_name = self._build_flavor_widget_name('mysql', '5.5')
        res = self.client.post(LAUNCH_URL, {
            'name': 'MyCluster', 'volume': 1, 'num_instances': 3,
            'group_replication_mode': mode, 'datastore': field_name,
            field_name: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        })
        self.assertNoFormErrors(res)
        return self.mock_cluster_create.call_args[1]['extended_properties']

    @test.create_mocks({trove_api.trove: ['datastore_flavors',
                                          'cluster_create',
                                          'datastore_list',
                                          'datastore_version_list'],
                        api.cinder: ['volume_type_list'],
                        api.base: ['is_service_enabled']})
    def test_create_multi_primary_cluster(self):
        self.assertEqual(
            {'group_replication_mode': 'multi-primary'},
            self._create_group_replication_cluster('multi-primary'))

    @test.create_mocks({trove_api.trove: ['datastore_flavors',
                                          'cluster_create',
                                          'datastore_list',
                                          'datastore_version_list'],
                        api.cinder: ['volume_type_list'],
                        api.base: ['is_service_enabled']})
    def test_create_group_replication_cluster_defaults_to_single(self):
        self.assertEqual(
            {'group_replication_mode': 'single-primary'},
            self._create_group_replication_cluster(''))

    @test.create_mocks({trove_api.trove: ['datastore_flavors',
                                          'cluster_create',
                                          'datastore_list',
                                          'datastore_version_list'],
                        api.cinder: ['volume_type_list'],
                        api.base: ['is_service_enabled']})
    def test_create_redis_cluster_with_replicas(self):
        self.mock_is_service_enabled.return_value = False
        self.mock_volume_type_list.return_value = []
        self.mock_datastore_flavors.return_value = self.flavors.list()
        filtered_datastores = self._get_filtered_datastores('redis')
        self.mock_datastore_list.return_value = filtered_datastores
        self.mock_datastore_version_list.return_value = (
            self._get_filtered_datastore_versions(filtered_datastores))
        self.mock_cluster_create.return_value = self.trove_clusters.first()

        field_name = self._build_flavor_widget_name('redis', '3.0')
        res = self.client.post(LAUNCH_URL, {
            'name': 'MyCluster', 'volume': 1, 'num_instances': 6,
            'replicas_per_master': 1, 'datastore': field_name,
            field_name: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        })
        self.assertNoFormErrors(res)
        self.mock_cluster_create.assert_called_once_with(
            test.IsHttpRequest(), 'MyCluster', 1,
            'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 6,
            datastore='redis', datastore_version='3.0', nics='',
            root_password=None, locality=None, configuration=None,
            volume_type=None,
            extended_properties={'replicas_per_master': 1})

    @test.create_mocks({trove_api.trove: ['datastore_flavors',
                                          'cluster_create',
                                          'datastore_list',
                                          'datastore_version_list'],
                        api.cinder: ['volume_type_list'],
                        api.base: ['is_service_enabled']})
    def test_create_cluster_volume_type_and_mongodb_volumes(self):
        # The volume type goes on every member's volume; a MongoDB
        # cluster's config server and mongos volume sizes go as extended
        # properties, so Trove does not give each of them 10 GB.
        self.mock_is_service_enabled.return_value = False
        self.mock_volume_type_list.return_value = (
            self.cinder_volume_types.list())
        self.mock_datastore_flavors.return_value = self.flavors.list()
        filtered_datastores = self._get_filtered_datastores('mongodb')
        self.mock_datastore_list.return_value = filtered_datastores
        self.mock_datastore_version_list.return_value = (
            self._get_filtered_datastore_versions(filtered_datastores))
        self.mock_cluster_create.return_value = self.trove_clusters.first()

        volume_type = self.cinder_volume_types.first().name
        field_name = self._build_flavor_widget_name('mongodb', '2.6')
        res = self.client.post(LAUNCH_URL, {
            'name': 'MyCluster',
            'volume': 2,
            'volume_type': volume_type,
            'num_instances': 3,
            'num_shards': 1,
            'configsvr_volume_size': 2,
            'mongos_volume_size': 3,
            'datastore': field_name,
            field_name: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        })
        self.assertNoFormErrors(res)
        self.mock_cluster_create.assert_called_once_with(
            test.IsHttpRequest(), 'MyCluster', 2,
            'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 3,
            datastore='mongodb', datastore_version='2.6', nics='',
            root_password=None, locality=None, configuration=None,
            volume_type=volume_type,
            extended_properties={'configsvr_volume_size': 2,
                                 'mongos_volume_size': 3})

    @test.create_mocks({trove_api.trove: ['datastore_flavors',
                                          'cluster_create',
                                          'datastore_list',
                                          'datastore_version_list'],
                        api.neutron: ['network_list_for_tenant'],
                        api.cinder: ['volume_type_list'],
                        api.base: ['is_service_enabled']})
    def test_create_simple_cluster_neutron(self):
        self.mock_is_service_enabled.return_value = True
        self.mock_volume_type_list.return_value = (
            self.cinder_volume_types.list())
        self.mock_network_list_for_tenant.return_value = self.networks.list()
        self.mock_datastore_flavors.return_value = self.flavors.list()

        filtered_datastores = self._get_filtered_datastores('mongodb')
        self.mock_datastore_list.return_value = filtered_datastores
        self.mock_datastore_version_list.return_value = (
            self._get_filtered_datastore_versions(filtered_datastores))

        self.mock_cluster_create.return_value = self.trove_clusters.first()

        cluster_name = 'MyCluster'
        cluster_volume = 1
        cluster_flavor = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        cluster_instances = 3
        cluster_datastore = 'mongodb'
        cluster_datastore_version = '2.6'
        cluster_network = '82288d84-e0a5-42ac-95be-e6af08727e42'

        field_name = self._build_flavor_widget_name(cluster_datastore,
                                                    cluster_datastore_version)
        post = {
            'name': cluster_name,
            'volume': cluster_volume,
            'num_instances': cluster_instances,
            'num_shards': 1,
            'datastore': field_name,
            field_name: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'network': cluster_network,
        }

        res = self.client.post(LAUNCH_URL, post)
        self.mock_is_service_enabled.assert_called_once_with(
            test.IsHttpRequest(), 'network')
        self.mock_network_list_for_tenant.assert_called_once_with(
            test.IsHttpRequest(), '1')
        self.mock_datastore_flavors.assert_called_once_with(
            test.IsHttpRequest(), 'mongodb', '2.6')
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_datastore_version_list.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_cluster_create.assert_called_once_with(
            test.IsHttpRequest(),
            cluster_name,
            cluster_volume,
            cluster_flavor,
            cluster_instances,
            datastore=cluster_datastore,
            datastore_version=cluster_datastore_version,
            nics=cluster_network,
            root_password=None,
            locality=None,
            configuration=None,
            volume_type=None,
            extended_properties=None)
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)

    @test.create_mocks({trove_api.trove: ['datastore_flavors',
                                          'cluster_create',
                                          'datastore_list',
                                          'datastore_version_list'],
                        api.neutron: ['network_list_for_tenant'],
                        api.cinder: ['volume_type_list']})
    def test_create_simple_cluster_exception(self):
        self.mock_network_list_for_tenant.return_value = self.networks.list()
        self.mock_volume_type_list.return_value = (
            self.cinder_volume_types.list())
        self.mock_datastore_flavors.return_value = self.flavors.list()

        filtered_datastores = self._get_filtered_datastores('mongodb')
        self.mock_datastore_list.return_value = filtered_datastores
        self.mock_datastore_version_list.return_value = (
            self._get_filtered_datastore_versions(filtered_datastores))

        self.mock_cluster_create.side_effect = self.exceptions.trove

        cluster_name = 'MyCluster'
        cluster_volume = 1
        cluster_flavor = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        cluster_instances = 3
        cluster_datastore = 'mongodb'
        cluster_datastore_version = '2.6'
        cluster_network = ''

        field_name = self._build_flavor_widget_name(cluster_datastore,
                                                    cluster_datastore_version)
        post = {
            'name': cluster_name,
            'volume': cluster_volume,
            'num_instances': cluster_instances,
            'num_shards': 1,
            'datastore': field_name,
            field_name: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        }

        res = self.client.post(LAUNCH_URL, post)
        self.mock_network_list_for_tenant.assert_called_once_with(
            test.IsHttpRequest(), '1')
        self.mock_datastore_flavors.assert_called_once_with(
            test.IsHttpRequest(), 'mongodb', '2.6')
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_datastore_version_list.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_cluster_create.assert_called_once_with(
            test.IsHttpRequest(),
            cluster_name,
            cluster_volume,
            cluster_flavor,
            cluster_instances,
            datastore=cluster_datastore,
            datastore_version=cluster_datastore_version,
            nics=cluster_network,
            root_password=None,
            locality=None,
            configuration=None,
            volume_type=None,
            extended_properties=None)
        self.assertRedirectsNoFollow(res, INDEX_URL)
        self.assertMessageCount(error=1)

    @test.create_mocks({trove_api.trove: ('cluster_get',
                                          'instance_get',
                                          'flavor_get',)})
    def test_details(self):
        cluster = self.trove_clusters.first()
        self.mock_cluster_get.return_value = cluster
        self.mock_instance_get.return_value = self.databases.first()
        self.mock_flavor_get.return_value = self.flavors.first()

        details_url = reverse('horizon:project:database_clusters:detail',
                              args=[cluster.id])
        res = self.client.get(details_url)
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_cluster_get, 2,
            mock.call(test.IsHttpRequest(), cluster.id))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_instance_get, 3,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_flavor_get, 4,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.assertTemplateUsed(res, 'horizon/common/_detail.html')
        self.assertContains(res, cluster.ip[0])

    @test.create_mocks({trove_api.trove: ('cluster_get',
                                          'instance_get',
                                          'flavor_get',)})
    def test_details_without_locality(self):
        cluster = self.trove_clusters.list()[1]
        self.mock_cluster_get.return_value = cluster
        self.mock_instance_get.return_value = self.databases.first()
        self.mock_flavor_get.return_value = self.flavors.first()

        details_url = reverse('horizon:project:database_clusters:detail',
                              args=[cluster.id])
        res = self.client.get(details_url)
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_cluster_get, 2,
            mock.call(test.IsHttpRequest(), cluster.id))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_instance_get, 3,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_flavor_get, 4,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.assertTemplateUsed(res, 'horizon/common/_detail.html')
        self.assertNotContains(res, "Locality")

    @test.create_mocks({trove_api.trove: ('cluster_get',
                                          'instance_get',
                                          'flavor_get',)})
    def test_details_with_locality(self):
        cluster = self.trove_clusters.first()
        self.mock_cluster_get.return_value = cluster
        self.mock_instance_get.return_value = self.databases.first()
        self.mock_flavor_get.return_value = self.flavors.first()

        details_url = reverse('horizon:project:database_clusters:detail',
                              args=[cluster.id])
        res = self.client.get(details_url)
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_cluster_get, 2,
            mock.call(test.IsHttpRequest(), cluster.id))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_instance_get, 3,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_flavor_get, 4,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.assertTemplateUsed(res, 'project/database_clusters/'
                                     '_detail_overview.html')
        self.assertContains(res, "Location Policy")

    @test.create_mocks(
        {trove_api.trove: ('cluster_get',
                           'cluster_grow'),
         cluster_manager: ('get',)})
    def test_grow_cluster(self):
        cluster = self.trove_clusters.first()
        self.mock_cluster_get.return_value = cluster
        cluster_volume = 1
        flavor = self.flavors.first()
        cluster_flavor = flavor.id
        cluster_flavor_name = flavor.name
        instances = [
            cluster_manager.ClusterInstance("id1", "name1", cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, "master", None,
                                            None),
            cluster_manager.ClusterInstance("id2", "name2", cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, "slave",
                                            "master", None),
            cluster_manager.ClusterInstance("id3", None, cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, None, None, None),
        ]

        manager = cluster_manager.ClusterInstanceManager(cluster.id)
        manager.instances = instances
        self.mock_get.return_value = manager

        url = reverse('horizon:project:database_clusters:cluster_grow_details',
                      args=[cluster.id])
        res = self.client.get(url)
        self.assertTemplateUsed(
            res, 'project/database_clusters/cluster_grow_details.html')
        table = res.context_data[
            "".join([tables.ClusterGrowInstancesTable.Meta.name, '_table'])]
        self.assertEqual(len(cluster.instances), len(table.data))

        action = "".join([tables.ClusterGrowInstancesTable.Meta.name, '__',
                          tables.ClusterGrowRemoveInstance.name, '__',
                          'id1'])
        self.client.post(url, {'action': action})
        self.assertEqual(len(cluster.instances) - 1, len(table.data))

        action = "".join([tables.ClusterGrowInstancesTable.Meta.name, '__',
                          tables.ClusterGrowAction.name, '__',
                          cluster.id])
        res = self.client.post(url, {'action': action})
        self.mock_cluster_get.assert_called_with(
            test.IsHttpRequest(), cluster.id)
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_get, 5, mock.call(cluster.id))
        self.mock_cluster_grow.assert_called_once_with(
            test.IsHttpRequest(), cluster.id, instances)
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({trove_api.trove: ('cluster_get',)})
    def test_grow_cluster_no_instances(self):
        cluster = self.trove_clusters.first()
        self.mock_cluster_get.return_value = cluster

        url = reverse('horizon:project:database_clusters:cluster_grow_details',
                      args=[cluster.id])
        res = self.client.get(url)
        self.assertTemplateUsed(
            res, 'project/database_clusters/cluster_grow_details.html')

        action = "".join([tables.ClusterGrowInstancesTable.Meta.name, '__',
                          tables.ClusterGrowAction.name, '__',
                          cluster.id])
        self.client.post(url, {'action': action})
        self.mock_cluster_get.assert_called_once_with(
            test.IsHttpRequest(), cluster.id)
        self.assertMessageCount(info=1)

    @test.create_mocks(
        {trove_api.trove: ('cluster_get',
                           'cluster_grow',),
         cluster_manager: ('get',)})
    def test_grow_cluster_exception(self):
        cluster = self.trove_clusters.first()
        self.mock_cluster_get.return_value = cluster
        cluster_volume = 1
        flavor = self.flavors.first()
        cluster_flavor = flavor.id
        cluster_flavor_name = flavor.name
        instances = [
            cluster_manager.ClusterInstance("id1", "name1", cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, "master", None,
                                            None),
            cluster_manager.ClusterInstance("id2", "name2", cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, "slave",
                                            "master", None),
            cluster_manager.ClusterInstance("id3", None, cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, None, None, None),
        ]

        manager = cluster_manager.ClusterInstanceManager(cluster.id)
        manager.instances = instances
        self.mock_get.return_value = manager
        self.mock_cluster_grow.side_effect = self.exceptions.trove

        url = reverse('horizon:project:database_clusters:cluster_grow_details',
                      args=[cluster.id])
        res = self.client.get(url)
        self.assertTemplateUsed(
            res, 'project/database_clusters/cluster_grow_details.html')

        toSuppress = ["trove_dashboard.content.database_clusters.tables"]

        # Suppress expected log messages in the test output
        loggers = []
        for cls in toSuppress:
            logger = logging.getLogger(cls)
            loggers.append((logger, logger.getEffectiveLevel()))
            logger.setLevel(logging.CRITICAL)

        try:
            action = "".join([tables.ClusterGrowInstancesTable.Meta.name, '__',
                              tables.ClusterGrowAction.name, '__',
                              cluster.id])
            res = self.client.post(url, {'action': action})

            self.mock_cluster_get.assert_called_with(
                test.IsHttpRequest(), cluster.id)
            self.assert_mock_multiple_calls_with_same_arguments(
                self.mock_get, 3, mock.call(cluster.id))
            self.mock_cluster_grow.assert_called_once_with(
                test.IsHttpRequest(), cluster.id, instances)
            self.assertMessageCount(error=1)
            self.assertRedirectsNoFollow(res, INDEX_URL)
        finally:
            # Restore the previous log levels
            for (log, level) in loggers:
                log.setLevel(level)

    @test.create_mocks({trove_api.trove: ('cluster_get',
                                          'cluster_shrink')})
    def test_shrink_cluster(self):
        cluster = self.trove_clusters.first()
        self.mock_cluster_get.return_value = cluster
        instance_id = cluster.instances[0]['id']
        cluster_instances = [{'id': instance_id}]

        url = reverse(
            'horizon:project:database_clusters:cluster_shrink_details',
            args=[cluster.id])
        res = self.client.get(url)
        self.assertTemplateUsed(
            res, 'project/database_clusters/cluster_shrink_details.html')
        table = res.context_data[
            "".join([tables.ClusterShrinkInstancesTable.Meta.name, '_table'])]
        self.assertEqual(len(cluster.instances), len(table.data))

        action = "".join([tables.ClusterShrinkInstancesTable.Meta.name, '__',
                          tables.ClusterShrinkAction.name, '__',
                          instance_id])
        res = self.client.post(url, {'action': action})
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_cluster_get, 2,
            mock.call(test.IsHttpRequest(), cluster.id))
        self.mock_cluster_shrink.assert_called_once_with(
            test.IsHttpRequest(), cluster.id, cluster_instances)
        self.assertNoFormErrors(res)
        self.assertMessageCount(info=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({trove_api.trove: ('cluster_get',
                                          'cluster_shrink')})
    def test_shrink_cluster_exception(self):
        cluster = self.trove_clusters.first()
        self.mock_cluster_get.return_value = cluster
        instance_id = cluster.instances[0]['id']
        cluster_instances = [{'id': instance_id}]
        self.mock_cluster_shrink.side_effect = self.exceptions.trove

        url = reverse(
            'horizon:project:database_clusters:cluster_shrink_details',
            args=[cluster.id])
        action = "".join([tables.ClusterShrinkInstancesTable.Meta.name, '__',
                          tables.ClusterShrinkAction.name, '__',
                          instance_id])

        toSuppress = ["trove_dashboard.content.database_clusters.tables"]

        # Suppress expected log messages in the test output
        loggers = []
        for cls in toSuppress:
            logger = logging.getLogger(cls)
            loggers.append((logger, logger.getEffectiveLevel()))
            logger.setLevel(logging.CRITICAL)

        try:
            res = self.client.post(url, {'action': action})
            self.mock_cluster_get.assert_called_once_with(
                test.IsHttpRequest(), cluster.id)
            self.mock_cluster_shrink.assert_called_once_with(
                test.IsHttpRequest(), cluster.id, cluster_instances)
            self.assertMessageCount(error=1)
            self.assertRedirectsNoFollow(res, INDEX_URL)
        finally:
            # Restore the previous log levels
            for (log, level) in loggers:
                log.setLevel(level)

    def _get_filtered_datastores(self, datastore):
        filtered_datastore = []
        for ds in self.datastores.list():
            if datastore in ds.name:
                filtered_datastore.append(ds)
        return filtered_datastore

    def _get_filtered_datastore_versions(self, datastores):
        filtered_datastore_versions = []
        for ds in datastores:
            for dsv in self.datastore_versions.list():
                if ds.id == dsv.datastore:
                    filtered_datastore_versions.append(dsv)
        return filtered_datastore_versions

    def _contains_datastore_in_attribute(self, field, datastore):
        for key, value in field.widget.attrs.items():
            if datastore in key:
                return True
        return False

    def _build_datastore_display_text(self, datastore, datastore_version):
        return datastore + ' - ' + datastore_version

    def _build_flavor_widget_name(self, datastore, datastore_version):
        return common_utils.hexlify(self._build_datastore_display_text(
            datastore, datastore_version))


class ClusterMemberRoleTests(test.TestCase):

    def test_role_column(self):
        self.assertEqual('Primary', str(tables.get_role(
            mock.Mock(role='primary'))))
        self.assertEqual('Secondary', str(tables.get_role(
            mock.Mock(role='secondary'))))
        # A role the dashboard does not know is shown as it comes.
        self.assertEqual('unreachable', tables.get_role(
            mock.Mock(role='unreachable')))
        self.assertEqual('Not available', str(tables.get_role(
            mock.Mock(spec=[]))))
        self.assertIn('role', tables.InstancesTable.base_columns)

    @mock.patch.object(trove_api.trove, 'flavor_get')
    @mock.patch.object(trove_api.trove, 'instance_get')
    @mock.patch.object(trove_api.trove, 'cluster_get')
    def test_instances_tab_carries_the_role(self, cluster_get, instance_get,
                                            flavor_get):
        cluster_get.return_value.instances = [
            {'id': 'i1', 'type': 'member', 'role': 'primary'},
            {'id': 'i2', 'type': 'member'}]
        instance_get.side_effect = lambda request, i: mock.Mock(
            spec=['flavor'], flavor={'id': 'f1'})
        tab = tabs.InstancesTab(mock.Mock(kwargs={'cluster': mock.Mock()}),
                                mock.Mock())
        data = tab.get_instances_data()
        self.assertEqual('primary', data[0].role)
        self.assertFalse(hasattr(data[1], 'role'))


class ClusterGrowGroupTests(test.TestCase):

    def _cluster(self, datastore, types):
        return mock.Mock(datastore={'type': datastore, 'version': '7.2'},
                         instances=[{'type': t} for t in types])

    def test_group_size(self):
        size = cluster_manager.grow_group_size
        self.assertEqual(2, size(self._cluster(
            'redis', ['member', 'replica'] * 3)))
        self.assertEqual(3, size(self._cluster(
            'redis', ['member', 'replica', 'replica'] * 3)))
        self.assertEqual(1, size(self._cluster('redis', ['member'] * 3)))
        self.assertEqual(1, size(self._cluster(
            'mongodb', ['member', 'query_router', 'config_server'])))
        # Valkey and KeyDB clusters run on the Redis strategies.
        for datastore in ('valkey', 'keydb'):
            self.assertEqual(2, size(self._cluster(
                datastore, ['member', 'replica'] * 3)))

    def test_group_replication_clusters(self):
        for datastore in ('mysql', 'percona'):
            self.assertTrue(
                db_capability.is_cluster_capable_datastore(datastore))
            self.assertTrue(db_capability.can_modify_cluster(datastore))
            self.assertTrue(
                db_capability.is_group_replication_datastore(datastore))
        for datastore in ('mariadb', 'pxc'):
            self.assertFalse(
                db_capability.is_group_replication_datastore(datastore))

    def test_locality_defaults_to_the_platform(self):
        # Sent as None, so that the service applies its default policy.
        field = forms.LaunchForm.base_fields['locality']
        self.assertEqual('', field.choices[0][0])
        self.assertIn('anti-affinity', str(field.choices[0][1]))

    def test_redis_family_clusters(self):
        for datastore in ('valkey', 'keydb'):
            self.assertTrue(
                db_capability.is_cluster_capable_datastore(datastore))
            self.assertTrue(db_capability.can_modify_cluster(datastore))
            self.assertTrue(db_capability.is_redis_datastore(datastore))
        self.assertFalse(db_capability.is_redis_datastore('mongodb'))

    @mock.patch.object(tables, 'messages')
    @mock.patch.object(trove_api.trove, 'cluster_grow')
    @mock.patch.object(trove_api.trove, 'cluster_get')
    def test_grow_refuses_part_of_a_group(self, cluster_get, cluster_grow,
                                          messages):
        # Trove would refuse it; the instances stay listed so the rest of
        # the group can be added.
        cluster_get.return_value = self._cluster(
            'redis', ['member', 'replica'] * 3)
        table = mock.Mock(data=[mock.Mock()], kwargs={'cluster_id': 'c1'})
        request = mock.Mock()
        request.build_absolute_uri.return_value = '/grow'
        res = tables.ClusterGrowAction().handle(table, request, [])
        self.assertEqual('/grow', res.url)
        cluster_grow.assert_not_called()
        messages.error.assert_called_once()
