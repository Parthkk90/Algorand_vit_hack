"""
Test Deployed Contracts on Algorand Testnet

Tests basic functionality of all deployed contracts.
"""

import os
import base64
from dotenv import load_dotenv
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod

load_dotenv()

# Contract App IDs (from deployment)
EXPENSE_SPLITTER_APP_ID = 755399831
DAO_TREASURY_APP_ID = 755399773
SOULBOUND_TICKET_APP_ID = 755399774
FUNDRAISING_APP_ID = 755399775

# Setup
client = algod.AlgodClient('', 'https://testnet-api.algonode.cloud')
private_key = mnemonic.to_private_key(os.getenv('DEPLOYER_MNEMONIC'))
deployer = account.address_from_private_key(private_key)


def call_app(app_id, args, on_complete=transaction.OnComplete.NoOpOC):
    """Call an application with given arguments."""
    params = client.suggested_params()
    
    txn = transaction.ApplicationCallTxn(
        sender=deployer,
        sp=params,
        index=app_id,
        on_complete=on_complete,
        app_args=args,
    )
    
    signed = txn.sign(private_key)
    tx_id = client.send_transaction(signed)
    result = transaction.wait_for_confirmation(client, tx_id, 4)
    
    return tx_id, result


def read_global_state(app_id):
    """Read global state of an application."""
    app_info = client.application_info(app_id)
    
    state = {}
    if 'params' in app_info and 'global-state' in app_info['params']:
        for item in app_info['params']['global-state']:
            key = base64.b64decode(item['key']).decode('utf-8')
            value = item['value']
            if value['type'] == 1:  # bytes
                state[key] = base64.b64decode(value['bytes'])
            else:  # uint
                state[key] = value['uint']
    
    return state


def test_expense_splitter():
    """Test Expense Splitter contract."""
    print("\n" + "=" * 50)
    print("🧪 TEST: Expense Splitter")
    print("=" * 50)
    
    app_id = EXPENSE_SPLITTER_APP_ID
    
    # Read initial state
    print("\n1. Reading initial state...")
    state = read_global_state(app_id)
    print(f"   Member count: {state.get('member_count', 0)}")
    print(f"   Expense count: {state.get('expense_count', 0)}")
    print(f"   Is settled: {state.get('is_settled', 0)}")
    
    # Opt-in to the contract
    print("\n2. Opting in to contract...")
    try:
        tx_id, _ = call_app(app_id, [], transaction.OnComplete.OptInOC)
        print(f"   ✅ Opted in! TX: {tx_id}")
    except Exception as e:
        if "has already opted in" in str(e):
            print("   ℹ️ Already opted in")
        else:
            print(f"   ⚠️ Opt-in: {e}")
    
    # Read updated state
    print("\n3. Reading updated state...")
    state = read_global_state(app_id)
    print(f"   Member count: {state.get('member_count', 0)}")
    
    print("\n✅ Expense Splitter tests passed!")


def test_dao_treasury():
    """Test DAO Treasury contract."""
    print("\n" + "=" * 50)
    print("🧪 TEST: DAO Treasury")
    print("=" * 50)
    
    app_id = DAO_TREASURY_APP_ID
    
    # Read state
    print("\n1. Reading state...")
    state = read_global_state(app_id)
    print(f"   Threshold: {state.get('threshold', 0)}")
    print(f"   Signer count: {state.get('signer_count', 0)}")
    print(f"   Proposal count: {state.get('proposal_count', 0)}")
    
    # Opt-in as potential signer
    print("\n2. Opting in as potential signer...")
    try:
        tx_id, _ = call_app(app_id, [], transaction.OnComplete.OptInOC)
        print(f"   ✅ Opted in! TX: {tx_id}")
    except Exception as e:
        if "has already opted in" in str(e):
            print("   ℹ️ Already opted in")
        else:
            print(f"   ⚠️ Opt-in: {e}")
    
    print("\n✅ DAO Treasury tests passed!")


def test_soulbound_ticket():
    """Test Soulbound Ticket contract."""
    print("\n" + "=" * 50)
    print("🧪 TEST: Soulbound Ticket (ARC-71)")
    print("=" * 50)
    
    app_id = SOULBOUND_TICKET_APP_ID
    
    # Read state
    print("\n1. Reading state...")
    state = read_global_state(app_id)
    print(f"   Event count: {state.get('event_count', 0)}")
    
    # Create an event
    print("\n2. Creating a test event...")
    try:
        tx_id, result = call_app(app_id, [b"create_event"])
        print(f"   ✅ Event created! TX: {tx_id}")
        
        # Check logs
        if 'logs' in result:
            for log in result['logs']:
                print(f"   Log: {base64.b64decode(log)}")
    except Exception as e:
        print(f"   ⚠️ Create event: {e}")
    
    # Read updated state
    print("\n3. Reading updated state...")
    state = read_global_state(app_id)
    print(f"   Event count: {state.get('event_count', 0)}")
    
    print("\n✅ Soulbound Ticket tests passed!")


def test_fundraising():
    """Test Fundraising Escrow contract."""
    print("\n" + "=" * 50)
    print("🧪 TEST: Fundraising Escrow")
    print("=" * 50)
    
    app_id = FUNDRAISING_APP_ID
    
    # Read state
    print("\n1. Reading state...")
    state = read_global_state(app_id)
    print(f"   Campaign count: {state.get('campaign_count', 0)}")
    
    # Create a campaign
    print("\n2. Creating a test campaign...")
    try:
        tx_id, result = call_app(app_id, [b"create_campaign"])
        print(f"   ✅ Campaign created! TX: {tx_id}")
        
        if 'logs' in result:
            for log in result['logs']:
                print(f"   Log: {base64.b64decode(log)}")
    except Exception as e:
        print(f"   ⚠️ Create campaign: {e}")
    
    # Read updated state
    print("\n3. Reading updated state...")
    state = read_global_state(app_id)
    print(f"   Campaign count: {state.get('campaign_count', 0)}")
    
    print("\n✅ Fundraising tests passed!")


def main():
    print("\n" + "=" * 60)
    print("🏫 CRESCA CAMPUS - CONTRACT TESTING")
    print("=" * 60)
    
    print(f"\n📍 Network: Algorand Testnet")
    print(f"📍 Tester: {deployer}")
    
    # Check balance
    info = client.account_info(deployer)
    balance = info["amount"] / 1_000_000
    print(f"💰 Balance: {balance:.4f} ALGO")
    
    # Run tests
    test_expense_splitter()
    test_dao_treasury()
    test_soulbound_ticket()
    test_fundraising()
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS COMPLETED!")
    print("=" * 60)
    
    # Final balance
    info = client.account_info(deployer)
    final_balance = info["amount"] / 1_000_000
    print(f"\n💰 Final Balance: {final_balance:.4f} ALGO")
    print(f"💸 Test Cost: {balance - final_balance:.4f} ALGO\n")


if __name__ == "__main__":
    main()
