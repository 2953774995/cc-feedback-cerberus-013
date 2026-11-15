# -*-: coding utf-8 -*-
"""跨字段比较规则：``min_field`` / ``max_field``。

用法::

    from cerberus.crossfield import enable
    enable()

之后即可在 schema 中引用其他字段作为比较基准::

    {
        'start': {'type': 'integer'},
        'end': {'type': 'integer', 'min_field': 'start'},
        'min_qty': {'type': 'integer'},
        'max_qty': {'type': 'integer', 'max_field': 'min_qty'},
    }

``min_field: "<字段名>"`` 表示当前字段的值不得小于参照字段的值；
``max_field: "<字段名>"`` 方向相反，表示参照字段的值不得大于当前字段
（即当前字段是参照字段的上界）。两个规则可以共存于同一 schema。

参照字段缺失、或参照字段未通过其自身规则校验时，本条规则静默跳过，
不产生误报。违规时错误挂在携带规则的那个字段上。

``enable()`` 只做进程内的规则注册，可重复调用；未调用时这两个规则名
在 schema 里仍按未知规则处理，:class:`~cerberus.Validator` 的默认构造
行为不受影响。
"""

from __future__ import absolute_import

from cerberus import errors
from cerberus.validator import Validator

__all__ = ['enable', 'MIN_FIELD', 'MAX_FIELD']


MIN_FIELD = errors.ErrorDefinition(0x49, 'min_field')
MAX_FIELD = errors.ErrorDefinition(0x4A, 'max_field')

_RULE_NAMES = ('min_field', 'max_field')
_RULE_SCHEMA = {'type': 'string'}
_MISSING = object()


def _referenced_value(validator, field):
    """返回参照字段用于比较的值。

    参照字段缺失、或其值未通过自身规则校验时返回 ``_MISSING``，
    调用方据此跳过比较，避免误报。
    """
    document = validator.document
    if document is None or field not in document:
        return _MISSING
    value = document[field]

    # 参照字段已校验过且留有错误
    path = validator.document_path + (field,)
    for error in validator._errors:
        if error.document_path == path:
            return _MISSING

    # 参照字段在文档中排在当前字段之后、尚未校验时，
    # 用其自身规则（剔除跨字段规则，避免递归）试算一次
    schema = validator.schema
    if schema is not None and field in schema:
        resolved = validator._resolve_rules_set(schema[field])
        if resolved:
            rules = {k: v for k, v in resolved.items() if k not in _RULE_NAMES}
            if rules:
                probe = validator._get_child_validator(schema={field: rules})
                if not probe.validate({field: value}):
                    return _MISSING
    return value


def _validate_min_field(self, other_field, field, value):
    """{'type': 'string'}"""
    # 当前字段的值不得小于参照字段的值
    other = _referenced_value(self, other_field)
    if other is _MISSING:
        return
    try:
        if value < other:
            self._error(field, MIN_FIELD)
    except TypeError:
        pass


def _validate_max_field(self, other_field, field, value):
    """{'type': 'string'}"""
    # 方向相反：参照字段的值不得大于当前字段（当前字段是其上界）
    other = _referenced_value(self, other_field)
    if other is _MISSING:
        return
    try:
        if other > value:
            self._error(field, MAX_FIELD)
    except TypeError:
        pass


def enable():
    """在当前进程里向 :class:`cerberus.Validator` 注册跨字段比较规则。

    注册 ``min_field`` / ``max_field`` 两个规则及其错误消息模板。
    幂等，可重复调用。
    """
    Validator._validate_min_field = _validate_min_field
    Validator._validate_max_field = _validate_max_field
    for rule in _RULE_NAMES:
        Validator.validation_rules[rule] = dict(_RULE_SCHEMA)
        Validator.rules[rule] = dict(_RULE_SCHEMA)
    errors.BasicErrorHandler.messages[MIN_FIELD.code] = (
        "min_field: value is less than field '{constraint}'"
    )
    errors.BasicErrorHandler.messages[MAX_FIELD.code] = (
        "max_field: field '{constraint}' exceeds this value"
    )
