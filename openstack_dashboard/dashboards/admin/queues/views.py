from horizon import views
from horizon import tables
from horizon import forms
from openstack_dashboard.dashboards.admin.queues import tables as project_tables
from horizon import workflows
from openstack_dashboard.dashboards.admin.queues import workflows as queues_flows
from openstack_dashboard.dashboards.admin.queues import forms as project_forms
from django.core.urlresolvers import reverse_lazy


#class IndexView(views.APIView):
class IndexView(tables.DataTableView):
    table_class = project_tables.QueuesTable
    template_name = 'admin/queues/index.html'

    #def get_data(self, request, context, *args, **kwargs):
        # Add data to the context here...
    #    return context
    def get_data(self):
        result = []
        return result

#class DefineView(workflows.WorkflowView):
#    workflow_class = queues_flows.DefineConsumer
#    template_name = 'admin/queues/define.html'

class DefineView(forms.ModalFormView):
    form_class = project_forms.DefineForm
    template_name = 'admin/queues/define.html'
    success_url = reverse_lazy('horizon:admin:queues:index')
