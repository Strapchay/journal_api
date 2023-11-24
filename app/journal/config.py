JOURNAL_DESCRIPTION = """
Document your life - daily happenings, special occasions,
and reflections on your goals. Categorize entries with
tags and automatically capture the date.
<br />
<br />
↓ Click through the different database tabs to filter
entries by a specific category such as daily or personal.
"""

DEFAULT_JOURNAL_NAME = "Untitled"


def get_table_defaults(journal):
    return [
        {"journal": journal, "table_name": "All entries"},
        {"journal": journal, "table_name": "Daily entries"},
        {"journal": journal, "table_name": "Personal entries"},
    ]
