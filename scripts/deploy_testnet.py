"""
Deploy Contracts to Algorand Testnet

This script deploys all compiled TEAL contracts to testnet.
"""

import os
import json
import base64
from pathlib import Path
from dotenv import load_dotenv
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod

load_dotenv()

# Testnet configuration - use a node that supports compilation
ALGOD_ADDRESS = "https://testnet-api.algonode.cloud"
ALGOD_TOKEN = ""

# Compilation endpoint (Algonode supports this)
COMPILE_ADDRESS = "https://testnet-api.algonode.cloud"

# Deployer account
DEPLOYER_MNEMONIC = os.getenv("DEPLOYER_MNEMONIC")


def get_client():
    """Get Algorand client for testnet."""
    return algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)


def get_deployer():
    """Get deployer account from environment."""
    if not DEPLOYER_MNEMONIC:
        raise ValueError("DEPLOYER_MNEMONIC not set in environment")
    
    private_key = mnemonic.to_private_key(DEPLOYER_MNEMONIC)
    address = account.address_from_private_key(private_key)
    return private_key, address


def compile_teal(client, source):
    """Compile TEAL source code using the Algorand node."""
    try:
        response = client.compile(source)
        return base64.b64decode(response["result"])
    except Exception as e:
        print(f"      Compilation error: {e}")
        raise


def deploy_contract(client, private_key, sender, approval_file, clear_file, global_ints, global_bytes, local_ints, local_bytes, app_args=None):
    """Deploy a smart contract."""
    
    # Read TEAL files
    with open(approval_file) as f:
        approval_source = f.read()
    with open(clear_file) as f:
        clear_source = f.read()
    
    # Compile
    approval_program = compile_teal(client, approval_source)
    clear_program = compile_teal(client, clear_source)
    
    # Create schemas
    global_schema = transaction.StateSchema(global_ints, global_bytes)
    local_schema = transaction.StateSchema(local_ints, local_bytes)
    
    # Get suggested params
    params = client.suggested_params()
    
    # Create transaction
    txn = transaction.ApplicationCreateTxn(
        sender=sender,
        sp=params,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval_program,
        clear_program=clear_program,
        global_schema=global_schema,
        local_schema=local_schema,
        app_args=app_args,
    )
    
    # Sign and send
    signed_txn = txn.sign(private_key)
    tx_id = client.send_transaction(signed_txn)
    
    print(f"   Transaction ID: {tx_id}")
    
    # Wait for confirmation
    result = transaction.wait_for_confirmation(client, tx_id, 4)
    app_id = result["application-index"]
    
    return app_id, tx_id


def main():
    print("\n" + "=" * 60)
    print("🏫 CRESCA CAMPUS - TESTNET DEPLOYMENT")
    print("=" * 60)
    
    # Initialize
    client = get_client()
    private_key, deployer = get_deployer()
    
    print(f"\n📍 Network: Algorand Testnet")
    print(f"📍 Deployer: {deployer}")
    
    # Check balance
    info = client.account_info(deployer)
    balance = info["amount"] / 1_000_000
    print(f"💰 Balance: {balance} ALGO")
    
    if balance < 1:
        print("❌ Insufficient balance! Need at least 1 ALGO")
        return
    
    print("\n" + "-" * 60)
    print("📄 DEPLOYING CONTRACTS")
    print("-" * 60)
    
    deployed = {}
    
    # 1. Expense Splitter
    print("\n1️⃣ Expense Splitter")
    try:
        app_id, tx_id = deploy_contract(
            client, private_key, deployer,
            "build/expense_splitter_approval.teal",
            "build/expense_splitter_clear.teal",
            global_ints=5, global_bytes=1,  # Changed: need 1 bytes for creator address
            local_ints=3, local_bytes=0,
        )
        deployed["expense_splitter"] = {"app_id": app_id, "tx_id": tx_id}
        print(f"   ✅ Deployed! App ID: {app_id}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # 2. DAO Treasury
    print("\n2️⃣ DAO Treasury")
    try:
        app_id, tx_id = deploy_contract(
            client, private_key, deployer,
            "build/dao_treasury_approval.teal",
            "build/dao_treasury_clear.teal",
            global_ints=4, global_bytes=1,
            local_ints=1, local_bytes=0,
            app_args=[2],  # Threshold = 2
        )
        deployed["dao_treasury"] = {"app_id": app_id, "tx_id": tx_id}
        print(f"   ✅ Deployed! App ID: {app_id}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # 3. Soulbound Ticket
    print("\n3️⃣ Soulbound Ticket (ARC-71)")
    try:
        app_id, tx_id = deploy_contract(
            client, private_key, deployer,
            "build/soulbound_ticket_approval.teal",
            "build/soulbound_ticket_clear.teal",
            global_ints=1, global_bytes=0,
            local_ints=0, local_bytes=0,
        )
        deployed["soulbound_ticket"] = {"app_id": app_id, "tx_id": tx_id}
        print(f"   ✅ Deployed! App ID: {app_id}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # 4. Fundraising Escrow
    print("\n4️⃣ Fundraising Escrow")
    try:
        app_id, tx_id = deploy_contract(
            client, private_key, deployer,
            "build/fundraising_approval.teal",
            "build/fundraising_clear.teal",
            global_ints=1, global_bytes=0,
            local_ints=0, local_bytes=0,
        )
        deployed["fundraising"] = {"app_id": app_id, "tx_id": tx_id}
        print(f"   ✅ Deployed! App ID: {app_id}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 DEPLOYMENT SUMMARY")
    print("=" * 60)
    
    for name, info in deployed.items():
        print(f"\n{name}:")
        print(f"   App ID: {info['app_id']}")
        print(f"   Explorer: https://testnet.explorer.perawallet.app/application/{info['app_id']}")
    
    # Save deployment info
    deployment_info = {
        "network": "testnet",
        "deployer": deployer,
        "contracts": deployed,
    }
    
    with open("deployment_testnet.json", "w") as f:
        json.dump(deployment_info, f, indent=2)
    
    print(f"\n💾 Deployment info saved to: deployment_testnet.json")
    
    # Update .env
    print("\n📝 Add these to your .env file:")
    for name, info in deployed.items():
        env_key = f"{name.upper()}_APP_ID"
        print(f"   {env_key}={info['app_id']}")
    
    print("\n" + "=" * 60)
    print("🎉 DEPLOYMENT COMPLETE!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
