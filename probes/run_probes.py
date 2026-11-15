#!/usr/bin/env python3
"""跨字段比较规则验收探针。

契约：
  from cerberus.crossfield import enable
  enable()   在当前进程里注册 min_field / max_field 两个规则
  Validator({"start": {...}, "end": {... "min_field": "start"}}) 据此校验
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FAILED = 0
PASSED = 0


def check(code, desc, fn):
    global FAILED, PASSED
    try:
        fn()
        print(f"[PASS] {code} {desc}")
        PASSED += 1
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {code} {desc}")
        print(f"        {type(exc).__name__}: {exc}")
        FAILED += 1


def main():
    try:
        from cerberus.crossfield import enable  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] P0 导入 cerberus.crossfield 失败：{type(exc).__name__}: {exc}")
        print("-" * 60)
        print("探针汇总：0/6 通过")
        return 1

    from cerberus import Validator
    enable()

    schema = {
        "start": {"type": "integer"},
        "end": {"type": "integer", "min_field": "start"},
        "min_qty": {"type": "integer"},
        "max_qty": {"type": "integer", "max_field": "min_qty"},
    }

    def p1():
        v = Validator(schema)
        assert v.validate({"start": 1, "end": 5}) is True, v.errors

    def p2():
        v = Validator(schema)
        assert v.validate({"start": 5, "end": 3}) is False, v.errors
        assert "end" in v.errors, v.errors

    def p3():
        v = Validator(schema)
        v.validate({"start": 5, "end": 3})
        assert "min_field" in str(v.errors["end"]), v.errors["end"]

    def p4():
        v = Validator(schema)
        assert v.validate({"min_qty": 1, "max_qty": 2}) is True, v.errors
        v2 = Validator(schema)
        assert v2.validate({"min_qty": 3, "max_qty": 2}) is False, v2.errors

    def p5():
        v = Validator(schema)
        assert v.validate({"end": 3}) is True, v.errors

    def p6():
        v = Validator({"n": {"type": "integer", "min": 1}})
        assert v.validate({"n": 0}) is False
        assert v.validate({"n": 2}) is True

    check("P1", "合法区间通过", p1)
    check("P2", "越界判失败", p2)
    check("P3", "错误挂在被校验字段上并带规则名", p3)
    check("P4", "max_field 方向相反", p4)
    check("P5", "参照字段缺失时不误报", p5)
    check("P6", "既有 min/max 规则不受影响", p6)

    print("-" * 60)
    print(f"探针汇总：{PASSED}/{PASSED + FAILED} 通过")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
