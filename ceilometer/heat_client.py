#
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

import functools
from urlparse import urlparse

from keystoneclient import auth
from keystoneclient import session
from keystoneclient.auth.identity import v2 as v2_auth
from keystoneclient.auth import token_endpoint

from heatclient import client as heat_client
from oslo_config import cfg
from ceilometer import keystone_client
from ceilometer.openstack.common import log

heat_opts = [
    cfg.StrOpt('url',
               default='http://127.0.0.1:8004',
               help='URL for connecting to neutron'),
    cfg.StrOpt('admin_user_id',
               help='User id for connecting to neutron in admin context. '
                    'DEPRECATED: specify an auth_plugin and appropriate '
                    'credentials instead.'),
    cfg.StrOpt('admin_username',
               help='Username for connecting to neutron in admin context '
                    'DEPRECATED: specify an auth_plugin and appropriate '
                    'credentials instead.'),
    cfg.StrOpt('admin_password',
               help='Password for connecting to neutron in admin context '
                    'DEPRECATED: specify an auth_plugin and appropriate '
                    'credentials instead.',
               secret=True),
    cfg.StrOpt('admin_tenant_id',
               help='Tenant id for connecting to neutron in admin context '
                    'DEPRECATED: specify an auth_plugin and appropriate '
                    'credentials instead.'),
    cfg.StrOpt('admin_tenant_name',
               help='Tenant name for connecting to neutron in admin context. '
                    'This option will be ignored if neutron_admin_tenant_id '
                    'is set. Note that with Keystone V3 tenant names are '
                    'only unique within a domain. '
                    'DEPRECATED: specify an auth_plugin and appropriate '
                    'credentials instead.'),
    cfg.StrOpt('region_name',
               help='Region name for connecting to neutron in admin context'),
    cfg.StrOpt('admin_auth_url',
               default='http://localhost:5000/v2.0',
               help='Authorization URL for connecting to neutron in admin '
                    'context. DEPRECATED: specify an auth_plugin and '
                    'appropriate credentials instead.'),
    cfg.StrOpt('auth_strategy',
               default='keystone',
               help='Authorization strategy for connecting to neutron in '
                    'admin context. DEPRECATED: specify an auth_plugin and '
                    'appropriate credentials instead. If an auth_plugin is '
                    'specified strategy will be ignored.'),
]

SERVICE_OPTS = [
    cfg.StrOpt('heat',
               default='orchestration',
               help='Heat service type.'),
]

cfg.CONF.register_opts(heat_opts, 'heat')
cfg.CONF.register_opts(SERVICE_OPTS, group='service_types')
cfg.CONF.import_opt('http_timeout', 'ceilometer.service')
cfg.CONF.import_group('service_credentials', 'ceilometer.service')

deprecations = {'cafile': [cfg.DeprecatedOpt('ca_certificates_file',
                                             group='heat')],
                'insecure': [cfg.DeprecatedOpt('api_insecure',
                                               group='heat')],
                'timeout': [cfg.DeprecatedOpt('url_timeout',
                                              group='heat')]}

session.Session.register_conf_options(cfg.CONF, 'heat',
                                      deprecated_opts=deprecations)
auth.register_conf_options(cfg.CONF, 'heat')

LOG = log.getLogger(__name__)

def logged(func):

    @functools.wraps(func)
    def with_logging(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            LOG.exception(e)
            raise

    return with_logging


class Client(object):
    """A client which gets information via python-heatclient."""

    _SESSION = None
    _ADMIN_AUTH = None

    def __init__(self):
        self._make_client()

    def _make_client(self, auth_url=None, user_id=None, username=None,
                     password=None, tenant_id=None, tenant_name=None,
                     service_type=None, region_name=None,
                     insecure=None, ca_file=None):

        service_cred_conf = cfg.CONF.service_credentials
        heat_conf = cfg.CONF.heat

        heat_url = keystone_client.get_client().service_catalog.url_for(
                    service_type=cfg.CONF.service_types.heat,
                    endpoint_type=service_cred_conf.os_endpoint_type)

        _SESSION = session.Session.load_from_conf_options(cfg.CONF, 'heat')
        _ADMIN_AUTH = v2_auth.Password(auth_url=heat_conf.admin_auth_url,
                                user_id=heat_conf.admin_user_id,
                                username=heat_conf.admin_username,
                                password=heat_conf.admin_password,
                                tenant_id=service_cred_conf.os_tenant_id,
                                tenant_name=service_cred_conf.os_tenant_name)

        auth_token = _ADMIN_AUTH.get_token(_SESSION)
        auth_plugin = token_endpoint.Token(heat_url, auth_token)

        params = {
            'insecure': heat_conf.insecure,
            'ca_file': service_cred_conf.os_cacert,
            'username': heat_conf.admin_username,
            'password': heat_conf.admin_password,
            'auth_url': heat_conf.admin_auth_url,
            'region_name': service_cred_conf.os_region_name,
            'endpoint_type': service_cred_conf.os_endpoint_type,
            'timeout': cfg.CONF.http_timeout,
            'service_type': cfg.CONF.service_types.heat,
            'session': _SESSION,
            'auth': auth_plugin
        }

        self.client = heat_client.Client('1', heat_url, **params)

    @logged
    def ec2_instance_get_all(self):
        kwargs = {'sort_dir': 'desc', 'sort_key': 'created_at', 'global_tenant': True}
        all_stacks = self.get_all_stacks(1000, **kwargs)
        ec2_instances = []

        for stack in all_stacks:
            stack_identifier = '%s/%s' % (stack.stack_name, stack.id)
            resources = self.get_all_resources(stack_identifier, nested_depth=3)

            for resource in resources:
                if resource.resource_type == 'AWS::VPC::EC2Instance':
                    for link in resource.links:
                        if link['rel'] == 'stack':
                            stack_url_path = urlparse(link['href']).path
                            split_stack_id = stack_url_path.split('/')[-2:]
                            nested_stack_id = '%s/%s' % (split_stack_id[0], split_stack_id[1])

                            EC2Instance = type("EC2Instance", (object,), dict())
                            instance = EC2Instance()

                            setattr(instance, 'id', resource.logical_resource_id)
                            setattr(instance, 'ec2_id', resource.physical_resource_id)
                            setattr(instance, 'display_name', resource.resource_name)
                            setattr(instance, 'name', resource.resource_name)
                            setattr(instance, 'status', resource.resource_status)
                            setattr(instance, 'metadata', self.get_metadata(nested_stack_id,
                                                                         resource.resource_name))

                            service_cred_conf = cfg.CONF.service_credentials
                            heat_conf = cfg.CONF.heat

                            setattr(instance, 'user_id', heat_conf.admin_user_id)
                            setattr(instance, 'tenant_id', service_cred_conf.os_tenant_id or \
                                                            service_cred_conf.os_tenant_name)

                            ec2_instances.append(instance)
        return ec2_instances

    @logged
    def get_all_stacks(self, limit, **kwargs):
        return self.client.stacks.list(limit=limit, **kwargs)

    @logged
    def get_all_resources(self, stack_id, nested_depth=0):
        return self.client.resources.list(stack_id, nested_depth)

    @logged
    def get_metadata(self, stack_id, resource_name):
        return self.client.resources.metadata(stack_id, resource_name)


