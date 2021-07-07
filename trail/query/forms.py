from django import forms
from django.db import models

"""Add buttons or selection options for upload here."""


# class FileFieldForm(forms.Form):
    # file_field = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))


class Settings(models.Model):
    receive_newsletter = models.BooleanField()