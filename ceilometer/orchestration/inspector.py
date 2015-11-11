# Copyright 2013 Cloudbase Solutions Srl
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
"""Implementation of Inspector abstraction for Hyper-V"""

import datetime
import boto.ec2.cloudwatch

from oslo_config import cfg

from ceilometer.compute.virt import inspector as virt_inspector
from ceilometer.openstack.common import log

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class CloudWatchInspector(virt_inspector.Inspector):
    def inspect_cpu_util(self, instance, duration=None):
        duration = int(duration) if duration else 60

        end = datetime.datetime.utcnow()
        start = end - datetime.timedelta(seconds=duration)

        cw = boto.ec2.cloudwatch.CloudWatchConnection()

        statistics = cw.get_metric_statistics(
            period=duration,
            start_time=start,
            end_time=end,
            metric_name='CPUUtilization',
            namespace='AWS/EC2',
            statistics=['Average'],
            dimensions={'InstanceId':[instance.ec2_id]}
        )

        index = len(statistics) - 1
        utils = statistics[index].get('Maximum') if index >= 0 else 0

        return virt_inspector.CPUUtilStats(util=utils)
