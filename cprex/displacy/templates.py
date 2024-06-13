# ruff: noqa: E501

TPL_ENT = """
<mark class="entity" style="background: {bg}; padding: 0.45em 0.6em; margin: 0 0.25em; line-height: 1; border-radius: 0.35em;display: inline-block;">
    {text}
    <span style="font-size: 0.8em; font-weight: bold; line-height: 1; border-radius: 0.35em; vertical-align: middle; margin-left: 0.5rem">{label}{kb_link}</span>
</mark>
"""

TPL_ENT_RTL = """
<mark class="entity" style="background: {bg}; padding: 0.45em 0.6em; margin: 0 0.25em; line-height: 1; border-radius: 0.35em; display: inline-block;">
    {text}
    <span style="font-size: 0.8em; font-weight: bold; line-height: 1; border-radius: 0.35em; vertical-align: middle; margin-right: 0.5rem">{label}{kb_link}</span>
</mark>
"""

TPL_SPAN = """
<span style="display: inline-block; position: relative; height: {total_height}px;">
    {text}
    {span_slices}
    {span_starts}
</span>
"""

TPL_SPAN_SLICE = """
<span style="background: {bg}; top: {top_offset}px; height: 4px; left: -1px; width: calc(100% + 4px); position: absolute;">
</span>
"""


TPL_SPAN_START = """
<span style="background: {bg}; top: {top_offset}px; height: 4px; border-top-left-radius: 3px; border-bottom-left-radius: 3px; left: -1px; width: calc(100% + 4px); position: absolute;">
    <span style="background: {bg}; z-index: 10; color: #000; top: -0.5em; padding: 2px 3px; position: absolute; font-size: 0.6em; font-weight: bold; line-height: 1; border-radius: 3px">
        {label}{kb_link}
    </span>
</span>
"""

TPL_SPAN_START_INV = """
<span style="background: {bg}; top: {top_offset}px; height: 4px; border-top-left-radius: 3px; border-bottom-left-radius: 3px; left: -1px; width: calc(100% + 2px); position: absolute;">
    <span style="background: {bg}; z-index: 10; color: #000; top: -0.5em; right: -2px; padding: 2px 3px; position: absolute; font-size: 0.6em; font-weight: bold; line-height: 1; border-radius: 3px">
        {label}{kb_link}
    </span>
</span>
"""

TPL_SPAN_END = """
<span style="background: {bg}; top: {top_offset}px; height: 4px; left: -1px; width: calc(100% - 20px); position: absolute;">
    <span style="background: {bg}; z-index: 10; color: {bg}; bottom: 0px; right: 0px; padding: 2px 3px; position: absolute; font-size: 0.6em; font-weight: bold; line-height: 1; border-radius: 3px">
        |
    </span>
</span>
"""

TPL_SPAN_END_INV = """
<span style="background: {bg}; top: {top_offset}px; height: 4px; left: -1px; width: calc(100% - 20px); position: absolute; margin-left: 20px;">
    <span style="background: {bg}; z-index: 10; color: {bg}; bottom: 0px; left: 0px; padding: 2px 3px; position: absolute; font-size: 0.6em; font-weight: bold; line-height: 1; border-radius: 3px">
        |
    </span>
</span>
"""
