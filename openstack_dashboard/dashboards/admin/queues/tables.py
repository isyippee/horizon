from horizon import tables
from django.utils.translation import ugettext_lazy as _

class DefineConsumer(tables.LinkAction):
    name = "define"
    verbose_name = _("Define Consumer")
    url = "horizon:admin:queues:define"
    classes = ("ajax-model",)
    icon = "plus"

class SendMessage(tables.LinkAction):
    name = "send"
    verbose_name = "Send Message"
    url = "horizon:admin:queues:send"
    classes = ("ajax-model",)
    icon = "cloud-upload"

class QueuesTable(tables.DataTable):
    name = tables.Column("exchage_name",
                         verbose_name=_("Exchage Name"))
    id = tables.Column("consumer_tag", verbose_name=("Consumer Tag"))
    created = tables.Column("message_text", verbose_name=("Message Text"))

    class Meta:
        name = "queues"
        verbose_name = _("Queues")
        table_actions = (DefineConsumer, SendMessage)
