# eventing
[![Tests][test-badge]][test-uri]
[![Documentation Status][rtd-badge]][rtd-uri]
[![PyPI][pypi-badge]][pypi-uri]
[![License][license-badge]][license-uri]

[test-badge]: https://github.com/tim-timman/eventing/actions/workflows/tests.yaml/badge.svg?branch=master&event=push
[test-uri]: https://github.com/tim-timman/eventing/actions/workflows/tests.yaml
[rtd-badge]: https://readthedocs.org/projects/eventing/badge/?version=latest
[rtd-uri]: https://eventing.readthedocs.io/en/latest/?badge=latest
[pypi-badge]: https://img.shields.io/pypi/v/eventing
[pypi-uri]: https://pypi.org/project/eventing/
[license-badge]: https://img.shields.io/pypi/l/eventing
[license-uri]: https://github.com/tim-timman/eventing/blob/master/LICENSE

A pythonic event emitter inspired by Node.js' [EventEmitter][njs-ee]
and Python's [logging][pylogging] libraries.

[njs-ee]: https://nodejs.org/api/events.html#class-eventemitter
[pylogging]: https://docs.python.org/3/library/logging.html

This project adheres to [Semantic Versioning][semver].

[semver]: https://semver.org/spec/v2.0.0.html

### Rationale
This project sprung to life partly from wanting to learn TDD and publishing a
python package, but also from the need of an event pattern akin to Node.js'
EventEmitter that will with asyncio in a nice pythonic way.

I envision it in a similar API as Python's logging module, in that it'll
"just work" regardless of event loops, threads (and possibly even subprocesses);
something I haven't found in the myriad event packages on PyPI. Hopefully, it'll
become something of use to others as well.

## Docs
Autogenerated API docs can be found at <https://eventing.readthedocs.io>.

> **Note:** Until a version `>=1.0.0` these are not maintained as a public API
> has yet to be established.

## Development

See [DEVELOPMENT][dev-doc]

[dev-doc]: https://github.com/tim-timman/eventing/blob/master/DEVELOPMENT.md

## Changelog

See [CHANGELOG][changelog]

[changelog]: https://github.com/tim-timman/eventing/blob/master/CHANGELOG.md

## License

MIT, see [LICENSE][license]

[license]: https://github.com/tim-timman/eventing/blob/master/LICENSE
