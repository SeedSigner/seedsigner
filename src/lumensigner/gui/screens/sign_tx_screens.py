import base64
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence, Union, List, Tuple
from decimal import Decimal
from stellar_sdk import (
    MuxedAccount,
    Transaction,
    TransactionEnvelope,
    FeeBumpTransactionEnvelope,
    Asset,
    LiquidityPoolAsset,
)
from stellar_sdk.memo import *
from stellar_sdk.operation import *
from stellar_sdk.operation.revoke_sponsorship import RevokeSponsorshipType
from stellar_sdk.utils import from_xdr_amount

from lumensigner.hardware.buttons import HardwareButtonsConstants
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


def build_tx_info_screens(te: TransactionEnvelope) -> List[GenericTxDetailsScreen]:
    tx = te.transaction
    items = []
    # Network
    network_title, network_content = format_network(te.network_passphrase)
    items.append(Item(label=network_title, content=network_content))

    # Max Fee
    items.append(Item(label="Max Fee", content=f"{from_xdr_amount(tx.fee)} XLM"))

    # Memo
    if isinstance(tx.memo, NoneMemo):
        memo_title = "None Memo"
        memo_content = "[Empty]"
    elif isinstance(tx.memo, TextMemo):
        try:
            if tx.memo.memo_text.decode("utf-8").isascii():
                memo_title = "Text Memo"
                memo_content = tx.memo.memo_text.decode("utf-8")
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

    if tx.preconditions is not None:
        # Time Bounds
        if tx.preconditions.time_bounds is not None:
            if tx.preconditions.time_bounds.min_time:
                items.append(
                    Item(
                        label="Valid After (UTC)",
                        content=timestamp_to_utc(tx.preconditions.time_bounds.min_time),
                    )
                )
            if tx.preconditions.time_bounds.max_time:
                items.append(
                    Item(
                        label="Valid Before (UTC)",
                        content=timestamp_to_utc(tx.preconditions.time_bounds.max_time),
                    )
                )

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
                    label="Min Sequence Age",
                    content=str(tx.preconditions.min_sequence_age),
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
    items.append(
        Item(label="Transaction Source", content=tx.source.universal_account_id)
    )

    items.append(Item(label="Transaction Hash", content=te.hash_hex()))

    item_size = 4
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


@dataclass
class CreateAccountOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: CreateAccount = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        send_str = f"{self.op.starting_balance} XLM"

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
        asset_str = format_asset(self.op.asset)

        send_str = f"{self.op.amount} {asset_str}"
        items = [
            Item(label="Send", content=send_str, auto_trim_content=False),
            Item(label="To", content=self.op.destination.universal_account_id),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class PathPaymentStrictReceiveOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: PathPaymentStrictReceive = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        send_asset_str = format_asset(self.op.send_asset)
        send_str = f"{self.op.send_max} {send_asset_str}"

        items = [
            Item(label="Path Pay At Most", content=send_str, auto_trim_content=False),
            Item(label="To", content=self.op.destination.universal_account_id),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class PathPaymentStrictSendOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: PathPaymentStrictSend = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        send_asset_str = format_asset(self.op.send_asset)
        send_str = f"{self.op.send_amount} {send_asset_str}"

        items = [
            Item(label="Path Pay", content=send_str, auto_trim_content=False),
            Item(label="To", content=self.op.destination.universal_account_id),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class ManageSellOfferOperationScreenPage1(GenericTxDetailsScreen):
    op_index: int = None
    op: ManageSellOffer = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        if self.op.offer_id == 0:
            op_type = "Create Offer"
        else:
            if Decimal(self.op.amount) == 0:
                op_type = f"Delete Offer #{self.op.offer_id}"
            else:
                op_type = f"Update Offer #{self.op.offer_id}"

        sell_asset_str = format_asset(self.op.selling)
        sell_str = f"{self.op.amount} {sell_asset_str}"
        buy_asset_str = format_asset(self.op.buying)

        items = [
            Item(label="Operation Type", content=op_type),
            Item(label="Selling", content=sell_str, auto_trim_content=False),
            Item(label="Buying", content=buy_asset_str, auto_trim_content=False),
        ]

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class ManageSellOfferOperationScreenPage2(GenericTxDetailsScreen):
    op_index: int = None
    op: ManageSellOffer = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        price = Decimal(self.op.price.n) / Decimal(self.op.price.d)
        price_str = f"{price} {format_asset(self.op.buying, include_issuer=False)}/{format_asset(self.op.selling, include_issuer=False)}"

        items = [
            Item(label="Price", content=price_str, auto_trim_content=False),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class ManageBuyOfferOperationScreenPage1(GenericTxDetailsScreen):
    op_index: int = None
    op: ManageBuyOffer = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        if self.op.offer_id == 0:
            op_type = "Create Offer"
        else:
            if Decimal(self.op.amount) == 0:
                op_type = f"Delete Offer #{self.op.offer_id}"
            else:
                op_type = f"Update Offer #{self.op.offer_id}"

        buy_asset_str = format_asset(self.op.buying)
        buy_str = f"{self.op.amount} {buy_asset_str}"
        sell_asset_str = format_asset(self.op.selling)

        items = [
            Item(label="Operation Type", content=op_type),
            Item(label="Buying", content=buy_str, auto_trim_content=False),
            Item(label="Selling", content=sell_asset_str, auto_trim_content=False),
        ]

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class ManageBuyOfferOperationScreenPage2(GenericTxDetailsScreen):
    op_index: int = None
    op: ManageBuyOffer = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        price = Decimal(self.op.price.n) / Decimal(self.op.price.d)
        price_str = f"{price} {format_asset(self.op.selling, include_issuer=False)}/{format_asset(self.op.buying, include_issuer=False)}"

        items = [
            Item(label="Price", content=price_str, auto_trim_content=False),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class CreatePassiveSellOfferOperationScreenPage1(GenericTxDetailsScreen):
    op_index: int = None
    op: CreatePassiveSellOffer = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        op_type = "Create Passive Offer"
        sell_asset_str = format_asset(self.op.selling)
        sell_str = f"{self.op.amount} {sell_asset_str}"
        buy_asset_str = format_asset(self.op.buying)

        items = [
            Item(label="Operation Type", content=op_type),
            Item(label="Selling", content=sell_str, auto_trim_content=False),
            Item(label="Buying", content=buy_asset_str, auto_trim_content=False),
        ]

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class CreatePassiveSellOfferOperationScreenPage2(GenericTxDetailsScreen):
    op_index: int = None
    op: CreatePassiveSellOffer = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        price = Decimal(self.op.price.n) / Decimal(self.op.price.d)
        price_str = f"{price} {format_asset(self.op.buying, include_issuer=False)}/{format_asset(self.op.selling, include_issuer=False)}"

        items = [
            Item(label="Price", content=price_str, auto_trim_content=False),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class ChangeTrustOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: ChangeTrust = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        if Decimal(self.op.limit) == 0:
            op_type = "Delete Trustline"
            if isinstance(self.op.asset, LiquidityPoolAsset):
                line = f"{self.op.asset.liquidity_pool_id}"
            else:
                line = f"{format_asset(self.op.asset)}"
        else:
            op_type = "Add Trustline"
            if isinstance(self.op.asset, LiquidityPoolAsset):
                # TODO: check if this is correct
                line = f"{self.op.limit} {self.op.asset.liquidity_pool_id}"
            else:
                line = f"{self.op.limit} {format_asset(self.op.asset)}"

        items = [
            Item(label="Operation Type", content=op_type),
            Item(label="Trustline", content=line, auto_trim_content=False),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class AccountMergeOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: AccountMerge = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(label="Operation Type", content="Merge Account"),
            Item(
                label="Send All XLM To",
                content=self.op.destination.universal_account_id,
            ),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class AllowTrustOperationScreenPage1(GenericTxDetailsScreen):
    op_index: int = None
    op: AllowTrust = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(label="Operation Type", content="Allow Trust"),
            Item(label="Asset Code", content=self.op.asset_code),
            Item(label="Trustor", content=self.op.trustor),
        ]
        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class AllowTrustOperationScreenPage2(GenericTxDetailsScreen):
    op_index: int = None
    op: AllowTrust = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(label="Authorize", content=str(self.op.authorize.name)),
        ]
        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class ManageDataOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: ManageData = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        op_type = "Set Data" if self.op.data_value is not None else "Remove Data"
        key = self.op.data_name
        items = [
            Item(label="Operation Type", content=op_type),
            Item(label="Data Name", content=key),
        ]

        if self.op.data_value is not None:
            try:
                if self.op.data_value.decode("utf-8").isascii():
                    title = "Data Value"
                    value = self.op.data_value.decode("utf-8")
                else:
                    title = "Data Value (base64)"
                    value = base64.b64encode(self.op.data_value).decode("utf-8")
            except UnicodeDecodeError:
                title = "Data Value (base64)"
                value = base64.b64encode(self.op.data_value).decode("utf-8")
            items.append(Item(label=title, content=value, auto_trim_content=True))

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class InflationOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: Inflation = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(label="Operation Type", content="Inflation"),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class BumpSequenceOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: BumpSequence = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(label="Operation Type", content="Bump Sequence"),
            Item(label="Bump To", content=str(self.op.bump_to)),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class CreateClaimableBalanceOperationScreenPage1(GenericTxDetailsScreen):
    op_index: int = None
    op: CreateClaimableBalance = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(label="Operation Type", content="Create Claimable Balance"),
            Item(
                label="WARNING",
                content="Currently does not support displaying claimant details",
            ),
        ]

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class CreateClaimableBalanceOperationScreenPage2(GenericTxDetailsScreen):
    op_index: int = None
    op: CreateClaimableBalance = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        balance = f"{self.op.amount} {format_asset(self.op.asset)}"
        items = [
            Item(label="Balance", content=balance),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class BeginSponsoringFutureReservesOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: BeginSponsoringFutureReserves = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(label="Operation Type", content="Begin Sponsoring Future Reserves"),
            Item(label="Sponsored ID", content=self.op.sponsored_id),
        ]
        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class EndSponsoringFutureReservesOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: EndSponsoringFutureReserves = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(label="Operation Type", content="End Sponsoring Future Reserves"),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class ClaimClaimableBalanceOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: ClaimClaimableBalance = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        Item(label="Operation Type", content="Claim Claimable Balance"),
        Item(label="Balance ID", content=self.op.balance_id),
        items = [
            Item(label="Operation Type", content="Claim Claimable Balance"),
            Item(label="Balance ID", content=self.op.balance_id),
        ]
        append_op_source_to_items(items, self.op.source, self.tx_source)

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class RevokeSponsorshipOperationScreenPage1(GenericTxDetailsScreen):
    op_index: int = None
    op: RevokeSponsorship = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        if self.op.revoke_sponsorship_type == RevokeSponsorshipType.ACCOUNT:
            items = [
                Item(label="Operation Type", content="Revoke Account Sponsorship"),
                Item(label="Account ID", content=self.op.account_id),
            ]
        elif self.op.revoke_sponsorship_type == RevokeSponsorshipType.TRUSTLINE:
            if isinstance(self.op.trustline.asset, LiquidityPoolAsset):
                asset = self.op.trustline.asset.liquidity_pool_id
            else:
                asset = format_asset(self.op.trustline.asset)
            items = [
                Item(label="Operation Type", content="Revoke Trustline Sponsorship"),
                Item(label="Account ID", content=self.op.trustline.account_id),
                Item(label="Asset", content=asset),
            ]
        elif self.op.revoke_sponsorship_type == RevokeSponsorshipType.OFFER:
            items = [
                Item(label="Operation Type", content="Revoke Offer Sponsorship"),
                Item(label="Seller ID", content=str(self.op.offer.seller_id)),
                Item(label="Offer ID", content=str(self.op.offer.offer_id)),
            ]
        elif self.op.revoke_sponsorship_type == RevokeSponsorshipType.DATA:
            items = [
                Item(label="Operation Type", content="Revoke Data Sponsorship"),
                Item(label="Seller ID", content=str(self.op.offer.seller_id)),
                Item(label="Offer ID", content=str(self.op.offer.offer_id)),
            ]
        elif self.op.revoke_sponsorship_type == RevokeSponsorshipType.CLAIMABLE_BALANCE:
            items = [
                Item(
                    label="Operation Type",
                    content="Revoke Claimable Balance Sponsorship",
                ),
                Item(label="Balance ID", content=self.op.claimable_balance_id),
            ]
        elif self.op.revoke_sponsorship_type == RevokeSponsorshipType.SIGNER:
            items = [
                Item(label="Operation Type", content="Revoke Signer Sponsorship"),
                Item(label="Account ID", content=self.op.signer.account_id),
                Item(
                    label="Signer", content=self.op.signer.signer_key.encoded_signer_key
                ),
            ]
        elif self.op.revoke_sponsorship_type == RevokeSponsorshipType.LIQUIDITY_POOL:
            items = [
                Item(
                    label="Operation Type", content="Revoke Liquidity Pool Sponsorship"
                ),
                Item(label="Liquidity Pool ID", content=self.op.liquidity_pool_id),
            ]
        else:
            raise ValueError(
                f"Unknown revoke sponsorship type: {self.op.revoke_sponsorship_type}"
            )

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class RevokeSponsorshipOperationScreenPage2(GenericTxDetailsScreen):
    # Source only
    op_index: int = None
    op: RevokeSponsorship = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = []
        append_op_source_to_items(items, self.op.source, self.tx_source)
        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class ClawbackOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: Clawback = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(
                label="Clawback",
                content=f"{self.op.amount} {format_asset(self.op.asset)}",
            ),
            Item(label="From", content=self.op.from_.account_id),
        ]
        append_op_source_to_items(items, self.op.source, self.tx_source)
        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class ClawbackClaimableBalanceOperationScreen(GenericTxDetailsScreen):
    op_index: int = None
    op: ClawbackClaimableBalance = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(label="Operation Type", content="Clawback Claimable Balance"),
            Item(label="Balance ID", content=self.op.balance_id),
        ]
        append_op_source_to_items(items, self.op.source, self.tx_source)
        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class SetTrustLineFlagsOperationScreenPage1(GenericTxDetailsScreen):
    op_index: int = None
    op: SetTrustLineFlags = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(label="Operation Type", content="Set Trustline Flags"),
            Item(label="Trustor", content=self.op.trustor),
            Item(label="Asset", content=format_asset(asset=self.op.asset)),
        ]
        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class SetTrustLineFlagsOperationScreenPage2(GenericTxDetailsScreen):
    op_index: int = None
    op: SetTrustLineFlags = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        clear_flags: List[str] = [
            f.name for f in TrustLineFlags if f in self.op.clear_flags
        ]
        clear_flags_str = "| ".join(clear_flags) if clear_flags else "[Not Set]"

        set_flags: List[str] = [
            f.name for f in TrustLineFlags if f in self.op.set_flags
        ]
        set_flags_str = "| ".join(set_flags) if set_flags else "[Not Set]"

        items = [
            Item(label="Clear Flags", content=clear_flags_str),
            Item(label="Set Flags", content=set_flags_str),
        ]
        append_op_source_to_items(items, self.op.source, self.tx_source)
        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class LiquidityPoolDepositOperationScreenPage1(GenericTxDetailsScreen):
    op_index: int = None
    op: LiquidityPoolDeposit = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(label="Operation Type", content="Liquidity Pool Deposit"),
            Item(label="Liquidity Pool ID", content=self.op.liquidity_pool_id),
            Item(label="Max Amount A", content=self.op.max_amount_a),
        ]

        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class LiquidityPoolDepositOperationScreenPage2(GenericTxDetailsScreen):
    op_index: int = None
    op: LiquidityPoolDeposit = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(label="Max Amount B", content=self.op.max_amount_b),
            Item(
                label="Min Price",
                content=f"{self.op.min_price.n / self.op.min_price.d:.7f}",
            ),
            Item(
                label="Max Price",
                content=f"{self.op.max_price.n / self.op.max_price.d:.7f}",
            ),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)
        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class LiquidityPoolWithdrawOperationScreenPage1(GenericTxDetailsScreen):
    op_index: int = None
    op: LiquidityPoolWithdraw = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(label="Operation Type", content="Liquidity Pool Withdraw"),
            Item(label="Liquidity Pool ID", content=self.op.liquidity_pool_id),
            Item(label="Amount", content=self.op.amount),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)
        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


@dataclass
class LiquidityPoolWithdrawOperationScreenPage2(GenericTxDetailsScreen):
    op_index: int = None
    op: LiquidityPoolWithdraw = None
    tx_source: MuxedAccount = None

    def __post_init__(self):
        items = [
            Item(label="Min Amount A", content=self.op.min_amount_a),
            Item(label="Min Amount B", content=self.op.min_amount_b),
        ]

        append_op_source_to_items(items, self.op.source, self.tx_source)
        self.title = f"Operation {self.op_index + 1}"
        self.items = items
        super().__post_init__()


def build_set_options_screens(
    op_index: int, op: SetOptions, tx_source: MuxedAccount
) -> List[GenericTxDetailsScreen]:
    items = [Item(label="Operation Type", content="Set Options")]
    if op.inflation_dest:
        items.append(Item(label="Inflation Destination", content=op.inflation_dest))
    if op.clear_flags:
        clear_flags: List[str] = [
            f.name for f in AuthorizationFlag if f in op.clear_flags
        ]

        items.append(Item(label="Clear Flags", content="| ".join(clear_flags)))
    if op.set_flags:
        set_flags: List[str] = [f.name for f in AuthorizationFlag if f in op.set_flags]

        items.append(Item(label="Set Flags", content="| ".join(set_flags)))
    if op.master_weight is not None:
        items.append(Item(label="Master Weight", content=str(op.master_weight)))
    if op.low_threshold is not None:
        items.append(Item(label="Low Threshold", content=str(op.low_threshold)))
    if op.med_threshold is not None:
        items.append(Item(label="Medium Threshold", content=str(op.med_threshold)))
    if op.high_threshold is not None:
        items.append(Item(label="High Threshold", content=str(op.high_threshold)))
    if op.home_domain is not None:
        items.append(Item(label="Home Domain", content=op.home_domain))
    if op.signer:
        if op.signer.weight == 0:
            items.append(
                Item(
                    label="Remove Signer",
                    content=op.signer.signer_key.encoded_signer_key,
                )
            )
        else:
            items.append(
                Item(
                    label="Add Signer", content=op.signer.signer_key.encoded_signer_key
                )
            )
            items.append(Item(label="Signer Weight", content=str(op.signer.weight)))

    append_op_source_to_items(items, op.source, tx_source)

    item_size = 3
    item_count = len(items)
    screen_count = math.ceil(item_count / item_size)
    screens = []
    for i in range(screen_count):
        screen_items = items[i * item_size : (i + 1) * item_size]
        screens.append(
            GenericTxDetailsScreen(
                title=f"Operation {op_index + 1}", items=screen_items
            )
        )
    return screens


def append_op_source_to_items(
    items: List[Item], op_source: MuxedAccount, tx_source: MuxedAccount
):
    if op_source and op_source != tx_source:
        items.append(
            Item(label="Operation Source", content=op_source.universal_account_id)
        )


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


def format_asset(asset: Asset, include_issuer: bool = True) -> str:
    if asset.is_native():
        return "XLM"
    else:
        if include_issuer:
            return f"{asset.code}({asset.issuer[-4:]})"
        else:
            return asset.code


def timestamp_to_utc(timestamp: int) -> str:
    return datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class FeeBumpTransactionScreen(GenericTxDetailsScreen):
    te: FeeBumpTransactionEnvelope = None

    def __post_init__(self):
        tx = self.te.transaction
        network_title, network_content = format_network(self.te.network_passphrase)
        max_fee = tx.base_fee * (
            len(tx.inner_transaction_envelope.transaction.operations) + 1
        )
        items = [
            Item(label=network_title, content=network_content),
            Item(label="Max Fee", content=f"{from_xdr_amount(max_fee)} XLM"),
            Item(label="Fee Source", content=tx.fee_source.universal_account_id),
            Item(
                label="Inner Transaction Hash",
                content=tx.inner_transaction_envelope.hash_hex(),
            ),
        ]
        self.items = items
        self.title = "Fee Bump Tx"
        super().__post_init__()


def build_transaction_screens(
    te: Union[TransactionEnvelope, FeeBumpTransactionEnvelope]
) -> List[GenericTxDetailsScreen]:
    if isinstance(te, FeeBumpTransactionEnvelope):
        return [FeeBumpTransactionScreen(te=te)]

    tx = te.transaction

    if tx.operations is None or len(tx.operations) == 0:
        raise ValueError("Transaction must have at least one operation")

    screens = []
    screens.extend(build_tx_info_screens(te))

    for i, op in enumerate(tx.operations):
        if isinstance(op, CreateAccount):
            screens.append(
                CreateAccountOperationScreen(op_index=i, op=op, tx_source=tx.source)
            )
        elif isinstance(op, Payment):
            screens.append(
                PaymentOperationScreen(op_index=i, op=op, tx_source=tx.source)
            )
        elif isinstance(op, PathPaymentStrictReceive):
            screens.append(
                PathPaymentStrictReceiveOperationScreen(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
        elif isinstance(op, ManageSellOffer):
            screens.append(
                ManageSellOfferOperationScreenPage1(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
            screens.append(
                ManageSellOfferOperationScreenPage2(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
        elif isinstance(op, CreatePassiveSellOffer):
            screens.append(
                CreatePassiveSellOfferOperationScreenPage1(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
            screens.append(
                CreatePassiveSellOfferOperationScreenPage2(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
        elif isinstance(op, SetOptions):
            screens.extend(build_set_options_screens(i, op, tx_source=tx.source))
        elif isinstance(op, ChangeTrust):
            screens.append(
                ChangeTrustOperationScreen(op_index=i, op=op, tx_source=tx.source)
            )
        elif isinstance(op, AllowTrust):
            screens.append(
                AllowTrustOperationScreenPage1(op_index=i, op=op, tx_source=tx.source)
            )
            screens.append(
                AllowTrustOperationScreenPage2(op_index=i, op=op, tx_source=tx.source)
            )
        elif isinstance(op, AccountMerge):
            screens.append(
                AccountMergeOperationScreen(op_index=i, op=op, tx_source=tx.source)
            )
        elif isinstance(op, Inflation):
            screens.append(
                InflationOperationScreen(op_index=i, op=op, tx_source=tx.source)
            )
        elif isinstance(op, ManageData):
            screens.append(
                ManageDataOperationScreen(op_index=i, op=op, tx_source=tx.source)
            )
        elif isinstance(op, BumpSequence):
            screens.append(
                BumpSequenceOperationScreen(op_index=i, op=op, tx_source=tx.source)
            )
        elif isinstance(op, ManageBuyOffer):
            screens.append(
                ManageBuyOfferOperationScreenPage1(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
            screens.append(
                ManageBuyOfferOperationScreenPage2(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
        elif isinstance(op, PathPaymentStrictSend):
            screens.append(
                PathPaymentStrictSendOperationScreen(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
        elif isinstance(op, CreateClaimableBalance):
            screens.append(
                CreateClaimableBalanceOperationScreenPage1(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
            screens.append(
                CreateClaimableBalanceOperationScreenPage2(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
        elif isinstance(op, ClaimClaimableBalance):
            screens.append(
                ClaimClaimableBalanceOperationScreen(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
        elif isinstance(op, BeginSponsoringFutureReserves):
            screens.append(
                BeginSponsoringFutureReservesOperationScreen(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
        elif isinstance(op, EndSponsoringFutureReserves):
            screens.append(
                EndSponsoringFutureReservesOperationScreen(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
        elif isinstance(op, RevokeSponsorship):
            screens.append(
                RevokeSponsorshipOperationScreenPage1(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
            if op.source and op.source != tx.source:
                screens.append(
                    RevokeSponsorshipOperationScreenPage2(
                        op_index=i, op=op, tx_source=tx.source
                    )
                )  # source only
        elif isinstance(op, Clawback):
            screens.append(
                ClawbackOperationScreen(op_index=i, op=op, tx_source=tx.source)
            )
        elif isinstance(op, ClawbackClaimableBalance):
            screens.append(
                ClawbackClaimableBalanceOperationScreen(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
        elif isinstance(op, SetTrustLineFlags):
            screens.append(
                SetTrustLineFlagsOperationScreenPage1(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
            screens.append(
                SetTrustLineFlagsOperationScreenPage2(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
        elif isinstance(op, LiquidityPoolDeposit):
            screens.append(
                LiquidityPoolDepositOperationScreenPage1(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
            screens.append(
                LiquidityPoolDepositOperationScreenPage2(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
        elif isinstance(op, LiquidityPoolWithdraw):
            screens.append(
                LiquidityPoolWithdrawOperationScreenPage1(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
            screens.append(
                LiquidityPoolWithdrawOperationScreenPage2(
                    op_index=i, op=op, tx_source=tx.source
                )
            )
        else:
            raise NotImplementedError(f"Operation type {type(op)} not implemented yet")
    return screens


def format_network(network_passphrase: str) -> Tuple[str, str]:
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
    return network_title, network_content
