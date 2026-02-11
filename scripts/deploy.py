"""
Deployment Script for Cresca Campus Smart Contracts

This script deploys all smart contracts to the Algorand network.
Run with: python scripts/deploy.py

Environment variables required:
- ALGOD_SERVER: Algorand node URL
- ALGOD_TOKEN: Algorand node token
- DEPLOYER_MNEMONIC: 25-word mnemonic for deployer account
- NETWORK: localnet | testnet | mainnet
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from algosdk import account, mnemonic
from algosdk.v2client import algod
from algosdk import transaction

# Load environment variables
load_dotenv()


def get_algod_client() -> algod.AlgodClient:
    """Create Algorand client from environment variables."""
    server = os.getenv("ALGOD_SERVER", "http://localhost:4001")
    token = os.getenv("ALGOD_TOKEN", "a" * 64)
    
    return algod.AlgodClient(token, server)


def get_deployer_account() -> tuple[str, str]:
    """Get deployer account from mnemonic."""
    mnemonic_phrase = os.getenv("DEPLOYER_MNEMONIC")
    
    if not mnemonic_phrase:
        # For localnet, use default account
        print("Warning: No DEPLOYER_MNEMONIC set. Using generated account for localnet.")
        private_key, address = account.generate_account()
        return private_key, address
    
    private_key = mnemonic.to_private_key(mnemonic_phrase)
    address = account.address_from_private_key(private_key)
    
    return private_key, address


def compile_contract(client: algod.AlgodClient, source_code: str) -> bytes:
    """Compile TEAL source code."""
    compile_response = client.compile(source_code)
    return bytes.fromhex(compile_response["result"])


def deploy_contract(
    client: algod.AlgodClient,
    private_key: str,
    sender: str,
    approval_program: bytes,
    clear_program: bytes,
    global_schema: transaction.StateSchema,
    local_schema: transaction.StateSchema,
    app_args: list = None,
) -> int:
    """Deploy a smart contract and return the app ID."""
    params = client.suggested_params()
    
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
    
    signed_txn = txn.sign(private_key)
    tx_id = client.send_transaction(signed_txn)
    
    # Wait for confirmation
    result = transaction.wait_for_confirmation(client, tx_id, 4)
    app_id = result["application-index"]
    
    return app_id


def main():
    """Main deployment function."""
    print("=" * 60)
    print("Cresca Campus - Smart Contract Deployment")
    print("=" * 60)
    
    # Get network info
    network = os.getenv("NETWORK", "localnet")
    print(f"\nNetwork: {network}")
    
    # Initialize client
    client = get_algod_client()
    
    # Get deployer account
    private_key, deployer = get_deployer_account()
    print(f"Deployer: {deployer}")
    
    # Check balance
    try:
        account_info = client.account_info(deployer)
        balance = account_info["amount"] / 1_000_000
        print(f"Balance: {balance:.6f} ALGO")
        
        if balance < 1:
            print("\nWarning: Low balance. Fund your account before deploying.")
            if network == "localnet":
                print("Run: algokit goal clerk send -a 10000000 -f <dispenser> -t " + deployer)
    except Exception as e:
        print(f"Could not check balance: {e}")
    
    print("\n" + "-" * 60)
    print("Contract Deployment")
    print("-" * 60)
    
    # Deploy contracts
    # Note: In production, you would compile the Puya contracts first using:
    # algokit project run build
    
    contracts_to_deploy = [
        {
            "name": "ExpenseSplitter",
            "path": "contracts/expense_splitter",
            "global_ints": 5,
            "global_bytes": 0,
            "local_ints": 3,
            "local_bytes": 0,
        },
        {
            "name": "DAOTreasury",
            "path": "contracts/dao_treasury",
            "global_ints": 4,
            "global_bytes": 1,
            "local_ints": 1,
            "local_bytes": 0,
        },
        {
            "name": "SoulboundTicket",
            "path": "contracts/soulbound_ticket",
            "global_ints": 1,
            "global_bytes": 0,
            "local_ints": 0,
            "local_bytes": 0,
        },
        {
            "name": "FundraisingEscrow",
            "path": "contracts/fundraising",
            "global_ints": 1,
            "global_bytes": 0,
            "local_ints": 0,
            "local_bytes": 0,
        },
    ]
    
    deployed = {}
    
    for contract in contracts_to_deploy:
        print(f"\n📄 {contract['name']}")
        
        # In production, load compiled TEAL from build output
        # For now, we'll just print info
        print(f"   Path: {contract['path']}")
        print(f"   Global: {contract['global_ints']} ints, {contract['global_bytes']} bytes")
        print(f"   Local: {contract['local_ints']} ints, {contract['local_bytes']} bytes")
        
        # To actually deploy, uncomment and provide compiled TEAL:
        # app_id = deploy_contract(
        #     client=client,
        #     private_key=private_key,
        #     sender=deployer,
        #     approval_program=approval_teal,
        #     clear_program=clear_teal,
        #     global_schema=transaction.StateSchema(
        #         contract['global_ints'],
        #         contract['global_bytes']
        #     ),
        #     local_schema=transaction.StateSchema(
        #         contract['local_ints'],
        #         contract['local_bytes']
        #     ),
        # )
        # deployed[contract['name']] = app_id
        # print(f"   ✅ Deployed: App ID {app_id}")
        
        print(f"   ⏳ Ready for deployment (compile contracts first)")
    
    print("\n" + "=" * 60)
    print("Deployment Instructions")
    print("=" * 60)
    print("""
To deploy the contracts:

1. Build the contracts:
   algokit project run build

2. Set environment variables:
   - ALGOD_SERVER (e.g., http://localhost:4001)
   - ALGOD_TOKEN
   - DEPLOYER_MNEMONIC (your 25-word mnemonic)
   - NETWORK (localnet/testnet/mainnet)

3. Run this script again:
   python scripts/deploy.py

For localnet development:
   algokit localnet start
   algokit goal clerk send -a 10000000 -f <dispenser> -t <your-address>
""")
    
    # Save deployment info
    output_path = Path("deployment.json")
    deployment_info = {
        "network": network,
        "deployer": deployer,
        "contracts": deployed,
    }
    
    with open(output_path, "w") as f:
        json.dump(deployment_info, f, indent=2)
    
    print(f"\nDeployment info saved to: {output_path}")


if __name__ == "__main__":
    main()
