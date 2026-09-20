class ResolveBuilderError(RuntimeError):
    """Base error for M11."""


class ContractError(ResolveBuilderError):
    """Input contract or provenance is invalid."""


class MediaVerificationError(ResolveBuilderError):
    """A referenced media file is missing or has the wrong digest."""
