# eventing

A pythonic event emitter inspired by Node.js' [EventEmitter][njs-ee]
and Python's [logging][pylogging] libraries.

[njs-ee]: https://nodejs.org/api/events.html#class-eventemitter
[pylogging]: https://docs.python.org/3/library/logging.html

This package uses [Semantic Versioning][semver].

[semver]: https://semver.org/

## Develop

### Setup
```
python3.10 -m venv --upgrade-deps venv
source venv/bin/activate
pip install flit
flit install -s --extras=all
pre-commit install
```

### pre-commit hook
[pre-commit][pre-commit] used as a git pre-commit hook. It runs several checks
and tests to verify that the commit adheres to the code style for consistency
and make sure tests are passing.

[pre-commit]: https://pre-commit.com/

Aside from running on git's pre-commit hook, it can be manually run on the
current working tree. It will run against staged files, only applying any
modifications if there are no unstaged ones.
```
pre-commit run
```

### Testing
Tests are written using [pytest][pytest] with the
[pytest-asyncio][pytest-asyncio] plugin to allow testing coroutines.

[pytest]: https://docs.pytest.org/en/latest/contents.html
[pytest-asyncio]: https://github.com/pytest-dev/pytest-asyncio

These are run as part of pre-commit but can also be run manually against the
dirty working tree.
```
pytest
```
