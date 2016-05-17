# Copyright 2012 Nebula, Inc.
# All rights reserved.

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

"""
Views for managing volumes.
"""

from django.conf import settings
from django.core.urlresolvers import reverse
from django.forms import ValidationError  # noqa
from django.template.defaultfilters import filesizeformat  # noqa
from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon.utils import functions
from horizon.utils.memoized import memoized  # noqa

from openstack_dashboard import api
from openstack_dashboard.api import cinder
from openstack_dashboard.api import glance
from openstack_dashboard.dashboards.project.images import utils
from openstack_dashboard.dashboards.project.instances import tables
from openstack_dashboard.usage import quotas

IMAGE_BACKEND_SETTINGS = getattr(settings, 'OPENSTACK_IMAGE_BACKEND', {})
IMAGE_FORMAT_CHOICES = IMAGE_BACKEND_SETTINGS.get('image_formats', [])
VALID_DISK_FORMATS = ('raw', 'vmdk', 'vdi', 'qcow2')
DEFAULT_CONTAINER_FORMAT = 'bare'

class DefineForm(forms.SelfHandlingForm):
#    exchage_type = forms.ChoiceField(label=_("Exchage Type"),
#                                     widget=forms.Select(attrs={
#                                         'class': 'switchable',
#                                               'data-slug': 'source'}))
    route_key = forms.CharField(max_length=255, label=_("Route Key"), required=False)

    def handle(self, request, data):
        return request

class AttachForm(forms.SelfHandlingForm):
    instance = forms.ChoiceField(label=_("Attach to Instance"),
                                 help_text=_("Select an instance to "
                                             "attach to."))

    device = forms.CharField(label=_("Device Name"),
                             widget=forms.TextInput(attrs={'placeholder':
                                                           '/dev/vdc'}),
                             required=False,
                             help_text=_("Actual device name may differ due "
                                         "to hypervisor settings. If not "
                                         "specified, then hypervisor will "
                                         "select a device name."))

    def __init__(self, *args, **kwargs):
        super(AttachForm, self).__init__(*args, **kwargs)

        # Hide the device field if the hypervisor doesn't support it.
        hypervisor_features = getattr(settings,
                                      "OPENSTACK_HYPERVISOR_FEATURES",
                                      {})
        can_set_mount_point = hypervisor_features.get("can_set_mount_point",
                                                      False)
        if not can_set_mount_point:
            self.fields['device'].widget = forms.widgets.HiddenInput()

        # populate volume_id
        volume = kwargs.get('initial', {}).get("volume", None)
        if volume:
            volume_id = volume.id
        else:
            volume_id = None
        self.fields['volume_id'] = forms.CharField(widget=forms.HiddenInput(),
                                                   initial=volume_id)

        # Populate instance choices
        instance_list = kwargs.get('initial', {}).get('instances', [])
        instances = []
        for instance in instance_list:
            if instance.status in tables.VOLUME_ATTACH_READY_STATES and \
                    not any(instance.id == att["server_id"]
                            for att in volume.attachments):
                instances.append((instance.id, '%s (%s)' % (instance.name,
                                                            instance.id)))
        if instances:
            instances.insert(0, ("", _("Select an instance")))
        else:
            instances = (("", _("No instances available")),)
        self.fields['instance'].choices = instances

    def handle(self, request, data):
        instance_choices = dict(self.fields['instance'].choices)
        instance_name = instance_choices.get(data['instance'],
                                             _("Unknown instance (None)"))
        # The name of the instance in the choices list has the ID appended to
        # it, so let's slice that off...
        instance_name = instance_name.rsplit(" (")[0]
        try:
            attach = api.nova.instance_volume_attach(request,
                                                     data['volume_id'],
                                                     data['instance'],
                                                     data.get('device', ''))
            volume = cinder.volume_get(request, data['volume_id'])
            message = _('Attaching volume %(vol)s to instance '
                         '%(inst)s on %(dev)s.') % {"vol": volume.name,
                                                    "inst": instance_name,
                                                    "dev": attach.device}
            messages.info(request, message)
            return True
        except Exception:
            redirect = reverse("horizon:project:volumes:index")
            exceptions.handle(request,
                              _('Unable to attach volume.'),
                              redirect=redirect)


class CreateSnapshotForm(forms.SelfHandlingForm):
    name = forms.CharField(max_length=255, label=_("Snapshot Name"))
    description = forms.CharField(max_length=255, widget=forms.Textarea,
            label=_("Description"), required=False)

    def __init__(self, request, *args, **kwargs):
        super(CreateSnapshotForm, self).__init__(request, *args, **kwargs)

        # populate volume_id
        volume_id = kwargs.get('initial', {}).get('volume_id', [])
        self.fields['volume_id'] = forms.CharField(widget=forms.HiddenInput(),
                                                   initial=volume_id)

    def handle(self, request, data):
        try:
            volume = cinder.volume_get(request,
                                       data['volume_id'])
            force = False
            message = _('Creating volume snapshot "%s".') % data['name']
            if volume.status == 'in-use':
                force = True
                message = _('Forcing to create snapshot "%s" '
                            'from attached volume.') % data['name']
            snapshot = cinder.volume_snapshot_create(request,
                                                     data['volume_id'],
                                                     data['name'],
                                                     data['description'],
                                                     force=force)

            messages.info(request, message)
            return snapshot
        except Exception:
            redirect = reverse("horizon:project:volumes:index")
            exceptions.handle(request,
                              _('Unable to create volume snapshot.'),
                              redirect=redirect)


class UpdateForm(forms.SelfHandlingForm):
    name = forms.CharField(max_length=255, label=_("Volume Name"))
    description = forms.CharField(max_length=255, widget=forms.Textarea,
            label=_("Description"), required=False)

    def handle(self, request, data):
        volume_id = self.initial['volume_id']
        try:
            cinder.volume_update(request, volume_id, data['name'],
                                 data['description'])

            message = _('Updating volume "%s"') % data['name']
            messages.info(request, message)
            return True
        except Exception:
            redirect = reverse("horizon:project:volumes:index")
            exceptions.handle(request,
                              _('Unable to update volume.'),
                              redirect=redirect)


class UploadToImageForm(forms.SelfHandlingForm):
    name = forms.CharField(label=_('Volume Name'),
                           widget=forms.TextInput(
                               attrs={'readonly': 'readonly'}))
    image_name = forms.CharField(max_length=255, label=_('Image Name'))
    disk_format = forms.ChoiceField(label=_('Disk Format'),
                                    widget=forms.Select(),
                                    required=False)
    force = forms.BooleanField(
        label=pgettext_lazy("Force upload volume in in-use status to image",
                            u"Force"),
        widget=forms.CheckboxInput(),
        required=False)

    def __init__(self, request, *args, **kwargs):
        super(UploadToImageForm, self).__init__(request, *args, **kwargs)

        # 'vhd','iso','aki','ari' and 'ami' disk formats are supported by
        # glance, but not by qemu-img. qemu-img supports 'vpc', 'cloop', 'cow'
        # and 'qcow' which are not supported by glance.
        # I can only use 'raw', 'vmdk', 'vdi' or 'qcow2' so qemu-img will not
        # have issues when processes image request from cinder.
        disk_format_choices = [(value, name) for value, name
                                in IMAGE_FORMAT_CHOICES
                                if value in VALID_DISK_FORMATS]
        self.fields['disk_format'].choices = disk_format_choices
        self.fields['disk_format'].initial = 'raw'
        if self.initial['status'] != 'in-use':
            self.fields['force'].widget = forms.widgets.HiddenInput()

    def handle(self, request, data):
        volume_id = self.initial['id']

        try:
            # 'aki','ari','ami' container formats are supported by glance,
            # but they need matching disk format to use.
            # Glance usually uses 'bare' for other disk formats except
            # amazon's. Please check the comment in CreateImageForm class
            cinder.volume_upload_to_image(request,
                                          volume_id,
                                          data['force'],
                                          data['image_name'],
                                          DEFAULT_CONTAINER_FORMAT,
                                          data['disk_format'])
            message = _(
                'Successfully sent the request to upload volume to image '
                'for volume: "%s"') % data['name']
            messages.info(request, message)

            return True
        except Exception:
            error_message = _(
                'Unable to upload volume to image for volume: "%s"') \
                % data['name']
            exceptions.handle(request, error_message)

            return False


class ExtendForm(forms.SelfHandlingForm):
    name = forms.CharField(
        label=_("Volume Name"),
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False,
    )
    orig_size = forms.IntegerField(
        label=_("Current Size (GB)"),
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False,
    )
    new_size = forms.IntegerField(label=_("New Size (GB)"))

    def clean(self):
        cleaned_data = super(ExtendForm, self).clean()
        new_size = cleaned_data.get('new_size')
        orig_size = self.initial['orig_size']
        if new_size <= orig_size:
            raise ValidationError(
                _("New size must be greater than current size."))

        usages = quotas.tenant_limit_usages(self.request)
        availableGB = usages['maxTotalVolumeGigabytes'] - \
            usages['gigabytesUsed']
        if availableGB < (new_size - orig_size):
            message = _('Volume cannot be extended to %(req)iGB as '
                        'you only have %(avail)iGB of your quota '
                        'available.')
            params = {'req': new_size, 'avail': availableGB}
            self._errors["new_size"] = self.error_class([message % params])
        return cleaned_data

    def handle(self, request, data):
        volume_id = self.initial['id']
        try:
            volume = cinder.volume_extend(request,
                                          volume_id,
                                          data['new_size'])

            message = _('Extending volume: "%s"') % data['name']
            messages.info(request, message)
            return volume
        except Exception:
            redirect = reverse("horizon:project:volumes:index")
            exceptions.handle(request,
                              _('Unable to extend volume.'),
                              redirect=redirect)


class RetypeForm(forms.SelfHandlingForm):
    name = forms.CharField(label=_('Volume Name'),
                           widget=forms.TextInput(
                               attrs={'readonly': 'readonly'}))
    volume_type = forms.ChoiceField(label=_('Type'))
    MIGRATION_POLICY_CHOICES = [('never', _('Never')),
                                ('on-demand', _('On Demand'))]
    migration_policy = forms.ChoiceField(label=_('Migration Policy'),
                                         widget=forms.Select(),
                                         choices=(MIGRATION_POLICY_CHOICES),
                                         initial='never',
                                         required=False)

    def __init__(self, request, *args, **kwargs):
        super(RetypeForm, self).__init__(request, *args, **kwargs)

        try:
            volume_types = cinder.volume_type_list(request)
            self.fields['volume_type'].choices = [(t.name, t.name)
                                                   for t in volume_types]
            self.fields['volume_type'].initial = self.initial['volume_type']

        except Exception:
            redirect_url = reverse("horizon:project:volumes:index")
            error_message = _('Unable to retrieve the volume type list.')
            exceptions.handle(request, error_message, redirect=redirect_url)

    def clean_volume_type(self):
        cleaned_volume_type = self.cleaned_data['volume_type']
        origin_type = self.initial['volume_type']

        if cleaned_volume_type == origin_type:
            error_message = _(
                'New volume type must be different from '
                'the original volume type "%s".') % cleaned_volume_type
            raise ValidationError(error_message)

        return cleaned_volume_type

    def handle(self, request, data):
        volume_id = self.initial['id']

        try:
            cinder.volume_retype(request,
                                 volume_id,
                                 data['volume_type'],
                                 data['migration_policy'])

            message = _(
                'Successfully sent the request to change the volume '
                'type to "%(vtype)s" for volume: "%(name)s"')
            params = {'name': data['name'],
                      'vtype': data['volume_type']}
            messages.info(request, message % params)

            return True
        except Exception:
            error_message = _(
                'Unable to change the volume type for volume: "%s"') \
                % data['name']
            exceptions.handle(request, error_message)

            return False
