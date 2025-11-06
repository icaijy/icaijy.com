from django import forms

class SubmissionForm(forms.Form):
    LANGUAGE_CHOICES = [
        ('cpp', 'C++'),
        ('py', 'Python'),
    ]
    language = forms.ChoiceField(
        choices=LANGUAGE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    code = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 10})
    )
