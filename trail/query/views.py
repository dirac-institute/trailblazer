from django import forms
from django.forms import ModelForm
from django.apps import apps
from django.shortcuts import render


Metadata = apps.get_model('upload', 'Metadata')

# This is the ModelForm on the link I sent you. We import the Metadata DB model
# fom Uploads, we then map the felds from that model onto our Form. We can,
# during that mapping, mark some fields as mandatory and some as not. We can
# give some constraints on our inputs, such as length or format. We can pick
# from a variety of different input fields, from charaters, to number, dates,
# to long text form input. Some examples of mandatory/nonmandatory, validation
# and type of inputs provided.
class MetadataForm(ModelForm):
    instrument = forms.CharField(max_length=20)
    telescope = forms.CharField(max_length=20, required=False)

    # processor_name = forms.CharField(max_length=20, required=False)
    # standardizer_name = forms.CharField(max_length=20, required=False)
    # datetime_begin = forms.DateTimeField(
    #     input_formats=['%d/%m/%Y %H:%M:%S'],
    #     widget=forms.DateTimeInput(attrs={
    #         'class': 'form-control datetimepicker-input',
    #         'data-target': '#datetimepicker_begin'
    #     }),
    #     required=False
    # )
    # datetime_end = forms.DateTimeField(
    #     input_formats=['%d/%m/%Y %H:%M:%S'],
    #     widget=forms.DateTimeInput(attrs={
    #         'class': 'form-control datetimepicker-input',
    #         'data-target': '#datetimepicker_end'
    #     }),
    #     required=False
    # )

    # This maps our database schema model columns onto our form entries
    class Meta:
        model = Metadata
        fields = ['instrument', "telescope", ]


def index(request):
    """Index renders the form when root url is visited, bypassing slower checks
    required fo rendering of the results url, where rendering of the table and
    checking for results are performed.

    It is assumed the request type is POST.
    """
    form = MetadataForm()
    return render(request, "query.html", {"queryform": form, "render_table":False})


def print_results(request):
    """Renders the results url, which is a placeolder copy of the root url of
    query interface, where any results are rendered alongside the table headers.
    """
    if request.method == "POST":
        # when the request is type post (user sending data to us), then we want
        # to instantiate the form using the post request, and leave ourselfs the
        # option of using that data in our form as well.
        form = MetadataForm(request.POST)

        # triggers validation of input data, for now we don't have any real
        # limits on what kinds of strings users can write in our form, except
        # that most of them can't be longer than 20 characters and that datetime
        # has to be in the '%d/%m/%Y %H:%M:%S' format. It's good to leave us
        # with the ability to implement any changes in the future more easily
        # so we perform validation now, before making the query and waste CPU
        if form.is_valid():
            # This is the django way of doing `select * from upload_metadata;
            query_results = Metadata.objects.filter(instrument__icontains=form.data["instrument"])

            # Previously, so that you can see the results when you're
            # debugging, we converted each one to a dictionary. Dicts have
            # pretty print outputs by default. I will add a nice strigification
            # to our models when I manage, and then they wll also have pretty
            # outputs too. Until then they wont. Nevertheless it's not
            # *strictly neccessary* to convert results to dictionaries. They
            # already behave like a list of dicts, they just have ugly default
            # printing.
            #for item in query_result:
            #    itemDict = item.toDict()
            #    emptylist.append(itemDict)
    else:
        # if *somehow* we ended in results url, but the method type is not POST
        # (no data was sent), we render an empty form again and send back an
        # empty list of results
        query_results = []
        form = MetadataForm()

    return render(request, "query.html", {"data": query_results, "queryform": form, "render_table":True})
