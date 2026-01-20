from django import forms

class LicenseUpdateForm(forms.Form):
    license_key = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Pegue su licencia aquí...'}),
        label="Clave de Licencia",
        help_text="Copie y pegue la cadena de texto de su licencia completa."
    )
