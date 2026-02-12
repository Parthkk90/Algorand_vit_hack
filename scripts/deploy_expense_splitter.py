"""Deploy just the Expense Splitter contract."""
import os
import base64
from dotenv import load_dotenv
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod

load_dotenv()

client = algod.AlgodClient('', 'https://testnet-api.algonode.cloud')
private_key = mnemonic.to_private_key(os.getenv('DEPLOYER_MNEMONIC'))
deployer = account.address_from_private_key(private_key)

print(f"Deploying from: {deployer}")

with open('build/expense_splitter_approval.teal') as f:
    approval = base64.b64decode(client.compile(f.read())['result'])
with open('build/expense_splitter_clear.teal') as f:
    clear = base64.b64decode(client.compile(f.read())['result'])

params = client.suggested_params()
txn = transaction.ApplicationCreateTxn(
    sender=deployer, sp=params,
    on_complete=transaction.OnComplete.NoOpOC,
    approval_program=approval, clear_program=clear,
    global_schema=transaction.StateSchema(5, 1),
    local_schema=transaction.StateSchema(3, 0))

signed = txn.sign(private_key)
tx_id = client.send_transaction(signed)
print(f"Transaction: {tx_id}")

result = transaction.wait_for_confirmation(client, tx_id, 4)
app_id = result["application-index"]
print(f"✅ Expense Splitter App ID: {app_id}")
print(f"   Explorer: https://testnet.explorer.perawallet.app/application/{app_id}")
