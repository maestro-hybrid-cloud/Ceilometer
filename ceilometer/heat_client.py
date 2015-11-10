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
import urlparse

from heatclient import client as heat_client
from oslo_config import cfg
from ceilometer import keystone_client
from ceilometer.openstack.common import log

SERVICE_OPTS = [
    cfg.StrOpt('heat',
               default='orchestration',
               help='Heat service type.'),
]

cfg.CONF.register_opts(SERVICE_OPTS, group='service_types')
cfg.CONF.import_opt('http_timeout', 'ceilometer.service')
cfg.CONF.import_group('service_credentials', 'ceilometer.service')

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

    def __init__(self):
        conf = cfg.CONF.service_credentials

        api_version = '1'
        heat_url = keystone_client.get_client().service_catalog.url_for(
                    service_type=cfg.CONF.service_types.heat,
                    endpoint_type=conf.os_endpoint_type)
        endpoint = urlparse.urljoin(heat_url, '/admin')

        params = {
            'insecure': conf.insecure,
            'ca_file': conf.os_cacert,
            'username': conf.os_username,
            'password': conf.os_password,
            'auth_url': conf.os_auth_url,
            'region_name': conf.os_region_name,
            'endpoint_type': conf.os_endpoint_type,
            'timeout': cfg.CONF.http_timeout,
            'service_type': cfg.CONF.service_types.heat,
        }

        if conf.os_tenant_id:
            params['tenant_id'] = conf.os_tenant_id
        else:
            params['tenant_name'] = conf.os_tenant_name

        self.client = heat_client.Client(api_version, endpoint, **params)

    @logged
    def ec2_instance_get_all(self):
        all_stacks = self.get_all_stacks()

        for stack in all_stacks:
            stack_identifier = '%s/%s' % (stack.stack_name, stack.id)
            resources = self.get_all_resources(stack_identifier, nested_depth=3)

            for resource in resources:
                if resource.resource_type == 'OS::Heat::EC2Instance':
                    resource['metadata'] = self.get_metadata(stack_identifier, resource.resource_name)
                    yield resource

    @logged
    def get_all_stacks(self):
        return self.client.stacks.list()

    @logged
    def get_all_resources(self, stack_id, nested_depth=0):
        return self.client.resources.list(stack_id, nested_depth)

    @logged
    def get_metadata(self, stack_id, resource_name):
        return self.client.resources.metadata(stack_id, resource_name)


