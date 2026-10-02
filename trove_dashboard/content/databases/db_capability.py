# Copyright 2015 Tesora Inc.
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

CASSANDRA = "cassandra"
MARIADB = "mariadb"
MONGODB = "mongodb"
MYSQL = "mysql"
PERCONA = "percona"
PERCONA_CLUSTER = "pxc"
POSTGRESQL = "postgresql"
KEYDB = "keydb"
REDIS = "redis"
VALKEY = "valkey"
VERTICA = "vertica"

_mysql_compatible_datastores = (MYSQL, MARIADB, PERCONA, PERCONA_CLUSTER)
_cluster_capable_datastores = (CASSANDRA, KEYDB, MARIADB, MONGODB, MYSQL,
                               PERCONA, PERCONA_CLUSTER, REDIS, VALKEY,
                               VERTICA)
# Clusters on MySQL Group Replication, single- or multi-primary.
_group_replication_datastores = (MYSQL, PERCONA)
# Clusters on the Redis Cluster protocol: Valkey's and KeyDB's run on
# Trove's Redis cluster strategies, replicas per master and growing by
# groups included.
_redis_cluster_datastores = (KEYDB, REDIS, VALKEY)
# The backups of these can be incremental, on a parent backup; Trove
# refuses an incremental backup of any other datastore.
_incremental_backup_datastores = (MYSQL, MARIADB, PERCONA, PERCONA_CLUSTER,
                                  POSTGRESQL)
_cluster_grow_shrink_capable_datastores = (CASSANDRA, KEYDB, MARIADB,
                                           MONGODB, MYSQL, PERCONA,
                                           PERCONA_CLUSTER, REDIS, VALKEY)


def can_modify_cluster(datastore):
    return _is_datastore_in_list(datastore,
                                 _cluster_grow_shrink_capable_datastores)


def is_mongodb_datastore(datastore):
    return (datastore is not None) and (MONGODB in datastore.lower())


def is_percona_cluster_datastore(datastore):
    return (datastore is not None) and (PERCONA_CLUSTER in datastore.lower())


def is_group_replication_datastore(datastore):
    return _is_datastore_in_list(datastore, _group_replication_datastores)


def is_redis_datastore(datastore):
    return _is_datastore_in_list(datastore, _redis_cluster_datastores)


def is_vertica_datastore(datastore):
    return (datastore is not None) and (VERTICA in datastore.lower())


def is_mysql_compatible(datastore):
    return _is_datastore_in_list(datastore, _mysql_compatible_datastores)


def supports_incremental_backup(datastore):
    return _is_datastore_in_list(datastore, _incremental_backup_datastores)


def is_cluster_capable_datastore(datastore):
    return _is_datastore_in_list(datastore, _cluster_capable_datastores)


def _is_datastore_in_list(datastore, datastores):
    if datastore is not None:
        datastore_lower = datastore.lower()
        for ds in datastores:
            if ds in datastore_lower:
                return True
    return False
