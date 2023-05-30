import base64
import math
from dataclasses import dataclass
from typing import Sequence, Union, List

from stellar_sdk import (
    MuxedAccount,
    Transaction,
    TransactionEnvelope,
    FeeBumpTransactionEnvelope,
)
from stellar_sdk.memo import *
from stellar_sdk.operation import *
from stellar_sdk.utils import from_xdr_amount

from seedsigner.hardware.buttons import HardwareButtonsConstants
from . import BaseTopNavScreen, ButtonListScreen
from ..components import (
    IconTextLine,
    GUIConstants,
    TextArea,
)

NETWORK_PASSPHRASE_PUBLIC = "Public Global Stellar Network ; September 2015"
NETWORK_PASSPHRASE_TESTNET = "Test SDF Network ; September 2015"


@dataclass
class Item:
    label: str
    content: str
    auto_trim_content: bool = True


@dataclass
class TxDetailsBaseScreen(BaseTopNavScreen):
    def _run(self):
        while True:
            user_input = self.hw_inputs.wait_for(
                HardwareButtonsConstants.ALL_KEYS,
                check_release=True,
                release_keys=HardwareButtonsConstants.KEYS__ANYCLICK,
            )

            with self.renderer.lock:
                if not self.top_nav.is_selected and user_input in [
                    HardwareButtonsConstants.KEY_LEFT,
                ]:
                    self.top_nav.is_selected = True
                    self.top_nav.render_buttons()

                elif self.top_nav.is_selected and user_input in [
                    HardwareButtonsConstants.KEY_DOWN,
                    HardwareButtonsConstants.KEY_RIGHT,
                ]:
                    self.top_nav.is_selected = False
                    self.top_nav.render_buttons()

                elif (
                    self.top_nav.is_selected
                    and user_input in HardwareButtonsConstants.KEYS__ANYCLICK
                ):
                    return self.top_nav.selected_button

                else:
                    return user_input

                # Write the screen updates
                self.renderer.show_image()


@dataclass
class GenericTxDetailsScreen(TxDetailsBaseScreen):
    title: str = None
    items: Sequence[Item] = None

    def __post_init__(self):
        self.title = self.title
        super().__post_init__()

        for i, item in enumerate(self.items):
            if i == 0:
                screen_y = self.top_nav.height + GUIConstants.COMPONENT_PADDING
            else:
                screen_y = (
                    self.components[-1].screen_y
                    + self.components[-1].height
                    + GUIConstants.COMPONENT_PADDING * 2
                )

            content = item.content
            if (
                item.auto_trim_content
                and item.content is not None
                and len(item.content) > 23
                and len(item.content.split()) == 1
            ):
                content = f"{item.content[:10]}...{item.content[-10:]}"

            self.components.append(
                IconTextLine(
                    label_text=item.label,
                    value_text=content,
                    font_name=GUIConstants.FIXED_WIDTH_FONT_NAME,
                    font_size=18,
                    is_text_centered=False,
                    auto_line_break=True,
                    screen_x=GUIConstants.EDGE_PADDING,
                    screen_y=screen_y,
                )
            )


def build_tx_info_screens(
    tx: Transaction, network_passphrase: str
) -> List[GenericTxDetailsScreen]:
    items = []
    # Network
    if network_passphrase == NETWORK_PASSPHRASE_TESTNET:
        network_title = "Network"
        network_content = "Testnet"
    elif network_passphrase == NETWORK_PASSPHRASE_PUBLIC:
        network_title = "Network"
        network_content = "Public"
    else:
        network_title = "Network Passphrase"
        network_content = network_passphrase
    items.append(Item(label=network_title, content=network_content))

    # Max Fee
    items.append(Item(label="Max Fee", content=f"{from_xdr_amount(tx.fee)} XLM"))

    # Memo
    if isinstance(tx.memo, NoneMemo):
        pass
    elif isinstance(tx.memo, TextMemo):
        try:
            if tx.memo.memo_text.decode("utf-8").isascii():
                memo_title = "Text Memo"
                memo_content = tx.memo.memo_text
            else:
                memo_title = "Text Memo (base64)"
                memo_content = base64.b64encode(tx.memo.memo_text).decode("utf-8")
        except UnicodeDecodeError:
            memo_title = "Text Memo (base64)"
            memo_content = base64.b64encode(tx.memo.memo_text).decode("utf-8")
    elif isinstance(tx.memo, IdMemo):
        memo_title = "Id Memo"
        memo_content = str(tx.memo.memo_id)
    elif isinstance(tx.memo, HashMemo):
        memo_title = "Hash Memo"
        memo_content = tx.memo.memo_hash.hex()
    elif isinstance(tx.memo, ReturnHashMemo):
        memo_title = "ReturnHash Memo"
        memo_content = tx.memo.memo_return.hex()
    else:
        raise ValueError(f"Unknown memo type: {type(tx.memo)}")
    if not isinstance(tx.memo, NoneMemo):
        items.append(Item(label=memo_title, content=memo_content))

    # Sequence
    items.append(Item(label="Sequence", content=str(tx.sequence)))

    # Time Bounds
    if tx.preconditions.time_bounds is not None:
        if tx.preconditions.time_bounds.min_time:
            pass
        if tx.preconditions.time_bounds.max_time:
            pass

    # Ledger Bounds
    if tx.preconditions.ledger_bounds is not None:
        if tx.preconditions.ledger_bounds.min_ledger:
            items.append(
                Item(
                    label="Ledger Bounds Min",
                    content=str(tx.preconditions.ledger_bounds.min_ledger),
                )
            )
        if tx.preconditions.ledger_bounds.max_ledger:
            items.append(
                Item(
                    label="Ledger Bounds Max",
                    content=str(tx.preconditions.ledger_bounds.max_ledger),
                )
            )

    # Min Seq Num
    if tx.preconditions.min_sequence_number:
        items.append(
            Item(
                label="Min Sequence Number",
                content=str(tx.preconditions.min_sequence_number),
            )
        )

    # Min Seq Age
    if tx.preconditions.min_sequence_age:
        items.append(
            Item(
                label="Min Sequence Age", content=str(tx.preconditions.min_sequence_age)
            )
        )

    # Min Seq Ledger Gap
    if tx.preconditions.min_sequence_ledger_gap:
        items.append(
            Item(
                label="Min Sequence Ledger Gap",
                content=str(tx.preconditions.min_sequence_ledger_gap),
            )
        )

    # Tx Source
    items.append(Item(label="Tx Source", content=tx.source.universal_account_id))

    item_size = 3
    item_count = len(items)
    screen_count = math.ceil(item_count / item_size)
    screens = []
    for i in range(screen_count):
        screen_items = items[i * item_size : (i + 1) * item_size]
        screens.append(
            GenericTxDetailsScreen(
                title=f"Tx Info {i + 1}/{screen_count}", items=screen_items
            )
        )
    return screens


def build_transaction_screens(
    te: Union[TransactionEnvelope, FeeBumpTransactionEnvelope]
) -> List[GenericTxDetailsScreen]:
    if isinstance(te, FeeBumpTransactionEnvelope):
        raise NotImplementedError(
            "FeeBumpTransactionEnvelope support not implemented yet"
        )

    tx = te.transaction

    if tx.operations is None or len(tx.operations) == 0:
        raise ValueError("Transaction must have at least one operation")

    screens = []
    screens.extend(build_tx_info_screens(tx, te.network_passphrase))

    for i, op in enumerate(tx.operations):
        if isinstance(op, CreateAccount):
            screens.append(
                CreateAccountOperationScreen(op_index=i, op=op, tx_source=tx.source)
            )
        elif isinstance(op, Payment):
            screens.append(
                PaymentOperationScreen(op_index=i, op=op, tx_source=tx.source)
            )
        else:
            raise NotImplementedError(f"Operation type {type(op)} not implemented yet")
    return screens


@dataclass
class CreateAccountOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: CreateAccount = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        send_str = f"{self.op.amount} XLM"

        items = [
            Item(label="Send", content=send_str, auto_trim_content=False),
            Item(label="To", content=self.op.destination),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class PaymentOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: Payment = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        asset_str = "XLM"
        if not self.op.asset.is_native():
            asset_str = f"{self.op.asset.code}({self.op.asset.issuer[-4:]})"

        send_str = f"{self.op.amount} {asset_str}"
        items = [
            Item(label="Send", content=send_str, auto_trim_content=False),
            Item(label="To", content=self.op.destination.universal_account_id),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


def append_op_source_to_items(
    items: List[Item], op_source: MuxedAccount, tx_source: MuxedAccount
):
    if op_source and op_source != tx_source:
        items.append(Item(label="Tx source", content=op_source.universal_account_id))


@dataclass
class SignTxShowAddressScreen(ButtonListScreen):
    address: str = None

    def __post_init__(self):
        self.title = "Sign with"
        self.is_bottom_list = True

        super().__post_init__()

        break_point = 14
        # break every 14 characters
        address_with_break = " ".join(
            [
                self.address[i : i + break_point]
                for i in range(0, len(self.address), break_point)
            ]
        )

        self.components.append(
            TextArea(
                text=address_with_break,
                font_size=GUIConstants.BODY_FONT_MAX_SIZE + 1,
                font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
                screen_y=self.top_nav.height,
                is_text_centered=True,
            )
        )
