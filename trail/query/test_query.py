Test1 = {'instrument': 'DECam', 'telescope': ' ', 'processor_name': ' ', 'col': ' '}
Test2 = {'instrument': 'DECam', 'telescope': 'asd', 'processor_name': ' ', 'col': ' '}
Test3 = {'instrument': 'DECam', 'telescope': 'asd', 'processor_name': 'asss', 'col': ' '}
Test4 = {'instrument': 'DECam', 'telescope': ' ', 'processor_name': 'asss', 'col': ' '}


def get_query(test):
    # values = test.copy()
    # breakpoint()
    # values.pop("csrfmiddlewaretoken", False)
    # pop telescope if there's no input
    # for test['']

    if test['telescope'] == ' ':
        test.pop('telescope', False)
    if test['processor_name'] == ' ':
        test.pop('processor_name')
    if test['col'] == ' ':
        test.pop('col')
    return test


print(get_query(Test1))
print(get_query(Test2))
print(get_query(Test3))
print(get_query(Test4))
