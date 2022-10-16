# Helper function to wait for a specific round
import json
import os
from hashlib import sha256

from algosdk.atomic_transaction_composer import AccountTransactionSigner, TransactionWithSigner
from algosdk.future import transaction
from algosdk.future.transaction import AssetTransferTxn, AssetConfigTxn, wait_for_confirmation
from algosdk.v2client import algod
from algosdk.v2client.models import Account
from algosdk import account, mnemonic
from beaker import sandbox
from beaker.sandbox import SandboxAccount


# Predefined accounts funded on Testnet
mnemonics = [
    "plunge odor company index ceiling body frozen canvas soul tooth mule glass tip economy govern boost earth behind space gap galaxy myth alone ability access",
    "banana mixed foam tower wet snap kitten amused scheme govern convince brick cannon other strong dog chicken pattern sight abstract topic lucky member absent bamboo",
    "goat speed door indoor bright sibling vehicle load major stereo saddle clump cube pledge essay velvet employ design timber space assault vote supply able biology",
    "material tower kiss tower chimney remind kind lottery pill soldier december pretty list denial donate admit post tonight govern pledge hand old oblige ability other",
]

nft_metadata_github_url = "https://raw.githubusercontent.com/dariocast/algorand-nft-loan/main/assets/nft_metadata.json"

def wait_for_round(client, round_to_wait_for):
    last_round = client.status().get('last-round')
    print(f"Waiting for round {round_to_wait_for}")
    while last_round < round_to_wait_for:
        last_round += 1
        client.status_after_block(last_round)
        print(f"Round {last_round}")


def opt_in_to_asset(client: algod.AlgodClient, account: SandboxAccount | Account, asset_id: int):
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
            # print("Signed transaction with txID: {}".format(txid))
            # Wait for the transaction to be confirmed
            confirmed_txn = transaction.wait_for_confirmation(client, txid, 4)
            # print("TXID: ", txid)
            # print("Result confirmed in round: {}".format(confirmed_txn['confirmed-round']))
        except Exception as err:
            print(err)
        # Now check the asset holding for that account.
        # This should now show a holding with a balance of 0.
        # print_asset_holding(client, account.address, asset_id)


#   Utility function used to print asset holding for account and assetid
def print_asset_holding(algodclient, account, assetid=None):
    # note: if you have an indexer instance available it is easier to just use this
    # response = myindexer.accounts(asset_id = assetid)
    # then loop thru the accounts returned and match the account you are looking for
    account_info = algodclient.account_info(account)
    idx = 0
    for my_account_info in account_info['assets']:
        scrutinized_asset = account_info['assets'][idx]
        idx = idx + 1
        if not assetid or scrutinized_asset['asset-id'] == assetid:
            print("Asset ID: {}".format(scrutinized_asset['asset-id']))
            print(json.dumps(scrutinized_asset, indent=4))
            break


# helper method to generate new algorand keypair
def generate_algorand_keypair():
    private_key, address = account.generate_account()
    print("My address: {}".format(address))
    print("My private key: {}".format(private_key))
    print("My passphrase: {}".format(mnemonic.from_private_key(private_key)))
    return private_key, address


# Return account in the form of sandbox one (but they are on testnet!!!)
def get_testnet_account():
    accounts = []
    for mn in mnemonics:
        sk = get_private_key_from_mnemonic(mn)
        address = get_address_from_private_key(sk)
        account = SandboxAccount(
            address=address,
            private_key=sk,
            signer=AccountTransactionSigner(private_key=sk),
        )
        accounts.append(account)
    return accounts


def put_testnet_account_into_sandbox_and_fund():
    sandbox_account = sandbox.get_accounts()[0]
    client = sandbox.get_algod_client()
    for mn in mnemonics:
        sk = get_private_key_from_mnemonic(mn)
        sandbox.add_account(private_key=sk)
        txn = TransactionWithSigner(
            txn = transaction.PaymentTxn(
                sender=sandbox_account.address,
                sp=client.suggested_params(),
                receiver=account.address_from_private_key(sk),
                amt=100000000,
            ),
            signer=sandbox_account.signer,
        )
        client.send_transaction(txn)
    for acct in sandbox.get_accounts():
        print(acct.address)
        check_balance(client, acct.address)

def check_balance(algod_client, my_address):
    account_info = algod_client.account_info(my_address)
    print("Account balance: {} microAlgos".format(account_info.get('amount')) + "\n")
    return account_info


# helper function that converts a mnemonic passphrase into a private signing key
def get_private_key_from_mnemonic(mn):
    private_key = mnemonic.to_private_key(mn)
    return private_key


# helper function that convert a mnemonic passphrase into a public key = address
def get_address_from_private_key(sk):
    address = account.address_from_private_key(sk)
    return address


def get_algod_client():
    # set the address and token from the environment variables, otherwise use the sandbox values
    algod_address = os.environ.get("ALGOD_ADDRESS","http://localhost:4001")
    algod_token = os.environ.get("ALGOD_TOKEN","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    headers = {
        "X-API-Key": algod_token,
    }
    algod_client = algod.AlgodClient(algod_token, algod_address, headers)
    return algod_client


def create_default_nft(client, private_key, address, asset_name, asset_unit_name, asset_url):
    # create a new asset
    # note that the manager, reserve, freeze, and clawback
    # are all empty for the nft as specified in documentation
    # https://developer.algorand.org/docs/get-started/tokenization/nft/

    f = open('../../assets/nft_metadata.json')
    json_metadata = json.load(f)
    f.close()

    asset_metadata_hash = sha256(json.dumps(json_metadata).encode('utf-8')).digest()

    print("Creating transaction...")
    txn = AssetConfigTxn(
        sender=address,
        sp=client.suggested_params(),
        total=1,
        decimals=0,
        default_frozen=False,
        unit_name=asset_unit_name,
        asset_name=asset_name,
        url=asset_url,
        metadata_hash=asset_metadata_hash,
        note=b"NFT creation",
        strict_empty_address_check=False,
        manager="",
        reserve="",
        freeze="",
        clawback="",
    )

    # sign the transaction
    print("Signing transaction...")
    signed_txn = txn.sign(private_key)

    # send the transaction to the network and retrieve the txid
    print("Sending transaction...")
    txid = client.send_transaction(signed_txn)

    # wait for confirmation
    print("Waiting for confirmation...")
    wait_for_confirmation(algod_client=client, txid=txid)

    # retrieve the asset id of the newly created asset
    ptx = client.pending_transaction_info(txid)
    asset_id = ptx["asset-index"]
    print("Created NFT with asset ID: {}".format(asset_id))

    return asset_id


# Print testnet accounts balance
if __name__ == "__main__":
    put_testnet_account_into_sandbox_and_fund()