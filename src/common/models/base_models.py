from typing import Annotated

from pydantic import Field

HexUUIDString = Annotated[str, Field()]
IntSeed = Annotated[int, Field(ge=-999999, le=999999)]
