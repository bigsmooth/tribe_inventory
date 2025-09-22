# inventory/forms.py
from django import forms

class AdjustStockForm(forms.Form):
    hub_id = forms.IntegerField(widget=forms.HiddenInput)
    sku_id = forms.IntegerField(widget=forms.HiddenInput)
    delta = forms.IntegerField(help_text="Use + for stock in, - for stock out")
    note = forms.CharField(required=False)
