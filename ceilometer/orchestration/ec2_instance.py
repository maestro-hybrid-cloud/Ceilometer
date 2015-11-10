#
# Copyright 2012 eNovance <licensing@enovance.com>
# Copyright 2012 Red Hat, Inc
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

import abc
import six

from ceilometer.compute import pollsters
from ceilometer.orchestration import util
from ceilometer.i18n import _
from ceilometer.openstack.common import log
from ceilometer import sample
from ceilometer.orchestration.inspector import CloudWatchInspector

LOG = log.getLogger(__name__)

@six.add_metaclass(abc.ABCMeta)
class AWSEC2PollsterBase(pollsters.BaseComputePollster):

    @property
    def inspector(self):
        try:
            inspector = self._inspector
        except AttributeError:
            inspector = CloudWatchInspector()
            AWSEC2PollsterBase._inspector = inspector
        return inspector

    @property
    def default_discovery(self):
        return 'aws_ec2_instances'

class CPUUtilPollster(AWSEC2PollsterBase):
    def get_samples(self, manager, cache, resources):
        self._inspection_duration = self._record_poll_time()
        for instance in resources:
            LOG.debug(_('Checking CPU util for AWS EC2 instance %s'), instance.id)
            try:
                cpu_info = self.inspector.inspect_cpu_util(
                    instance, self._inspection_duration)
                LOG.debug(_("CPU UTIL: %(instance)s %(util)d"),
                          ({'instance': instance.__dict__,
                            'util': cpu_info.util}))
                yield util.make_sample_from_ec2_instance(
                    instance,
                    name='cpu_util',
                    type=sample.TYPE_GAUGE,
                    unit='%',
                    volume=cpu_info.util,
                )
            except Exception as err:
                LOG.exception(_('Could not get CPU Util for %(id)s: %(e)s'),
                              {'id': instance.id, 'e': err})
