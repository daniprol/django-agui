# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- towncrier release notes start -->

## [0.1.0] - 2025-02-12

### Features

- Initial release of django-agui
- Core AG-UI protocol support with SSE streaming
- Django-native views with async support
- Simple router API for single and multi-agent setups
- `@agui_view` decorator for function-based agents
- Django REST Framework integration (streaming and REST views)
- DRF router support
- Configurable authentication backends
- Django settings integration
- Django system checks
- Comprehensive documentation

### Added

- `get_agui_urlpatterns()` - Simple URL pattern helper
- `AGUIRouter` / `MultiAgentRouter` - Multi-agent routing
- `AGUIView` - Core streaming view
- `agui_view` decorator
- DRF views: `AGUIView`, `AGUIRestView`
- DRF router: `AGUIRouter`
- `SSEEventEncoder` for Server-Sent Events
- `DjangoAuthBackend` for authentication
