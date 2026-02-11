"""
P2P Payment Utilities for Cresca Campus

This module provides helper functions for P2P payments using native Algorand
PaymentTxn and ASA transfers. No smart contract needed - just transaction utilities.

For gasless onboarding, we use Atomic Fee Pooling where a sponsor account
covers the fees for new students.
"""

from algosdk import transaction
from algosdk.v2client import algod
from typing import Optional


def create_payment_txn(
    sender: str,
    receiver: str,
    amount: int,
    algod_client: algod.AlgodClient,
    note: Optional[str] = None,
) -> transaction.PaymentTxn:
    """
    Create a simple ALGO payment transaction.
    
    Args:
        sender: Sender's Algorand address
        receiver: Receiver's Algorand address  
        amount: Amount in microALGOs (1 ALGO = 1,000,000 microALGOs)
        algod_client: Algorand client instance
        note: Optional transaction note
        
    Returns:
        Unsigned PaymentTxn
    """
    params = algod_client.suggested_params()
    
    txn = transaction.PaymentTxn(
        sender=sender,
        sp=params,
        receiver=receiver,
        amt=amount,
        note=note.encode() if note else None,
    )
    
    return txn


def create_sponsored_payment_txn(
    sender: str,
    receiver: str,
    amount: int,
    sponsor: str,
    algod_client: algod.AlgodClient,
    note: Optional[str] = None,
) -> tuple[transaction.PaymentTxn, transaction.PaymentTxn]:
    """
    Create a sponsored (gasless) payment using Atomic Fee Pooling.
    
    The sponsor pays the fees for both transactions, allowing the sender
    to transact with zero ALGO for fees.
    
    Args:
        sender: Sender's Algorand address
        receiver: Receiver's Algorand address
        amount: Amount in microALGOs
        sponsor: Sponsor's address who pays the fees
        algod_client: Algorand client instance
        note: Optional transaction note
        
    Returns:
        Tuple of (sender_txn, sponsor_txn) to be grouped atomically
    """
    params = algod_client.suggested_params()
    min_fee = params.min_fee
    
    # Sender's transaction with fee = 0
    sender_params = params
    sender_params.fee = 0
    sender_params.flat_fee = True
    
    sender_txn = transaction.PaymentTxn(
        sender=sender,
        sp=sender_params,
        receiver=receiver,
        amt=amount,
        note=note.encode() if note else None,
    )
    
    # Sponsor's transaction with fee = 2x min (covers both)
    sponsor_params = algod_client.suggested_params()
    sponsor_params.fee = min_fee * 2
    sponsor_params.flat_fee = True
    
    # Sponsor sends 0 ALGO to themselves (just paying fees)
    sponsor_txn = transaction.PaymentTxn(
        sender=sponsor,
        sp=sponsor_params,
        receiver=sponsor,
        amt=0,
        note=b"cresca-fee-sponsor",
    )
    
    # Group the transactions
    gid = transaction.calculate_group_id([sender_txn, sponsor_txn])
    sender_txn.group = gid
    sponsor_txn.group = gid
    
    return sender_txn, sponsor_txn


def create_asa_transfer_txn(
    sender: str,
    receiver: str,
    asset_id: int,
    amount: int,
    algod_client: algod.AlgodClient,
    note: Optional[str] = None,
) -> transaction.AssetTransferTxn:
    """
    Create an ASA (Algorand Standard Asset) transfer transaction.
    
    Args:
        sender: Sender's Algorand address
        receiver: Receiver's Algorand address
        asset_id: The ASA ID to transfer
        amount: Amount of the asset to transfer
        algod_client: Algorand client instance
        note: Optional transaction note
        
    Returns:
        Unsigned AssetTransferTxn
    """
    params = algod_client.suggested_params()
    
    txn = transaction.AssetTransferTxn(
        sender=sender,
        sp=params,
        receiver=receiver,
        amt=amount,
        index=asset_id,
        note=note.encode() if note else None,
    )
    
    return txn


def create_opt_in_txn(
    account: str,
    asset_id: int,
    algod_client: algod.AlgodClient,
) -> transaction.AssetTransferTxn:
    """
    Create an ASA opt-in transaction.
    
    Required before an account can receive an ASA.
    
    Args:
        account: Account address to opt-in
        asset_id: The ASA ID to opt into
        algod_client: Algorand client instance
        
    Returns:
        Unsigned opt-in AssetTransferTxn
    """
    params = algod_client.suggested_params()
    
    txn = transaction.AssetTransferTxn(
        sender=account,
        sp=params,
        receiver=account,
        amt=0,
        index=asset_id,
    )
    
    return txn


def generate_payment_qr_data(
    receiver: str,
    amount: Optional[int] = None,
    asset_id: Optional[int] = None,
    note: Optional[str] = None,
) -> str:
    """
    Generate data for a payment QR code.
    
    Returns a URI that can be encoded as QR and scanned by Pera Wallet.
    
    Args:
        receiver: Receiver's Algorand address
        amount: Optional amount in microALGOs
        asset_id: Optional ASA ID (for asset transfers)
        note: Optional transaction note
        
    Returns:
        Algorand payment URI string
    """
    uri = f"algorand://{receiver}"
    params = []
    
    if amount:
        params.append(f"amount={amount}")
    if asset_id:
        params.append(f"asset={asset_id}")
    if note:
        params.append(f"note={note}")
    
    if params:
        uri += "?" + "&".join(params)
    
    return uri
