# views.py
from django.views.generic import ListView, DetailView, TemplateView
from .models import Transaction
from django.db.models import Count


class TransactionListView(ListView):
    model = Transaction
    template_name = 'transactions/transaction_list.html'
    context_object_name = 'transactions'

class TransactionDetailView(DetailView):
    model = Transaction
    template_name = 'transactions/transaction_detail.html'
    context_object_name = 'transaction'

class TransactionStatusListView(ListView):
    model = Transaction
    template_name = 'transactions/transaction_status_list.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        status = self.kwargs.get('status')
        return Transaction.objects.filter(transaction_status=status)


class DashboardView(TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status_counts = Transaction.objects.values('transaction_status').annotate(count=Count('transaction_status'))
        context['status_counts'] = status_counts
        return context