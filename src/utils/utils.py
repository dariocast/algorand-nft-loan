# Helper function to wait for a specific round
import json

from algosdk.future import transaction
from algosdk.future.transaction import AssetTransferTxn
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.models import Account
from beaker.sandbox import SandboxAccount


def wait_for_round(client, round_to_wait_for):
    last_round = client.status().get('last-round')
    print(f"Waiting for round {round_to_wait_for}")
    while last_round < round_to_wait_for:
        last_round += 1
        client.status_after_block(last_round)
        print(f"Round {last_round}")


def opt_in_to_asset(client: AlgodClient, account: SandboxAccount | Account, asset_id: int):
    # OPT-IN
    # Check if asset_id is in account's asset holdings prior to opt-in
    params = client.suggested_params()
    account_info = client.account_info(account.address)
    holding = None
    idx = 0
    for my_account_info in account_info['assets']:
        scrutinized_asset = account_info['assets'][idx]
        idx = idx + 1
        if scrutinized_asset['asset-id'] == asset_id:
            holding = True
            break
    if not holding:
        # Use the AssetTransferTxn class to transfer assets and opt-in
        txn = AssetTransferTxn(
            sender=account.address,
            sp=params,
            receiver=account.address,
            amt=0,
            index=asset_id)
        stxn = txn.sign(account.private_key)
        # Send the transaction to the network and retrieve the txid.
        try:
            txid = client.send_transaction(stxn)
            print("Signed transaction with txID: {}".format(txid))
            # Wait for the transaction to be confirmed
            confirmed_txn = transaction.wait_for_confirmation(client, txid, 4)
            print("TXID: ", txid)
            print("Result confirmed in round: {}".format(confirmed_txn['confirmed-round']))
        except Exception as err:
            print(err)
        # Now check the asset holding for that account.
        # This should now show a holding with a balance of 0.
        print_asset_holding(client, account.address, asset_id)


#   Utility function used to print asset holding for account and assetid
def print_asset_holding(algodclient, account, assetid):
    # note: if you have an indexer instance available it is easier to just use this
    # response = myindexer.accounts(asset_id = assetid)
    # then loop thru the accounts returned and match the account you are looking for
    account_info = algodclient.account_info(account)
    idx = 0
    for my_account_info in account_info['assets']:
        scrutinized_asset = account_info['assets'][idx]
        idx = idx + 1
        if (scrutinized_asset['asset-id'] == assetid):
            print("Asset ID: {}".format(scrutinized_asset['asset-id']))
            print(json.dumps(scrutinized_asset, indent=4))
            break