"""Add support for typed-checked versions of primatives."""
import pydantic as pyd

@pyd.validate_call
def non_neg_int(_val: pyd.conint(ge=0)) -> pyd.conint(ge=0):
    return _val

@pyd.validate_call
def pos_int(_val: pyd.conint(gt=0)) -> pyd.conint(gt=0):
    return _val

@pyd.validate_call
def non_neg_float(_val: pyd.confloat(ge=0)) -> pyd.confloat(ge=0):
    return _val

@pyd.validate_call
def pos_float(_val: pyd.confloat(gt=0)) -> pyd.confloat(gt=0):
    return _val

if __name__ == '__main__':
    x = non_neg_int(0)
    print(x, type(x))
    x = pos_int(5)
    print(x, type(x))
    x = non_neg_float(0)
    print(x, type(x))
    x = pos_float(0.5)
    print(x, type(x))

    try:
        y = non_neg_int(-0.5)
    except pyd.ValidationError as exc:
        print()
        print(exc)
    
    try:
        y = pos_int(-1)
    except pyd.ValidationError as exc:
        print()
        print(exc)
