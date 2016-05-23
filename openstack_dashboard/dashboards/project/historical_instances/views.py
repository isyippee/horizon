from horizon import views

from horizon import tables

from openstack_dashboard import api

from openstack_dashboard.dashboards.project.historical_instances import tables as project_tables
from horizon import exceptions
from django.utils.translation import ugettext_lazy as _


class IndexView(tables.DataTableView):
    # A very simple class-based view...
    table_class = project_tables.InstancesTable
    template_name = 'project/historical_instances/index.html'

    # def get_data(self, request, context, *args, **kwargs):
    # Add data to the context here...
    #    return context

    def get_data(self):
        search_opts = {'deleted': True}
        try:
            instances, self._more = api.nova.server_list(
                self.request,
                search_opts=search_opts)
        except Exception:
            self._more = False
            instances = []
            exceptions.handle(self.request,
                              _('Unable to retrieve instances.'))
        print instances
        # instances = []
        return instances
