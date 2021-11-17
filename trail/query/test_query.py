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