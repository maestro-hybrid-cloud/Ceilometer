# -*- encoding: utf-8 -*-
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

from ceilometer.agent import plugin_base
from ceilometer import heat_client
from ceilometer.openstack.common import log

LOG = log.getLogger(__name__)

class AWSEC2InstancesDiscovery(plugin_base.DiscoveryBase):
    def __init__(self):
        super(AWSEC2InstancesDiscovery, self).__init__()
        self.heat_cli = heat_client.Client()

    def discover(self, manager, param=None):
        """Discover resources to monitor."""

        ec2_instances = self.heat_cli.ec2_instance_get_all()
        return [instance for instance in ec2_instances]
