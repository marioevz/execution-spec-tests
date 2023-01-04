"""
Test suite for `code.eof.v1` module.
"""
import pytest

from ..eof.v1 import Container, Section, SectionKind


@pytest.mark.parametrize(
    ["container", "hex"],
    [
        # No sections
        (
            Container(
                auto_data_section=False,
                auto_type_section=False,
                sections=[],
            ),
            "ef0001 00",
        ),
        # Single code section
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                    ),
                ],
            ),
            "ef0001 01 0004 02 0001 0001 03 0000 00 00000000 00",
        ),
        # No code section
        (
            Container(
                name="no_code_section",
                sections=[Section(kind=SectionKind.DATA, data="0x00")],
            ),
            "ef0001 01 0000 03 0001 00 00",
        ),
        # Single data section
        (
            Container(
                auto_type_section=False,
                auto_code_header=False,
                sections=[
                    Section(
                        kind=SectionKind.DATA,
                        data="0x00",
                    ),
                ],
            ),
            "ef0001 03 0001 00 00",
        ),
        # Custom invalid section
        (
            Container(
                auto_data_section=False,
                auto_type_section=False,
                auto_code_header=False,
                sections=[
                    Section(
                        kind=0xFE,
                        data="0x00",
                    ),
                ],
            ),
            "ef0001 fe 0001 00 00",
        ),
        # Multiple sections
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x0e",
                    ),
                    Section(
                        kind=SectionKind.DATA,
                        data="0x0f",
                    ),
                ],
            ),
            "ef0001 01 0004 02 0001 0001 03 0001 00 00000000 0e 0f",
        ),
        # Multiple type sections
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.TYPE,
                        data="0x00000000",
                    ),
                    Section(
                        kind=SectionKind.TYPE,
                        data="0x00000000",
                    ),
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                    ),
                ],
                auto_type_section=False,
            ),
            """
            ef0001 01 0004 01 0004 02 0001 0001 03 0000 00
            00000000 00000000 00
            """,
        ),
        # Invalid Magic
        (
            Container(
                custom_magic=0xFE,
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                    ),
                ],
            ),
            "effe01 01 0004 02 0001 0001 03 0000 00 00000000 00",
        ),
        # Invalid Version
        (
            Container(
                custom_version=0x02,
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                    ),
                ],
            ),
            "ef0002 01 0004 02 0001 0001 03 0000 00 00000000 00",
        ),
        # Section Invalid size Version
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                        custom_size=0xFFFF,
                    ),
                ],
            ),
            "ef0001 01 0004 02 0001 ffff 03 0000 00 00000000 00",
        ),
        # Nested EOF
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                    ),
                    Section(
                        kind=SectionKind.DATA,
                        data=Container(
                            sections=[
                                Section(
                                    kind=SectionKind.CODE,
                                    data="0x01",
                                )
                            ],
                        ),
                    ),
                ],
            ),
            """
            ef0001 01 0004 02 0001 0001 03 0014 00 00000000 00
            ef0001 01 0004 02 0001 0001 03 0000 00 00000000 01
            """,
        ),
        # Incomplete code section
        (
            Container(
                sections=[
                    Section(
                        custom_size=0x02,
                        kind=SectionKind.CODE,
                        data="0x",
                    ),
                ],
            ),
            "ef0001 01 0004 02 0001 0002 03 0000 00 00000000",
        ),
        # Trailing bytes after code section
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x600000",
                    ),
                ],
                extra=bytes.fromhex("deadbeef"),
            ),
            "ef0001 01 0004 02 0001 0003 03 0000 00 00000000 600000 deadbeef",
        ),
        # Multiple code sections
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x600000",
                    ),
                    Section(
                        kind=SectionKind.CODE,
                        data="0x600000",
                    ),
                ],
                name="multiple_code_sections",
            ),
            """
            ef0001 01 0008 02 0002 0003 0003 03 0000 00
            00000000 00000000
            600000
            600000
            """,
        ),
        # No section terminator
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x600000",
                    ),
                ],
                custom_terminator=bytes(),
            ),
            "ef0001 01 0004 02 0001 0003 03 0000 00000000 600000",
        ),
        # No auto type section
        (
            Container(
                auto_type_section=False,
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                    ),
                ],
            ),
            "ef0001 02 0001 0001 03 0000 00 00",
        ),
        # Data section in types
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                    ),
                    Section(
                        kind=SectionKind.DATA,
                        data="0x00",
                        force_type_listing=True,
                    ),
                ],
            ),
            """
            ef0001 01 0008 02 0001 0001 03 0001 00
            00000000 00000000
            00 00
            """,
        ),
        # Code section inputs
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                        code_inputs=1,
                    ),
                ],
            ),
            """
            ef0001 01 0004 02 0001 0001 03 0000 00
            01000000
            00
            """,
        ),
        # Code section inputs 2
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                        code_inputs=0xFF,
                    ),
                ],
            ),
            """
            ef0001 01 0004 02 0001 0001 03 0000 00
            ff000000
            00
            """,
        ),
        # Code section outputs
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                        code_outputs=1,
                    ),
                ],
            ),
            """
            ef0001 01 0004 02 0001 0001 03 0000 00
            00010000
            00
            """,
        ),
        # Code section outputs 2
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                        code_outputs=0xFF,
                    ),
                ],
            ),
            """
            ef0001 01 0004 02 0001 0001 03 0000 00
            00ff0000
            00
            """,
        ),
        # Code section max stack height
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                        max_stack_height=0x0201,
                    ),
                ],
            ),
            """
            ef0001 01 0004 02 0001 0001 03 0000 00
            00000201
            00
            """,
        ),
        # Code section max stack height 2
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                        max_stack_height=0xFFFF,
                    ),
                ],
            ),
            """
            ef0001 01 0004 02 0001 0001 03 0000 00
            0000FFFF
            00
            """,
        ),
        # Code section max stack height 3
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                        max_stack_height=0xFFFF,
                    ),
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                    ),
                ],
            ),
            """
            ef0001 01 0008 02 0002 0001 0001 03 0000 00
            0000FFFF 00000000
            00
            00
            """,
        ),
        # Custom type section
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.TYPE,
                        data="0x00",
                    ),
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                    ),
                ],
            ),
            "ef0001 01 0001 02 0001 0001 03 0000 00 00 00",
        ),
        (
            Container(
                sections=[
                    Section(
                        kind=SectionKind.TYPE,
                        data="0x0000000000",
                    ),
                    Section(
                        kind=SectionKind.CODE,
                        data="0x00",
                    ),
                ],
                name="eip_4750_single_code_section_oversized_type",
            ),
            "ef0001 01 0005 02 0001 0001 03 0000 00 0000000000 00",
        ),
        # Empty type section
        (
            Container(
                sections=[
                    Section(kind=SectionKind.TYPE, data="0x"),
                    Section(kind=SectionKind.CODE, data="0x00"),
                ],
                auto_type_section=False,
            ),
            "ef0001 01 0000 02 0001 0001 03 0000 00 00",
        ),
    ],
)
def test_eof_v1_assemble(container: Container, hex: str):
    """
    Test `ethereum_test.types.code`.
    """
    assembled_container = container.assemble()
    assert assembled_container == bytes.fromhex(
        hex.replace(" ", "").replace("\n", "")
    )