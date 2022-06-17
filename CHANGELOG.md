# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog][keep-a-changelog],
and this project adheres to [Semantic Versioning][semver].

[keep-a-changelog]: https://keepachangelog.com/en/1.0.0/
[semver]: https://semver.org/spec/v2.0.0.html

## [Unreleased]

## [0.3.0] - 2022-06-17
### Added
- Module level `eventing.set_event_loop(...)` setting the event loop on root,
  top of the hierarchy, making any emitter capable of handling coroutine
  function listeners.
- Support to add listeners to static, class, and instance methods and have them
  be called bound. This is opt-in by marking them with `@ee.on(..., method=True)`
  and decorating the class with `@ee.handle_methods` to complete setup. Instance
  methods are added first when instantiated. Note: this is a hacky
  implementation.
- Getting emitters and adding/removing listeners should now be threadsafe.

### Changed
- `ee.emit(...)` will now look for an event loop up the hierarchy on emit when
  a coroutine listener is encountered. If `a.b.c` emits an event with coroutine
  function listener it will first check if itself has a loop, then `a.b`, `a`
  and finally the root event emitter. If one isn't found it raises
  `NoEventLoopError`.

### Fixed
- Mutations of returned list of `ee.listeners(...)` would mutate the emitter's
  listeners. It now returns a copy.

## [0.2.0] - 2022-06-03
### Added
- Support coroutine functions (`async def`) as listeners. Threadsafe. The event
  loop to use has to be set before a coroutine function listener is emitted, eg.
  `ee.set_event_loop(asyncio.get_running_loop())`.
- Support listeners that emit events (including the one it's listening
  to) without potential for `RecursionError`.
- Support listeners removing themselves.
- Coverage report
- Decorator `@ee.on(...)` to add a listener for an event.

## [0.1.0] - 2022-05-24
### Added
- The eventing package with initial synchronous event emitting functionality
  using Flit build system.
- Tests for all package code.
- README containing package description, badges and project rationale along
  with links to further documentation.
- DEVELOPMENT describing setup, and use of local development, build and publish
- This CHANGELOG file to keep track of changes.
- LICENSE
- pytest configuration
- flake8 configuration
- mypy configuration
- tox configuration
- pre-commit configuration
- Documentation configuration to generate docs from Google style docstrings
  using sphinx with napoleon and Read the Docs theme.
- Read the Docs configuration
- GitHub Actions configuration running tests on push and pull requests

[Unreleased]: https://github.com/tim-timman/eventing/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/tim-timman/eventing/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/tim-timman/eventing/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/tim-timman/eventing/releases/tag/v0.1.0
