from typing import Annotated

from pydantic import Field

HexUUIDString = Annotated[str, Field(min_length=32, max_length=32, pattern=r"^[0-9a-fA-F]{32}$")]
IntSeed = Annotated[int, Field(ge=-999999, le=999999)]
