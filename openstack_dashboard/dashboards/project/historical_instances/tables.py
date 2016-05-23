import logging

from django.utils.translation import ugettext_lazy as _

from horizon import tables
from django import template
from horizon.templatetags import sizeformat

LOG = logging.getLogger(__name__)

def get_keyname(instance):
    if hasattr(instance, "key_name"):
        keyname = instance.key_name
        return keyname
    return _("Not available")

def get_ips(instance):
    template_name = 'project/instances/_instance_ips.html'
    context = {"instance": instance}
    return template.loader.render_to_string(template_name, context)

def get_size(instance):
    if hasattr(instance, "full_flavor"):
        template_name = 'project/instances/_instance_flavor.html'
        size_ram = sizeformat.mb_float_format(instance.full_flavor.ram)
        if instance.full_flavor.disk > 0:
            size_disk = sizeformat.diskgbformat(instance.full_flavor.disk)
        else:
            size_disk = _("%s GB") % "0"
        context = {
            "name": instance.full_flavor.name,
            "id": instance.id,
            "size_disk": size_disk,
            "size_ram": size_ram,
            "vcpus": instance.full_flavor.vcpus
        }
        return template.loader.render_to_string(template_name, context)
    return _("Not available")

class InstancesTable(tables.DataTable):
    name = tables.Column("name",
                         verbose_name=_("Instance Name"))
    id = tables.Column("id", verbose_name=("Instance Id"))
    created = tables.Column("created", verbose_name=("Instance Created"))
    image_name = tables.Column("image_name",
                               verbose_name=_("Image Name"))
    ip = tables.Column(get_ips,
                       verbose_name=_("IP Address"),
                       attrs={'data-type': "ip"})
    size = tables.Column(get_size,
                         verbose_name=_("Size"),
                         attrs={'data-type': 'size'})
    keypair = tables.Column(get_keyname, verbose_name=_("Key Pair"))
    az = tables.Column("availability_zone",
                       verbose_name=_("Availability Zone"))
    class Meta:
        name = "historical instances"
        verbose_name = _("Historical_Instances")
