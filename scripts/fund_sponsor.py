"""
Fund Sponsor Wallet Script

This script sets up a sponsor wallet for fee pooling (gasless transactions).
The sponsor wallet will pay fees for new students who have zero ALGO.

Usage:
    python scripts/fund_sponsor.py --amount 10

This will fund the sponsor wallet with 10 ALGO for fee sponsorship.
"""

import os
import argparse
from dotenv import load_dotenv
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod

load_dotenv()


def get_algod_client() -> algod.AlgodClient:
    """Create Algorand client from environment variables."""
    server = os.getenv("ALGOD_SERVER", "http://localhost:4001")
    token = os.getenv("ALGOD_TOKEN", "a" * 64)
    return algod.AlgodClient(token, server)


def create_or_load_sponsor() -> tuple[str, str]:
    """
    Create a new sponsor wallet or load existing from environment.
    
    Returns:
        Tuple of (private_key, address)
    """
    sponsor_mnemonic = os.getenv("SPONSOR_MNEMONIC")
    
    if sponsor_mnemonic:
        private_key = mnemonic.to_private_key(sponsor_mnemonic)
        address = account.address_from_private_key(private_key)
        print(f"Loaded existing sponsor wallet: {address}")
    else:
        private_key, address = account.generate_account()
        new_mnemonic = mnemonic.from_private_key(private_key)
        print(f"Created new sponsor wallet: {address}")
        print(f"\n⚠️  SAVE THIS MNEMONIC (add to .env as SPONSOR_MNEMONIC):")
        print(f"   {new_mnemonic}\n")
    
    return private_key, address


def fund_sponsor(
    client: algod.AlgodClient,
    funder_key: str,
    funder_address: str,
    sponsor_address: str,
    amount_algo: float
):
    """
    Fund the sponsor wallet with ALGO.
    
    Args:
        client: Algorand client
        funder_key: Private key of funder
        funder_address: Address of funder
        sponsor_address: Address of sponsor to fund
        amount_algo: Amount in ALGO to send
    """
    amount_microalgo = int(amount_algo * 1_000_000)
    
    params = client.suggested_params()
    
    txn = transaction.PaymentTxn(
        sender=funder_address,
        sp=params,
        receiver=sponsor_address,
        amt=amount_microalgo,
        note=b"cresca-sponsor-funding",
    )
    
    signed_txn = txn.sign(funder_key)
    tx_id = client.send_transaction(signed_txn)
    
    result = transaction.wait_for_confirmation(client, tx_id, 4)
    
    print(f"✅ Funded sponsor with {amount_algo} ALGO")
    print(f"   Transaction ID: {tx_id}")
    
    return tx_id


def check_sponsor_balance(client: algod.AlgodClient, address: str):
    """Check and display sponsor wallet balance."""
    account_info = client.account_info(address)
    balance = account_info["amount"] / 1_000_000
    min_balance = account_info["min-balance"] / 1_000_000
    available = balance - min_balance
    
    print(f"\nSponsor Wallet Status:")
    print(f"   Address: {address}")
    print(f"   Balance: {balance:.6f} ALGO")
    print(f"   Min Balance: {min_balance:.6f} ALGO")
    print(f"   Available for sponsorship: {available:.6f} ALGO")
    
    # Calculate approximate sponsored transactions
    # Each sponsored tx costs 0.002 ALGO (0.001 for user, 0.001 for sponsor)
    approx_txns = int(available / 0.002)
    print(f"   Approximate transactions sponsorable: {approx_txns:,}")
    
    return balance


def main():
    parser = argparse.ArgumentParser(
        description="Fund the sponsor wallet for gasless transactions"
    )
    parser.add_argument(
        "--amount",
        type=float,
        default=0,
        help="Amount in ALGO to fund the sponsor wallet"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check balance, don't fund"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Cresca Campus - Sponsor Wallet Setup")
    print("=" * 60)
    
    client = get_algod_client()
    
    # Create or load sponsor wallet
    sponsor_key, sponsor_address = create_or_load_sponsor()
    
    if args.check:
        check_sponsor_balance(client, sponsor_address)
        return
    
    if args.amount > 0:
        # Load funder account
        funder_mnemonic = os.getenv("DEPLOYER_MNEMONIC")
        if not funder_mnemonic:
            print("Error: Set DEPLOYER_MNEMONIC to fund the sponsor wallet")
            return
        
        funder_key = mnemonic.to_private_key(funder_mnemonic)
        funder_address = account.address_from_private_key(funder_key)
        
        # Fund the sponsor
        fund_sponsor(client, funder_key, funder_address, sponsor_address, args.amount)
    
    # Check final balance
    check_sponsor_balance(client, sponsor_address)
    
    print("\n" + "-" * 60)
    print("Usage Instructions")
    print("-" * 60)
    print("""
To use fee pooling for gasless transactions:

1. Create an atomic group with:
   - Student's transaction (fee = 0)
   - Sponsor's transaction (fee = 0.002 ALGO)

2. Sign sponsor's transaction with sponsor wallet
3. Student signs their transaction
4. Submit both as atomic group

Example in frontend:
   const sponsoredTxns = createSponsoredPayment(
       studentAddress,
       recipientAddress,
       amount,
       sponsorAddress
   );
""")


if __name__ == "__main__":
    main()
