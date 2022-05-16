import importlib

import eventing


# Since we're testing a package which keeps a global state across imports
# we need to reload it to remove previous state at the start of each test
# to avoid the side effects. This feels preferable than a fixture doing
# the import; this way is much less boilerplate and the tests better show
# the intended use of the package
def pytest_runtest_setup(item):
    importlib.reload(eventing)
