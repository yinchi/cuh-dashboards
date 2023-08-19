import pydantic as pyd

ZeroToTen = pyd.conint(strict=True, ge=0, le=10)

x = pyd.StrictBool(1)
y = pyd.StrictInt(5)
z = ZeroToTen(11)

print(x)
print(x*y)
print()

# Raw con___ are not validated in Pydantic
print(z)
print()

# To validate, embed in a BaseModel subclass
class TestType(pyd.BaseModel):
    x: ZeroToTen
    y: ZeroToTen


print(TestType(x=4, y=10))

try:
    print(TestType(x=11, y=-1))
except pyd.ValidationError as exc:
    print(exc)
