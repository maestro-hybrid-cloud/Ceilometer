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

from oslo_utils import timeutils

from ceilometer.compute import util as compute_util
from ceilometer import sample

def make_sample_from_ec2_instance(ec2_instance, name, type, unit, volume,
                              resource_id=None, additional_metadata=None):
    additional_metadata = additional_metadata or {}
    resource_metadata = compute_util.add_reserved_user_metadata(ec2_instance.metadata, additional_metadata)
    return sample.Sample(
        name=name,
        type=type,
        unit=unit,
        volume=volume,
        user_id=ec2_instance.user_id,
        project_id=ec2_instance.tenant_id,
        resource_id=resource_id or ec2_instance.id,
        timestamp=timeutils.isotime(),
        resource_metadata=resource_metadata,
    )
