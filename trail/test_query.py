import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trail.settings")
import django
django.setup()
#from core.models import (
    #Company, 
    #DomainDetails, 
    #SponsorshipTrail, 
    #JobBoard
#)

from django.apps import apps
# from django.conf import settings

#settings.configure(
    #DATABASES = {
        #"ENGINE":"django.db.backends.sqlite3",
        #"NAME":"/c/Users/jasmi/Desktop/ASTR 499/astr499_summer21/trailblazer-testdata/db.sqlite3"
    #}
#)

Test5 = {'instrument': 'DECam'}
print(Test5)

Metadata = apps.get_model('upload', 'Metadata')
Wcs = apps.get_model('upload', 'Wcs')
query_results = Metadata.objects.filter(instrument='DECam')

wcs_list = []
for obj in query_results:
    wcs_info = obj.wcs_set.all()
    wcs_list.append(wcs_info)

print(wcs_list)
print(query_results)

output = 1
print(output)
breakpoint()
























































Test1 = {'instrument': 'DECam', 'telescope': ' ', 'processor_name': ' ', 'col': ' '}
Test2 = {'instrument': 'DECam', 'telescope': 'asd', 'processor_name': ' ', 'col': ' '}
Test3 = {'instrument': 'DECam', 'telescope': 'asd', 'processor_name': 'asss', 'col': ' '}
Test4 = {'instrument': 'DECam', 'telescope': ' ', 'processor_name': 'asss', 'col': ' '}


def get_query1(test, arugment=True):
    # values = test.copy()
    # breakpoint()
    # values.pop("csrfmiddlewaretoken", False)
    # pop telescope if there's no input
    # for test['']
    new_dict = {}
    for key in test:
        if test[key] != ' ':
            if arugment:
                keyk = key + "__contains"
                new_dict[keyk] = test[key]
    return new_dict

# def print_results():

    # results = 
    
    # return results

# string = headers
# table.sort(string)

# def get_query(d, argument=True):
#     new_dict = {}
#     # argument = True
#     for key in d:
#         if d[key]:
#             if argument:
#                 keyk = key + "__contains"
#                 new_dict[keyk] = d[key]
#     return new_dict


print(get_query1(Test1))
# print(get_query(Test2))
# print(get_query(Test3))
# print(get_query(Test4))


# class TestClass():
#     b = 1
#     def __init__(self, a):
#         self.aa = a
#     def pprinter(self):
#         print(self.aa, self.b)

# tc = TestClass({"a":'1', "b":'2'})
# tc1 = TestClass('e')
# print(tc.aa)
# print(tc.b)
# print(TestClass.b)
# # print(TestClass.a)
# TestClass.b = 2
# print(tc.b)
# print(tc1.aa)
# print(tc.pprinter())