from dataclasses import dataclass
from enum import Enum


class SpoilerPolicy(Enum):
    KEEP_ORIGINAL = 0
    FORCE_SPOILER = 1
    FORCE_NO_SPOILER = 2


class DescriptionPolicy(Enum):
    KEEP_ORIGINAL = 0
    REMOVE_DESCRIPTION = 1


@dataclass(frozen=True)
class PostHandlingPolicies:
    spoiler_policy: SpoilerPolicy = SpoilerPolicy.KEEP_ORIGINAL
    description_policy: DescriptionPolicy = DescriptionPolicy.KEEP_ORIGINAL
