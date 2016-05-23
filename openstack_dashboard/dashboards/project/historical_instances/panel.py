from django.utils.translation import ugettext_lazy as _

import horizon

from openstack_dashboard.dashboards.project import dashboard


class Historical_Instances(horizon.Panel):
    name = _("Historical_Instances")
    slug = "historical_instances"


dashboard.Project.register(Historical_Instances)
