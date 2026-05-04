"""Connector-specific exceptions."""


class ConnectorError(Exception):
    """Base exception for all connector errors."""


class PullError(ConnectorError):
    """Raised when fetching raw data from a source fails."""


class ParseError(ConnectorError):
    """Raised when parsing raw data into InfraNode results fails."""
