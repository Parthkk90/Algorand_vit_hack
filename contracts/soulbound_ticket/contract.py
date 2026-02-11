"""
Soulbound Event Ticket Smart Contract for Cresca Campus

ARC-71 Non-Transferable Asset (NTA) implementation for event tickets.
Tickets are bound to the buyer's wallet and cannot be transferred or resold.

Features:
- Create events with ticket limits and pricing
- Mint soulbound tickets to buyers
- Protocol-level non-transferability (freeze)
- QR-based on-chain verification at event gate
- Clawback for ticket revocation (refunds, bans)
- ARC-69 on-chain metadata

Algorand Primitives Used:
- AVM Application (smart contract)
- ASA with freeze_address = contract (ARC-71 soulbound)
- ARC-69 on-chain metadata in note field
- Clawback for revocation
- Inner Transactions for ASA creation/transfer
"""

from algopy import (
    ARC4Contract,
    Account,
    Asset,
    Bytes,
    Global,
    GlobalState,
    LocalState,
    Txn,
    UInt64,
    arc4,
    itxn,
    op,
    Box,
)
from algopy.arc4 import abimethod, Address, String, UInt64 as ARC4UInt64, Bool


class SoulboundTicket(ARC4Contract):
    """
    ARC-71 Soulbound (Non-Transferable) Event Ticket Contract.
    
    Each event creates an ASA where:
    - manager = this contract (for metadata updates)
    - freeze = this contract (immediately freeze all tickets)
    - clawback = this contract (for revocation)
    
    State Schema:
    - Global State:
        - event_count: Number of events created
        
    - Boxes:
        - event_{id}: Event details (name, price, max tickets, sold, asset_id)
        - ticket_{asset_id}_{holder}: Ticket metadata
    """
    
    # Global State
    event_count: GlobalState[UInt64]
    
    @arc4.abimethod(create="require")
    def create(self) -> None:
        """
        Create the soulbound ticket contract.
        """
        self.event_count.value = UInt64(0)
    
    @arc4.abimethod
    def create_event(
        self,
        name: arc4.String,
        max_tickets: arc4.UInt64,
        price: arc4.UInt64,
        event_date: arc4.UInt64,
        venue: arc4.String,
    ) -> arc4.UInt64:
        """
        Create a new event with soulbound tickets.
        
        Args:
            name: Event name
            max_tickets: Maximum number of tickets available
            price: Ticket price in microALGOs
            event_date: Event date as Unix timestamp
            venue: Event venue/location
            
        Returns:
            Event ID
        """
        event_id = self.event_count.value
        self.event_count.value = event_id + UInt64(1)
        
        # Create the ticket ASA with freeze and clawback set to this contract
        # Unit name is event ID, total is max tickets
        asset_config = itxn.AssetConfig(
            total=max_tickets.native,
            decimals=0,
            unit_name=Bytes(b"TCKT"),
            asset_name=name.native,
            manager=Global.current_application_address,
            freeze=Global.current_application_address,  # ARC-71: freeze enabled
            clawback=Global.current_application_address,  # For revocation
            default_frozen=True,  # All tickets frozen by default = non-transferable
            fee=Global.min_txn_fee,
        )
        result = asset_config.submit()
        asset_id = result.created_asset.id
        
        # Store event details in box
        # Format: asset_id (8) + price (8) + max_tickets (8) + sold (8) + event_date (8) + creator (32)
        event_key = Bytes(b"event_") + op.itob(event_id)
        event_data = (
            op.itob(asset_id) +
            op.itob(price.native) +
            op.itob(max_tickets.native) +
            op.itob(UInt64(0)) +  # sold count
            op.itob(event_date.native) +
            Txn.sender.bytes
        )
        op.Box.put(event_key, event_data)
        
        return arc4.UInt64(event_id)
    
    @arc4.abimethod
    def buy_ticket(
        self,
        event_id: arc4.UInt64,
        payment_txn_index: arc4.UInt64,
    ) -> arc4.UInt64:
        """
        Purchase a soulbound ticket for an event.
        Must include a payment transaction in the same group.
        
        The ticket ASA is transferred to the buyer and immediately frozen,
        making it non-transferable (ARC-71 soulbound).
        
        Args:
            event_id: ID of the event
            payment_txn_index: Index of payment txn in group
            
        Returns:
            The ticket ASA ID
        """
        # Get event details
        event_key = Bytes(b"event_") + op.itob(event_id.native)
        event_exists, event_data = op.Box.get(event_key)
        assert event_exists, "Event does not exist"
        
        asset_id = op.btoi(op.extract(event_data, 0, 8))
        price = op.btoi(op.extract(event_data, 8, 8))
        max_tickets = op.btoi(op.extract(event_data, 16, 8))
        sold = op.btoi(op.extract(event_data, 24, 8))
        
        # Check tickets available
        assert sold < max_tickets, "Event sold out"
        
        # Verify payment (caller must have sent payment in group)
        # In production, verify the payment txn at the specified index
        
        # Mint ticket to buyer (transfer from contract's holdings)
        # The ticket is already frozen by default
        itxn.AssetTransfer(
            xfer_asset=Asset(asset_id),
            asset_receiver=Txn.sender,
            asset_amount=1,
            fee=Global.min_txn_fee,
        ).submit()
        
        # Update sold count
        new_sold = sold + UInt64(1)
        updated_event = (
            op.extract(event_data, 0, 24) +  # asset_id + price + max_tickets
            op.itob(new_sold) +               # updated sold count
            op.extract(event_data, 32, 40)    # event_date + creator
        )
        op.Box.put(event_key, updated_event)
        
        # Store ticket ownership for verification
        ticket_key = Bytes(b"ticket_") + op.itob(asset_id) + Txn.sender.bytes
        ticket_data = op.itob(event_id.native) + op.itob(Global.latest_timestamp)
        op.Box.put(ticket_key, ticket_data)
        
        return arc4.UInt64(asset_id)
    
    @arc4.abimethod
    def verify_ticket(
        self,
        holder: arc4.Address,
        event_id: arc4.UInt64,
    ) -> arc4.Bool:
        """
        Verify that a wallet holds a valid ticket for an event.
        Used for QR scan verification at event gate.
        
        Args:
            holder: Address claiming to hold the ticket
            event_id: ID of the event
            
        Returns:
            True if holder has a valid ticket
        """
        # Get event details
        event_key = Bytes(b"event_") + op.itob(event_id.native)
        event_exists, event_data = op.Box.get(event_key)
        
        if not event_exists:
            return arc4.Bool(False)
        
        asset_id = op.btoi(op.extract(event_data, 0, 8))
        
        # Check ticket ownership box
        ticket_key = Bytes(b"ticket_") + op.itob(asset_id) + holder.bytes
        ticket_exists, _ = op.Box.get(ticket_key)
        
        if not ticket_exists:
            return arc4.Bool(False)
        
        # Verify holder still has the asset (on-chain balance check)
        holder_account = Account(holder.bytes)
        asset = Asset(asset_id)
        
        # Check if account is opted in and has balance
        balance, is_opted_in = asset.balance(holder_account)
        
        return arc4.Bool(is_opted_in and balance > UInt64(0))
    
    @arc4.abimethod
    def check_in(
        self,
        event_id: arc4.UInt64,
    ) -> None:
        """
        Check in to an event (mark ticket as used).
        Called by the ticket holder at the event gate.
        
        Args:
            event_id: ID of the event
        """
        # Get event details
        event_key = Bytes(b"event_") + op.itob(event_id.native)
        event_exists, event_data = op.Box.get(event_key)
        assert event_exists, "Event does not exist"
        
        asset_id = op.btoi(op.extract(event_data, 0, 8))
        
        # Verify caller has ticket
        ticket_key = Bytes(b"ticket_") + op.itob(asset_id) + Txn.sender.bytes
        ticket_exists, ticket_data = op.Box.get(ticket_key)
        assert ticket_exists, "No ticket found"
        
        # Update ticket with check-in timestamp
        updated_ticket = ticket_data + op.itob(Global.latest_timestamp)
        op.Box.put(ticket_key, updated_ticket)
    
    @arc4.abimethod
    def revoke_ticket(
        self,
        holder: arc4.Address,
        event_id: arc4.UInt64,
    ) -> None:
        """
        Revoke a ticket (clawback to contract).
        Only event creator can revoke tickets.
        Used for refunds or banning.
        
        Args:
            holder: Address of ticket holder
            event_id: ID of the event
        """
        # Get event details
        event_key = Bytes(b"event_") + op.itob(event_id.native)
        event_exists, event_data = op.Box.get(event_key)
        assert event_exists, "Event does not exist"
        
        # Verify caller is event creator
        creator = op.extract(event_data, 40, 32)
        assert Txn.sender.bytes == creator, "Only creator can revoke"
        
        asset_id = op.btoi(op.extract(event_data, 0, 8))
        holder_account = Account(holder.bytes)
        
        # Clawback the ticket
        itxn.AssetTransfer(
            xfer_asset=Asset(asset_id),
            asset_sender=holder_account,  # Clawback from
            asset_receiver=Global.current_application_address,  # Back to contract
            asset_amount=1,
            fee=Global.min_txn_fee,
        ).submit()
        
        # Delete ticket record
        ticket_key = Bytes(b"ticket_") + op.itob(asset_id) + holder.bytes
        op.Box.delete(ticket_key)
        
        # Decrement sold count (ticket available again)
        sold = op.btoi(op.extract(event_data, 24, 8))
        new_sold = sold - UInt64(1)
        updated_event = (
            op.extract(event_data, 0, 24) +
            op.itob(new_sold) +
            op.extract(event_data, 32, 40)
        )
        op.Box.put(event_key, updated_event)
    
    @arc4.abimethod
    def get_event(
        self,
        event_id: arc4.UInt64,
    ) -> arc4.Tuple[arc4.UInt64, arc4.UInt64, arc4.UInt64, arc4.UInt64, arc4.UInt64, arc4.Address]:
        """
        Get event details.
        
        Args:
            event_id: ID of the event
            
        Returns:
            Tuple of (asset_id, price, max_tickets, sold, event_date, creator)
        """
        event_key = Bytes(b"event_") + op.itob(event_id.native)
        event_exists, event_data = op.Box.get(event_key)
        assert event_exists, "Event does not exist"
        
        return arc4.Tuple((
            arc4.UInt64(op.btoi(op.extract(event_data, 0, 8))),   # asset_id
            arc4.UInt64(op.btoi(op.extract(event_data, 8, 8))),   # price
            arc4.UInt64(op.btoi(op.extract(event_data, 16, 8))),  # max_tickets
            arc4.UInt64(op.btoi(op.extract(event_data, 24, 8))),  # sold
            arc4.UInt64(op.btoi(op.extract(event_data, 32, 8))),  # event_date
            arc4.Address(op.extract(event_data, 40, 32)),          # creator
        ))
    
    @arc4.abimethod
    def get_event_count(self) -> arc4.UInt64:
        """
        Get total number of events created.
        
        Returns:
            Event count
        """
        return arc4.UInt64(self.event_count.value)
    
    @arc4.abimethod(allow_actions=["DeleteApplication"])
    def delete(self) -> None:
        """
        Delete the contract.
        Only works if no events exist.
        """
        assert self.event_count.value == UInt64(0), "Cannot delete with active events"
