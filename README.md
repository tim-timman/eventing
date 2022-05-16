# eventing

A pythonic event emitter inspired by Node.js'
EventEmitter and Python's logging libraries.

This package uses [Semantic Versioning][semver].

[semver]: https://semver.org/

## Develop

### Setup
```
python3.10 -m venv --upgrade-deps venv
source venv/bin/activate
pip install flit
flit install -s --deps=develop
pre-commit install
```
