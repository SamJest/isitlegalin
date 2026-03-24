import re

from .strings import _js_string


_TOKEN_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


def renderTemplate(template, values):
    def replace(match):
        key = match.group(1)
        value = values.get(key)
        return "" if value is None else _js_string(value)

    return _TOKEN_PATTERN.sub(replace, template)
