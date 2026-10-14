"""Buckets (entity types) and relationship types, and the one way names are compared.

These are the defaults a workspace starts with; after that the Entity types
tab in the Document Index workbook is the source, so buckets can be added,
described or renamed without code changes.
"""
import re

OTHER = "other"
DEFAULT_BUCKETS = (
    ("company", "A business or organisation, e.g. a competitor, supplier or partner."),
    ("product", "Something sold or made, e.g. our newsletter or a competitor's product."),
    ("platform or tool", "Software or an online service used to do work, e.g. Shopify, Beehiiv, ClickUp."),
    ("service or component", "A part of our own systems, e.g. the gateway, the sync job, a database."),
    ("market or country", "A geographic market or country, e.g. Singapore, the US."),
    ("audience segment", "A group of people we target, e.g. Singapore startup founders."),
    ("channel", "A sales or marketing channel, e.g. LinkedIn, email, referrals."),
    ("person", "A named individual."),
    ("feature", "A capability of a product or system, e.g. a referral programme, passage search."),
    ("metric", "Something measured, e.g. open rate, monthly recurring revenue."),
    (OTHER, "Anything that fits no other bucket; suggest the bucket it should have."),
)
DEFAULT_RELATIONS = (
    ("competes with", "Offers an alternative to the other."),
    ("uses", "Relies on or is built with the other."),
    ("targets", "Is aimed at the other (an audience, market or channel)."),
    ("supplies", "Provides goods or services to the other."),
    ("part of", "Is a component or subset of the other."),
    ("replaces", "Supersedes or is chosen instead of the other."),
    ("integrates with", "Connects to or works together with the other."),
    ("owns", "Owns or operates the other."),
)

_SPACES = re.compile(r"\s+")
_EDGES = " \t\"'`.,;:!?()[]{}"


def normalize(name):
    """'  LinkedIn. ' and 'linkedin' compare equal: lowercase, single spaces, no surrounding punctuation."""
    return _SPACES.sub(" ", str(name or "")).strip(_EDGES).lower()
