from django import forms

class KeywordForm(forms.Form):
	keyword = forms.CharField(max_length=25, label="Entrez votre mot clef")