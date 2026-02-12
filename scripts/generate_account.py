"""
Account Generator Script for Cresca Campus

This script creates wallets and accounts for deploying contracts.
Uses AlgoKit utils for KMD-based account management on LocalNet.

Usage:
    python scripts/generate_account.py --name deployer
    python scripts/generate_account.py --name deployer --fund 10
"""

import os
import argparse
from dotenv import load_dotenv
from algosdk import account, mnemonic
from algosdk.v2client import algod
from algosdk import kmd

load_dotenv()


def get_algod_client() -> algod.AlgodClient:
    """Create Algorand client from environment variables."""
    server = os.getenv("ALGOD_SERVER", "http://localhost:4001")
    token = os.getenv("ALGOD_TOKEN", "a" * 64)
    return algod.AlgodClient(token, server)


def get_kmd_client() -> kmd.KMDClient:
    """Create KMD client for LocalNet."""
    server = os.getenv("KMD_SERVER", "http://localhost:4002")
    token = os.getenv("KMD_TOKEN", "a" * 64)
    return kmd.KMDClient(token, server)


def create_wallet(kmd_client: kmd.KMDClient, name: str, password: str = ""):
    """
    Create a wallet with the KMD client.
    
    Args:
        kmd_client: KMD client instance
        name: Wallet name
        password: Wallet password
        
    Returns:
        Wallet ID
    """
    try:
        # Check if wallet already exists
        wallets = kmd_client.list_wallets()
        for wallet in wallets:
            if wallet["name"] == name:
                print(f"Wallet '{name}' already exists with ID: {wallet['id']}")
                return wallet["id"]
        
        # Create new wallet
        wallet = kmd_client.create_wallet(name, password)
        wallet_id = wallet["id"]
        print(f"✅ Created wallet '{name}' with ID: {wallet_id}")
        return wallet_id
    except Exception as e:
        print(f"❌ Error creating wallet: {e}")
        return None


def generate_account_in_wallet(
    kmd_client: kmd.KMDClient, 
    wallet_id: str, 
    password: str = ""
) -> tuple[str, str]:
    """
    Generate a new account within a wallet.
    
    Args:
        kmd_client: KMD client instance
        wallet_id: Wallet ID
        password: Wallet password
        
    Returns:
        Tuple of (address, private_key)
    """
    try:
        # Get wallet handle
        wallet_handle = kmd_client.init_wallet_handle(wallet_id, password)
        
        # Generate new account
        address = kmd_client.generate_key(wallet_handle)
        
        # Export the private key
        private_key = kmd_client.export_key(wallet_handle, password, address)
        
        # Release wallet handle
        kmd_client.release_wallet_handle(wallet_handle)
        
        return address, private_key
    except Exception as e:
        print(f"❌ Error generating account: {e}")
        return None, None


def generate_standalone_account() -> tuple[str, str, str]:
    """
    Generate a standalone account (not in KMD).
    
    Returns:
        Tuple of (address, private_key, mnemonic_phrase)
    """
    private_key, address = account.generate_account()
    mnemonic_phrase = mnemonic.from_private_key(private_key)
    
    return address, private_key, mnemonic_phrase


def get_account_from_kmd(kmd_client: kmd.KMDClient, name: str, password: str = ""):
    """
    Get or create an account from LocalNet's KMD by name.
    If the wallet/account doesn't exist, it will be created.
    
    Similar to: algorand_client.account.from_kmd(name="ACCOUNT_NAME")
    
    Args:
        kmd_client: KMD client instance
        name: Account/wallet name
        password: Wallet password
        
    Returns:
        Tuple of (address, private_key)
    """
    # Create or get wallet
    wallet_id = create_wallet(kmd_client, name, password)
    if not wallet_id:
        return None, None
    
    # Get wallet handle
    wallet_handle = kmd_client.init_wallet_handle(wallet_id, password)
    
    # List existing keys
    keys = kmd_client.list_keys(wallet_handle)
    
    if keys:
        # Return existing account
        address = keys[0]
        private_key = kmd_client.export_key(wallet_handle, password, address)
        print(f"📍 Using existing account: {address}")
    else:
        # Generate new account
        address, private_key = generate_account_in_wallet(kmd_client, wallet_id, password)
        print(f"✅ Generated new account: {address}")
    
    kmd_client.release_wallet_handle(wallet_handle)
    return address, private_key


def fund_from_dispenser(
    algod_client: algod.AlgodClient,
    kmd_client: kmd.KMDClient,
    receiver: str,
    amount_algo: float = 10
):
    """
    Fund an account from the LocalNet dispenser (default funded wallet).
    
    Args:
        algod_client: Algorand client
        kmd_client: KMD client
        receiver: Address to fund
        amount_algo: Amount in ALGO
    """
    try:
        # Get the default funded wallet on LocalNet
        wallets = kmd_client.list_wallets()
        default_wallet = None
        
        for wallet in wallets:
            if wallet["name"] == "unencrypted-default-wallet":
                default_wallet = wallet
                break
        
        if not default_wallet:
            print("❌ Default wallet not found. Make sure LocalNet is running.")
            return
        
        # Get wallet handle and first account (dispenser)
        wallet_handle = kmd_client.init_wallet_handle(default_wallet["id"], "")
        keys = kmd_client.list_keys(wallet_handle)
        
        if not keys:
            print("❌ No accounts in default wallet")
            return
        
        dispenser_address = keys[0]
        dispenser_key = kmd_client.export_key(wallet_handle, "", dispenser_address)
        kmd_client.release_wallet_handle(wallet_handle)
        
        # Send payment
        from algosdk import transaction
        
        params = algod_client.suggested_params()
        amount_microalgo = int(amount_algo * 1_000_000)
        
        txn = transaction.PaymentTxn(
            sender=dispenser_address,
            sp=params,
            receiver=receiver,
            amt=amount_microalgo,
        )
        
        signed_txn = txn.sign(dispenser_key)
        tx_id = algod_client.send_transaction(signed_txn)
        transaction.wait_for_confirmation(algod_client, tx_id, 4)
        
        print(f"✅ Funded {receiver} with {amount_algo} ALGO")
        print(f"   Transaction: {tx_id}")
        
    except Exception as e:
        print(f"❌ Error funding account: {e}")


def check_balance(algod_client: algod.AlgodClient, address: str):
    """Check and display account balance."""
    try:
        info = algod_client.account_info(address)
        balance = info["amount"] / 1_000_000
        print(f"\n💰 Account Balance: {balance} ALGO")
        print(f"   Address: {address}")
    except Exception as e:
        print(f"❌ Error checking balance: {e}")


def main():
    parser = argparse.ArgumentParser(description="Generate accounts for Cresca Campus")
    parser.add_argument(
        "--name", 
        type=str, 
        default="cresca-deployer",
        help="Account/wallet name"
    )
    parser.add_argument(
        "--fund", 
        type=float, 
        default=0,
        help="Amount of ALGO to fund (from LocalNet dispenser)"
    )
    parser.add_argument(
        "--standalone", 
        action="store_true",
        help="Generate standalone account (not in KMD)"
    )
    parser.add_argument(
        "--check", 
        action="store_true",
        help="Only check balance of existing account"
    )
    
    args = parser.parse_args()
    
    print("\n🏫 Cresca Campus - Account Generator\n")
    print("=" * 50)
    
    if args.standalone:
        # Generate standalone account
        print("\n📝 Generating standalone account...")
        address, private_key, mnemonic_phrase = generate_standalone_account()
        
        print(f"\n✅ Account Generated!")
        print(f"   Address: {address}")
        print(f"\n⚠️  SAVE THIS MNEMONIC (never share it!):")
        print(f"   {mnemonic_phrase}")
        print(f"\n📋 Add to .env file:")
        print(f"   DEPLOYER_MNEMONIC={mnemonic_phrase}")
        print(f"   DEPLOYER_ADDRESS={address}")
    else:
        # Use KMD for LocalNet
        print(f"\n📝 Getting/Creating account '{args.name}' from KMD...")
        
        algod_client = get_algod_client()
        kmd_client = get_kmd_client()
        
        address, private_key = get_account_from_kmd(kmd_client, args.name)
        
        if address:
            if args.fund > 0:
                print(f"\n💸 Funding account with {args.fund} ALGO...")
                fund_from_dispenser(algod_client, kmd_client, address, args.fund)
            
            check_balance(algod_client, address)
            
            # Export mnemonic for reference
            mnemonic_phrase = mnemonic.from_private_key(private_key)
            print(f"\n📋 Account Details:")
            print(f"   Address: {address}")
            print(f"\n⚠️  Mnemonic (save securely):")
            print(f"   {mnemonic_phrase}")
    
    print("\n" + "=" * 50)
    print("Done!\n")


if __name__ == "__main__":
    main()
