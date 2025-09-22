# inventory/forms.py
from django import forms
from .models import Hub, SKU

class AdjustStockForm(forms.Form):
    hub_id = forms.IntegerField(widget=forms.HiddenInput)
    sku_id = forms.IntegerField(widget=forms.HiddenInput)
    delta = forms.IntegerField(help_text="Use +10 to add, -5 to subtract")
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))

class SKUCSVUploadForm(forms.Form):
    file = forms.FileField(help_text="CSV with headers: sku,name,barcode,low_stock_threshold,hubs")
    clear_assignments = forms.BooleanField(required=False, initial=False,
                                           help_text="Remove existing hub assignments before applying CSV")
    default_threshold = forms.IntegerField(required=False, min_value=0, initial=5)

class SKUAssignForm(forms.ModelForm):
    hubs = forms.ModelMultipleChoiceField(
        queryset=Hub.objects.all().order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = SKU
        fields = ["hubs"]

class HubFilterForm(forms.Form):
    hub = forms.ModelChoiceField(
        queryset=Hub.objects.all().order_by("name"),
        required=False,
        empty_label="— Select a hub —"
    )
