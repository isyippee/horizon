from django.utils.translation import ugettext_lazy as _

import horizon

from openstack_dashboard.dashboards.admin import dashboard


class Queues(horizon.Panel):
    name = _("Queues")
    slug = "queues"


dashboard.Admin.register(Queues)
